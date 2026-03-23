"""API endpoints for markdown help documents used by the frontend."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

router = APIRouter()

DOCS_DIR = Path(__file__).resolve().parents[5] / "docs"


@router.get("/help-docs/{doc_path:path}", response_class=PlainTextResponse)
async def get_help_doc(doc_path: str) -> PlainTextResponse:
    """Return a markdown document used by the Help view."""
    if not doc_path:
        raise HTTPException(status_code=400, detail="Invalid help document path")

    relative_path = Path(doc_path)
    if relative_path.is_absolute() or any(part in {"", ".", ".."} for part in relative_path.parts):
        raise HTTPException(status_code=400, detail="Invalid help document path")

    if relative_path.suffix != ".md":
        relative_path = relative_path.with_suffix(".md")

    resolved_docs_dir = DOCS_DIR.resolve()
    resolved_doc_path = (DOCS_DIR / relative_path).resolve()
    if resolved_docs_dir not in resolved_doc_path.parents:
        raise HTTPException(status_code=400, detail="Invalid help document path")

    if not resolved_doc_path.exists() or not resolved_doc_path.is_file():
        raise HTTPException(status_code=404, detail=f"Help document not found: {relative_path.as_posix()}")

    return PlainTextResponse(resolved_doc_path.read_text(encoding="utf-8"), media_type="text/markdown")
