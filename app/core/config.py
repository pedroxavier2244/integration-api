from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "Integration API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    API_PREFIX: str = "/api/v1"
    ALLOWED_HOSTS: List[str] = ["*"]

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_INVITE_TOKEN_EXPIRE_HOURS: int = 48
    JWT_RESET_TOKEN_EXPIRE_HOURS: int = 1

    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    REDIS_URL: str = "redis://localhost:6379/0"

    SMTP_HOST: str = "smtp.office365.com"
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM: str
    SMTP_TLS: bool = True

    FRONTEND_URL: str = "http://localhost:3000"
    RATE_LIMIT_LOGIN: str = "5/minute"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
