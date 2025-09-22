#!/usr/bin/env python3
"""
Simple WebSocket client to test system stats messages
"""
import asyncio
import json

import websockets


async def test_websocket():
    uri = "ws://localhost:8002/ws"

    try:
        print("Connecting to WebSocket...")
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to WebSocket")

            # Listen for messages for 20 seconds
            timeout_duration = 20
            print(f"Listening for messages for {timeout_duration} seconds...")

            try:
                while True:
                    message = await asyncio.wait_for(
                        websocket.recv(), timeout=timeout_duration
                    )
                    print(f"📨 Received: {message}")

                    # Try to parse as JSON, otherwise show as text
                    try:
                        parsed = json.loads(message)
                        print(f"   JSON: {json.dumps(parsed, indent=2)}")
                    except json.JSONDecodeError:
                        print(f"   Text: {message}")
                    print()

            except asyncio.TimeoutError:
                print("⏰ Timeout reached, closing connection")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket())
