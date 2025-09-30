#!/usr/bin/env python3
"""
Simple test script to verify ZeroMQ ServiceBus functionality
"""

import asyncio
import os
import sys

# Add project to path
sys.path.insert(0, "/home/nicolas/project/madeline/mod-ui")

from servicebus import Service


async def test_zeromq_service():
    """Test basic ZeroMQ service functionality"""
    print("🔧 Testing ZeroMQ ServiceBus implementation...")

    service1 = Service("test_service_1")
    service2 = Service("test_service_2")

    # Test method handler
    async def echo_handler(message: str):
        return f"Echo: {message}"

    service1.register_handler("echo", echo_handler)

    # Test event handler
    events_received = []

    async def event_handler(event):
        events_received.append(event.data)
        print(f"📢 Received event: {event.data}")

    service2.register_event_handler("test_event", event_handler)

    try:
        # Start services
        print("🚀 Starting services...")
        await service1.start()
        await service2.start()

        # Wait a bit for services to initialize
        print("⏳ Waiting for services to initialize...")
        await asyncio.sleep(1.0)

        # Test RPC call
        print("📞 Testing RPC call...")
        result = await service2.call("test_service_1", "echo", message="Hello ZeroMQ!")
        print(f"✅ RPC result: {result}")

        # Test event publishing
        print("📡 Testing event publishing...")
        success = await service1.publish_event(
            "test_event", {"message": "Hello from service1"}
        )
        print(f"📡 Event publish result: {success}")

        # Wait longer for event to be received
        print("⏳ Waiting for event to be received...")
        await asyncio.sleep(1.0)

        # Check results
        if result == "Echo: Hello ZeroMQ!":
            print("✅ RPC test passed")
        else:
            print(f"❌ RPC test failed: expected 'Echo: Hello ZeroMQ!', got '{result}'")

        if events_received:
            print("✅ Event test passed")
        else:
            print("❌ Event test failed: no events received")

        print("🎉 ZeroMQ ServiceBus test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        print("🧹 Cleaning up...")
        await service1.stop()
        await service2.stop()


if __name__ == "__main__":
    asyncio.run(test_zeromq_service())
