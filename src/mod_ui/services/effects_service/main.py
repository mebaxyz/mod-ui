"""
Effects Service - Pure Redis pub/sub service for managing effects/plugins
"""

import asyncio
import logging
import os
from typing import Any, Dict

from servicebus import Service, get_redis_url_from_env, set_config, CommConfig

from .handlers import EffectsServiceHandlers

logger = logging.getLogger(__name__)


async def main():
    """Main entry point for the Effects Service"""

    # Initialize handlers
    handlers = EffectsServiceHandlers()

    # Setup configuration from environment
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_db = os.getenv("REDIS_DB", "0")
    redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
    
    # Configure ServiceBus with Docker environment
    config = CommConfig(redis_url=redis_url)
    set_config(config)
    
    logger.info("Using Redis URL: %s", redis_url)

    # Create service 
    service = Service("effects_service")

    # Register handlers
    service.register_handler("effect_add", handlers.handle_effect_add)
    service.register_handler("effect_remove", handlers.handle_effect_remove)
    service.register_handler("effect_get", handlers.handle_effect_get)
    service.register_handler("effect_list", handlers.handle_effect_list)
    service.register_handler("effect_connect", handlers.handle_effect_connect)
    service.register_handler("effect_disconnect", handlers.handle_effect_disconnect)
    service.register_handler(
        "effect_parameter_set", handlers.handle_effect_parameter_set
    )
    service.register_handler(
        "effect_parameter_address", handlers.handle_effect_parameter_address
    )
    service.register_handler("effect_preset_load", handlers.handle_effect_preset_load)
    service.register_handler("effect_preset_save", handlers.handle_effect_preset_save)
    service.register_handler(
        "effect_preset_delete", handlers.handle_effect_preset_delete
    )
    service.register_handler("effect_image", handlers.handle_effect_image)
    service.register_handler("effect_file", handlers.handle_effect_file)

    logger.info("Effects Service starting...")

    try:
        async with service:
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
