import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "Kee Crochet AI Platform"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # JWT Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "cozy_crochet_yarn_secret_key_1234567890_change_me_in_prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    OTP_EXPIRE_MINUTES: int = 10
    
    # Database
    # Using SQLite + aiosqlite as fallback for easy local runs, Postgres in prod.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./crochet.db")
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str | None = os.getenv("GOOGLE_CLIENT_ID", None)
    
    # Razorpay Payment Gateway
    RAZORPAY_KEY_ID: str | None = os.getenv("RAZORPAY_KEY_ID", None)
    RAZORPAY_KEY_SECRET: str | None = os.getenv("RAZORPAY_KEY_SECRET", None)
    
    # AI Services
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY", None)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
