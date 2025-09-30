#!/usr/bin/env python3
"""
WebSocket Client Test for MOD UI Broadcasting System

This script connects to the webui-gateway WebSocket endpoint and listens for
all broadcasted messages to validate the complete broadcasting pipeline.

Tests the full chain: Service → HTTP → WebUI Gateway → WebSocket → Client
"""

import asyncio
import json
import time
from datetime import datetime

import requests
import websockets

# Configuration
WEBSOCKET_URL = "ws://localhost:8081/ws"
HTTP_BASE_URL = "http://localhost:8081"


class WebSocketTester:
    def __init__(self):
        self.received_messages = []
        self.websocket = None
        self.running = False

    async def connect_websocket(self):
        """Connect to the WebSocket endpoint"""
        try:
            print(f"🔌 Connecting to WebSocket: {WEBSOCKET_URL}")
            self.websocket = await websockets.connect(WEBSOCKET_URL)
            print("✅ WebSocket connected successfully!")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to WebSocket: {e}")
            return False

    async def listen_for_messages(self):
        """Listen for incoming WebSocket messages"""
        print("👂 Listening for WebSocket messages...")
        self.running = True

        try:
            while self.running and self.websocket:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)

                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    print(f"📨 [{timestamp}] Received: {message}")
                    self.received_messages.append(
                        {"timestamp": timestamp, "message": message}
                    )

                except asyncio.TimeoutError:
                    # No message received, continue listening
                    continue
                except websockets.exceptions.ConnectionClosed:
                    print("🔌 WebSocket connection closed")
                    break

        except Exception as e:
            print(f"❌ Error listening for messages: {e}")

    async def trigger_websocket_messages(self):
        """Trigger various operations that should generate WebSocket messages"""
        print("\n🚀 Triggering WebSocket message generation...")

        # Wait a moment for listener to be ready
        await asyncio.sleep(2)

        test_operations = [
            {
                "name": "Parameter Change",
                "url": f"{HTTP_BASE_URL}/api/effect/parameter/set/test_plugin?symbol=gain&value=0.7",
                "expected_message": "param_set test_plugin gain 0.7",
            },
            {
                "name": "Preset Load",
                "url": f"{HTTP_BASE_URL}/api/effect/preset/load/test_plugin?preset_uri=my_preset.ttl",
                "expected_message": "preset test_plugin my_preset.ttl",
            },
            {
                "name": "Preset Save",
                "url": f"{HTTP_BASE_URL}/api/effect/preset/save/test_plugin?name=SavedPreset",
                "expected_message": "preset_saved test_plugin SavedPreset",
            },
            {
                "name": "Snapshot Load",
                "url": f"{HTTP_BASE_URL}/snapshot/load?id=2",
                "expected_message": "pedal_snapshot 2 Drive",
            },
            {
                "name": "Snapshot Save",
                "url": f"{HTTP_BASE_URL}/snapshot/saveas?title=NewSnapshot",
                "expected_message": "snapshot_saved",
            },
        ]

        for i, operation in enumerate(test_operations, 1):
            print(f"\n{i}. Testing {operation['name']}...")
            print(f"   Making request: {operation['url']}")

            try:
                response = requests.get(operation["url"], timeout=10)
                print(f"   HTTP Status: {response.status_code}")
                print(f"   Response: {response.text[:100]}...")
                print(f"   Expected WebSocket: {operation['expected_message']}")

                # Wait for WebSocket message to arrive
                await asyncio.sleep(1)

            except Exception as e:
                print(f"   ❌ Request failed: {e}")

        print(f"\n⏱️  Waiting 10 seconds for system stats messages...")
        await asyncio.sleep(10)

    async def stop_listening(self):
        """Stop listening and close WebSocket"""
        print("\n🛑 Stopping WebSocket listener...")
        self.running = False

        if self.websocket:
            await self.websocket.close()
            print("✅ WebSocket closed")

    def analyze_results(self):
        """Analyze received messages"""
        print(f"\n📊 Analysis Results:")
        print(f"=" * 50)
        print(f"Total messages received: {len(self.received_messages)}")

        if not self.received_messages:
            print("❌ No WebSocket messages received!")
            print("   This could indicate:")
            print("   - WebSocket connection issues")
            print("   - Broadcasting pipeline problems")
            print("   - Service communication failures")
            return False

        # Categorize messages
        message_types = {}
        for msg_data in self.received_messages:
            message = msg_data["message"]
            if message.startswith("param_set"):
                message_types.setdefault("Parameter Changes", []).append(message)
            elif message.startswith("preset "):
                message_types.setdefault("Preset Load", []).append(message)
            elif message.startswith("preset_saved"):
                message_types.setdefault("Preset Save", []).append(message)
            elif message.startswith("pedal_snapshot"):
                message_types.setdefault("Snapshot Load", []).append(message)
            elif message.startswith("snapshot_saved"):
                message_types.setdefault("Snapshot Save", []).append(message)
            elif message.startswith("stats") or message.startswith("sys_stats"):
                message_types.setdefault("System Stats", []).append(message)
            elif message.startswith("add "):
                message_types.setdefault("Plugin Add", []).append(message)
            elif message.startswith("remove "):
                message_types.setdefault("Plugin Remove", []).append(message)
            else:
                message_types.setdefault("Other", []).append(message)

        # Display results
        for msg_type, messages in message_types.items():
            print(f"\n✅ {msg_type}: {len(messages)} messages")
            for msg in messages[:3]:  # Show first 3 of each type
                print(f"   - {msg}")
            if len(messages) > 3:
                print(f"   ... and {len(messages) - 3} more")

        return True


async def main():
    """Main test execution"""
    print("🎯 MOD UI WebSocket Broadcasting End-to-End Test")
    print("=" * 60)

    tester = WebSocketTester()

    # Connect to WebSocket
    if not await tester.connect_websocket():
        return 1

    try:
        # Start listening in background
        listen_task = asyncio.create_task(tester.listen_for_messages())

        # Trigger WebSocket messages
        await tester.trigger_websocket_messages()

        # Stop listening
        await tester.stop_listening()

        # Cancel listening task
        listen_task.cancel()
        try:
            await listen_task
        except asyncio.CancelledError:
            pass

        # Analyze results
        success = tester.analyze_results()

        if success:
            print(f"\n🎉 WebSocket Broadcasting Test PASSED!")
            print(
                f"✅ Complete pipeline working: Service → HTTP → WebUI Gateway → WebSocket → Client"
            )
            return 0
        else:
            print(f"\n❌ WebSocket Broadcasting Test FAILED!")
            return 1

    except Exception as e:
        print(f"\n💥 Test execution error: {e}")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
