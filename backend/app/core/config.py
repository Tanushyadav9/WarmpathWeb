"""
backend/app/core/config.py - Central configuration using pydantic-settings.
"""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    PROJECT_NAME: str = "WarmPath"
    ENVIRONMENT: str = "development"
    DEMO_MODE: bool = True
    PORT: int = 8000
    APP_SECRET_KEY: str = "warmpath-insecure-secret-key-change-in-production"

    # Database & Redis
    DATABASE_URL: str = "postgresql+asyncpg://warmpath:secretpassword@localhost:5432/warmpath_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Authentication & Security
    JWT_SECRET: str = "warmpath-jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 60
    REFRESH_TOKEN_DAYS: int = 30

    # SMTP (Email OTP)
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "no-reply@warmpath.org"

    # AI (Gemini)
    GEMINI_API_KEY: str = ""
    GEMINI_TEXT_MODEL: str = "gemini-1.5-flash"
    GEMINI_EMBED_MODEL: str = "text-embedding-004"

    # Payments (Razorpay test mode)
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # Push notifications & Meetings
    FCM_SERVICE_ACCOUNT_PATH: str = ""
    JITSI_BASE_URL: str = "https://meet.jit.si"

    # Domain defaults from PROJECT_CONTEXT Section 6
    PRIOR_MEAN: float = 4.0
    PRIOR_WEIGHT: int = 5
    MIN_RATED_SESSIONS_BAND: int = 5

    # Rating Band Thresholds
    TRUSTED_RATING_THRESHOLD: float = 4.2
    TRUSTED_MIN_SESSIONS: int = 5
    TOP_RATED_THRESHOLD: float = 4.6
    TOP_RATED_MIN_SESSIONS: int = 10
    TOP_RATED_MIN_COMPLETION_RATE: float = 0.90

    # Payout shares
    PAYOUT_SHARE_RISING: float = 0.60
    PAYOUT_SHARE_TRUSTED: float = 0.70
    PAYOUT_SHARE_TOP_RATED: float = 0.80

    # Plans (INR)
    PLAN_CAMPUS_PRICE: int = 0
    PLAN_CAMPUS_CREDITS: int = 0
    PLAN_STANDARD_PRICE: int = 299
    PLAN_STANDARD_CREDITS: int = 1
    PLAN_HIGH_PRICE: int = 499
    PLAN_HIGH_CREDITS: int = 2
    PLAN_PREMIUM_PRICE: int = 899
    PLAN_PREMIUM_CREDITS: int = 4

    # Booking Horizons (Days)
    BOOKING_HORIZON_STANDARD: int = 3
    BOOKING_HORIZON_HIGH: int = 14
    BOOKING_HORIZON_PREMIUM: int = 30

    # Session Rules
    MIN_CALL_DURATION_MINUTES: int = 5
    DISPUTE_WINDOW_HOURS: int = 48
    AUTO_REFUND_HOURS: int = 72

    # Daily Request Limits by Trust Level
    REQUEST_LIMIT_NEW: int = 3
    REQUEST_LIMIT_VERIFIED: int = 10
    REQUEST_LIMIT_ESTABLISHED: int = 25
    REQUEST_LIMIT_RESTRICTED: int = 1


settings = Settings()
