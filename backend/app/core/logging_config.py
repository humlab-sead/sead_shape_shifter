"""Logging configuration for the backend application."""

import sys
import traceback
from pathlib import Path

from loguru import logger


def format_exception_with_filtered_frames(record: dict) -> str:
    """Format exception with filtered stack frames (removes framework noise).

    Args:
        record: Loguru record dict

    Returns:
        Formatted exception string
    """
    if not record.get("exception"):
        return ""

    exception = record["exception"]
    if not exception:
        return ""

    # Paths to filter out from stack traces
    noisy_paths = [
        "/site-packages/uvicorn/",
        "/site-packages/starlette/",
        "/site-packages/fastapi/",
        "/multiprocessing/spawn.py",
        "/multiprocessing/process.py",
        "/asyncio/",
        "/site-packages/pydantic/",
        "/site-packages/pydantic_core/",
        "/_exception_handler.py",
    ]

    # Extract traceback
    exc_type, exc_value, exc_tb = exception.type, exception.value, exception.traceback

    # Filter frames
    filtered_tb = []
    while exc_tb:
        frame_file = exc_tb.tb_frame.f_code.co_filename
        # Keep frames from /app/ or first/last frames
        if "/app/" in frame_file or not any(noisy in frame_file for noisy in noisy_paths):
            filtered_tb.append(exc_tb)
        exc_tb = exc_tb.tb_next

    # If we filtered everything, keep original
    if not filtered_tb:
        return "".join(traceback.format_exception(exc_type, exc_value, exception.traceback))

    # Format filtered traceback
    lines = ["Traceback (most recent call last):\n"]
    for tb in filtered_tb:
        frame = tb.tb_frame
        lines.append(f'  File "{frame.f_code.co_filename}", line {tb.tb_lineno}, in {frame.f_code.co_name}\n')
        # Add code line if available
        import linecache

        line = linecache.getline(frame.f_code.co_filename, tb.tb_lineno, frame.f_globals).strip()
        if line:
            lines.append(f"    {line}\n")

    lines.append(f"{exc_type.__name__}: {exc_value}\n")
    return "".join(lines)


def configure_logging(
    log_dir: Path | str = "logs",
    log_level: str = "INFO",
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
    rotation: str = "10 MB",
    retention: str = "30 days",
    compression: str = "zip",
    filter_framework_frames: bool = True,  # New parameter
) -> None:
    """Configure application logging with loguru.

    Args:
        log_dir: Directory for log files
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_file_logging: Whether to log to files
        enable_console_logging: Whether to log to console
        rotation: When to rotate log files (size or time based)
        retention: How long to keep old log files
        compression: Compression format for rotated logs
        filter_framework_frames: Filter out FastAPI/Uvicorn frames from tracebacks
    """
    # Remove default handler
    logger.remove()

    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True, parents=True)

    # Console logging with colored output
    if enable_console_logging:
        logger.add(
            sys.stderr,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True,
            backtrace=not filter_framework_frames,  # Disable full backtrace if filtering
            diagnose=True,
        )

    # File logging with rotation and full exception dumps
    if enable_file_logging:
        # Main application log (always full trace for debugging)
        logger.add(
            log_path / "app.log",
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=rotation,
            retention=retention,
            compression=compression,
            backtrace=True,  # Always full trace in files
            diagnose=True,
            enqueue=True,  # Thread-safe logging
        )

        # Error log (ERROR and above only)
        logger.add(
            log_path / "error.log",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=rotation,
            retention=retention,
            compression=compression,
            backtrace=True,
            diagnose=True,
            enqueue=True,
        )

    logger.info(
        f"Logging configured: level={log_level}, file_logging={enable_file_logging}, "
        f"console_logging={enable_console_logging}, filter_frames={filter_framework_frames}"
    )
    if enable_file_logging:
        logger.info(f"Log directory: {log_path.absolute()}")
