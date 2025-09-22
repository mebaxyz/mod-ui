"""
WebSocket Hub Service for Session System

Manages WebSocket connections, client subscriptions, and real-time message
broadcasting. Provides modern FastAPI WebSocket support with event filtering.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

from ..models.events import EventType, SessionEvent, create_client_event
from ..utils.event_bus import EventBus


class WebSocketClient:
    """Represents a connected WebSocket client"""

    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.connected_at = datetime.now()
        self.last_activity = datetime.now()
        self.subscriptions: Set[EventType] = set()
        self.user_agent: Optional[str] = None
        self.ip_address: Optional[str] = None

    def update_activity(self) -> None:
        """Update last activity timestamp"""
        self.last_activity = datetime.now()

    def add_subscription(self, event_type: EventType) -> None:
        """Add event type subscription"""
        self.subscriptions.add(event_type)

    def remove_subscription(self, event_type: EventType) -> None:
        """Remove event type subscription"""
        self.subscriptions.discard(event_type)

    def is_subscribed_to(self, event_type: EventType) -> bool:
        """Check if client is subscribed to event type"""
        return event_type in self.subscriptions

    async def send_message(self, message) -> bool:
        """Send message to client (JSON dict or plain text string). Returns True if successful."""
        try:
            if isinstance(message, str):
                await self.websocket.send_text(message)
            else:
                await self.websocket.send_text(json.dumps(message))
            self.update_activity()
            return True
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert client info to dictionary"""
        return {
            "client_id": self.client_id,
            "connected_at": self.connected_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "subscriptions": [event_type.value for event_type in self.subscriptions],
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
        }


