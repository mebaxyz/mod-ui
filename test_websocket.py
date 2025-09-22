#!/usr/bin/env python3
"""
Simple WebSocket test script to verify nginx proxy is working
"""

import asyncio
import json
import logging

import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_websocket():
    """Test WebSocket connection through nginx proxy"""
    uri = "ws://localhost/websocket"

    try:
        logger.info(f"Connecting to WebSocket: {uri}")

        async with websockets.connect(uri) as websocket:
            logger.info("✅ WebSocket connection established!")

            # Send a test message
            test_message = {"type": "ping", "data": "test connection"}
            await websocket.send(json.dumps(test_message))
            logger.info(f"📤 Sent: {test_message}")

            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                logger.info(f"📥 Received: {response}")

                # Try to parse as JSON
                try:
                    response_data = json.loads(response)
                    logger.info(f"✅ Valid JSON response: {response_data}")
                except json.JSONDecodeError:
                    logger.info(f"ℹ️  Raw response: {response}")

            except asyncio.TimeoutError:
                logger.info(
                    "⏰ No response received within timeout (this might be expected)"
                )

    except Exception as e:
        logger.error(f"❌ WebSocket connection failed: {e}")
        return False

    return True


async def test_direct_connection():
    """Test direct connection to session service v2"""
    uri = "ws://localhost:8002/ws"

    try:
        logger.info(f"Testing direct connection to: {uri}")

        async with websockets.connect(uri) as websocket:
            logger.info("✅ Direct WebSocket connection established!")

            # Send a test message
            test_message = {"type": "ping", "data": "direct connection test"}
            await websocket.send(json.dumps(test_message))
            logger.info(f"📤 Sent: {test_message}")

            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                logger.info(f"📥 Received: {response}")
            except asyncio.TimeoutError:
                logger.info("⏰ No response received within timeout")

    except Exception as e:
        logger.error(f"❌ Direct WebSocket connection failed: {e}")
        return False

    return True


async def main():
    """Run WebSocket tests"""
    logger.info("🧪 Starting WebSocket connection tests...")

    logger.info("\n" + "=" * 50)
    logger.info("TEST 1: Direct connection to Session Service v2")
    logger.info("=" * 50)
    direct_result = await test_direct_connection()

    logger.info("\n" + "=" * 50)
    logger.info("TEST 2: Connection through nginx proxy")
    logger.info("=" * 50)
    proxy_result = await test_websocket()

    logger.info("\n" + "=" * 50)
    logger.info("TEST RESULTS")
    logger.info("=" * 50)
    logger.info(f"Direct connection: {'✅ PASS' if direct_result else '❌ FAIL'}")
    logger.info(f"Proxy connection:  {'✅ PASS' if proxy_result else '❌ FAIL'}")

    if proxy_result:
        logger.info("\n🎉 WebSocket proxy is working correctly!")
        logger.info("Frontend clients can now connect to ws://localhost/websocket")
        logger.info("and will be proxied to the modern Session Service v2")
    else:
        logger.error("\n💥 WebSocket proxy is not working")
        logger.error("Check nginx configuration and service networking")


if __name__ == "__main__":
    asyncio.run(main())
