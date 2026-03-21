"""API endpoints for user-facing release notes metadata."""

import re
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

WHATS_NEW_DIR = Path(__file__).resolve().parents[5] / "docs" / "whats-new"
VERSION_FILE_PATTERN = re.compile(r"^v(?P<version>\d+\.\d+\.\d+)\.md$")


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


def _version_key(version: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in version.split("."))


def _extract_metadata(note_path: Path) -> WhatsNewManifestItem:
    markdown = note_path.read_text(encoding="utf-8")
    version_match = VERSION_FILE_PATTERN.match(note_path.name)
    version = version_match.group("version") if version_match else note_path.stem.removeprefix("v")

    title = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    release_date = re.search(r"^Date:\s+(.+)$", markdown, re.MULTILINE)

    return WhatsNewManifestItem(
        version=version,
        title=title.group(1).strip() if title else f"What's New in v{version}",
        date=release_date.group(1).strip() if release_date else None,
        path=f"/docs/whats-new/{note_path.name}",
    )


def _build_manifest() -> WhatsNewManifestResponse:
    if not WHATS_NEW_DIR.exists() or not WHATS_NEW_DIR.is_dir():
        return WhatsNewManifestResponse(latest_version=None, items=[])

    note_paths = [path for path in WHATS_NEW_DIR.iterdir() if path.is_file() and VERSION_FILE_PATTERN.match(path.name)]
    items = sorted((_extract_metadata(path) for path in note_paths), key=lambda item: _version_key(item.version), reverse=True)

    return WhatsNewManifestResponse(
        latest_version=items[0].version if items else None,
        items=items,
    )


@router.get("/whats-new", response_model=WhatsNewManifestResponse)
async def get_whats_new_manifest() -> WhatsNewManifestResponse:
    """Return metadata for available what's-new markdown files."""
    return _build_manifest()
