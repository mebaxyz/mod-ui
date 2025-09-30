#!/usr/bin/env python3
"""
Test ServiceBus Event-Based WebSocket Broadcasting

This script tests the complete ServiceBus event-based WebSocket broadcasting system:
1. Effects Service publishes events via ServiceBus
2. System Stats Service publishes events via ServiceBus
3. WebUI Gateway subscribes to events and broadcasts to WebSocket clients
4. Snapshots service publishes events via ServiceBus
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any, Dict

import websockets
from servicebus import CommConfig, Service, set_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure ServiceBus - use Docker Redis instance
redis_host = os.getenv("REDIS_HOST", "localhost")  # Docker exposes Redis on localhost
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_db = int(os.getenv("REDIS_DB", "0"))

config = CommConfig(
    host=redis_host, port=redis_port, db=redis_db, retry_attempts=3, timeout=10
)
set_config(config)


class ServiceBusWebSocketTester:
    """Test ServiceBus event-based WebSocket broadcasting"""

    def __init__(self):
        self.received_messages = []
        self.websocket = None
        self.test_service = None

    async def setup(self):
        """Setup test service and WebSocket connection"""
        # Create test service for publishing events
        self.test_service = Service("test_service")
        await self.test_service.start()

        # Connect to WebSocket gateway
        try:
            self.websocket = await websockets.connect("ws://localhost:8081/ws")
            logger.info("Connected to WebSocket gateway")
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            raise

    async def cleanup(self):
        """Cleanup connections"""
        if self.websocket:
            await self.websocket.close()
        if self.test_service:
            await self.test_service.stop()

    async def listen_for_messages(self, duration: int = 10):
        """Listen for WebSocket messages for specified duration"""
        logger.info(f"Listening for WebSocket messages for {duration} seconds...")

        start_time = time.time()
        try:
            while time.time() - start_time < duration:
                try:
                    # Set a timeout for receiving messages
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    self.received_messages.append(message)
                    logger.info(f"Received WebSocket message: {message}")
                except asyncio.TimeoutError:
                    # No message received in timeout period, continue
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    break

        except Exception as e:
            logger.error(f"Error listening for messages: {e}")

    async def test_effects_service_events(self):
        """Test effects service event publishing"""
        logger.info("Testing effects service events...")

        # Test plugin addition event
        await self.test_service.publish_event(
            "websocket_broadcast",
            {
                "type": "legacy_websocket",
                "content": "add http://test.plugin.uri/ 123 456 0",
                "message_type": "plugin_added",
                "plugin_uri": "http://test.plugin.uri/",
                "instance_id": "123",
            },
        )

        # Test parameter change event
        await self.test_service.publish_event(
            "websocket_broadcast",
            {
                "type": "legacy_websocket",
                "content": "param_set 123 :param1 42.5",
                "message_type": "parameter_changed",
                "instance_id": "123",
                "parameter": ":param1",
                "value": 42.5,
            },
        )

        logger.info("Published effects service events")

    async def test_system_stats_events(self):
        """Test system stats service event publishing"""
        logger.info("Testing system stats events...")

        # Test stats message event
        await self.test_service.publish_event(
            "websocket_broadcast",
            {
                "type": "legacy_websocket",
                "content": "stats 15.2 0",
                "message_type": "system_stats",
                "cpu_load": 15.2,
                "xruns": 0,
            },
        )

        # Test sys_stats message event
        await self.test_service.publish_event(
            "websocket_broadcast",
            {
                "type": "legacy_websocket",
                "content": "sys_stats 45.8 1800 65.2",
                "message_type": "system_stats_detailed",
                "memory_usage": 45.8,
                "cpu_frequency": 1800,
                "cpu_temp": 65.2,
            },
        )

        logger.info("Published system stats events")

    async def test_snapshots_events(self):
        """Test snapshots service event publishing"""
        logger.info("Testing snapshots events...")

        # Test snapshot load event
        await self.test_service.publish_event(
            "websocket_broadcast",
            {
                "type": "legacy_websocket",
                "content": "pedal_snapshot 1 Clean",
                "message_type": "snapshot_load",
                "snapshot_id": 1,
                "snapshot_name": "Clean",
            },
        )

        # Test snapshot save event
        await self.test_service.publish_event(
            "websocket_broadcast",
            {
                "type": "legacy_websocket",
                "content": "snapshot_saved 2 Drive",
                "message_type": "snapshot_save",
                "snapshot_id": 2,
                "snapshot_name": "Drive",
            },
        )

        logger.info("Published snapshots events")

    async def test_connection_events(self):
        """Test connection/disconnection events"""
        logger.info("Testing connection events...")

        # Test port connection event
        await self.test_service.publish_event(
            "websocket_broadcast",
            {
                "type": "legacy_websocket",
                "content": "connect system:playback_1 effect_123:input",
                "message_type": "port_connect",
                "action": "connect",
                "from_port": "system:playback_1",
                "to_port": "effect_123:input",
            },
        )

        # Test port disconnection event
        await self.test_service.publish_event(
            "websocket_broadcast",
            {
                "type": "legacy_websocket",
                "content": "disconnect system:playback_1 effect_123:input",
                "message_type": "port_disconnect",
                "action": "disconnect",
                "from_port": "system:playback_1",
                "to_port": "effect_123:input",
            },
        )

        logger.info("Published connection events")

    async def run_test(self):
        """Run the complete test suite"""
        logger.info("Starting ServiceBus WebSocket Broadcasting Test")

        try:
            await self.setup()

            # Start listening for messages in background
            listen_task = asyncio.create_task(self.listen_for_messages(30))

            # Wait a moment for listener to start
            await asyncio.sleep(1)

            # Publish test events
            await self.test_effects_service_events()
            await asyncio.sleep(2)

            await self.test_system_stats_events()
            await asyncio.sleep(2)

            await self.test_snapshots_events()
            await asyncio.sleep(2)

            await self.test_connection_events()
            await asyncio.sleep(5)  # Wait for remaining messages

            # Cancel listening task
            listen_task.cancel()
            try:
                await listen_task
            except asyncio.CancelledError:
                pass

            # Analyze results
            self.analyze_results()

        except Exception as e:
            logger.error(f"Test failed: {e}")
            return False
        finally:
            await self.cleanup()

        return len(self.received_messages) > 0

    def analyze_results(self):
        """Analyze test results"""
        logger.info(f"\n{'='*50}")
        logger.info("TEST RESULTS SUMMARY")
        logger.info(f"{'='*50}")
        logger.info(f"Total WebSocket messages received: {len(self.received_messages)}")

        if not self.received_messages:
            logger.warning("❌ No WebSocket messages received!")
            logger.warning("Possible issues:")
            logger.warning("- WebUI Gateway service not running")
            logger.warning("- ServiceBus event subscription not working")
            logger.warning("- WebSocket broadcasting not implemented")
            return

        # Categorize messages
        message_types = {}
        expected_messages = [
            "add http://test.plugin.uri/",
            "param_set 123 :param1",
            "stats 15.2 0",
            "sys_stats 45.8 1800",
            "pedal_snapshot 1 Clean",
            "snapshot_saved 2 Drive",
            "connect system:playback_1",
            "disconnect system:playback_1",
        ]

        received_patterns = []
        for message in self.received_messages:
            received_patterns.append(message[:30])  # First 30 chars

        logger.info(f"\nReceived message patterns:")
        for i, pattern in enumerate(received_patterns, 1):
            logger.info(f"  {i}. {pattern}...")

        # Check if we got expected message types
        found_types = set()
        for message in self.received_messages:
            if "add http://test.plugin.uri/" in message:
                found_types.add("plugin_added")
            elif "param_set" in message:
                found_types.add("parameter_changed")
            elif message.startswith("stats "):
                found_types.add("system_stats")
            elif message.startswith("sys_stats "):
                found_types.add("system_stats_detailed")
            elif "pedal_snapshot" in message:
                found_types.add("snapshot_load")
            elif "snapshot_saved" in message:
                found_types.add("snapshot_save")
            elif message.startswith("connect "):
                found_types.add("port_connect")
            elif message.startswith("disconnect "):
                found_types.add("port_disconnect")

        logger.info(f"\nMessage types detected: {sorted(found_types)}")

        expected_types = {
            "plugin_added",
            "parameter_changed",
            "system_stats",
            "system_stats_detailed",
            "snapshot_load",
            "snapshot_save",
            "port_connect",
            "port_disconnect",
        }

        missing_types = expected_types - found_types
        if missing_types:
            logger.warning(f"Missing message types: {sorted(missing_types)}")
        else:
            logger.info("✅ All expected message types received!")

        success_rate = len(found_types) / len(expected_types) * 100
        logger.info(f"Success rate: {success_rate:.1f}%")

        if success_rate >= 100:
            logger.info("🎉 ServiceBus WebSocket Broadcasting Test: PASSED")
        elif success_rate >= 75:
            logger.info("⚠️  ServiceBus WebSocket Broadcasting Test: MOSTLY PASSED")
        else:
            logger.warning("❌ ServiceBus WebSocket Broadcasting Test: FAILED")


async def main():
    """Main test function"""
    tester = ServiceBusWebSocketTester()
    success = await tester.run_test()

    if success:
        logger.info("Test completed successfully")
        sys.exit(0)
    else:
        logger.error("Test failed")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test error: {e}")
        sys.exit(1)
