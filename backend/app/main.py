"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.app.api.v1.api import api_router
from backend.app.core.config import settings
from src.configuration.provider import ConfigStore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:  # pylint: disable=unused-argument, redefined-outer-name
    """Application lifespan events."""
    logger.info("Starting Shape Shifter Configuration Editor API")
    logger.info(f"Version: {settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Initialize configuration context
    config_file = os.getenv("CONFIG_FILE", "input/query_tester_config.yml")
    logger.info(f"Loading configuration from: {config_file}")
    try:
        ConfigStore.get_instance().configure_context(source=config_file)
        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise

    yield
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
