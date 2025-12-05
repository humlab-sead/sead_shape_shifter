import sys
from typing import Any, Callable

from loguru import logger

# Global set to track seen log messages (for deduplication)
_seen_messages: set[str] = set()


def unique(seq: list[Any] | None) -> list[Any]:
    if seq is None:
        return []
    seen: set[Any] = set()
    gx: Callable[[Any], None] = seen.add
    return [x for x in seq if not (x in seen or gx(x))]


def filter_once_per_message(record) -> bool:
    """Filter to show each unique message only once during the run."""
    global _seen_messages

    msg = record["message"]
    level_name = record["level"].name
    key = f"{level_name}:{msg}"

    if key not in _seen_messages:
        _seen_messages.add(key)
        return True
    return False


def setup_logging(verbose: bool = False, log_file: str | None = None) -> None:
    """Configure loguru logging with appropriate handlers and filters.

    Args:
        verbose: If True, set log level to DEBUG and show all messages.
                If False, set to INFO and filter duplicate messages.
        log_file: Optional path to log file. If provided, logs are written to file.
    """
    global _seen_messages

    _seen_messages = set()

    level = "DEBUG" if verbose else "INFO"

    logger.remove()

    log_format = (
        (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
        if verbose
        else "<level>{message}</level>"
    )

    # Add console handler with filter only if not verbose
    logger.add(
        sys.stderr,
        level=level,
        format=log_format,
        filter=filter_once_per_message if not verbose else None,
        colorize=True,
        enqueue=False,
    )

    # Add file handler if specified (always show all messages in log file)
    if log_file:
        logger.add(
            log_file,
            level="DEBUG",
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
            enqueue=False,
        )

    if verbose:
        logger.debug("Verbose logging enabled")
