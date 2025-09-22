"""
WebSocket Gateway Integration Test Client

Simple client to test WebSocket Gateway functionality.
"""

import asyncio
import json
import logging
import sys
import time
from typing import Dict, Optional

import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


class WebSocketGatewayClient:
    """Test client for WebSocket Gateway Service"""

    def __init__(self, gateway_url: str = "ws://localhost:8081/ws"):
        self.gateway_url = gateway_url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.client_id: Optional[str] = None
        self.is_connected = False

        # Message tracking
        self.messages_sent = 0
        self.messages_received = 0
        self.events_received: Dict[str, int] = {}

    async def connect(self):
        """Connect to WebSocket Gateway"""

        try:
            logger.info(f"Connecting to WebSocket Gateway at {self.gateway_url}")
            self.websocket = await websockets.connect(self.gateway_url)
            self.is_connected = True
            logger.info("Connected to WebSocket Gateway")

            # Start message handler
            asyncio.create_task(self._message_handler())

        except Exception as e:
            logger.error(f"Failed to connect to WebSocket Gateway: {e}")
            raise

    async def disconnect(self):
        """Disconnect from WebSocket Gateway"""

        if self.websocket and self.is_connected:
            await self.websocket.close()
            self.is_connected = False
            logger.info("Disconnected from WebSocket Gateway")

    async def subscribe_to_events(self, event_types: list):
        """Subscribe to specific event types"""

        if not self.is_connected:
            logger.error("Cannot subscribe: not connected")
            return False

        message = {
            "type": "subscribe",
            "event_types": event_types,
            "timestamp": time.time(),
        }

        await self._send_message(message)
        logger.info(f"Subscribed to events: {event_types}")
        return True

    async def unsubscribe_from_events(self, event_types: list):
        """Unsubscribe from specific event types"""

        if not self.is_connected:
            logger.error("Cannot unsubscribe: not connected")
            return False

        message = {
            "type": "unsubscribe",
            "event_types": event_types,
            "timestamp": time.time(),
        }

        await self._send_message(message)
        logger.info(f"Unsubscribed from events: {event_types}")
        return True

    async def ping(self):
        """Send ping to gateway"""

        if not self.is_connected:
            logger.error("Cannot ping: not connected")
            return False

        message = {"type": "ping", "timestamp": time.time()}

        await self._send_message(message)
        logger.info("Sent ping to gateway")
        return True

    async def request_status(self):
        """Request status from gateway"""

        if not self.is_connected:
            logger.error("Cannot request status: not connected")
            return False

        message = {"type": "request_status", "timestamp": time.time()}

        await self._send_message(message)
        logger.info("Requested status from gateway")
        return True

    def get_stats(self):
        """Get client statistics"""

        return {
            "client_id": self.client_id,
            "is_connected": self.is_connected,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "events_received": dict(self.events_received),
            "unique_event_types": len(self.events_received),
        }

    # Private methods

    async def _send_message(self, message: dict):
        """Send message to gateway"""

        if not self.websocket or not self.is_connected:
            return False

        try:
            await self.websocket.send(json.dumps(message))
            self.messages_sent += 1
            return True

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    async def _message_handler(self):
        """Handle incoming messages from gateway"""

        try:
            while self.is_connected:
                message = await self.websocket.recv()
                await self._process_message(message)

        except ConnectionClosed:
            logger.info("WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            self.is_connected = False

    async def _process_message(self, message: str):
        """Process incoming message"""

        try:
            data = json.loads(message)
            self.messages_received += 1

            message_type = data.get("type", "unknown")

            if message_type == "welcome":
                self.client_id = data.get("client_id")
                logger.info(f"Received welcome message, client_id: {self.client_id}")

            elif message_type == "event":
                event_type = data.get("event_type", "unknown")
                self.events_received[event_type] = (
                    self.events_received.get(event_type, 0) + 1
                )
                logger.info(f"Received event: {event_type}")

            elif message_type == "pong":
                logger.info("Received pong from gateway")

            elif message_type == "status":
                logger.info(f"Received status: {data}")

            elif message_type == "subscription_confirmed":
                event_types = data.get("event_types", [])
                logger.info(f"Subscription confirmed for: {event_types}")

            elif message_type == "unsubscription_confirmed":
                event_types = data.get("event_types", [])
                logger.info(f"Unsubscription confirmed for: {event_types}")

            elif message_type == "error":
                error = data.get("error", "Unknown error")
                logger.error(f"Gateway error: {error}")

            else:
                logger.info(f"Received message type '{message_type}': {data}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {message}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")


async def run_test_session():
    """Run a test session with the WebSocket Gateway"""

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    client = WebSocketGatewayClient()

    try:
        # Connect to gateway
        await client.connect()

        # Wait for welcome message
        await asyncio.sleep(1)

        # Test basic functionality
        logger.info("=== Testing Basic Functionality ===")

        # Send ping
        await client.ping()
        await asyncio.sleep(0.5)

        # Request status
        await client.request_status()
        await asyncio.sleep(0.5)

        # Test subscriptions
        logger.info("=== Testing Event Subscriptions ===")

        # Subscribe to some events
        await client.subscribe_to_events(
            [
                "session_transport_changed",
                "pedalboard_loaded",
                "plugin_parameter_changed",
                "system_stats_updated",
            ]
        )
        await asyncio.sleep(1)

        # Subscribe to all events (for testing)
        await client.subscribe_to_events(["*"])
        await asyncio.sleep(1)

        # Wait for some events
        logger.info("=== Waiting for Events (30 seconds) ===")
        await asyncio.sleep(30)

        # Unsubscribe from some events
        await client.unsubscribe_from_events(["system_stats_updated"])
        await asyncio.sleep(1)

        # Final stats
        stats = client.get_stats()
        logger.info("=== Final Statistics ===")
        logger.info(json.dumps(stats, indent=2))

    except KeyboardInterrupt:
        logger.info("Test session interrupted by user")
    except Exception as e:
        logger.error(f"Test session error: {e}")
    finally:
        await client.disconnect()


async def main():
    """Main entry point"""

    if len(sys.argv) > 1:
        gateway_url = sys.argv[1]
        client = WebSocketGatewayClient(gateway_url)
    else:
        client = WebSocketGatewayClient()

    # Run test session
    await run_test_session()


if __name__ == "__main__":
    asyncio.run(main())
