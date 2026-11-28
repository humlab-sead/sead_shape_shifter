"""Reads the secret that the reverse proxy sends with each request.

The secret is read from a file, not from an environment variable, so project directives and
data source settings that expand ``${VARIABLE}`` cannot reach it. Keep the file outside the
application folder.
"""

import re
from pathlib import Path

from loguru import logger
from pydantic import SecretStr

_SECRET_PATTERN = re.compile(r"[A-Za-z0-9_-]{32,}")


class ProxySecretError(RuntimeError):
    """The proxy secret file is missing or unusable. The message never includes its content."""


def load_proxy_secret(path: Path, *, required: bool) -> SecretStr | None:
    """Read the proxy secret from ``path``.

    Args:
        path: File that holds the secret on one line.
        required: Whether a missing file is an error.

    Returns:
        The secret, or None when the file does not exist and ``required`` is False.

    Raises:
        ProxySecretError: If the file is required and missing, cannot be read, or does not
            hold one line of at least 32 characters from ``A-Z a-z 0-9 _ -``.
    """
    try:
        content: str = path.read_bytes().decode("ascii")
    except FileNotFoundError:
        if required:
            raise ProxySecretError(f"Proxy secret file does not exist: {path}") from None
        logger.warning("Proxy secret file does not exist: {}. Sign-in headers are accepted without a proxy secret.", path)
        return None
    except OSError as error:
        raise ProxySecretError(f"Proxy secret file cannot be read: {path} ({type(error).__name__})") from None
    except UnicodeDecodeError:
        content = ""

    secret: str = content.removesuffix("\n")
    if not _SECRET_PATTERN.fullmatch(secret):
        raise ProxySecretError(
            f"Proxy secret file is not valid: {path}. It must hold one line of at least 32 characters from A-Z a-z 0-9 _ -."
        )
    return SecretStr(secret)
