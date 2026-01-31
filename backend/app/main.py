"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from backend.app.api.v1.api import api_router
from backend.app.core.config import settings
from backend.app.core.logging_config import configure_logging
from backend.app.core.state_manager import ApplicationState, init_app_state
from backend.app.ingesters.registry import Ingesters
from src.loaders.sql_loaders import init_jvm_for_ucanaccess


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:  # pylint: disable=unused-argument, redefined-outer-name
    """Application lifespan events."""
    # Configure logging first
    configure_logging(
        log_dir=settings.LOGS_DIR,
        log_level=settings.LOG_LEVEL,
        enable_file_logging=settings.LOG_FILE_ENABLED,
        enable_console_logging=settings.LOG_CONSOLE_ENABLED,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression=settings.LOG_COMPRESSION,
    )

    logger.info("")
    logger.info("Starting Shape Shifter Project Editor API")
    logger.info(f"Version: {settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Initialize application state (NO default config loading)
    logger.info(f"Project directory: {settings.PROJECTS_DIR}")
    app_state: ApplicationState = init_app_state(settings.PROJECTS_DIR)
    await app_state.start()

    # Initialize JVM for UCanAccess (MS Access database support)
    # Must be done once at startup, as JPype doesn't allow JVM restart
    logger.info("Initializing JVM for MS Access database support...")
    init_jvm_for_ucanaccess()

    Ingesters.discover(search_paths=settings.INGESTER_PATHS, enabled_only=settings.ENABLED_INGESTERS)

    logger.info("Application ready - configurations loaded on-demand via sessions")

    yield

    # Cleanup
    await app_state.stop()
    logger.info("Shutting down Shape Shifter Project Editor API")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="REST API for editing Shape Shifter YAML projects",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# logger.debug("Configuring FastAPI application")
# logger.debug(f"Allowed CORS origins: {settings.ALLOWED_ORIGINS}")
# logger.debug(f"Allowed CORS origin regex: {settings.ALLOWED_ORIGIN_REGEX}")


# Exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch all unhandled exceptions and log with full traceback."""
    logger.exception(f"Unhandled exception during {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
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


# Serve static frontend files (production mode)
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists() and frontend_dist.is_dir():
    logger.info(f"Serving frontend from: {frontend_dist}")
    # Mount static files (JS, CSS, assets)
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")
    # Serve index.html for all non-API routes (SPA routing)
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
else:
    logger.info(f"Frontend dist directory not found: {frontend_dist}")
    logger.info("Running in API-only mode. Build frontend with 'cd frontend && pnpm run build'")

    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint - redirect to docs (API-only mode)."""
        return {
            "message": "Shape Shifter Project Editor API",
            "version": settings.VERSION,
            "docs": f"{settings.API_V1_PREFIX}/docs",
        }
