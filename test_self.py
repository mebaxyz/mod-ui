#!/usr/bin/env python3
"""
Test self-call via ZeroMQ
"""

import asyncio
import sys
sys.path.insert(0, '/home/nicolas/project/madeline/mod-ui')

from servicebus import Service

async def test_self():
    print("Creating service...")
    service = Service("test")
    await service.start()
    
    # Register a handler
    async def echo_handler(message=""):
        return f"Echo: {message}"
    
    service.register_handler("echo", echo_handler)
    
    print("Calling self...")
    try:
        result = await asyncio.wait_for(
            service.call("test", "echo", message="Hello self!"), 
            timeout=5.0
        )
        print(f"SUCCESS: {result}")
    except Exception as e:
        print(f"FAILED: {e}")
    
    await service.stop()

if __name__ == "__main__":
    asyncio.run(test_self())
