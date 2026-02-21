"""API endpoints for application logs."""

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from backend.app.core.config import get_settings

router = APIRouter()

LogType = Literal["app", "error"]


@router.get("/logs/{log_type}")
async def get_logs(
    log_type: LogType,
    lines: int = Query(default=500, ge=1, le=10000, description="Number of lines to fetch from end of file"),
    level: str | None = Query(default=None, description="Filter by log level (INFO, WARNING, ERROR, etc.)"),
) -> dict[str, list[str] | int]:
    """Fetch application logs.

    Args:
        log_type: Type of log file ('app' or 'error')
        lines: Number of lines to fetch from end of file (default 500, max 10000)
        level: Optional log level filter (INFO, WARNING, ERROR, CRITICAL, DEBUG)

    Returns:
        Dictionary with 'lines' (list of log lines) and 'total' (total lines returned)
    """
    settings = get_settings()
    log_dir = Path(settings.LOG_DIR)

    log_file = log_dir / f"{log_type}.log"

    if not log_file.exists():
        logger.warning(f"Log file not found: {log_file}")
        return {"lines": [], "total": 0}

    try:
        # Read last N lines efficiently
        with open(log_file, "r", encoding="utf-8") as f:
            # Read all lines and get last N
            all_lines = f.readlines()
            tail_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        # Filter by level if specified
        if level:
            level_upper = level.upper()
            filtered_lines = [line for line in tail_lines if f"| {level_upper: <8} |" in line or f"| {level_upper} |" in line]
        else:
            filtered_lines = tail_lines

        # Remove trailing newlines
        cleaned_lines = [line.rstrip("\n") for line in filtered_lines]

        return {"lines": cleaned_lines, "total": len(cleaned_lines)}

    except Exception as e:
        logger.error(f"Error reading log file {log_file}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read log file: {str(e)}") from e


@router.get("/logs/{log_type}/download")
async def download_logs(log_type: LogType) -> dict[str, str]:
    """Get download path for log file.

    Args:
        log_type: Type of log file ('app' or 'error')

    Returns:
        Dictionary with log file content as string
    """
    settings = get_settings()
    log_dir = Path(settings.LOG_DIR)
    log_file = log_dir / f"{log_type}.log"

    if not log_file.exists():
        raise HTTPException(status_code=404, detail="Log file not found")

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()

        return {"content": content, "filename": f"{log_type}.log"}

    except Exception as e:
        logger.error(f"Error reading log file for download: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read log file: {str(e)}") from e
