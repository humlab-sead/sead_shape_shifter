#!/usr/bin/env python3
"""Check that no Python file in `src/` imports `backend`.

`src/` is the Core layer and must work without the backend (see "Cross-Cutting Rules" in the root `AGENTS.md`).

Reports `import` and `from ... import` statements anywhere in a file, including inside functions and
`TYPE_CHECKING` blocks. Also reports `import_module()` and `__import__()` calls whose module name is
written as text. A module name built at run time is not detected.

Usage:
    python3 scripts/ci/check_layer_imports.py   # exit 1 and list the imports

Uses only the standard library, so it runs without the project environment. Changes no files.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
CHECKED_FOLDER: str = "src"
FORBIDDEN_PACKAGE: str = "backend"
IMPORT_FUNCTIONS: frozenset[str] = frozenset({"import_module", "__import__"})


@dataclass(frozen=True)
class Violation:
    """One import of the forbidden package."""

    file: str
    line: int
    module: str


def _imported_modules(node: ast.AST) -> Iterator[str]:
    """Yields the absolute module names that one syntax node imports."""
    if isinstance(node, ast.Import):
        yield from (alias.name for alias in node.names)
    elif isinstance(node, ast.ImportFrom):
        # A relative import (level > 0) stays inside its own package.
        if node.level == 0 and node.module:
            yield node.module
    elif isinstance(node, ast.Call) and node.args:
        name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", None)
        first = node.args[0]
        if name in IMPORT_FUNCTIONS and isinstance(first, ast.Constant) and isinstance(first.value, str):
            yield first.value


def find_layer_violations(root: Path) -> list[Violation]:
    """Returns every `backend` import in the Python files under `root/src`.

    Raises FileNotFoundError when there are no files to check, so a wrong root cannot pass.
    """
    paths = sorted((root / CHECKED_FOLDER).rglob("*.py"))
    if not paths:
        raise FileNotFoundError(f"No Python files found under {root / CHECKED_FOLDER}")

    violations: list[Violation] = []
    for path in paths:
        tree = ast.parse(path.read_bytes(), filename=str(path))
        for node in ast.walk(tree):
            violations.extend(
                Violation(file=path.relative_to(root).as_posix(), line=getattr(node, "lineno", 0), module=module)
                for module in _imported_modules(node)
                if module.split(".")[0] == FORBIDDEN_PACKAGE
            )
    return sorted(violations, key=lambda item: (item.file, item.line, item.module))


def main(argv: Sequence[str] | None = None) -> int:
    """Prints the forbidden imports and returns 1 when there are any, otherwise 0."""
    parser = argparse.ArgumentParser(description="Check that no Python file in src/ imports backend.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root (default: this repository)")
    args = parser.parse_args(argv)

    violations = find_layer_violations(args.root)
    for item in violations:
        print(f"{item.file}:{item.line}: {item.module}")
    if violations:
        print(f"{len(violations)} import(s) of {FORBIDDEN_PACKAGE} in {CHECKED_FOLDER}/. Core code must not depend on the backend.")
        return 1
    print(f"No file in {CHECKED_FOLDER}/ imports {FORBIDDEN_PACKAGE}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
