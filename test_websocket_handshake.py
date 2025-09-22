#!/usr/bin/env python3
"""
Test WebSocket Gateway initialization handshake
Simulates the frontend JavaScript behavior
"""

import asyncio
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_handshake():
    """Test the WebSocket handshake sequence that the frontend expects"""
    uri = "ws://localhost:8081/ws"
    
    try:
        logger.info(f"Connecting to {uri}")
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to WebSocket Gateway")
            
            # Wait for initial data_ready message from server
            logger.info("Waiting for initial data_ready message from server...")
            message = await websocket.recv()
            logger.info(f"Received: {message}")
            
            if message.startswith("data_ready "):
                # Extract counter and respond back (as frontend does)
                counter = message.split(" ", 1)[1]
                response = f"data_ready {counter}"
                logger.info(f"Sending response: {response}")
                await websocket.send(response)
                
                # Now listen for initialization sequence
                logger.info("Listening for initialization sequence...")
                timeout_count = 0
                max_timeout = 10
                
                while timeout_count < max_timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        logger.info(f"Received initialization message: {message}")
                        
                        # Check if we got loading_end (indicates initialization complete)
                        if message.startswith("loading_end"):
                            logger.info("✅ Initialization sequence completed successfully!")
                            break
                            
                    except asyncio.TimeoutError:
                        timeout_count += 1
                        logger.info(f"Waiting for more messages... ({timeout_count}/{max_timeout})")
                
                if timeout_count >= max_timeout:
                    logger.warning("⚠️  Timeout waiting for complete initialization sequence")
            else:
                logger.error(f"❌ Expected data_ready message, got: {message}")
                
    except Exception as e:
        logger.error(f"❌ WebSocket test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_handshake())