"""Logging configuration for the backend application."""

import sys
from pathlib import Path

from loguru import logger


def configure_logging(
    log_dir: Path | str = "logs",
    log_level: str = "INFO",
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
    rotation: str = "10 MB",
    retention: str = "30 days",
    compression: str = "zip",
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
            backtrace=True,
            diagnose=True,
        )

    # File logging with rotation and full exception dumps
    if enable_file_logging:
        # Main application log
        logger.add(
            log_path / "app.log",
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=rotation,
            retention=retention,
            compression=compression,
            backtrace=True,
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

    logger.info(f"Logging configured: level={log_level}, file_logging={enable_file_logging}, console_logging={enable_console_logging}")
    if enable_file_logging:
        logger.info(f"Log directory: {log_path.absolute()}")
