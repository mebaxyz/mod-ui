"""
Configuration settings for WebSocket Gateway Service
"""

import os
from typing import List, Optional


class WebSocketGatewayConfig:
    """Configuration for WebSocket Gateway Service"""

    # Service settings
    HOST: str = os.getenv("WEBSOCKET_GATEWAY_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("WEBSOCKET_GATEWAY_PORT", "8081"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Redis settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")

    # Redis channels
    REDIS_CHANNEL_PREFIX: str = os.getenv("REDIS_CHANNEL_PREFIX", "mod_ui")

    # WebSocket settings
    WEBSOCKET_HEARTBEAT_INTERVAL: int = int(
        os.getenv("WEBSOCKET_HEARTBEAT_INTERVAL", "30")
    )
    WEBSOCKET_TIMEOUT: int = int(os.getenv("WEBSOCKET_TIMEOUT", "300"))
    MAX_CONNECTIONS: int = int(os.getenv("MAX_CONNECTIONS", "100"))

    # Message settings
    MAX_MESSAGE_SIZE: int = int(os.getenv("MAX_MESSAGE_SIZE", "10485760"))  # 10MB
    MESSAGE_QUEUE_SIZE: int = int(os.getenv("MESSAGE_QUEUE_SIZE", "1000"))

    # Event routing settings
    EVENT_BUFFER_SIZE: int = int(os.getenv("EVENT_BUFFER_SIZE", "1000"))
    EVENT_BATCH_SIZE: int = int(os.getenv("EVENT_BATCH_SIZE", "10"))
    EVENT_BATCH_TIMEOUT: float = float(os.getenv("EVENT_BATCH_TIMEOUT", "0.1"))

    # Service discovery
    SERVICE_REGISTRY_TTL: int = int(os.getenv("SERVICE_REGISTRY_TTL", "60"))
    HEALTH_CHECK_INTERVAL: int = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))

    # Default subscriptions for backward compatibility
    DEFAULT_SUBSCRIPTIONS: List[str] = [
        "session_transport_changed",
        "pedalboard_loaded",
        "pedalboard_changed",
        "plugin_parameter_changed",
        "system_stats_updated",
        "hardware_status_updated",
    ]

    # Legacy WebSocket paths for backward compatibility
    LEGACY_WEBSOCKET_PATHS: List[str] = [
        "/websocket",
        "/ws",
        "/socket.io/",  # If Socket.IO compatibility is needed
    ]

    # Rate limiting
    RATE_LIMIT_MESSAGES_PER_MINUTE: int = int(
        os.getenv("RATE_LIMIT_MESSAGES_PER_MINUTE", "1000")
    )
    RATE_LIMIT_SUBSCRIPTIONS_PER_MINUTE: int = int(
        os.getenv("RATE_LIMIT_SUBSCRIPTIONS_PER_MINUTE", "100")
    )

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Metrics
    ENABLE_METRICS: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", "8082"))

    @classmethod
    def get_redis_url(cls) -> str:
        """Get Redis connection URL"""
        auth = f":{cls.REDIS_PASSWORD}@" if cls.REDIS_PASSWORD else ""
        return f"redis://{auth}{cls.REDIS_HOST}:{cls.REDIS_PORT}/{cls.REDIS_DB}"

    @classmethod
    def get_redis_channel(cls, channel: str) -> str:
        """Get full Redis channel name with prefix"""
        return f"{cls.REDIS_CHANNEL_PREFIX}:{channel}"

    @classmethod
    def validate(cls) -> None:
        """Validate configuration settings"""
        if cls.PORT < 1 or cls.PORT > 65535:
            raise ValueError(f"Invalid port: {cls.PORT}")

        if cls.MAX_CONNECTIONS < 1:
            raise ValueError(f"Invalid max_connections: {cls.MAX_CONNECTIONS}")

        if cls.WEBSOCKET_TIMEOUT < 1:
            raise ValueError(f"Invalid websocket_timeout: {cls.WEBSOCKET_TIMEOUT}")

        if cls.MESSAGE_QUEUE_SIZE < 1:
            raise ValueError(f"Invalid message_queue_size: {cls.MESSAGE_QUEUE_SIZE}")

        if cls.EVENT_BUFFER_SIZE < 1:
            raise ValueError(f"Invalid event_buffer_size: {cls.EVENT_BUFFER_SIZE}")


# Global config instance
config = WebSocketGatewayConfig()
