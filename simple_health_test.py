#!/usr/bin/env python3
"""
Simple health check test
"""

import asyncio
import sys
sys.path.insert(0, '/home/nicolas/project/madeline/mod-ui')

from servicebus import Service

async def test():
    print("Creating test service...")
    service = Service("test")
    await service.start()
    
    print("Calling health on audio_processing...")
    try:
        result = await asyncio.wait_for(
            service.call("audio_processing", "health"), 
            timeout=5.0
        )
        print(f"SUCCESS: {result}")
    except Exception as e:
        print(f"FAILED: {e}")
    
    await service.stop()

if __name__ == "__main__":
    asyncio.run(test())
