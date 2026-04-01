#!/usr/bin/env python3
"""Generate a draft user-facing release note from changelog data."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib import error, request

from jinja2 import Environment, FileSystemLoader, StrictUndefined


EXCLUDED_SCOPES = {
    "docs",
    "doc",
    "test",
    "tests",
    "chore",
    "style",
    "build",
    "ci",
    "vscode",
    "todo",
    "todos",
    "readme",
}

SUBJECT_EXCLUDED_TOKENS = (
    "readme",
    "cspell",
    "pylint",
    "lint",
    "todo",
    "test",
)

SUBJECT_EXCLUDED_PHRASES = (
    "proposal",
    "system_diagrams",
    "globalcomponents",
)

USER_VISIBLE_SCOPES = {
    "frontend",
    "ui",
    "query",
    "sql",
    "api",
    "backend",
    "validation",
    "entity",
    "foreignkeyeditor",
    "entityformdialog",
    "components",
    "loader",
    "graph",
    "project",
    "projects",
}

USER_VISIBLE_SUBJECT_PHRASES = (
    "graph",
    "editor",
    "column",
    "validation",
    "query",
    "foreign key",
    "data source",
    "form",
    "preview",
    "ui",
    "workflow",
)

IMPROVEMENT_KEYWORDS = (
    "improve",
    "enhance",
    "clarify",
    "support",
    "enable",
    "add readonly",
)

AI_INPUT_ORDERED_HEADINGS = ("features", "bug fixes")
VERSION_HEADING_PATTERN = re.compile(r"^# \[(?P<version>[^\]]+)\]\([^\n]+\) \((?P<date>[^)]+)\)$", re.MULTILINE)

DEFAULT_AI_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_AI_MODEL = "gpt-4.1-mini"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
LOCAL_ENV_KEYS = {
    "RELEASE_NOTES_API_KEY",
    "OPENAI_API_KEY",
    "RELEASE_NOTES_API_URL",
    "RELEASE_NOTES_MODEL",
    "RELEASE_NOTES_API_TIMEOUT",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    version_group = parser.add_mutually_exclusive_group(required=True)
    version_group.add_argument("--version", help="Release version without a leading v")
    version_group.add_argument(
        "--list-versions",
        action="store_true",
        help="List release versions available in CHANGELOG.md and exit.",
    )
    version_group.add_argument(
        "--generate-missing",
        action="store_true",
        help="Generate release notes for all versions since the last generated note.",
    )
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="Repository root containing CHANGELOG.md",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output path. Defaults to docs/whats-new/v<version>.md under the repo root.",
    )
    parser.add_argument(
        "--github-repository",
        default="humlab-sead/sead_shape_shifter",
        help="GitHub owner/repo used for the release URL",
    )
    parser.add_argument(
        "--update-github-release",
        action="store_true",
        help="If set, update the GitHub release body via gh release edit.",
    )
    parser.add_argument(
        "--force-heuristic",
        action="store_true",
        help="Skip AI generation and always use the local heuristic draft builder.",
    )
    return parser.parse_args()


def render_template(template_name: str, **context: object) -> str:
    environment = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )
    template = environment.get_template(template_name)
    return template.render(**context)


def load_local_env(repo_root: Path) -> None:
    env_path = repo_root / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if key not in LOCAL_ENV_KEYS or key in os.environ:
            continue

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ[key] = value


def read_release_section(changelog_path: Path, version: str) -> tuple[str, str | None]:
    changelog = changelog_path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"^# \[{re.escape(version)}\]\([^\n]+\) \((?P<date>[^)]+)\)\n(?P<body>.*?)(?=^# \[|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(changelog)
    if not match:
        raise ValueError(f"Could not find release section for version {version} in {changelog_path}")
    return match.group("body").strip(), match.group("date")


def list_available_versions(changelog_path: Path) -> list[tuple[str, str]]:
    changelog = changelog_path.read_text(encoding="utf-8")
    return [(match.group("version"), match.group("date")) for match in VERSION_HEADING_PATTERN.finditer(changelog)]


def parse_sections(section_text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_heading: str | None = None
    for line in section_text.splitlines():
        heading_match = re.match(r"^###\s+(.+)$", line.strip())
        if heading_match:
            current_heading = heading_match.group(1).strip().lower()
            sections.setdefault(current_heading, [])
            continue

        bullet_match = re.match(r"^\*\s+(.+?)\s+\(\[[0-9a-f]{7}\]\([^)]*\)\)(?:,.*)?$", line.strip())
        if bullet_match and current_heading:
            sections.setdefault(current_heading, []).append(bullet_match.group(1).strip())

    return sections


def split_scope(entry: str) -> tuple[str | None, str]:
    scoped = re.match(r"^\*\*(?P<scope>[^*:]+):\*\*\s+(?P<subject>.+)$", entry)
    if scoped:
        return scoped.group("scope").strip().lower(), scoped.group("subject").strip()

    scoped = re.match(r"^\*\*(?P<scope>[^*]+)\*\*:\s+(?P<subject>.+)$", entry)
    if scoped:
        return scoped.group("scope").strip().lower(), scoped.group("subject").strip()
    return None, entry.strip()


def is_user_visible(scope: str | None, subject: str) -> bool:
    normalized_scope = (scope or "").lower()
    normalized_subject = subject.lower()

    if normalized_scope in EXCLUDED_SCOPES:
        return False

    if any(token in normalized_subject for token in SUBJECT_EXCLUDED_TOKENS):
        return False

    if any(token in normalized_subject for token in SUBJECT_EXCLUDED_PHRASES):
        return False

    if normalized_scope in USER_VISIBLE_SCOPES:
        return True

    return any(phrase in normalized_subject for phrase in USER_VISIBLE_SUBJECT_PHRASES)


def to_sentence(subject: str) -> str:
    cleaned = subject.strip()
    if not cleaned:
        return ""
    cleaned = cleaned[0].upper() + cleaned[1:]
    if cleaned.endswith("."):
        return cleaned
    return f"{cleaned}."


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def get_latest_generated_version(whats_new_dir: Path) -> str | None:
    """Find the latest version that has a generated release note."""
    if not whats_new_dir.exists():
        return None
    
    version_pattern = re.compile(r"^v(\d+\.\d+\.\d+)\.md$")
    versions: list[tuple[int, int, int, str]] = []
    
    for file_path in whats_new_dir.iterdir():
        if not file_path.is_file():
            continue
        match = version_pattern.match(file_path.name)
        if match:
            version_str = match.group(1)
            parts = version_str.split(".")
            if len(parts) == 3:
                try:
                    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                    versions.append((major, minor, patch, version_str))
                except ValueError:
                    continue
    
    if not versions:
        return None
    
    versions.sort(reverse=True)
    return versions[0][3]


def get_missing_versions(changelog_path: Path, whats_new_dir: Path) -> list[tuple[str, str]]:
    """Get all versions from changelog that don't have generated release notes."""
    all_versions = list_available_versions(changelog_path)
    latest_generated = get_latest_generated_version(whats_new_dir)
    
    if latest_generated is None:
        return all_versions
    
    # Parse latest generated version
    latest_parts = latest_generated.split(".")
    latest_tuple = (int(latest_parts[0]), int(latest_parts[1]), int(latest_parts[2]))
    
    missing: list[tuple[str, str]] = []
    for version, date in all_versions:
        parts = version.split(".")
        if len(parts) == 3:
            try:
                version_tuple = (int(parts[0]), int(parts[1]), int(parts[2]))
                if version_tuple > latest_tuple:
                    missing.append((version, date))
            except ValueError:
                continue
    
    # Return in chronological order (oldest first)
    return list(reversed(missing))


