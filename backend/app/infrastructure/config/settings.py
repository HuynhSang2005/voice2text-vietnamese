"""Application settings and configuration."""
import logging
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Supports configuration for:
    - General application settings
    - CORS policies
    - Model storage paths
    - Content moderation
    - Database connection
    - Logging configuration
    - Dependency injection
    - Redis caching (optional)
    - Metrics and monitoring
    """
    
    # General
    PROJECT_NAME: str = "Real-time Vietnamese STT"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    
    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="List of allowed CORS origins"
    )
    
    # Model Storage
    MODEL_STORAGE_PATH: str = Field(
        default="models_storage",
        description="Base path for ML model storage"
    )
    
    # Content Moderation (ViSoBERT-HSD)
    ENABLE_CONTENT_MODERATION: bool = Field(
        default=True,
        description="Enable hate speech detection"
    )
    MODERATION_CONFIDENCE_THRESHOLD: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for moderation alerts"
    )
    MODERATION_ON_FINAL_ONLY: bool = Field(
        default=True,
        description="Only moderate final transcriptions, not interim results"
    )
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///database.db",
        description="SQLAlchemy database URL"
    )
    DATABASE_ECHO: bool = Field(
        default=False,
        description="Echo SQL statements for debugging"
    )
    DATABASE_POOL_SIZE: int = Field(
        default=5,
        ge=1,
        description="Database connection pool size"
    )
    DATABASE_MAX_OVERFLOW: int = Field(
        default=10,
        ge=0,
        description="Max connections beyond pool size"
    )
    
    # Redis (optional - for caching)
    REDIS_ENABLED: bool = Field(
        default=False,
        description="Enable Redis caching"
    )
    REDIS_URL: Optional[str] = Field(
        default=None,
        description="Redis connection URL (e.g., redis://localhost:6379/0)"
    )
    REDIS_TTL: int = Field(
        default=3600,
        ge=0,
        description="Default cache TTL in seconds"
    )
    
    # Logging
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    LOG_FORMAT: str = Field(
        default="json",
        description="Log format: 'json' for structured logs, 'text' for human-readable"
    )
    
    # Metrics & Monitoring
    ENABLE_METRICS: bool = Field(
        default=False,
        description="Enable Prometheus metrics endpoint"
    )
    METRICS_PORT: int = Field(
        default=9090,
        ge=1024,
        le=65535,
        description="Port for Prometheus metrics server"
    )
    
    # Dependency Injection
    DI_AUTO_WIRE: bool = Field(
        default=True,
        description="Automatically wire DI container"
    )
    DI_PACKAGES: List[str] = Field(
        default=["app.api", "app.application"],
        description="Packages to wire for DI"
    )
    
    @field_validator("LOG_LEVEL")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {valid_levels}")
        return v_upper
    
    @field_validator("LOG_FORMAT")
    def validate_log_format(cls, v: str) -> str:
        """Validate log format."""
        valid_formats = ["json", "text"]
        v_lower = v.lower()
        if v_lower not in valid_formats:
            raise ValueError(f"LOG_FORMAT must be one of: {valid_formats}")
        return v_lower
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Singleton settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get the settings instance (for dependency injection).
    
    Returns:
        Settings singleton
    """
    return settings


def setup_logging():
    """
    Configure application-wide logging.
    
    Supports both structured JSON logging (for production) and
    human-readable text logging (for development).
    """
    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    
    if settings.LOG_FORMAT == "json":
        # Structured logging (use structlog in Phase 3)
        logging.basicConfig(
            level=log_level,
            format='{"time":"%(asctime)s","name":"%(name)s","level":"%(levelname)s","message":"%(message)s"}',
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        # Human-readable logging
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("websockets.protocol").setLevel(logging.WARNING)
    logging.getLogger("websockets.server").setLevel(logging.WARNING)
    
    logging.info(f"Logging configured: level={settings.LOG_LEVEL}, format={settings.LOG_FORMAT}")


# Initialize logging on import
setup_logging()
