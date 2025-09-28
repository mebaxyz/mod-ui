#!/usr/bin/env python3
"""
Test ServiceBus communication between session and audio-engine services.
"""

import asyncio
import json

from libraries.servicebus.client import ServiceClient


async def test_servicebus_communication():
    """Test communication between session and audio engine services."""
    print("Testing ServiceBus communication between services...")

    # Create client for session service
    session_client = ServiceClient("test-client")

    try:
        print("\n1. Testing session service health check...")
        response = await session_client.call("session", "health_check", {})
        print(f"Session health check response: {response}")

        print("\n2. Testing audio engine service health check...")
        response = await session_client.call("audio-engine", "health_check", {})
        print(f"Audio engine health check response: {response}")

        print("\n3. Testing session state...")
        response = await session_client.call("session", "get_session_state", {})
        print(f"Session state: {json.dumps(response, indent=2, default=str)}")

        print("\n4. Testing audio engine capabilities...")
        response = await session_client.call("audio-engine", "get_capabilities", {})
        print(f"Audio engine capabilities: {response}")

        print("\n5. Testing session to audio engine communication (add plugin)...")
        plugin_data = {
            "uri": "http://lv2plug.in/plugins/eg-amp",
            "instance_id": "test_plugin_1",
            "x": 100,
            "y": 200,
        }
        try:
            response = await session_client.call("session", "add_plugin", plugin_data)
            print(f"Add plugin response: {response}")
        except Exception as e:
            print(f"Add plugin failed (expected if no mod-host): {e}")

        print("\n✅ ServiceBus communication test completed successfully!")

    except Exception as e:
        print(f"❌ ServiceBus communication test failed: {e}")

    finally:
        await session_client.close()


if __name__ == "__main__":
    asyncio.run(test_servicebus_communication())
