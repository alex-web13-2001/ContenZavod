"""ContenZavod — AI-powered content management platform.

FastAPI application factory with middleware, routers, and lifecycle management.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.v1.router import api_router
import workers.celery_app  # Initialize Celery conf so endpoints route tasks correctly


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifecycle: startup and shutdown events."""
    # Startup
    settings = get_settings()
    import structlog

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(settings.log_level),
    )
    logger = structlog.get_logger()
    logger.info("contenzavod.startup", env=settings.app_env, debug=settings.app_debug)

    yield

    # Shutdown
    from app.database import engine

    await engine.dispose()
    logger.info("contenzavod.shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI-управляемая платформа полного цикла контент-менеджмента",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(api_router, prefix="/api/v1")

    return app


# Module-level app instance for uvicorn
app = create_app()
