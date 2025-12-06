import sys
from typing import Any, Callable

from loguru import logger


def unique(seq: list[Any] | None) -> list[Any]:
    if seq is None:
        return []
    seen: set[Any] = set()
    gx: Callable[[Any], None] = seen.add
    return [x for x in seq if not (x in seen or gx(x))]


# Global set to track seen log messages (for deduplication)
_seen_messages: set[str] = set()


def filter_once_per_message(record) -> bool:
    """Filter to show each unique message only once during the run."""
    global _seen_messages

    msg = record["message"]
    level_name = record["level"].name
    key: str = f"{level_name}:{msg}"

    if key not in _seen_messages:
        _seen_messages.add(key)
        return True
    return False


def setup_logging(verbose: bool = False, log_file: str | None = None) -> None:
    """Configure loguru logging with appropriate handlers and filters."""
    global _seen_messages

    format_str: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    _seen_messages = set()
    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG" if verbose else "INFO",
        format=format_str if verbose else "<level>{message}</level>",
        filter=filter_once_per_message if not verbose else None,
        colorize=True,
        enqueue=False,
    )

    if log_file:
        logger.add(log_file, level="DEBUG", format=format_str, enqueue=False)

    if verbose:
        logger.debug("Verbose logging enabled")


def load_shape_file(filename: str) -> dict[str, tuple[int, int]]:
    df: pd.DataFrame = pd.read_csv(filename, sep="\t")
    truth_shapes: dict[str, tuple[int, int]] = {x["entity"]: (x["num_rows"], x["num_columns"]) for x in df.to_dict(orient="records")}
    return truth_shapes
