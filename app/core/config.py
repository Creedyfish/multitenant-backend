from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Auth settings
    SECRET_KEY: str = Field(..., description="Secret key for JWT encoding")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENV: str = Field(..., description="env")

    # API settings
    API_PREFIX: str = "/api"
    API_VERSION: str = "v1"
    PROJECT_NAME: str = "My API"
    DEBUG: bool = False

    # Database settings
    DATABASE_URL: str = Field(..., description="database url")
    DATABASE_URL_TESTING: str = Field(..., description="test database url")
    model_config = SettingsConfigDict(env_file=".env")

    # Services settings
    RESEND_API: str = Field(..., description="resend api")

    @property
    def API_BASE(self) -> str:
        return f"{self.API_PREFIX}/{self.API_VERSION}"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


# Usage
settings = get_settings()