class WebSocketHubService:
    """
    Modern WebSocket management service for real-time communication

    Features:
    - Client connection management
    - Event-based message broadcasting
    - Subscription-based message filtering
    - Connection health monitoring
    - Message history and replay
    """

    def __init__(self, event_bus: EventBus):
        self.logger = logging.getLogger(__name__)
        self.event_bus = event_bus
        self.clients: Dict[str, WebSocketClient] = {}
        self.message_history: List[Dict[str, Any]] = []
        self.max_history = 100
        self._event_subscription_id: Optional[str] = None

        self.logger.info("WebSocketHubService initialized")

    async def initialize(self) -> None:
        """Initialize the WebSocket hub service"""
        try:
            # Subscribe to all events from the event bus
            self._event_subscription_id = await self.event_bus.subscribe_all(
                self._handle_event
            )

            self.logger.info("WebSocket Hub Service initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize WebSocket Hub Service: {e}")
            raise

    async def connect_client(self, websocket: WebSocket) -> str:
        """Register a new WebSocket connection (websocket should already be accepted)"""
        try:
            # Generate unique client ID
            client_id = str(uuid.uuid4())

            # Create client object
            client = WebSocketClient(websocket, client_id)

            # Extract client info from headers if available
            headers = dict(websocket.headers)
            client.user_agent = headers.get("user-agent")
            client.ip_address = getattr(websocket.client, "host", None)

            # Store client
            self.clients[client_id] = client

            # Publish client connected event
            if self.event_bus:
                event = create_client_event(
                    EventType.CLIENT_CONNECTED,
                    "websocket_hub",
                    client_id,
                    user_agent=client.user_agent,
                    ip_address=client.ip_address,
                )
                await self.event_bus.publish(event)

            self.logger.info(f"Client connected: {client_id} from {client.ip_address}")

            # Send initial data_ready message to initialize frontend
            await client.send_message("data_ready 1")

            return client_id

        except Exception as e:
            self.logger.error(f"Failed to connect client: {e}")
            raise

    async def disconnect_client(self, client_id: str) -> None:
        """Handle client disconnection"""
        try:
            if client_id in self.clients:
                client = self.clients[client_id]

                # Publish client disconnected event
                if self.event_bus:
                    event = create_client_event(
                        EventType.CLIENT_DISCONNECTED, "websocket_hub", client_id
                    )
                    await self.event_bus.publish(event)

                # Remove client
                del self.clients[client_id]

                self.logger.info(f"Client disconnected: {client_id}")

        except Exception as e:
            self.logger.error(f"Error disconnecting client {client_id}: {e}")

    async def handle_client_message(self, client_id: str, message_data: str) -> None:
        """Handle incoming message from client (text or JSON)"""
        try:
            if client_id not in self.clients:
                self.logger.warning(f"Message from unknown client: {client_id}")
                return

            client = self.clients[client_id]
            client.update_activity()

            # Handle legacy plain-text messages (for backwards compatibility)
            if isinstance(message_data, str):
                await self._handle_plain_text_message(client, message_data)
                return

            # Handle JSON messages
            message_type = message_data.get("type")

            if message_type == "subscribe":
                await self._handle_subscription_message(client, message_data)
            elif message_type == "unsubscribe":
                await self._handle_unsubscription_message(client, message_data)
            elif message_type == "ping":
                await self._handle_ping_message(client, message_data)
            elif message_type == "request_history":
                await self._handle_history_request(client, message_data)
            else:
                self.logger.warning(
                    f"Unknown message type from {client_id}: {message_type}"
                )
                await client.send_message(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        except Exception as e:
            self.logger.error(f"Error handling message from {client_id}: {e}")

    async def broadcast_to_all(self, message) -> int:
        """Broadcast message to all connected clients (JSON dict or plain text string)"""
        try:
            # Add to message history (only if it's a dict)
            if isinstance(message, dict):
                self._add_to_history(message)

            successful_sends = 0
            failed_clients = []

            for client_id, client in self.clients.items():
                success = await client.send_message(message)
                if success:
                    successful_sends += 1
                else:
                    failed_clients.append(client_id)

            # Clean up failed connections
            for client_id in failed_clients:
                await self.disconnect_client(client_id)

            self.logger.debug(
                f"Broadcast to {successful_sends} clients, {len(failed_clients)} failed"
            )
            return successful_sends

        except Exception as e:
            self.logger.error(f"Error broadcasting message: {e}")
            return 0

    async def broadcast_to_subscribed(
        self, event_type: EventType, message: Dict[str, Any]
    ) -> int:
        """Broadcast message to clients subscribed to specific event type"""
        try:
            # Add to message history
            self._add_to_history(message)

            successful_sends = 0
            failed_clients = []

            for client_id, client in self.clients.items():
                if client.is_subscribed_to(event_type):
                    success = await client.send_message(message)
                    if success:
                        successful_sends += 1
                    else:
                        failed_clients.append(client_id)

            # Clean up failed connections
            for client_id in failed_clients:
                await self.disconnect_client(client_id)

            self.logger.debug(
                f"Broadcast {event_type} to {successful_sends} subscribers, {len(failed_clients)} failed"
            )
            return successful_sends

        except Exception as e:
            self.logger.error(f"Error broadcasting to subscribers: {e}")
            return 0

    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Send message to specific client"""
        try:
            if client_id not in self.clients:
                self.logger.warning(f"Attempted to send to unknown client: {client_id}")
                return False

            client = self.clients[client_id]
            success = await client.send_message(message)

            if not success:
                await self.disconnect_client(client_id)

            return success

        except Exception as e:
            self.logger.error(f"Error sending to client {client_id}: {e}")
            return False

    async def get_client_count(self) -> int:
        """Get number of connected clients"""
        return len(self.clients)

    async def get_client_info(self) -> List[Dict[str, Any]]:
        """Get information about all connected clients"""
        return [client.to_dict() for client in self.clients.values()]

    async def cleanup_inactive_clients(self, max_inactive_seconds: int = 300) -> int:
        """Remove clients that have been inactive for too long"""
        try:
            current_time = datetime.now()
            inactive_clients = []

            for client_id, client in self.clients.items():
                inactive_seconds = (current_time - client.last_activity).total_seconds()
                if inactive_seconds > max_inactive_seconds:
                    inactive_clients.append(client_id)

            for client_id in inactive_clients:
                await self.disconnect_client(client_id)
                self.logger.info(f"Removed inactive client: {client_id}")

            return len(inactive_clients)

        except Exception as e:
            self.logger.error(f"Error cleaning up inactive clients: {e}")
            return 0

    # Event handling

    async def _handle_event(self, event: SessionEvent) -> None:
        """Handle events from the event bus"""
        try:
            # Convert event to WebSocket message
            message = {
                "type": "event",
                "event": {
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "source_service": event.source_service,
                    "session_id": event.session_id,
                    "timestamp": event.timestamp.isoformat(),
                    "priority": event.priority.value,
                    "data": event.data,
                },
            }

            # Check if event should be sent to specific clients
            if event.target_clients:
                for client_id in event.target_clients:
                    await self.send_to_client(client_id, message)
            else:
                # Broadcast to subscribed clients
                await self.broadcast_to_subscribed(event.event_type, message)

        except Exception as e:
            self.logger.error(f"Error handling event {event.event_type}: {e}")

    # Private message handlers

    async def _handle_subscription_message(
        self, client: WebSocketClient, message_data: Dict[str, Any]
    ) -> None:
        """Handle subscription request from client"""
        try:
            event_types = message_data.get("event_types", [])

            for event_type_str in event_types:
                try:
                    event_type = EventType(event_type_str)
                    client.add_subscription(event_type)
                except ValueError:
                    self.logger.warning(
                        f"Invalid event type in subscription: {event_type_str}"
                    )

            # Send confirmation
            await client.send_message(
                {
                    "type": "subscription_confirmed",
                    "subscriptions": [et.value for et in client.subscriptions],
                    "timestamp": datetime.now().isoformat(),
                }
            )

            self.logger.debug(
                f"Client {client.client_id} subscribed to {len(event_types)} event types"
            )

        except Exception as e:
            self.logger.error(f"Error handling subscription: {e}")

    async def _handle_unsubscription_message(
        self, client: WebSocketClient, message_data: Dict[str, Any]
    ) -> None:
        """Handle unsubscription request from client"""
        try:
            event_types = message_data.get("event_types", [])

            for event_type_str in event_types:
                try:
                    event_type = EventType(event_type_str)
                    client.remove_subscription(event_type)
                except ValueError:
                    self.logger.warning(
                        f"Invalid event type in unsubscription: {event_type_str}"
                    )

            # Send confirmation
            await client.send_message(
                {
                    "type": "unsubscription_confirmed",
                    "subscriptions": [et.value for et in client.subscriptions],
                    "timestamp": datetime.now().isoformat(),
                }
            )

            self.logger.debug(
                f"Client {client.client_id} unsubscribed from {len(event_types)} event types"
            )

        except Exception as e:
            self.logger.error(f"Error handling unsubscription: {e}")

    async def _handle_ping_message(
        self, client: WebSocketClient, message_data: Dict[str, Any]
    ) -> None:
        """Handle ping message from client"""
        await client.send_message(
            {
                "type": "pong",
                "timestamp": datetime.now().isoformat(),
                "client_id": client.client_id,
            }
        )

    async def _handle_history_request(
        self, client: WebSocketClient, message_data: Dict[str, Any]
    ) -> None:
        """Handle request for message history"""
        try:
            limit = min(message_data.get("limit", 10), self.max_history)

            history = self.message_history[-limit:] if self.message_history else []

            await client.send_message(
                {
                    "type": "history_response",
                    "messages": history,
                    "count": len(history),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        except Exception as e:
            self.logger.error(f"Error handling history request: {e}")

    def _add_to_history(self, message: Dict[str, Any]) -> None:
        """Add message to history"""
        try:
            # Add timestamp if not present
            if "timestamp" not in message:
                message["timestamp"] = datetime.now().isoformat()

            self.message_history.append(message)

            # Trim history if too long
            if len(self.message_history) > self.max_history:
                self.message_history.pop(0)

        except Exception as e:
            self.logger.error(f"Error adding message to history: {e}")

    # Legacy compatibility methods

    async def _handle_plain_text_message(
        self, client: WebSocketClient, message: str
    ) -> None:
        """Handle plain text messages from client (legacy format)"""
        try:
            message = message.strip()
            if not message:
                return

            # Parse command and arguments
            parts = message.split(" ", 1)
            cmd = parts[0]
            data = parts[1] if len(parts) > 1 else ""

            self.logger.debug(f"Legacy message from {client.client_id}: {cmd} {data}")

            # Handle legacy commands
            if cmd == "pong":
                # Client responded to ping - just update activity (already done)
                pass
            elif cmd == "data_ready":
                # Data ready acknowledgment from client
                await self._handle_data_ready_ack(client, data)
            else:
                self.logger.warning(
                    f"Unknown legacy command from {client.client_id}: {cmd}"
                )

        except Exception as e:
            self.logger.error(
                f"Error handling plain text message from {client.client_id}: {e}"
            )

    async def _handle_data_ready_ack(
        self, client: WebSocketClient, counter: str
    ) -> None:
        """Handle data_ready acknowledgment from client"""
        self.logger.debug(
            f"Client {client.client_id} acknowledged data_ready {counter}"
        )
        # TODO: Implement data synchronization logic if needed

    async def broadcast_legacy_message(self, message: str) -> int:
        """Broadcast a legacy plain-text message to all clients"""
        return await self.broadcast_to_all(message)

    async def send_stats_message(self, cpu_load: float, xruns: int) -> int:
        """Send stats message in legacy format: 'stats CPU_LOAD XRUNS'"""
        message = f"stats {cpu_load:.1f} {xruns}"
        return await self.broadcast_legacy_message(message)

    async def send_sys_stats_message(
        self, mem_load: float, cpu_freq: str, cpu_temp: str
    ) -> int:
        """Send system stats message in legacy format: 'sys_stats MEM_LOAD CPU_FREQ CPU_TEMP'"""
        message = f"sys_stats {mem_load:.1f} {cpu_freq} {cpu_temp}"
        return await self.broadcast_legacy_message(message)

    async def send_ping_message(self) -> int:
        """Send ping message to all clients"""
        return await self.broadcast_legacy_message("ping")

    async def send_data_ready_message(self, counter: int) -> int:
        """Send data_ready message in legacy format: 'data_ready COUNTER'"""
        message = f"data_ready {counter}"
        return await self.broadcast_legacy_message(message)

    async def send_loading_start_message(
        self, empty: bool = True, modified: bool = False
    ) -> int:
        """Send loading_start message to all connected clients."""
        message = f"loading_start {int(empty)} {int(modified)}"
        result = await self.broadcast_legacy_message(message)
        self.logger.info(
            f"Sent loading_start to {result} clients: empty={empty}, modified={modified}"
        )
        return result

    async def send_loading_end_message(self, snapshot_id: int = 0) -> int:
        """Send loading_end message to all connected clients."""
        message = f"loading_end {snapshot_id}"
        result = await self.broadcast_legacy_message(message)
        self.logger.info(
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
        result = await self.broadcast_legacy_message(message)
        self.logger.info(
            f"Sent transport to {result} clients: rolling={rolling}, bpb={bpb}, bpm={bpm}, sync={sync}"
        )
        return result

    async def send_truebypass_message(
        self, left: bool = False, right: bool = False
    ) -> int:
        """Send truebypass message to all connected clients."""
        message = f"truebypass {int(left)} {int(right)}"
        result = await self.broadcast_legacy_message(message)
        self.logger.info(
            f"Sent truebypass to {result} clients: left={left}, right={right}"
        )
        return result

    async def send_size_message(self, width: int = 0, height: int = 0) -> int:
        """Send size message to all connected clients."""
        message = f"size {width} {height}"
        result = await self.broadcast_legacy_message(message)
        self.logger.info(
            f"Sent size to {result} clients: width={width}, height={height}"
        )
        return result

    async def close(self) -> None:
        """Close the WebSocket hub service"""
        try:
            # Disconnect all clients
            client_ids = list(self.clients.keys())
            for client_id in client_ids:
                await self.disconnect_client(client_id)

            # Unsubscribe from event bus
            if self._event_subscription_id and self.event_bus:
                await self.event_bus.unsubscribe(self._event_subscription_id)

            self.logger.info("WebSocket Hub Service closed")

        except Exception as e:
            self.logger.error(f"Error closing WebSocket Hub Service: {e}")
