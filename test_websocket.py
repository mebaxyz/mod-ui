#!/usr/bin/env python3
"""
Simple WebSocket test client to verify the WebUI Gateway works correctly.
"""

import asyncio
import json

import websockets


async def test_websocket():
    uri = "ws://localhost:8081/websocket"
    print(f"Connecting to {uri}")

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Waiting for initial messages...")

            # Send data_ready message as the frontend would
            await websocket.send("data_ready 1")
            print("Sent: data_ready 1")

            # Listen for responses
            message_count = 0
            while message_count < 10:  # Get first few messages
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    print(f"Received: {message}")
                    message_count += 1
                except asyncio.TimeoutError:
                    print("Timeout waiting for message")
                    break

    except Exception as e:
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket())
