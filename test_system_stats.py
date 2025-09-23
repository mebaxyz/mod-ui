#!/usr/bin/env python3
"""
Test script for the System Stats Service

This script tests the system stats service using the new simplified package.
"""

import asyncio
import logging
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, "/home/nicolas/project/madeline/mod-ui/src")

from mod_ui.common import RequestType, ServiceClient


async def test_system_stats_service():
    """Test the system stats service"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Create service client
    client = ServiceClient()

    try:
        logger.info("Testing system info request...")

        # Test system info
        response = await client.make_request(
            request_type=RequestType.GET_SYSTEM_INFO,
            data={},
            service_name="system-stats-service",
            timeout=10.0,
            correlation_id="test-system-info",
        )

        if response.status == "success":
            logger.info("✅ System info request successful!")
            logger.info(f"Hardware: {response.data.get('hwname', 'Unknown')}")
            logger.info(f"CPU: {response.data.get('cpu', 'Unknown')}")
            logger.info(f"Architecture: {response.data.get('architecture', 'Unknown')}")
        else:
            logger.error(f"❌ System info request failed: {response.error_message}")

        logger.info("\nTesting system stats request...")

        # Test system stats
        response = await client.make_request(
            request_type="get_system_stats",
            data={},
            service_name="system-stats-service",
            timeout=10.0,
            correlation_id="test-system-stats",
        )

        if response.status == "success":
            logger.info("✅ System stats request successful!")
            logger.info(f"CPU Load: {response.data.get('cpu_load', 0):.1f}%")
            logger.info(f"Memory Usage: {response.data.get('mem_usage', 0):.1f}%")
            logger.info(f"Disk Usage: {response.data.get('disk_usage', 0):.1f}%")
        else:
            logger.error(f"❌ System stats request failed: {response.error_message}")

    except Exception as e:
        logger.error(f"Test failed with exception: {e}")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_system_stats_service())
