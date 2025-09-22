#!/usr/bin/env python3
"""
Simple test script for system stats service
"""
import asyncio
import os
import sys

# Add the src directory to the path
sys.path.insert(0, "/home/nicolas/project/madeline/mod-ui/src")

from mod_ui.services.session_v2.models.events import (
    EventType,
    create_system_stats_event,
)
from mod_ui.services.session_v2.utils.event_bus import RedisEventBus


async def test_system_stats():
    print("Testing system stats service...")

    # Initialize Redis event bus
    redis_url = "redis://localhost:6379/0"
    event_bus = RedisEventBus(redis_url)

    try:
        await event_bus.initialize()
        print("✓ Connected to Redis event bus")

        # Create and publish a test system stats event
        event = create_system_stats_event(
            event_type=EventType.SYSTEM_STATS_UPDATED,
            source_service="system_stats_test",
            cpu_percent=75.5,
            memory_percent=60.2,
            cpu_frequency="1800000000",
            cpu_temperature="45000",
            xruns=0,
        )

        await event_bus.publish(event)
        print("✓ Published test system stats event")

        # Wait a bit to ensure the event is processed
        await asyncio.sleep(2)

    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    finally:
        await event_bus.close()
        print("✓ Closed event bus connection")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_system_stats())
    if success:
        print("✓ System stats test completed successfully!")
    else:
        print("✗ System stats test failed!")
        sys.exit(1)
