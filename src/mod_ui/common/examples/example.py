#!/usr/bin/env python3
"""
Example usage of the MOD UI Common Service Communication Package

This script demonstrates how to use the ServiceClient to make requests
to backend services.
"""

import asyncio
import logging
from mod_ui.common import ServiceClient, RequestType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_system_info_request():
    """Example of requesting system information from a backend service"""
    logger.info("Making system info request...")

    try:
        async with ServiceClient() as client:
            response = await client.make_request(
                request_type=RequestType.GET_SYSTEM_INFO,
                data={},
                service_name="system-service",
                timeout=5.0
            )

            if response.status == "success":
                logger.info("System info received:")
                for key, value in response.data.items():
                    logger.info(f"  {key}: {value}")
            else:
                logger.error(f"Request failed: {response.error_message}")

    except Exception as e:
        logger.error(f"Request failed with exception: {e}")


async def example_custom_request():
    """Example of making a custom request"""
    logger.info("Making custom request...")

    try:
        async with ServiceClient() as client:
            response = await client.make_request(
                request_type="custom_action",
                data={"parameter": "value", "count": 42},
                service_name="my-service",
                timeout=3.0
            )

            logger.info(f"Response status: {response.status}")
            logger.info(f"Response data: {response.data}")

    except Exception as e:
        logger.error(f"Custom request failed: {e}")


async def example_session_request():
    """Example of session-related request"""
    logger.info("Making session state request...")

    try:
        async with ServiceClient() as client:
            response = await client.make_request(
                request_type=RequestType.GET_SESSION_STATE,
                data={},
                service_name="session-service"
            )

            if response.status == "success":
                logger.info("Session state received")
                logger.info(f"Session data: {response.data}")
            else:
                logger.warning(f"Session request failed: {response.error_message}")

    except Exception as e:
        logger.error(f"Session request failed: {e}")


async def main():
    """Main example function"""
    logger.info("Starting MOD UI Service Communication Examples")

    # Example 1: System info
    await example_system_info_request()

    print("\n" + "="*50 + "\n")

    # Example 2: Custom request
    await example_custom_request()

    print("\n" + "="*50 + "\n")

    # Example 3: Session request
    await example_session_request()

    logger.info("Examples completed")


if __name__ == "__main__":
    asyncio.run(main())