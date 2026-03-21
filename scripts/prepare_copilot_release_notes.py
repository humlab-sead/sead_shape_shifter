#!/usr/bin/env python3
"""Prepare a heuristic release-notes draft plus a ready-to-paste Copilot CLI prompt."""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    version_group = parser.add_mutually_exclusive_group(required=True)
    version_group.add_argument("--version", help="Release version without a leading v")
    version_group.add_argument(
        "--list-versions",
        action="store_true",
        help="List release versions available in CHANGELOG.md and exit.",
    )
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="Repository root containing CHANGELOG.md and docs/whats-new/",
    )
    parser.add_argument(
        "--draft-output",
        type=Path,
        help="Optional draft output path. Defaults to docs/whats-new/v<version>.md under the repo root.",
    )
    parser.add_argument(
        "--prompt-output",
        type=Path,
        help="Optional prompt output path. Defaults to tmp/copilot-release-notes-v<version>.prompt.md under the repo root.",
    )
    return parser.parse_args()


def load_release_notes_module(repo_root: Path):
    module_path = repo_root / "scripts" / "generate_user_release_notes.py"
    spec = importlib.util.spec_from_file_location("generate_user_release_notes", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_filtered_context(notes_module, changelog_section: str) -> str:
    parsed_sections = notes_module.parse_sections(changelog_section)
    highlights, features, improvements, fixes = notes_module.classify_sections(parsed_sections)

    sections = [
        ("Highlights", highlights),
        ("New Features", features),
        ("Improvements", improvements),
        ("Fixes", fixes),
    ]

    lines: list[str] = []
    for heading, items in sections:
        if not items:
            continue
        lines.append(f"## {heading}")
        lines.extend(f"- {item}" for item in items)
        lines.append("")

    return "\n".join(lines).strip()


def build_copilot_prompt(render_template, version: str, draft_path: Path, template_path: Path, filtered_context: str) -> str:
    return render_template(
        "copilot_release_notes_prompt.md.j2",
        version=version,
        draft_path=str(draft_path),
        template_path=str(template_path),
        filtered_context=filtered_context,
    )


def run_heuristic_draft(repo_root: Path, version: str, draft_output: Path) -> None:
    generator = repo_root / "scripts" / "generate_user_release_notes.py"
    subprocess.run(
        [
            sys.executable,
            str(generator),
            "--version",
            version,
            "--force-heuristic",
            "--output",
            str(draft_output),
        ],
        cwd=repo_root,
        check=True,
    )


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    template_path = repo_root / "docs" / "whats-new" / "TEMPLATE.md"
    changelog_path = repo_root / "CHANGELOG.md"

    notes_module = load_release_notes_module(repo_root)
    if args.list_versions:
        for version, release_date in notes_module.list_available_versions(changelog_path):
            print(f"{version}\t{release_date}")
        return 0

    draft_output = args.draft_output or repo_root / "docs" / "whats-new" / f"v{args.version}.md"
    prompt_output = args.prompt_output or repo_root / "tmp" / f"copilot-release-notes-v{args.version}.prompt.md"

    run_heuristic_draft(repo_root, args.version, draft_output)

    changelog_section, _ = notes_module.read_release_section(changelog_path, args.version)
    filtered_context = build_filtered_context(notes_module, changelog_section)
    render_template = notes_module.render_template

    prompt = build_copilot_prompt(
        render_template=notes_module.render_template,
        version=args.version,
        draft_path=draft_output.relative_to(repo_root),
        template_path=template_path.relative_to(repo_root),
        filtered_context=filtered_context,
    )

    prompt_output.parent.mkdir(parents=True, exist_ok=True)
    prompt_output.write_text(prompt, encoding="utf-8")

    print(f"Draft file: {draft_output}")
    print(f"Prompt file: {prompt_output}")
    print()
    print(prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())