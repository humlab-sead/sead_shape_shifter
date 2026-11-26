"""Tests for scripts/ci/check_layer_imports.py.

Each test writes a small source tree and runs the check against those files.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ci.check_layer_imports import find_layer_violations, main


def make_tree(root: Path, files: dict[str, str]) -> Path:
    """Writes the given files below root and returns root."""
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def violations(root: Path) -> list[tuple[str, int, str]]:
    return [(item.file, item.line, item.module) for item in find_layer_violations(root)]


@pytest.mark.parametrize(
    "statement, module",
    [
        ("import backend", "backend"),
        ("import backend.app.main", "backend.app.main"),
        ("import os, backend.app", "backend.app"),
        ("from backend import app", "backend"),
        ("from backend.app.models import Project", "backend.app.models"),
        ('importlib.import_module("backend.app.main")', "backend.app.main"),
        ('import_module("backend")', "backend"),
        ('__import__("backend.app")', "backend.app"),
    ],
)
def test_reports_backend_import_in_src(tmp_path: Path, statement: str, module: str) -> None:
    root = make_tree(tmp_path, {"src/loaders/base.py": f"{statement}\n"})

    assert violations(root) == [("src/loaders/base.py", 1, module)]


@pytest.mark.parametrize(
    "text",
    [
        "def load():\n    from backend.app import main\n",
        "if TYPE_CHECKING:\n    from backend.app import main\n",
    ],
)
def test_reports_nested_import_with_its_line(tmp_path: Path, text: str) -> None:
    root = make_tree(tmp_path, {"src/model.py": text})

    assert violations(root) == [("src/model.py", 2, "backend.app")]


@pytest.mark.parametrize(
    "text",
    [
        "from src.model import TableConfig\n",
        "import backend_tools\n",
        "from src.backend import thing\n",
        "from .backend import thing\n",
        '"""Never import backend.app from here."""\n# import backend\n',
        'name = "backend.app.main"\n',
        "importlib.import_module(name)\n",
    ],
)
def test_accepts_code_that_does_not_import_backend(tmp_path: Path, text: str) -> None:
    root = make_tree(tmp_path, {"src/model.py": text})

    assert not violations(root)


def test_ignores_backend_imports_outside_src(tmp_path: Path) -> None:
    root = make_tree(tmp_path, {"src/model.py": "", "backend/app/main.py": "from backend.app import api\n"})

    assert not violations(root)


def test_fails_when_src_has_no_python_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        find_layer_violations(tmp_path)


def test_main_returns_1_and_lists_each_violation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = make_tree(tmp_path, {"src/model.py": "import backend\n"})

    assert main(["--root", str(root)]) == 1
    assert "src/model.py:1: backend" in capsys.readouterr().out


def test_main_returns_0_when_src_is_clean(tmp_path: Path) -> None:
    root = make_tree(tmp_path, {"src/model.py": "import os\n"})

    assert main(["--root", str(root)]) == 0
