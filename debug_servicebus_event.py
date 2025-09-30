#!/usr/bin/env python3
"""
Simple ServiceBus Event Test

Test if we can publish ServiceBus events from outside Docker that are received by Docker services.
"""

import asyncio
import logging
import os
import sys

from servicebus import CommConfig, Service, set_config

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def test_servicebus_event():
    """Test publishing a ServiceBus event"""

    # Configure ServiceBus to connect to Docker Redis
    redis_host = "localhost"  # Docker exposes Redis on localhost
    redis_port = 6379
    redis_db = 0
    redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

    config = CommConfig(redis_url=redis_url)
    set_config(config)

    logger.info(f"Connecting to Redis at {redis_url}")

    # Create test service
    service = Service("debug_test_service")

    try:
        # Start service
        await service.start()
        logger.info("Test service started")

        # Publish a websocket_broadcast event
        event_data = {
            "type": "legacy_websocket",
            "content": "test_message from debug script",
            "message_type": "debug_test",
            "timestamp": "2025-09-30T05:25:00Z",
        }

        logger.info(f"Publishing websocket_broadcast event: {event_data}")
        await service.publish_event("websocket_broadcast", event_data)
        logger.info("Event published successfully")

        # Wait a moment for event processing
        await asyncio.sleep(3)

        logger.info("Test completed")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False
    finally:
        await service.stop()

    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_servicebus_event())
        if result:
            logger.info("✅ ServiceBus event test passed")
            sys.exit(0)
        else:
            logger.error("❌ ServiceBus event test failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Test error: {e}")
        sys.exit(1)
