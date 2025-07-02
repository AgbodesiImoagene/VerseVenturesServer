"""
Configuration settings for the subscription server.
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv(".env")


class Settings:
    """Application settings loaded from environment variables."""

    # Database Configuration
    DB_HOST: str = os.environ.get("DB_HOST", "localhost")
    DB_PORT: int = int(os.environ.get("DB_PORT", "5432"))
    DB_USER: str = os.environ.get("DB_USER", "postgres")
    DB_PASSWORD: str = os.environ.get("DB_PASSWORD", "")
    DB_NAME: str = os.environ.get("DB_NAME", "verseventures_subscriptions")

    # Stripe Configuration
    STRIPE_SECRET_KEY: Optional[str] = os.environ.get("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[str] = os.environ.get("STRIPE_WEBHOOK_SECRET")

    # JWT Configuration
    JWT_SECRET: str = os.environ.get("JWT_SECRET", "your-secret-key")

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: Optional[str] = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.environ.get("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = os.environ.get(
        "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
    )

    # AWS Configuration
    AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")
    TRANSCRIBE_ROLE_ARN: Optional[str] = os.environ.get("TRANSCRIBE_ROLE_ARN")
    SESSION_DURATION: int = int(os.environ.get("SESSION_DURATION", "900"))

    # Email Configuration
    SMTP_HOST: str = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME: Optional[str] = os.environ.get("SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = os.environ.get("SMTP_PASSWORD")
    FROM_EMAIL: str = os.environ.get("FROM_EMAIL", "noreply@verseventures.com")
    FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    # Application Configuration
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

    @property
    def database_url(self) -> str:
        """Get database connection URL."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT.lower() == "production"


# Global settings instance
settings = Settings()
