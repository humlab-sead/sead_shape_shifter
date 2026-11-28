"""The backend accepts sign-in headers only from requests that carry the proxy's secret."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from backend.app.core.proxy_secret import ProxySecretError, load_proxy_secret

SECRET = "a1" * 32
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _file(tmp_path: Path, content: bytes) -> Path:
    path = tmp_path / "proxy-secret"
    path.write_bytes(content)
    return path


@pytest.mark.parametrize("content", [f"{SECRET}\n".encode(), SECRET.encode()])
def test_loads_a_valid_secret(tmp_path: Path, content: bytes) -> None:
    secret = load_proxy_secret(_file(tmp_path, content), required=True)

    assert secret is not None
    assert secret.get_secret_value() == SECRET
    assert SECRET not in repr(secret)


def test_missing_file_stops_startup_when_required(tmp_path: Path) -> None:
    with pytest.raises(ProxySecretError, match="does not exist"):
        load_proxy_secret(tmp_path / "missing", required=True)


def test_missing_file_is_allowed_when_not_required(tmp_path: Path) -> None:
    assert load_proxy_secret(tmp_path / "missing", required=False) is None


@pytest.mark.parametrize("required", [True, False])
@pytest.mark.parametrize(
    "content",
    [b"", b"a" * 31, f"{SECRET}\n{SECRET}\n".encode(), b"a" * 31 + b" b", b"a" * 32 + b'"', "é".encode() * 40, b"\xff" * 40],
    ids=["empty", "too-short", "two-lines", "space", "quote", "non-ascii", "not-utf8"],
)
def test_invalid_content_always_stops_startup(tmp_path: Path, content: bytes, required: bool) -> None:
    path = _file(tmp_path, content)

    with pytest.raises(ProxySecretError) as error:
        load_proxy_secret(path, required=required)

    assert str(path) in str(error.value)
    assert "aaaa" not in str(error.value)


@pytest.mark.parametrize("required", [True, False])
def test_a_directory_in_place_of_the_file_stops_startup(tmp_path: Path, required: bool) -> None:
    with pytest.raises(ProxySecretError, match="cannot be read"):
        load_proxy_secret(tmp_path, required=required)


@pytest.mark.skipif(os.geteuid() == 0, reason="root can read any file")
def test_an_unreadable_file_stops_startup(tmp_path: Path) -> None:
    path = _file(tmp_path, SECRET.encode())
    path.chmod(0)

    with pytest.raises(ProxySecretError, match="cannot be read"):
        load_proxy_secret(path, required=False)


def _start_application(tmp_path: Path, secret_file: Path, code: str) -> subprocess.CompletedProcess[str]:
    """Imports the application in a new process with production sign-in settings."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith("SHAPE_SHIFTER_")}
    environment.update(
        {
            "SHAPE_SHIFTER_ENVIRONMENT": "production",
            "SHAPE_SHIFTER_TRUSTED_PROXY_AUTH_ENABLED": "true",
            "SHAPE_SHIFTER_AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS": '["admin"]',
            "SHAPE_SHIFTER_AUTHORIZATION_DATABASE_PATH": str(tmp_path / "state" / "auth.sqlite3"),
            "SHAPE_SHIFTER_LOG_DIR": str(tmp_path / "logs"),
            "SHAPE_SHIFTER_TRUSTED_PROXY_SECRET_FILE": str(secret_file),
        }
    )
    return subprocess.run(
        [sys.executable, "-c", code], cwd=REPOSITORY_ROOT, env=environment, capture_output=True, text=True, timeout=90, check=False
    )


def test_production_application_does_not_start_without_the_secret(tmp_path: Path) -> None:
    result = _start_application(tmp_path, tmp_path / "missing", "import backend.app.main")

    assert result.returncode != 0
    assert "ProxySecretError" in result.stderr


def test_production_application_passes_the_secret_to_the_middleware(tmp_path: Path) -> None:
    code = (
        "from backend.app.main import app\n"
        "from backend.app.middleware.proxy_auth import ProxyAuthenticationMiddleware as M\n"
        "options = next(m.kwargs for m in app.user_middleware if m.cls is M)\n"
        "print('configured' if options['secret'].get_secret_value() == '" + SECRET + "' else 'wrong')\n"
    )

    result = _start_application(tmp_path, _file(tmp_path, SECRET.encode()), code)

    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip().endswith("configured")


def test_command_line_settings_do_not_need_the_secret(tmp_path: Path) -> None:
    result = _start_application(tmp_path, tmp_path / "missing", "from backend.app.core.config import get_settings; get_settings()")

    assert result.returncode == 0, result.stderr[-2000:]
