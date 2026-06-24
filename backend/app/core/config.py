from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "Millenium Radius API"
    API_V1_STR: str = "/api/v1"

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/millenium_radius"
    )

    # Security & Authentication Configuration
    SECRET_KEY: str = Field(
        default="949f50f553ef7183e950882e34ff6c875d19bfd8112d8a562477c7d42cf38a08"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # Default: 8 days

settings = Settings()
