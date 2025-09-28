#!/usr/bin/env python3
"""
Test script for the System Stats Service

This script tests the system stats service using the new simplified package.
"""

import asyncio
import logging
import sys

# Add the project root to the Python path
sys.path.insert(0, "/home/nicolas/project/madeline/mod-ui/src")

from servicebus import CommConfig, ServiceClient, set_config


async def test_system_stats_service():
    """Test the system stats service"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Configure ServiceBus
    config = CommConfig(redis_url="redis://localhost:6379/0")
    set_config(config)

    # Create service client
    client = ServiceClient("test_client")

    try:
        logger.info("Testing system info request...")

        # Test system info
        response = await client.call(
            target_service="system-stats-service",
            request_type="get_system_info",
            data={},
            timeout=10.0,
        )

        if response is not None:
            logger.info("✅ System info request successful!")
            logger.info(f"Hardware: {response.get('hwname', 'Unknown')}")
            logger.info(f"CPU: {response.get('cpu', 'Unknown')}")
            logger.info(f"Architecture: {response.get('architecture', 'Unknown')}")
        else:
            logger.error("❌ System info request failed")

        logger.info("\nTesting system stats request...")

        # Test system stats
        response = await client.call(
            target_service="system-stats-service",
            request_type="get_system_stats",
            data={},
            timeout=10.0,
        )

        if response is not None:
            logger.info("✅ System stats request successful!")
            logger.info(f"CPU Load: {response.get('cpu_load', 0):.1f}%")
            logger.info(f"Memory Usage: {response.get('mem_usage', 0):.1f}%")
            logger.info(f"Disk Usage: {response.get('disk_usage', 0):.1f}%")
        else:
            logger.error("❌ System stats request failed")

    except Exception as e:
        logger.error(f"Test failed with exception: {e}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_system_stats_service())
