"""
NightBite AI — Centralized Configuration

All environment variables are defined and validated here.
AI provider: Anthropic Claude only (no Gemini, no OpenAI).
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import json


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "NightBite AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # ── Server ────────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── JWT ───────────────────────────────────────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    ALLOW_CREDENTIALS: bool = True

    # ── Anthropic Claude AI (sole AI provider) ────────────────────────────────
    CLAUDE_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-haiku-4-5"   # Current model (March 2026) — replaces deprecated claude-3-5-haiku-20241022
    ENABLE_LLM_ENHANCEMENT: bool = True
    AI_TIMEOUT_SECONDS: float = 25.0
    AI_MAX_TOKENS_SHORT: int = 400    # For short nudges / short coach replies
    AI_MAX_TOKENS_LONG: int = 900     # For detailed explanations / full AI coach

    # ── Android / Real device ─────────────────────────────────────────────────
    PUBLIC_BASE_URL: str = "http://192.168.0.101:8000"
    ANDROID_CLIENT_TIMEOUT_SECONDS: int = 30

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            # Support both JSON array and comma-separated
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
