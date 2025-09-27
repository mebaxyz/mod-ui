#!/usr/bin/env python3
"""
Test Session Service Integration

This script tests the integration between WebUI Gateway and Session Service
using the ServiceClient.
"""

import asyncio
import logging
import os
import sys

# Add the project root to Python path
sys.path.insert(0, "/home/nicolas/project/madeline/mod-ui")

from src.mod_ui.common import ServiceClient


async def test_session_integration():
    """Test the session service integration"""
    logger = logging.getLogger(__name__)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("🔧 Testing Session Service Integration...")

    try:
        # Initialize service client
        service_client = ServiceClient(redis_url="redis://localhost:6379")
        await service_client.start()

        print("✅ ServiceClient initialized")

        # Test direct session service call
        print("\n📡 Testing direct session service call...")
        response = await service_client.request(
            service="session", endpoint="/api/session/status", method="GET"
        )

        if response:
            print(f"✅ Session service responded: {response}")
            session_data = response.get("session", {})
            print(f"   Transport: {session_data.get('transport_state')}")
            print(f"   Tempo: {session_data.get('tempo_bpm')} BPM")
            print(f"   CPU Load: {session_data.get('cpu_load')}%")
        else:
            print("❌ No response from session service")

        # Test tempo change
        print("\n🎵 Testing tempo change...")
        tempo_response = await service_client.request(
            service="session",
            endpoint="/api/session/tempo",
            method="POST",
            data={"bpm": 140.0},
        )

        if tempo_response and tempo_response.get("success"):
            print(f"✅ Tempo changed to {tempo_response.get('tempo_bpm')} BPM")
        else:
            print(f"❌ Failed to change tempo: {tempo_response}")

        # Test transport control
        print("\n▶️ Testing transport control...")
        transport_response = await service_client.request(
            service="session", endpoint="/api/session/transport/play", method="POST"
        )

        if transport_response and transport_response.get("success"):
            print(f"✅ Transport started: {transport_response.get('transport_state')}")
        else:
            print(f"❌ Failed to start transport: {transport_response}")

        # Stop transport
        stop_response = await service_client.request(
            service="session", endpoint="/api/session/transport/stop", method="POST"
        )

        if stop_response and stop_response.get("success"):
            print(f"✅ Transport stopped: {stop_response.get('transport_state')}")
        else:
            print(f"❌ Failed to stop transport: {stop_response}")

        # Get final status
        print("\n📊 Final status check...")
        final_response = await service_client.request(
            service="session", endpoint="/api/session/status", method="GET"
        )

        if final_response:
            session_data = final_response.get("session", {})
            print(f"   Transport: {session_data.get('transport_state')}")
            print(f"   Tempo: {session_data.get('tempo_bpm')} BPM")
            print(f"   Uptime: {session_data.get('uptime_seconds')}s")

        await service_client.stop()
        print("\n🎉 Session integration test completed successfully!")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_session_integration())
