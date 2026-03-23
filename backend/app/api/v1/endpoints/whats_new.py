"""API endpoints for user-facing release notes metadata."""

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

router = APIRouter()

WHATS_NEW_DIR: Path = Path(__file__).resolve().parents[5] / "docs" / "whats-new"
VERSION_FILE_PATTERN: re.Pattern = re.compile(r"^v(?P<version>\d+\.\d+\.\d+)\.md$")
VERSION_VALUE_PATTERN: re.Pattern = re.compile(r"^\d+\.\d+\.\d+$")


class WhatsNewManifestItem(BaseModel):
    """Metadata for a single what's-new markdown file."""

    version: str
    title: str
    date: str | None = None
    path: str


class WhatsNewManifestResponse(BaseModel):
    """Archive manifest for user-facing release notes."""

    latest_version: str | None
    items: list[WhatsNewManifestItem]


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _extract_metadata(note_path: Path) -> WhatsNewManifestItem:
    markdown: str = note_path.read_text(encoding="utf-8")
    version_match: re.Match[str] | None = VERSION_FILE_PATTERN.match(note_path.name)
    version: str | Any = version_match.group("version") if version_match else note_path.stem.removeprefix("v")

    title: re.Match[str] | None = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    release_date: re.Match[str] | None = re.search(r"^Date:\s+(.+)$", markdown, re.MULTILINE)

    return WhatsNewManifestItem(
        version=version,
        title=title.group(1).strip() if title else f"What's New in v{version}",
        date=release_date.group(1).strip() if release_date else None,
        path=f"/docs/whats-new/{note_path.name}",
    )


def _build_manifest() -> WhatsNewManifestResponse:
    if not WHATS_NEW_DIR.exists() or not WHATS_NEW_DIR.is_dir():
        return WhatsNewManifestResponse(latest_version=None, items=[])

    note_paths: list[Path] = [path for path in WHATS_NEW_DIR.iterdir() if path.is_file() and VERSION_FILE_PATTERN.match(path.name)]
    items = sorted((_extract_metadata(path) for path in note_paths), key=lambda item: _version_key(item.version), reverse=True)

    return WhatsNewManifestResponse(
        latest_version=items[0].version if items else None,
        items=items,
    )


@router.get("/whats-new", response_model=WhatsNewManifestResponse)
async def get_whats_new_manifest() -> WhatsNewManifestResponse:
    """Return metadata for available what's-new markdown files."""
    return _build_manifest()


@router.get("/whats-new/{version}/content", response_class=PlainTextResponse)
async def get_whats_new_content(version: str) -> PlainTextResponse:
    """Return the markdown content for a specific what's-new note."""
    if not VERSION_VALUE_PATTERN.fullmatch(version):
        raise HTTPException(status_code=400, detail="Invalid release version")

    note_path = WHATS_NEW_DIR / f"v{version}.md"
    if not note_path.exists() or not note_path.is_file():
        raise HTTPException(status_code=404, detail=f"Release note not found: v{version}.md")

    return PlainTextResponse(note_path.read_text(encoding="utf-8"), media_type="text/markdown")
