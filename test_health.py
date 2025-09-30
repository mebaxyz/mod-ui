#!/usr/bin/env python3
"""
Test health check via ZeroMQ ServiceBus
"""

import asyncio
import sys
sys.path.insert(0, '/home/nicolas/project/madeline/mod-ui')

from servicebus import Service

async def test_health():
    """Test health check"""
    print("Testing health check via ZeroMQ ServiceBus...")
    
    # Create a test service
    test_service = Service("test_client")
    await test_service.start()
    
    try:
        # Call health method on audio_processing service
        result = await test_service.call("audio_processing", "health")
        print(f"Health check result: {result}")
        
        # Test echo method
        echo_result = await test_service.call("audio_processing", "echo", message="Hello ZeroMQ!")
        print(f"Echo result: {echo_result}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await test_service.stop()

if __name__ == "__main__":
    asyncio.run(test_health())
