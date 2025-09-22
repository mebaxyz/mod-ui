#!/usr/bin/env python3
"""
Long-running WebSocket connection test to verify client tracking
"""

import asyncio
import json
import logging

import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def long_connection_test():
    """Test long-running WebSocket connection and client tracking"""
    uri = "ws://localhost/websocket"

    try:
        logger.info(f"Establishing long-running connection to: {uri}")

        async with websockets.connect(uri) as websocket:
            logger.info("✅ WebSocket connection established!")

            # Keep connection alive for 10 seconds
            for i in range(10):
                # Send a heartbeat message
                heartbeat = {"type": "heartbeat", "sequence": i}
                await websocket.send(json.dumps(heartbeat))
                logger.info(f"📤 Heartbeat {i}: {heartbeat}")

                # Wait for any response (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    logger.info(f"📥 Response: {response}")
                except asyncio.TimeoutError:
                    logger.info("⏰ No response (timeout)")

                await asyncio.sleep(1)

            logger.info("✅ Long-running connection test completed")

    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")


if __name__ == "__main__":
    asyncio.run(long_connection_test())
