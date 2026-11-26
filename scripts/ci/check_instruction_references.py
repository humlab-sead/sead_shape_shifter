#!/usr/bin/env python3
"""Check that links and paths in the AI instruction files point at files that exist.

Checks the hand-written instruction files: every `AGENTS.md`, `RTK.md`, `.clinerules/`,
`.agents/skills/` and the instruction, agent and prompt files under `.github/`.
`.claude/rules/` is not checked, because it is generated from `.github/instructions/`.

Two kinds of reference are checked, outside fenced code blocks:
- Markdown links with a relative target. The target is followed from the file's own folder.
- Paths in backticks, including paths inside a backticked command. A path counts when it contains
  `/` and ends with `/` or a known file extension, or is the name of an `*.instructions.md` file.
  It may start at the repository root or at the file's folder. A shortened path such as
  `api/v1/endpoints/` also passes when a real path ends with it and its first folder is not a
  top-level folder.

Not checked: text with placeholders or wildcards (`<name>`, `{entity}`, `*`), absolute and home
paths, URLs, folder names without a trailing `/`, and paths that Git ignores (local build output).
"Exists" means a file that Git tracks or would add, so a local run and a CI run give the same result.

Usage:
    python3 scripts/ci/check_instruction_references.py   # exit 1 and list broken references

Uses only the standard library and Git. Changes no files.
"""

from __future__ import annotations

import argparse
import posixpath
import re
import subprocess
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[2]

# Paths that are written as examples and are not meant to exist, listed per file.
# An entry that no longer matches any text is reported, so this list cannot go stale.
EXAMPLES: dict[str, set[str]] = {
    # Invented topic and file names that show how links change when a proposal moves.
    ".agents/skills/move-proposal/SKILL.md": {
        "../../../X/README.md",
        "../../../future/X/README.md",
        "../../X/README.md",
        "../../a.md",
        "../../future/X/README.md",
        "../a.md",
        "docs/proposals/CHANGE_REQUEST_INGESTER/X/",
        "docs/proposals/CHANGE_REQUEST_INGESTER/done/X/",
        "docs/proposals/X.md",
        "docs/proposals/X/",
        "docs/proposals/X/README.md",
        "docs/proposals/X/X.md",
        "docs/proposals/X/Y/",
        "docs/proposals/done/A/B.md",
        "docs/proposals/done/A/done/C.md",
        "docs/proposals/done/X.md",
        "docs/proposals/done/X/",
        "docs/proposals/future/X.md",
    },
}