def classify_sections(parsed_sections: dict[str, list[str]]) -> tuple[list[str], list[str], list[str], list[str]]:
    features: list[str] = []
    improvements: list[str] = []
    fixes: list[str] = []

    for heading, entries in parsed_sections.items():
        for entry in entries:
            scope, subject = split_scope(entry)
            if not is_user_visible(scope, subject):
                continue
            sentence = to_sentence(subject)
            if not sentence:
                continue

            if heading == "features":
                features.append(sentence)
            elif any(keyword in subject.lower() for keyword in IMPROVEMENT_KEYWORDS):
                improvements.append(sentence)
            else:
                fixes.append(sentence)

    features = dedupe_preserve_order(features)
    improvements = dedupe_preserve_order(improvements)
    fixes = dedupe_preserve_order(fixes)

    highlights = dedupe_preserve_order((features[:2] + improvements[:2] + fixes[:1]))[:5]
    return highlights, features, improvements, fixes


def build_ai_input(parsed_sections: dict[str, list[str]]) -> str:
    remaining = [heading for heading in parsed_sections if heading not in AI_INPUT_ORDERED_HEADINGS]
    lines: list[str] = []

    for heading in list(AI_INPUT_ORDERED_HEADINGS) + sorted(remaining):
        entries = parsed_sections.get(heading)
        if not entries:
            continue
        lines.append(f"## {heading.title()}")
        for entry in entries:
            lines.append(f"- {entry}")
        lines.append("")

    return "\n".join(lines).strip()


