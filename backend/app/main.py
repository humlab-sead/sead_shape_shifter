"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.app.api.v1.api import api_router
from backend.app.core.config import settings
from backend.app.core.state_manager import init_app_state


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:  # pylint: disable=unused-argument, redefined-outer-name
    """Application lifespan events."""
    logger.info("Starting Shape Shifter Configuration Editor API")
    logger.info(f"Version: {settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Initialize application state (NO default config loading)
    logger.info(f"Configuration directory: {settings.CONFIGURATIONS_DIR}")
    app_state = init_app_state(settings.CONFIGURATIONS_DIR)
    await app_state.start()

    logger.info("Application ready - configurations loaded on-demand via sessions")

    yield

    # Cleanup
    await app_state.stop()
    logger.info("Shutting down Shape Shifter Configuration Editor API")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="REST API for editing Shape Shifter YAML configurations",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=settings.ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint - redirect to docs."""
    return {
        "message": "Shape Shifter Configuration Editor API",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_PREFIX}/docs",
    }