INSTRUCTION_FILE = re.compile(
    r"(?:^|/)AGENTS\.md$"
    r"|^RTK\.md$"
    r"|^\.clinerules/.+\.md$"
    r"|^\.agents/skills/.+\.md$"
    r"|^\.github/(?:instructions|agents|prompts)/.+\.md$"
    r"|^\.github/(?:copilot-instructions|pr-description-instructions)\.md$"
)
EXTENSIONS = re.compile(r"\.(?:cfg|css|csv|html|ini|j2|js|json|lock|md|mjs|mk|parquet|py|sh|sql|toml|ts|txt|vue|yaml|yml)$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
CODE_SPAN = re.compile(r"(`+)(.+?)\1")
MARKDOWN_LINK = re.compile(r"\]\(([^)\s]+)\)")
NOT_A_PATH = re.compile(r"[<>{}\[\]()*?$|\"'\\,;]|\.\.\.|…|://")
INSTRUCTION_SUFFIX: str = ".instructions.md"


@dataclass(frozen=True)
class BrokenReference:
    """One reference that does not point at a file. Line 0 marks an unused entry in the example list."""

    file: str
    line: int
    reference: str


class Repository:
    """The files and folders of one Git working tree."""

    def __init__(self, root: Path) -> None:
        self.root: Path = root
        listed: str = self._git("ls-files", "-z", "--cached", "--others", "--exclude-standard").stdout
        self.files: set[str] = {name for name in listed.split("\0") if name and (root / name).exists()}
        self.folders: set[str] = {parent.as_posix() for name in self.files for parent in Path(name).parents} - {"."}
        self.paths: set[str] = self.files | self.folders
        self.top_level: set[str] = {folder.split("/")[0] for folder in self.folders}
        self.file_names: set[str] = {posixpath.basename(name) for name in self.files}

    def _git(self, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", "-C", str(self.root), *args], input=stdin, capture_output=True, text=True, check=False)

    def contains(self, path: str, base: str) -> bool:
        """Returns True when `path`, read from the folder `base`, names an existing file or folder."""
        resolved: str = posixpath.normpath(posixpath.join(base, path))
        if resolved == ".":
            return True
        return resolved in (self.folders if path.endswith("/") else self.paths)

    def ends_with(self, path: str) -> bool:
        """Returns True when a shortened path matches the end of an existing path."""
        if path.startswith(".") or path.split("/")[0] in self.top_level:
            return False
        wanted: str = "/" + path.rstrip("/")
        return any(known.endswith(wanted) for known in (self.folders if path.endswith("/") else self.paths))

    def is_ignored(self, path: str) -> bool:
        """Returns True when Git's ignore rules cover the path, whether or not it exists."""
        if posixpath.normpath(path).startswith(".."):
            return False
        return self._git("check-ignore", "--no-index", "-q", "--", path).returncode == 0


def lines_outside_fences(text: str) -> Iterator[tuple[int, str]]:
    """Yields (line number, line) for the lines that are not inside a fenced code block."""
    fence: str = ""
    for number, line in enumerate(text.splitlines(), start=1):
        match = FENCE.match(line)
        if fence:
            if match and match.group(1).startswith(fence):
                fence = ""
        elif match:
            fence = match.group(1)
        else:
            yield number, line


def link_targets(line: str) -> Iterator[str]:
    """Yields the relative file targets of the Markdown links on a line, without anchors."""
    for target in MARKDOWN_LINK.findall(CODE_SPAN.sub("", line)):
        path: str = target.split("#")[0].split("?")[0]
        if path and not path.startswith(("/", "mailto:")) and not NOT_A_PATH.search(target):
            yield path


def backticked_paths(line: str) -> Iterator[str]:
    """Yields the parts of the backticked text on a line that name a repository file or folder."""
    for _, span in CODE_SPAN.findall(line):
        for word in span.split():
            token: str = re.split(r"::|#", word.split("=")[-1])[0]
            token = re.sub(r":\d+(?:-\d+)?$", "", token).rstrip(".:")
            if NOT_A_PATH.search(token) or ":" in token or token.startswith(("/", "~", "-", "@", "path/to/")):
                continue
            is_path: bool = "/" in token and (token.endswith("/") or bool(EXTENSIONS.search(token)))
            is_instruction_name: bool = token.endswith(INSTRUCTION_SUFFIX) and len(token) > len(INSTRUCTION_SUFFIX)
            if is_path or is_instruction_name:
                yield token


def from_folder(base: str, path: str) -> str:
    """Returns `path`, read from the folder `base`, as a path from the repository root.

    Keeps a trailing `/`, because Git needs it to match a folder-only ignore rule when the folder does not exist.
    """
    joined: str = posixpath.normpath(posixpath.join(base, path))
    return f"{joined}/" if path.endswith("/") else joined


def check_file(repository: Repository, name: str) -> Iterator[BrokenReference]:
    """Yields the broken links and paths in one instruction file."""
    base: str = posixpath.dirname(name)
    for number, line in lines_outside_fences((repository.root / name).read_text(encoding="utf-8")):
        for target in link_targets(line):
            if not repository.contains(target, base) and not repository.is_ignored(from_folder(base, target)):
                yield BrokenReference(name, number, target)
        for path in backticked_paths(line):
            if "/" not in path:
                found: bool = path in repository.file_names
            else:
                found = repository.contains(path, "") or repository.contains(path, base) or repository.ends_with(path)
            if not found and not any(repository.is_ignored(candidate) for candidate in (path, from_folder(base, path))):
                yield BrokenReference(name, number, path)


def find_broken_references(root: Path, examples: Mapping[str, set[str]] | None = None) -> list[BrokenReference]:
    """Returns the broken references in all instruction files under `root`, sorted by file and line.

    `examples` lists, per file, paths that are allowed to be missing. An entry that matches nothing
    is returned with line 0.
    """
    repository = Repository(root)
    allowed: Mapping[str, set[str]] = examples or {}
    used: set[tuple[str, str]] = set()
    broken: list[BrokenReference] = []
    for name in sorted(repository.files):
        if not INSTRUCTION_FILE.search(name) or (root / name).is_symlink():
            continue
        for item in check_file(repository, name):
            if item.reference in allowed.get(name, set()):
                used.add((name, item.reference))
            else:
                broken.append(item)
    unused = [BrokenReference(file, 0, ref) for file, refs in allowed.items() for ref in refs if (file, ref) not in used]
    return sorted(broken + unused, key=lambda item: (item.file, item.line, item.reference))


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Prints each broken reference and returns 1 when there is at least one."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository to check (default: this one)")
    root: Path = parser.parse_args(argv).root.resolve()
    broken = find_broken_references(root, examples=EXAMPLES if root == REPO_ROOT else None)
    for item in broken:
        if item.line:
            print(f"{item.file}:{item.line}: {item.reference}", file=sys.stderr)
        else:
            print(f"{item.file}: unused entry in EXAMPLES: {item.reference}", file=sys.stderr)
    if broken:
        print(f"{len(broken)} broken reference(s) in instruction files.", file=sys.stderr)
        return 1
    print("Links and paths in instruction files are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
