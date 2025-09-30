#!/usr/bin/env python3
"""
Test the new ResilientServiceBus to verify it works as expected
"""

import asyncio
import logging

from servicebus import ResilientServiceBus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_websocket_handler(event):
    """Test event handler"""
    logger.info(f"✅ Received event: {event.event_type}")
    logger.info(f"   Data: {event.data}")


async def main():
    """Test the ResilientServiceBus"""
    logger.info("🧪 Testing ResilientServiceBus...")

    try:
        # SIMPLE INTERFACE TEST
        logger.info("1️⃣ Creating ResilientServiceBus...")
        bus = ResilientServiceBus("test_service")

        logger.info("2️⃣ Registering event handler...")
        bus.on_event("websocket_broadcast", test_websocket_handler)

        logger.info("3️⃣ Starting ServiceBus...")
        await bus.start()

        logger.info("4️⃣ Checking connection status...")
        info = bus.connection_info
        logger.info(f"   Connection info: {info}")

        logger.info("5️⃣ Testing publish event...")
        success = await bus.publish_event("test_event", {"message": "Hello from test!"})
        logger.info(f"   Publish success: {success}")

        logger.info("6️⃣ Waiting a bit to see if everything works...")
        await asyncio.sleep(5)

        logger.info("7️⃣ Stopping ServiceBus...")
        await bus.stop()

        logger.info("✅ ResilientServiceBus test completed successfully!")

    except Exception as e:
        logger.error(f"❌ ResilientServiceBus test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
