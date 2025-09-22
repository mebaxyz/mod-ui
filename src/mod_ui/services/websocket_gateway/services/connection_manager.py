"""
Connection Manager for WebSocket Gateway

Manages all WebSocket client connections, subscriptions, and message routing.
"""

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from typing import Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from src.mod_ui.services.websocket_gateway.models import (
    ClientConnection,
    EventSubscription,
    GatewayMessage,
    GatewayStats,
)
from src.mod_ui.services.websocket_gateway.utils import EventType, MessageType, config

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message routing"""

    def __init__(self):
        # Active connections
        self.connections: Dict[str, ClientConnection] = {}

        # Subscription mappings
        self.subscriptions: Dict[EventType, Set[str]] = defaultdict(set)
        self.client_subscriptions: Dict[str, Set[EventType]] = defaultdict(set)

        # Message queues for offline clients
        self.message_queues: Dict[str, List[dict]] = defaultdict(list)

        # Connection limits and rate limiting
        self.connection_count = 0
        self.message_counts: Dict[str, int] = defaultdict(int)
        self.last_cleanup = time.time()

        # Heartbeat tracking
        self.heartbeat_task: Optional[asyncio.Task] = None

    async def connect(
        self, websocket: WebSocket, client_id: Optional[str] = None
    ) -> str:
        """Accept a new WebSocket connection"""

        # Check connection limits
        if self.connection_count >= config.MAX_CONNECTIONS:
            logger.warning(f"Connection limit reached: {config.MAX_CONNECTIONS}")
            await websocket.close(code=1008, reason="Connection limit reached")
            raise ConnectionError("Connection limit reached")

        # Generate client ID if not provided
        if not client_id:
            client_id = str(uuid.uuid4())

        # Accept the WebSocket connection
        await websocket.accept()

        # Create client connection record
        connection = ClientConnection(
            client_id=client_id,
            websocket=websocket,
            connected_at=time.time(),
            last_seen=time.time(),
            subscriptions=[],
            is_active=True,
            user_agent=websocket.headers.get("user-agent", "unknown"),
            ip_address=websocket.client.host if websocket.client else "unknown",
        )

        # Store connection
        self.connections[client_id] = connection
        self.connection_count += 1

        logger.info(f"Client {client_id} connected from {connection.ip_address}")

        # Send welcome message
        await self._send_welcome(client_id)

        # Apply default subscriptions for backward compatibility
        await self._apply_default_subscriptions(client_id)

        # Start heartbeat if this is the first connection
        if self.connection_count == 1 and not self.heartbeat_task:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        return client_id

    async def disconnect(
        self, client_id: str, code: int = 1000, reason: str = "Normal closure"
    ):
        """Disconnect a client"""

        if client_id not in self.connections:
            return

        connection = self.connections[client_id]

        # Close WebSocket if still open
        try:
            if connection.websocket.client_state.name in ["CONNECTED", "CONNECTING"]:
                await connection.websocket.close(code=code, reason=reason)
        except Exception as e:
            logger.warning(f"Error closing WebSocket for {client_id}: {e}")

        # Remove subscriptions
        await self._remove_all_subscriptions(client_id)

        # Remove connection
        del self.connections[client_id]
        self.connection_count -= 1

        # Clear message queue and counts
        if client_id in self.message_queues:
            del self.message_queues[client_id]
        if client_id in self.message_counts:
            del self.message_counts[client_id]

        logger.info(f"Client {client_id} disconnected: {reason}")

        # Stop heartbeat if no connections remain
        if self.connection_count == 0 and self.heartbeat_task:
            self.heartbeat_task.cancel()
            self.heartbeat_task = None

    async def subscribe(self, client_id: str, event_types: List[EventType]) -> bool:
        """Subscribe client to event types"""

        if client_id not in self.connections:
            return False

        connection = self.connections[client_id]

        for event_type in event_types:
            # Add to subscription mappings
            self.subscriptions[event_type].add(client_id)
            self.client_subscriptions[client_id].add(event_type)

            # Update connection record
            subscription = EventSubscription(
                event_type=event_type, subscribed_at=time.time()
            )
            connection.subscriptions.append(subscription)

        logger.debug(f"Client {client_id} subscribed to {len(event_types)} events")

        # Send confirmation
        await self._send_to_client(
            client_id,
            {
                "type": MessageType.SUBSCRIPTION_CONFIRMED,
                "event_types": [str(et) for et in event_types],
                "timestamp": time.time(),
            },
        )

        return True

    async def unsubscribe(self, client_id: str, event_types: List[EventType]) -> bool:
        """Unsubscribe client from event types"""

        if client_id not in self.connections:
            return False

        connection = self.connections[client_id]

        for event_type in event_types:
            # Remove from subscription mappings
            self.subscriptions[event_type].discard(client_id)
            self.client_subscriptions[client_id].discard(event_type)

            # Update connection record
            connection.subscriptions = [
                sub for sub in connection.subscriptions if sub.event_type != event_type
            ]

        logger.debug(f"Client {client_id} unsubscribed from {len(event_types)} events")

        # Send confirmation
        await self._send_to_client(
            client_id,
            {
                "type": MessageType.UNSUBSCRIPTION_CONFIRMED,
                "event_types": [str(et) for et in event_types],
                "timestamp": time.time(),
            },
        )

        return True

    async def broadcast_event(
        self,
        event_type: EventType,
        data: dict,
        exclude_clients: Optional[Set[str]] = None,
    ):
        """Broadcast event to all subscribed clients"""

        # Handle ALL_EVENTS subscription
        subscribers = set(self.subscriptions.get(event_type, set()))
        if EventType.ALL_EVENTS in self.subscriptions:
            subscribers.update(self.subscriptions[EventType.ALL_EVENTS])

        # Exclude specific clients if requested
        if exclude_clients:
            subscribers -= exclude_clients

        if not subscribers:
            return

        # Prepare message
        message = {
            "type": MessageType.EVENT,
            "event_type": str(event_type),
            "data": data,
            "timestamp": time.time(),
        }

        # Send to all subscribers
        tasks = []
        for client_id in subscribers:
            tasks.append(self._send_to_client(client_id, message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.debug(f"Broadcasted {event_type} to {len(subscribers)} clients")

    async def send_to_client(self, client_id: str, message: any) -> bool:
        """Send a message to a specific client (supports both JSON dict and plain text)"""
        if client_id not in self.connections:
            logger.warning(f"Attempted to send to non-existent client: {client_id}")
            return False

        connection = self.connections[client_id]
        try:
            if isinstance(message, dict):
                await connection.websocket.send_text(json.dumps(message))
            else:
                # Support plain text messages for legacy compatibility
                await connection.websocket.send_text(str(message))

            connection.last_activity = time.time()
            connection.messages_sent += 1
            self.stats.total_messages_sent += 1
            return True

        except Exception as e:
            logger.error(f"Failed to send message to client {client_id}: {e}")
            await self.remove_connection(client_id)
            return False

    async def handle_client_message(self, client_id: str, message: dict):
        """Handle incoming message from client"""

        if client_id not in self.connections:
            return

        # Update last seen
        self.connections[client_id].last_seen = time.time()

        # Rate limiting check
        if not self._check_rate_limit(client_id):
            await self._send_to_client(
                client_id,
                {
                    "type": MessageType.ERROR,
                    "error": "Rate limit exceeded",
                    "timestamp": time.time(),
                },
            )
            return

        message_type = message.get("type")

        if message_type == MessageType.SUBSCRIBE:
            event_types = message.get("event_types", [])
            try:
                parsed_types = [EventType(et) for et in event_types]
                await self.subscribe(client_id, parsed_types)
            except ValueError as e:
                await self._send_to_client(
                    client_id,
                    {
                        "type": MessageType.ERROR,
                        "error": f"Invalid event type: {e}",
                        "timestamp": time.time(),
                    },
                )

        elif message_type == MessageType.UNSUBSCRIBE:
            event_types = message.get("event_types", [])
            try:
                parsed_types = [EventType(et) for et in event_types]
                await self.unsubscribe(client_id, parsed_types)
            except ValueError as e:
                await self._send_to_client(
                    client_id,
                    {
                        "type": MessageType.ERROR,
                        "error": f"Invalid event type: {e}",
                        "timestamp": time.time(),
                    },
                )

        elif message_type == MessageType.PING:
            await self._send_to_client(
                client_id, {"type": MessageType.PONG, "timestamp": time.time()}
            )

        elif message_type == MessageType.REQUEST_STATUS:
            await self._send_status(client_id)

        else:
            logger.warning(f"Unknown message type from {client_id}: {message_type}")

    def get_stats(self) -> GatewayStats:
        """Get gateway statistics"""

        total_subscriptions = sum(
            len(subs) for subs in self.client_subscriptions.values()
        )
        event_type_counts = {
            str(event_type): len(clients)
            for event_type, clients in self.subscriptions.items()
            if clients
        }

        return GatewayStats(
            connected_clients=self.connection_count,
            total_subscriptions=total_subscriptions,
            event_type_subscriptions=event_type_counts,
            uptime=time.time()
            - (self.last_cleanup if hasattr(self, "start_time") else time.time()),
            messages_sent=sum(self.message_counts.values()),
            active_connections=[
                conn.client_id for conn in self.connections.values() if conn.is_active
            ],
        )

    def get_client_info(self, client_id: str) -> Optional[ClientConnection]:
        """Get information about a specific client"""
        return self.connections.get(client_id)

    def get_all_clients(self) -> List[ClientConnection]:
        """Get information about all connected clients"""
        return list(self.connections.values())

    async def cleanup_inactive_connections(self):
        """Remove connections that haven't been active recently"""
        current_time = time.time()
        inactive_threshold = config.MAX_INACTIVE_TIME

        inactive_clients = [
            client_id
            for client_id, conn in self.connections.items()
            if current_time - conn.last_activity > inactive_threshold
        ]

        for client_id in inactive_clients:
            logger.info(f"Removing inactive client: {client_id}")
            await self.remove_connection(client_id)

        if inactive_clients:
            logger.info(f"Cleaned up {len(inactive_clients)} inactive connections")

    # Legacy message support methods (for compatibility with existing frontend)

    async def broadcast_to_all(self, message: any) -> int:
        """Broadcast a message to all connected clients (supports both JSON dict and plain text)"""
        sent_count = 0
        failed_clients = []

        for client_id in list(self.connections.keys()):
            success = await self.send_to_client(client_id, message)
            if success:
                sent_count += 1
            else:
                failed_clients.append(client_id)

        # Clean up failed connections
        for client_id in failed_clients:
            await self.remove_connection(client_id)

        logger.debug(f"Broadcast message to {sent_count} clients")
        return sent_count

    async def send_stats_message(self, cpu_load: float, xruns: int) -> int:
        """Send stats message in legacy format: 'stats CPU_LOAD XRUNS'"""
        message = f"stats {cpu_load:.1f} {xruns}"
        return await self.broadcast_to_all(message)

    async def send_sys_stats_message(
        self, mem_load: float, cpu_freq: str, cpu_temp: str
    ) -> int:
        """Send system stats message in legacy format: 'sys_stats MEM_LOAD CPU_FREQ CPU_TEMP'"""
        message = f"sys_stats {mem_load:.1f} {cpu_freq} {cpu_temp}"
        return await self.broadcast_to_all(message)

    async def send_ping_message(self) -> int:
        """Send ping message to all clients"""
        return await self.broadcast_to_all("ping")

    async def send_data_ready_message(self, counter: int) -> int:
        """Send data_ready message in legacy format: 'data_ready COUNTER'"""
        message = f"data_ready {counter}"
        return await self.broadcast_to_all(message)

    async def send_loading_start_message(
        self, empty: bool = True, modified: bool = False
    ) -> int:
        """Send loading_start message to all connected clients."""
        message = f"loading_start {int(empty)} {int(modified)}"
        result = await self.broadcast_to_all(message)
        logger.info(
            f"Sent loading_start to {result} clients: empty={empty}, modified={modified}"
        )
        return result

    async def send_loading_end_message(self, snapshot_id: int = 0) -> int:
        """Send loading_end message to all connected clients."""
        message = f"loading_end {snapshot_id}"
        result = await self.broadcast_to_all(message)
        logger.info(
            f"Sent loading_end to {result} clients: snapshot_id={snapshot_id}"
        )
        return result

    async def send_transport_message(
        self,
        rolling: bool = False,
        bpb: float = 4.0,
        bpm: float = 120.0,
        sync: str = "none",
    ) -> int:
        """Send transport message to all connected clients."""
        message = f"transport {int(rolling)} {bpb} {bpm} {sync}"
        result = await self.broadcast_to_all(message)
        logger.info(
            f"Sent transport to {result} clients: rolling={rolling}, bpb={bpb}, bpm={bpm}, sync={sync}"
        )
        return result

    async def send_truebypass_message(
        self, left: bool = False, right: bool = False
    ) -> int:
        """Send truebypass message to all connected clients."""
        message = f"truebypass {int(left)} {int(right)}"
        result = await self.broadcast_to_all(message)
        logger.info(
            f"Sent truebypass to {result} clients: left={left}, right={right}"
        )
        return result

    async def send_size_message(self, width: int = 0, height: int = 0) -> int:
        """Send size message to all connected clients."""
        message = f"size {width} {height}"
        result = await self.broadcast_to_all(message)
        logger.info(
            f"Sent size to {result} clients: width={width}, height={height}"
        )
        return result

    # Private methods

    async def _send_welcome(self, client_id: str):
        """Send welcome message to new client"""

        connection = self.connections.get(client_id)
        if not connection:
            return

        welcome_msg = {
            "type": MessageType.WELCOME,
            "client_id": client_id,
            "server_time": time.time(),
            "supported_events": [str(et) for et in EventType],
            "default_subscriptions": config.DEFAULT_SUBSCRIPTIONS,
            "heartbeat_interval": config.WEBSOCKET_HEARTBEAT_INTERVAL,
        }

        await self._send_to_client(client_id, welcome_msg)

    async def _apply_default_subscriptions(self, client_id: str):
        """Apply default subscriptions for backward compatibility"""

        if not config.DEFAULT_SUBSCRIPTIONS:
            return

        try:
            event_types = [EventType(et) for et in config.DEFAULT_SUBSCRIPTIONS]
            await self.subscribe(client_id, event_types)
        except ValueError as e:
            logger.warning(f"Invalid default subscription: {e}")

    async def _send_to_client(self, client_id: str, message: dict) -> bool:
        """Send message to specific client"""

        if client_id not in self.connections:
            # Queue message for offline client
            self.message_queues[client_id].append(message)
            if len(self.message_queues[client_id]) > config.MESSAGE_QUEUE_SIZE:
                self.message_queues[client_id].pop(0)  # Remove oldest
            return False

        connection = self.connections[client_id]

        try:
            # Send message
            await connection.websocket.send_text(json.dumps(message))

            # Update counters
            self.message_counts[client_id] += 1

            return True

        except WebSocketDisconnect:
            # Client disconnected
            await self.disconnect(client_id, code=1001, reason="Client disconnected")
            return False

        except Exception as e:
            logger.error(f"Error sending message to {client_id}: {e}")
            await self.disconnect(client_id, code=1011, reason="Send error")
            return False

    async def _send_status(self, client_id: str):
        """Send status information to client"""

        connection = self.connections.get(client_id)
        if not connection:
            return

        status_msg = {
            "type": MessageType.STATUS,
            "client_id": client_id,
            "connected_at": connection.connected_at,
            "subscriptions": [str(sub.event_type) for sub in connection.subscriptions],
            "messages_received": self.message_counts.get(client_id, 0),
            "timestamp": time.time(),
        }

        await self._send_to_client(client_id, status_msg)

    async def _remove_all_subscriptions(self, client_id: str):
        """Remove all subscriptions for a client"""

        client_events = self.client_subscriptions.get(client_id, set())

        for event_type in client_events:
            self.subscriptions[event_type].discard(client_id)

        if client_id in self.client_subscriptions:
            del self.client_subscriptions[client_id]

    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client is within rate limits"""

        current_count = self.message_counts.get(client_id, 0)
        return current_count < config.RATE_LIMIT_MESSAGES_PER_MINUTE

    async def _heartbeat_loop(self):
        """Send periodic heartbeat to all clients"""

        try:
            while True:
                await asyncio.sleep(config.WEBSOCKET_HEARTBEAT_INTERVAL)

                # Send ping to all clients
                tasks = []
                for client_id in list(self.connections.keys()):
                    tasks.append(
                        self._send_to_client(
                            client_id,
                            {"type": MessageType.PING, "timestamp": time.time()},
                        )
                    )

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                # Cleanup inactive connections
                await self.cleanup_inactive_connections()

        except asyncio.CancelledError:
            logger.info("Heartbeat loop cancelled")
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}")
