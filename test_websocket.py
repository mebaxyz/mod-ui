#!/usr/bin/env python3
"""
Simple WebSocket test client for MOD UI
"""
import asyncio
import json

import websockets


async def test_websocket():
    uri = "ws://localhost:8888/websocket"
    
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connection established!")
            
            # Send a test command
            test_message = "data_ready 1"
            print(f"Sending: {test_message}")
            await websocket.send(test_message)
            
            # Try to receive a response (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"Received: {response}")
            except asyncio.TimeoutError:
                print("No response received (this is expected for data_ready)")
            
            # Send another test command
            test_message2 = "unknown_command test"
            print(f"Sending: {test_message2}")
            await websocket.send(test_message2)
            
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"Received: {response}")
            except asyncio.TimeoutError:
                print("No response received")
                
            print("✅ WebSocket test completed successfully!")
            
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())if __name__ == "__main__":
    asyncio.run(test_websocket())