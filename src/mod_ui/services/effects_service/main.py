"""
Effects Service - Pure Redis pub/sub service for managing effects/plugins
"""

import asyncio
import logging
from typing import Any, Dict

from mod_ui.common import ServiceServer
from mod_ui.common.config import get_redis_url_from_env

from .handlers import EffectsServiceHandlers

logger = logging.getLogger(__name__)


async def main():
    """Main entry point for the Effects Service"""

    # Initialize handlers
    handlers = EffectsServiceHandlers()

    # Get Redis URL from environment
    redis_url = get_redis_url_from_env()
    logger.info(f"Using Redis URL: {redis_url}")

    # Create service server
    server = ServiceServer("effects_service", redis_url=redis_url)

    # Register handlers
    server.register_handler("effect_add", handlers.handle_effect_add)
    server.register_handler("effect_remove", handlers.handle_effect_remove)
    server.register_handler("effect_get", handlers.handle_effect_get)
    server.register_handler("effect_list", handlers.handle_effect_list)
    server.register_handler("effect_connect", handlers.handle_effect_connect)
    server.register_handler("effect_disconnect", handlers.handle_effect_disconnect)
    server.register_handler(
        "effect_parameter_set", handlers.handle_effect_parameter_set
    )
    server.register_handler(
        "effect_parameter_address", handlers.handle_effect_parameter_address
    )
    server.register_handler("effect_preset_load", handlers.handle_effect_preset_load)
    server.register_handler("effect_preset_save", handlers.handle_effect_preset_save)
    server.register_handler(
        "effect_preset_delete", handlers.handle_effect_preset_delete
    )
    server.register_handler("effect_image", handlers.handle_effect_image)
    server.register_handler("effect_file", handlers.handle_effect_file)

    logger.info("Effects Service starting...")

    try:
        async with server:
            logger.info("Effects Service started successfully")

            # Keep the service running
            while True:
                await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Effects Service error: {e}")
        raise

    logger.info("Effects Service stopped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
