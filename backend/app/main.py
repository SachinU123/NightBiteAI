"""
NightBite AI — FastAPI Application Entry Point

Late-Night Food Risk Analyzer
Analyzes online food orders (10 PM – 4 AM window) for NCD risk patterns.
AI Provider: Anthropic Claude only.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.router import api_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "NightBite AI — Late-Night Food Risk Analyzer API\n\n"
            "Analyzes food orders from Android notification capture or manual entry.\n"
            "Focuses on the late-night window (10 PM – 4 AM) for NCD risk awareness.\n"
            "Returns risk scores, AI-generated smart nudges, healthier alternatives,\n"
            "grouped history analytics, and Claude-powered behavioral insights.\n\n"
            f"**Public base URL (for Android device):** `{settings.PUBLIC_BASE_URL}`\n"
            f"**AI Provider:** Anthropic Claude (`{settings.CLAUDE_MODEL}`)"
        ),
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — allow credentials for Android clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=settings.ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount all API routes
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # ── Health routes ──────────────────────────────────────────────────────────

    @app.get("/", tags=["health"])
    def root():
        return {
            "status": "ok",
            "service": settings.APP_NAME,
            "version": "2.0.0",
            "docs": "/docs",
            "api_prefix": settings.API_V1_PREFIX,
            "public_url": settings.PUBLIC_BASE_URL,
            "ai_provider": "anthropic",
            "ai_model": settings.CLAUDE_MODEL,
        }

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "healthy", "env": settings.APP_ENV}

    @app.get("/health/db", tags=["health"])
    def health_db():
        """Check database connectivity."""
        try:
            from app.db.session import SessionLocal
            import sqlalchemy
            db = SessionLocal()
            db.execute(sqlalchemy.text("SELECT 1"))
            db.close()
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            return {"status": "unhealthy", "database": "error", "detail": str(e)}

    @app.get("/health/ai", tags=["health"])
    def health_ai():
        """Check Anthropic Claude AI connectivity."""
        from app.services.claude_service import health_check
        return health_check(timeout_seconds=10.0)

    logger.info(f"🌙 {settings.APP_NAME} v2.0 starting in {settings.APP_ENV} mode")
    logger.info(f"📱 Android clients should connect to: {settings.PUBLIC_BASE_URL}")
    logger.info(
        f"🤖 Claude AI: {'enabled' if settings.ENABLE_LLM_ENHANCEMENT else 'disabled'} "
        f"(model: {settings.CLAUDE_MODEL})"
    )
    return app


app = create_app()
