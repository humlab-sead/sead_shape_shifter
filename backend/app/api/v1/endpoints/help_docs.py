"""API endpoints for markdown help documents used by the frontend."""

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

router = APIRouter()

DOCS_DIR = Path(__file__).resolve().parents[5] / "docs"
DOC_NAME_PATTERN = re.compile(r"^[A-Z0-9_-]+$")


@router.get("/help-docs/{doc_name}", response_class=PlainTextResponse)
async def get_help_doc(doc_name: str) -> PlainTextResponse:
    """Return a top-level markdown document used by the Help view."""
    if not DOC_NAME_PATTERN.fullmatch(doc_name):
        raise HTTPException(status_code=400, detail="Invalid help document name")

    doc_path = DOCS_DIR / f"{doc_name}.md"
    if not doc_path.exists() or not doc_path.is_file():
        raise HTTPException(status_code=404, detail=f"Help document not found: {doc_name}.md")

    return PlainTextResponse(doc_path.read_text(encoding="utf-8"), media_type="text/markdown")