def build_release_notes(
    version: str,
    release_date: str | None,
    github_repository: str,
    highlights: list[str],
    features: list[str],
    improvements: list[str],
    fixes: list[str],
) -> str:
    formatted_date = release_date or dt.date.today().isoformat()
    release_url = f"https://github.com/{github_repository}/releases/tag/v{version}"
    return render_template(
        "release_notes.md.j2",
        version=version,
        formatted_date=formatted_date,
        highlights=highlights,
        features=features,
        improvements=improvements,
        fixes=fixes,
        release_url=release_url,
    )


def build_ai_messages(
    version: str,
    release_date: str | None,
    github_repository: str,
    parsed_sections: dict[str, list[str]],
    heuristic_draft: str,
) -> list[dict[str, str]]:
    formatted_date = release_date or dt.date.today().isoformat()
    release_url = f"https://github.com/{github_repository}/releases/tag/v{version}"
    technical_input = build_ai_input(parsed_sections)
    system_prompt = render_template("release_notes_ai_system_prompt.txt.j2")
    user_prompt = render_template(
        "release_notes_ai_user_prompt.txt.j2",
        version=version,
        formatted_date=formatted_date,
        release_url=release_url,
        technical_input=technical_input,
        heuristic_draft=heuristic_draft,
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def extract_message_content(response_json: dict) -> str:
    choices = response_json.get("choices") or []
    if not choices:
        raise ValueError("AI response did not contain any choices")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text_parts = [part.get("text", "") for part in content if isinstance(part, dict)]
        text = "".join(text_parts).strip()
        if text:
            return text

    raise ValueError("AI response did not contain usable message content")


def maybe_generate_ai_draft(
    version: str,
    release_date: str | None,
    github_repository: str,
    parsed_sections: dict[str, list[str]],
    heuristic_draft: str,
    force_heuristic: bool,
) -> tuple[str, str]:
    if force_heuristic:
        return heuristic_draft, "heuristic"

    api_key = os.getenv("RELEASE_NOTES_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return heuristic_draft, "heuristic"

    model = os.getenv("RELEASE_NOTES_MODEL", DEFAULT_AI_MODEL)
    api_url = os.getenv("RELEASE_NOTES_API_URL", DEFAULT_AI_API_URL)
    timeout = float(os.getenv("RELEASE_NOTES_API_TIMEOUT", "60"))

    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": build_ai_messages(
            version=version,
            release_date=release_date,
            github_repository=github_repository,
            parsed_sections=parsed_sections,
            heuristic_draft=heuristic_draft,
        ),
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        req = request.Request(api_url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with request.urlopen(req, timeout=timeout) as response:  # noqa: S310
            response_json = json.loads(response.read().decode("utf-8"))
        content = extract_message_content(response_json)
    except error.HTTPError as http_error:
        details = http_error.read().decode("utf-8", errors="replace")
        print(
            f"Warning: AI draft generation failed, falling back to heuristic notes: HTTP {http_error.code}: {details}",
            file=sys.stderr,
        )
        return heuristic_draft, "heuristic"
    except error.URLError as url_error:
        print(f"Warning: AI draft generation failed, falling back to heuristic notes: {url_error}", file=sys.stderr)
        return heuristic_draft, "heuristic"
    except Exception as unexpected_error:  # pylint: disable=broad-except
        print(f"Warning: AI draft generation failed, falling back to heuristic notes: {unexpected_error}", file=sys.stderr)
        return heuristic_draft, "heuristic"

    if not content:
        return heuristic_draft, "heuristic"

    return content + ("\n" if not content.endswith("\n") else ""), f"ai:{model}"


def write_output(output_path: Path, content: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def update_github_release(version: str, output_path: Path, repo_root: Path) -> bool:
    try:
        subprocess.run(
            ["gh", "release", "edit", f"v{version}", "--notes-file", str(output_path)],
            cwd=repo_root,
            check=True,
        )
    except FileNotFoundError:
        print("Warning: gh CLI not found; skipping GitHub release body update.", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as error:
        print(f"Warning: failed to update GitHub release body: {error}", file=sys.stderr)
        return False

    return True


def generate_release_notes_for_version(
    version: str,
    repo_root: Path,
    changelog_path: Path,
    output_dir: Path,
    github_repository: str,
    force_heuristic: bool,
    update_github: bool,
) -> bool:
    """Generate release notes for a single version. Returns True on success."""
    try:
        output_path = output_dir / f"v{version}.md"
        section_text, release_date = read_release_section(changelog_path, version)
        parsed_sections = parse_sections(section_text)
        highlights, features, improvements, fixes = classify_sections(parsed_sections)
        heuristic_content = build_release_notes(
            version=version,
            release_date=release_date,
            github_repository=github_repository,
            highlights=highlights,
            features=features,
            improvements=improvements,
            fixes=fixes,
        )
        content, mode = maybe_generate_ai_draft(
            version=version,
            release_date=release_date,
            github_repository=github_repository,
            parsed_sections=parsed_sections,
            heuristic_draft=heuristic_content,
            force_heuristic=force_heuristic,
        )
        write_output(output_path, content)

        if update_github:
            update_github_release(version, output_path, repo_root)

        print(f"Generated {output_path} (mode={mode})", file=sys.stderr)
        return True
    except Exception as error:  # pylint: disable=broad-except
        print(f"Failed to generate release notes for version {version}: {error}", file=sys.stderr)
        return False


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    changelog_path = repo_root / "CHANGELOG.md"
    whats_new_dir = repo_root / "docs" / "whats-new"

    load_local_env(repo_root)

    if args.list_versions:
        for version, release_date in list_available_versions(changelog_path):
            print(f"{version}\t{release_date}")
        return 0

    if args.generate_missing:
        missing_versions = get_missing_versions(changelog_path, whats_new_dir)
        
        if not missing_versions:
            latest = get_latest_generated_version(whats_new_dir)
            print(f"No missing versions found. Latest generated: {latest or 'none'}", file=sys.stderr)
            return 0
        
        print(f"Found {len(missing_versions)} missing version(s): {', '.join(v for v, _ in missing_versions)}", file=sys.stderr)
        
        success_count = 0
        for version, _ in missing_versions:
            if generate_release_notes_for_version(
                version=version,
                repo_root=repo_root,
                changelog_path=changelog_path,
                output_dir=whats_new_dir,
                github_repository=args.github_repository,
                force_heuristic=args.force_heuristic,
                update_github=args.update_github_release,
            ):
                success_count += 1
        
        print(f"\nSuccessfully generated {success_count}/{len(missing_versions)} release notes", file=sys.stderr)
        return 0 if success_count == len(missing_versions) else 1

    # Single version mode
    output_path = args.output or repo_root / "docs" / "whats-new" / f"v{args.version}.md"
    section_text, release_date = read_release_section(changelog_path, args.version)
    parsed_sections = parse_sections(section_text)
    highlights, features, improvements, fixes = classify_sections(parsed_sections)
    heuristic_content = build_release_notes(
        version=args.version,
        release_date=release_date,
        github_repository=args.github_repository,
        highlights=highlights,
        features=features,
        improvements=improvements,
        fixes=fixes,
    )
    content, mode = maybe_generate_ai_draft(
        version=args.version,
        release_date=release_date,
        github_repository=args.github_repository,
        parsed_sections=parsed_sections,
        heuristic_draft=heuristic_content,
        force_heuristic=args.force_heuristic,
    )
    write_output(output_path, content)

    if args.update_github_release:
        update_github_release(args.version, output_path, repo_root)

    print(f"generation_mode={mode}", file=sys.stderr)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
