"""
Configuration management for microservice communication
"""

import os
from typing import Dict, Optional

from pydantic import BaseModel, Field


class CommConfig(BaseModel):
    """Configuration for microservice communication"""

    # Redis settings
    redis_url: str = Field(default="redis://localhost:6379")
    redis_max_connections: int = Field(default=20, ge=1, le=100)
    redis_socket_keepalive: bool = Field(default=True)
    redis_socket_keepalive_options: Dict[str, int] = Field(default_factory=dict)

    # Communication settings
    default_timeout: float = Field(default=5.0, gt=0.0, le=300.0)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay: float = Field(default=0.5, ge=0.0, le=10.0)

    # Service discovery settings
    service_registry_ttl: int = Field(default=30, ge=5, le=300)  # seconds
    discovery_refresh_interval: float = Field(default=10.0, ge=1.0, le=60.0)

    # Performance settings
    enable_connection_pooling: bool = Field(default=True)
    batch_timeout: float = Field(default=0.01, ge=0.001, le=1.0)  # 10ms
    batch_size: int = Field(default=10, ge=1, le=100)

    # Caching settings
    enable_caching: bool = Field(default=True)
    cache_ttl: int = Field(default=300, ge=10, le=3600)  # 5 minutes default

    # Monitoring settings
    enable_metrics: bool = Field(default=True)
    metrics_retention_seconds: int = Field(default=3600, ge=300, le=86400)  # 1 hour

    # Event bus settings
    event_buffer_size: int = Field(default=1000, ge=10, le=10000)
    event_batch_size: int = Field(default=50, ge=1, le=500)

    # ZeroMQ settings
    zeromq_base_port: int = Field(default=5555, ge=1024, le=65535)
    zeromq_bind_address: str = Field(default="127.0.0.1")
    zeromq_rcv_timeout_ms: int = Field(default=5000, ge=1)
    zeromq_snd_timeout_ms: int = Field(default=5000, ge=1)
    zeromq_hash_modulus: int = Field(default=1000, ge=1)

    # Development settings
    debug_mode: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    @classmethod
    def from_env(cls) -> "CommConfig":
        """Create configuration from environment variables"""
        config_data = {}

        # Redis configuration
        if redis_url := os.getenv("REDIS_URL"):
            config_data["redis_url"] = redis_url
        else:
            # Build Redis URL from components
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", "6379"))
            db = int(os.getenv("REDIS_DB", "0"))
            config_data["redis_url"] = f"redis://{host}:{port}/{db}"

        # Other settings from environment
        env_mappings = {
            "COMM_DEFAULT_TIMEOUT": "default_timeout",
            "COMM_MAX_RETRIES": "max_retries",
            "COMM_RETRY_DELAY": "retry_delay",
            "COMM_SERVICE_REGISTRY_TTL": "service_registry_ttl",
            "COMM_DISCOVERY_REFRESH": "discovery_refresh_interval",
            "COMM_ENABLE_POOLING": "enable_connection_pooling",
            "COMM_BATCH_TIMEOUT": "batch_timeout",
            "COMM_BATCH_SIZE": "batch_size",
            "COMM_ENABLE_CACHING": "enable_caching",
            "COMM_CACHE_TTL": "cache_ttl",
            "COMM_ENABLE_METRICS": "enable_metrics",
            "COMM_METRICS_RETENTION": "metrics_retention_seconds",
            "COMM_DEBUG": "debug_mode",
            "COMM_LOG_LEVEL": "log_level",
            # ZeroMQ configuration
            "COMM_ZEROMQ_BASE_PORT": "zeromq_base_port",
            "COMM_ZEROMQ_BIND_ADDRESS": "zeromq_bind_address",
            "COMM_ZEROMQ_RCV_TIMEOUT_MS": "zeromq_rcv_timeout_ms",
            "COMM_ZEROMQ_SND_TIMEOUT_MS": "zeromq_snd_timeout_ms",
            "COMM_ZEROMQ_HASH_MODULUS": "zeromq_hash_modulus",
        }

        for env_var, field_name in env_mappings.items():
            if value := os.getenv(env_var):
                # Convert to appropriate type
                field_info = cls.__fields__[field_name]
                # Use outer_type_ for more reliable runtime comparisons
                field_type = field_info.outer_type_

                if field_type is bool:
                    config_data[field_name] = value.lower() in (
                        "true",
                        "1",
                        "yes",
                        "on",
                    )
                elif field_type is int:
                    config_data[field_name] = int(value)
                elif field_type is float:
                    config_data[field_name] = float(value)
                else:
                    config_data[field_name] = value

        return cls(**config_data)


def get_redis_url_from_env() -> str:
    """Get Redis URL from environment variables - backward compatibility"""
    config = CommConfig.from_env()
    return config.redis_url


# Global configuration instance
_global_config: Optional[CommConfig] = None


def get_config() -> CommConfig:
    """Get global configuration instance"""
    global _global_config
    if _global_config is None:
        _global_config = CommConfig.from_env()
    return _global_config


def set_config(config: CommConfig) -> None:
    """Set global configuration instance"""
    global _global_config
    _global_config = config
