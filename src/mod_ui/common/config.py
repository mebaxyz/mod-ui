"""
Configuration Management Improvements

Enhanced configuration system with environment variables, validation, and presets.
"""

import os
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class Environment(str, Enum):
    """Deployment environment types"""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


def get_redis_url_from_env() -> str:
    """
    Build Redis URL from environment variables or REDIS_URL directly.

    Priority:
    1. REDIS_URL (if set directly)
    2. REDIS_HOST, REDIS_PORT, REDIS_DB components
    3. Default localhost
    """
    # Check if REDIS_URL is set directly
    if redis_url := os.getenv("REDIS_URL"):
        return redis_url

    # Build from components
    host = os.getenv("REDIS_HOST", "localhost")
    port = os.getenv("REDIS_PORT", "6379")
    db = os.getenv("REDIS_DB", "0")

    return f"redis://{host}:{port}/{db}"


class ServiceClientConfig(BaseModel):
    """Enhanced ServiceClient configuration with validation"""

    redis_url: str = Field(default_factory=get_redis_url_from_env)
    default_timeout: float = Field(default=5.0, ge=0.1, le=300.0)
    max_retries: int = Field(default=1, ge=0, le=10)
    connection_pool_size: int = Field(default=10, ge=1, le=100)
    enable_logging: bool = Field(default=True)
    log_level: str = Field(default="INFO")

    @validator("redis_url")
    def validate_redis_url(cls, v):
        if not v.startswith(("redis://", "rediss://")):
            raise ValueError("Redis URL must start with redis:// or rediss://")
        return v

    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    @classmethod
    def from_environment(
        cls, env: Environment = Environment.DEVELOPMENT
    ) -> "ServiceClientConfig":
        """Create configuration from environment variables and presets"""

        # Environment-specific defaults
        env_defaults = {
            Environment.DEVELOPMENT: {
                "default_timeout": 2.0,
                "max_retries": 1,
                "log_level": "DEBUG",
            },
            Environment.TESTING: {
                "default_timeout": 1.0,
                "max_retries": 0,
                "log_level": "WARNING",
            },
            Environment.STAGING: {
                "default_timeout": 5.0,
                "max_retries": 2,
                "log_level": "INFO",
            },
            Environment.PRODUCTION: {
                "default_timeout": 10.0,
                "max_retries": 3,
                "log_level": "WARNING",
            },
        }

        # Start with environment defaults
        config_data = env_defaults.get(env, {})

        # Override with environment variables
        config_data.update(
            {
                "redis_url": get_redis_url_from_env(),
                "default_timeout": float(
                    os.getenv(
                        "SERVICE_TIMEOUT", config_data.get("default_timeout", 5.0)
                    )
                ),
                "max_retries": int(
                    os.getenv("SERVICE_MAX_RETRIES", config_data.get("max_retries", 1))
                ),
                "connection_pool_size": int(os.getenv("REDIS_POOL_SIZE", 10)),
                "enable_logging": os.getenv("ENABLE_LOGGING", "true").lower() == "true",
                "log_level": os.getenv(
                    "LOG_LEVEL", config_data.get("log_level", "INFO")
                ),
            }
        )

        return cls(**config_data)


class ServiceServerConfig(BaseModel):
    """Enhanced ServiceServer configuration"""

    service_name: str
    redis_url: str = Field(default_factory=get_redis_url_from_env)
    max_concurrent_handlers: int = Field(default=100, ge=1, le=1000)
    handler_timeout: float = Field(default=30.0, ge=1.0, le=300.0)
    enable_metrics: bool = Field(default=True)
    health_check_interval: float = Field(default=30.0, ge=5.0, le=300.0)

    @classmethod
    def from_environment(
        cls, service_name: str, env: Environment = Environment.DEVELOPMENT
    ) -> "ServiceServerConfig":
        """Create server configuration from environment"""

        env_defaults = {
            Environment.DEVELOPMENT: {
                "max_concurrent_handlers": 10,
                "handler_timeout": 10.0,
                "health_check_interval": 60.0,
            },
            Environment.PRODUCTION: {
                "max_concurrent_handlers": 100,
                "handler_timeout": 30.0,
                "health_check_interval": 30.0,
            },
        }

        config_data = env_defaults.get(env, {})
        config_data.update(
            {
                "service_name": service_name,
                "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
                "max_concurrent_handlers": int(
                    os.getenv(
                        "MAX_CONCURRENT_HANDLERS",
                        config_data.get("max_concurrent_handlers", 100),
                    )
                ),
                "handler_timeout": float(
                    os.getenv(
                        "HANDLER_TIMEOUT", config_data.get("handler_timeout", 30.0)
                    )
                ),
                "enable_metrics": os.getenv("ENABLE_METRICS", "true").lower() == "true",
                "health_check_interval": float(
                    os.getenv(
                        "HEALTH_CHECK_INTERVAL",
                        config_data.get("health_check_interval", 30.0),
                    )
                ),
            }
        )

        return cls(**config_data)


def get_environment() -> Environment:
    """Auto-detect current environment"""
    env_name = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()

    env_mapping = {
        "dev": Environment.DEVELOPMENT,
        "development": Environment.DEVELOPMENT,
        "test": Environment.TESTING,
        "testing": Environment.TESTING,
        "stage": Environment.STAGING,
        "staging": Environment.STAGING,
        "prod": Environment.PRODUCTION,
        "production": Environment.PRODUCTION,
    }

    return env_mapping.get(env_name, Environment.DEVELOPMENT)


# Preset configurations for common scenarios
PRESET_CONFIGS = {
    "microservice": ServiceClientConfig(
        default_timeout=5.0, max_retries=2, connection_pool_size=20
    ),
    "high_throughput": ServiceClientConfig(
        default_timeout=1.0, max_retries=1, connection_pool_size=50
    ),
    "reliable": ServiceClientConfig(
        default_timeout=15.0, max_retries=5, connection_pool_size=10
    ),
    "testing": ServiceClientConfig(
        default_timeout=0.5, max_retries=0, connection_pool_size=5, log_level="WARNING"
    ),
}


def get_preset_config(preset_name: str) -> Optional[ServiceClientConfig]:
    """Get a preset configuration by name"""
    return PRESET_CONFIGS.get(preset_name)
