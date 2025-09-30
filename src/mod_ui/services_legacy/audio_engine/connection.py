"""
Audio Engine Service

This service handles direct communication with the mod-host audio engine process.
It provides an async interface for sending commands and receiving responses from mod-host.

The service maintains two socket connections:
- Write socket: For sending commands to mod-host
- Read socket: For receiving responses and real-time updates

This abstracts the low-level socket communication from higher-level services.
"""

import asyncio
import logging
import socket
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AudioEngineCommand(BaseModel):
    """Command to be sent to mod-host audio engine"""

    command: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    callback_id: Optional[str] = None
    datatype: str = "int"  # 'int', 'string', 'float'
    modifies_pedalboard: bool = (
        False  # Whether this command modifies the pedalboard state
    )


class AudioEngineResponse(BaseModel):
    """Response received from mod-host audio engine"""

    status: str  # 'success', 'error', 'timeout'
    data: Optional[str] = None
    error: Optional[str] = None
    callback_id: Optional[str] = None


class ConnectionStatus(str, Enum):
    """Audio engine connection status"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    CRASHED = "crashed"


class ModHostConnectionManager:
    """Manages socket connections to mod-host process"""

    def __init__(
        self, host: str = "localhost", write_port: int = 5555, read_port: int = 5556
    ):
        self.host = host
        self.write_port = write_port
        self.read_port = read_port

        self.write_socket: Optional[socket.socket] = None
        self.read_socket: Optional[socket.socket] = None

        self.status = ConnectionStatus.DISCONNECTED
        self.command_queue: asyncio.Queue = asyncio.Queue()
        self.response_callbacks: Dict[str, Callable] = {}
        self.message_handlers: List[Callable] = []

        self._write_task: Optional[asyncio.Task] = None
        self._read_task: Optional[asyncio.Task] = None
        self._processing = False

    async def connect(self) -> bool:
        """Establish connections to mod-host"""
        if self.status == ConnectionStatus.CONNECTED:
            return True

        try:
            self.status = ConnectionStatus.CONNECTING

            # Create write socket for sending commands
            self.write_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.write_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            await asyncio.get_event_loop().run_in_executor(
                None, self.write_socket.connect, (self.host, self.write_port)
            )

            # Create read socket for receiving responses
            self.read_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.read_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            await asyncio.get_event_loop().run_in_executor(
                None, self.read_socket.connect, (self.host, self.read_port)
            )

            self.status = ConnectionStatus.CONNECTED

            # Start processing tasks
            self._write_task = asyncio.create_task(self._process_write_queue())
            self._read_task = asyncio.create_task(self._process_read_queue())

            logger.info(
                "Successfully connected to mod-host at %s:%d/%d",
                self.host,
                self.write_port,
                self.read_port,
            )
            return True

        except Exception as e:
            logger.error("Failed to connect to mod-host: %s", e)
            self.status = ConnectionStatus.CRASHED
            await self._cleanup_connections()
            return False

    async def disconnect(self):
        """Close connections to mod-host"""
        logger.info("Disconnecting from mod-host")
        self.status = ConnectionStatus.DISCONNECTED

        # Cancel processing tasks
        if self._write_task and not self._write_task.done():
            self._write_task.cancel()
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()

        await self._cleanup_connections()

    async def _cleanup_connections(self):
        """Clean up socket connections"""
        if self.write_socket:
            try:
                self.write_socket.close()
            except Exception:
                pass
            self.write_socket = None

        if self.read_socket:
            try:
                self.read_socket.close()
            except Exception:
                pass
            self.read_socket = None

    async def send_command(
        self, command: AudioEngineCommand, timeout: float = 5.0
    ) -> AudioEngineResponse:
        """Send command to mod-host and wait for response"""
        if self.status != ConnectionStatus.CONNECTED:
            return AudioEngineResponse(
                status="error",
                error="Not connected to mod-host",
                callback_id=command.callback_id,
            )

        # Add command to queue
        await self.command_queue.put(command)

        # Wait for response if callback_id is provided
        if command.callback_id:
            future = asyncio.Future()
            self.response_callbacks[command.callback_id] = future.set_result

            try:
                response = await asyncio.wait_for(future, timeout=timeout)
                return response
            except asyncio.TimeoutError:
                self.response_callbacks.pop(command.callback_id, None)
                return AudioEngineResponse(
                    status="timeout",
                    error=f"Command timeout after {timeout}s",
                    callback_id=command.callback_id,
                )
        else:
            # Fire-and-forget command
            return AudioEngineResponse(status="queued", callback_id=command.callback_id)

    async def _process_write_queue(self):
        """Process commands from the write queue"""
        while self.status == ConnectionStatus.CONNECTED:
            try:
                command = await self.command_queue.get()
                await self._send_command_to_socket(command)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error processing write queue: %s", e)
                self.status = ConnectionStatus.CRASHED

    async def _send_command_to_socket(self, command: AudioEngineCommand):
        """Send a single command to the write socket"""
        if not self.write_socket:
            return

        try:
            # Format command for mod-host protocol
            cmd_string = self._format_command(command)
            message = f"{cmd_string}\0".encode("utf-8")

            await asyncio.get_event_loop().run_in_executor(
                None, self.write_socket.send, message
            )

            logger.debug("Sent command to mod-host: %s", cmd_string)

        except Exception as e:
            logger.error("Failed to send command: %s", e)
            self.status = ConnectionStatus.CRASHED

    async def _process_read_queue(self):
        """Process responses from the read socket"""
        buffer = b""

        while self.status == ConnectionStatus.CONNECTED:
            try:
                if not self.read_socket:
                    break

                # Read data from socket
                data = await asyncio.get_event_loop().run_in_executor(
                    None, self.read_socket.recv, 4096
                )

                if not data:
                    logger.warning("mod-host connection closed")
                    self.status = ConnectionStatus.CRASHED
                    break

                buffer += data

                # Process complete messages (terminated by \0)
                while b"\0" in buffer:
                    message, buffer = buffer.split(b"\0", 1)
                    await self._process_response_message(message.decode("utf-8"))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error processing read queue: %s", e)
                self.status = ConnectionStatus.CRASHED

    async def _process_response_message(self, message: str):
        """Process a response message from mod-host"""
        logger.debug("Received from mod-host: %s", message)

        # Handle different types of messages
        if message.startswith("resp "):
            # Standard response
            response_data = message[5:].strip()
            # TODO: Match with pending callback based on command ordering

        elif " " in message:
            # Real-time message (param_set, transport, etc.)
            cmd, data = message.split(" ", 1)
            await self._handle_realtime_message(cmd, data)
        else:
            logger.warning("Unknown message format: %s", message)

    async def _handle_realtime_message(self, cmd: str, data: str):
        """Handle real-time messages from mod-host"""
        # Notify registered handlers about real-time messages
        for handler in self.message_handlers:
            try:
                await handler(cmd, data)
            except Exception as e:
                logger.error("Error in message handler: %s", e)

    def _format_command(self, command: AudioEngineCommand) -> str:
        """Format command for mod-host protocol"""
        parts = [command.command]

        # Add parameters in the expected order
        for key in sorted(command.parameters.keys()):
            value = command.parameters[key]
            parts.append(str(value))

        return " ".join(parts)

    def add_message_handler(self, handler: Callable):
        """Add a handler for real-time messages"""
        self.message_handlers.append(handler)

    def remove_message_handler(self, handler: Callable):
        """Remove a message handler"""
        if handler in self.message_handlers:
            self.message_handlers.remove(handler)
