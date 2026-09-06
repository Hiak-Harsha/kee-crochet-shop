import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "Kee Crochet AI Platform"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # JWT Auth & Sessions
    SECRET_KEY: str = os.getenv("SECRET_KEY", "cozy_crochet_yarn_secret_key_1234567890_change_me_in_prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived access token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    SESSION_COOKIE_NAME: str = "kc_refresh_token"
    OTP_EXPIRE_MINUTES: int = 10
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./crochet.db")
    
    # Redis (Optional in local dev, recommended in distributed prod)
    REDIS_URL: str | None = os.getenv("REDIS_URL", None)
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str | None = os.getenv("GOOGLE_CLIENT_ID", None)
    
    # Razorpay Payment Gateway
    RAZORPAY_KEY_ID: str | None = os.getenv("RAZORPAY_KEY_ID", None)
    RAZORPAY_KEY_SECRET: str | None = os.getenv("RAZORPAY_KEY_SECRET", None)
    
    # AI Services
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY", None)
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    # Media Storage (Cloudinary / S3 / R2 / local fallback)
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local")  # "cloudinary", "s3", "r2", "local"
    CLOUDINARY_CLOUD_NAME: str | None = os.getenv("CLOUDINARY_CLOUD_NAME", None)
    CLOUDINARY_API_KEY: str | None = os.getenv("CLOUDINARY_API_KEY", None)
    CLOUDINARY_API_SECRET: str | None = os.getenv("CLOUDINARY_API_SECRET", None)
    
    AWS_ACCESS_KEY_ID: str | None = os.getenv("AWS_ACCESS_KEY_ID", None)
    AWS_SECRET_ACCESS_KEY: str | None = os.getenv("AWS_SECRET_ACCESS_KEY", None)
    AWS_S3_BUCKET: str | None = os.getenv("AWS_S3_BUCKET", None)
    AWS_S3_REGION: str | None = os.getenv("AWS_S3_REGION", "ap-south-1")
    CDN_BASE_URL: str | None = os.getenv("CDN_BASE_URL", None)
    
    # Email Services
    RESEND_API_KEY: str | None = os.getenv("RESEND_API_KEY", None)
    MAIL_FROM: str = os.getenv("MAIL_FROM", "Kee Crochet <onboarding@resend.dev>")
    
    # SMS Services
    MSG91_AUTH_KEY: str | None = os.getenv("MSG91_AUTH_KEY", None)
    MSG91_TEMPLATE_ID: str | None = os.getenv("MSG91_TEMPLATE_ID", None)
    TWILIO_ACCOUNT_SID: str | None = os.getenv("TWILIO_ACCOUNT_SID", None)
    TWILIO_AUTH_TOKEN: str | None = os.getenv("TWILIO_AUTH_TOKEN", None)
    TWILIO_FROM_NUMBER: str | None = os.getenv("TWILIO_FROM_NUMBER", None)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def validate_production_configuration(self) -> None:
        """Fail fast at startup if required configuration is missing in production."""
        if self.ENVIRONMENT != "production":
            return
            
        missing: list[str] = []
        if not self.SECRET_KEY or self.SECRET_KEY == "cozy_crochet_yarn_secret_key_1234567890_change_me_in_prod":
            missing.append("SECRET_KEY must be set to a cryptographically random secret string in production.")
            
        if not self.DATABASE_URL or "sqlite" in self.DATABASE_URL:
            missing.append("DATABASE_URL must be configured with a production PostgreSQL connection string.")
            
        if not self.FRONTEND_URL:
            missing.append("FRONTEND_URL must be configured.")
            
        if not self.RAZORPAY_KEY_ID or not self.RAZORPAY_KEY_SECRET:
            missing.append("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be configured for real payment processing.")
            
        if self.STORAGE_PROVIDER == "local":
            missing.append("STORAGE_PROVIDER must be configured with object storage ('cloudinary', 's3', or 'r2') in production.")
            
        if missing:
            raise RuntimeError(
                "CRITICAL PRODUCTION CONFIGURATION ERROR:\n" + "\n".join(f"- {m}" for m in missing)
            )


settings = Settings()
