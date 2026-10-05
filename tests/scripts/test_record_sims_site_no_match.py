from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from urllib.parse import unquote_plus

import pytest

from scripts.record_sims_site_no_match import record_no_match


def make_args(tmp_path: Path, *, apply: bool = False) -> argparse.Namespace:
    evidence = tmp_path / "review.json"
    evidence.write_text('{"candidates": []}', encoding="utf-8")
    return argparse.Namespace(
        base_url="http://127.0.0.1:8012",
        environment="disposable",
        project="test-project",
        target_field="site_name",
        source_value="Site with no match",
        snapshot_id="sead-snapshot-2026-10-02",
        snapshot_at="2026-10-02T10:00:00+00:00",
        site_row_count=3462,
        reviewer="reviewer@example.org",
        reason="Reviewed all candidates; none identifies the source site.",
        evidence=evidence,
        approve_no_match=apply,
        confirm_allocation_strategy=apply,
        apply=apply,
        timeout=15,
    )


def preview(*, target_id: int | None = None, will_not_match: bool = False, notes: str | None = None) -> list[dict[str, Any]]:
    return [
        {
            "site_name": "Site with no match",
            "target_id": target_id,
            "will_not_match": will_not_match,
            "notes": notes,
        }
    ]


def test_dry_run_checks_preview_without_writing(tmp_path: Path) -> None:
    args = make_args(tmp_path)
    calls: list[str] = []

    def requester(_method: str, _url: str, _data: bytes | None, _timeout: float) -> Any:
        calls.append(_method)
        return preview()

    message = record_no_match(args, requester)

    assert "Dry run passed" in message
    assert calls == ["GET"]


def test_apply_records_and_verifies_no_match(tmp_path: Path) -> None:
    args = make_args(tmp_path, apply=True)
    captured_notes: list[str] = []
    methods: list[str] = []

    def requester(method: str, url: str, _data: bytes | None, _timeout: float) -> Any:
        methods.append(method)
        if method == "POST":
            assert "mark-unmatched?" in url
            captured_notes.append(unquote_plus(url.split("notes=", 1)[1]))
            return {}
        notes = captured_notes[-1] if captured_notes else None
        return preview(will_not_match=notes is not None, notes=notes)

    message = record_no_match(args, requester)

    assert "Recorded and verified" in message
    assert methods == ["GET", "POST", "GET"]
    assert len(captured_notes) == 1
    notes = captured_notes[0]
    assert "SEAD snapshot: sead-snapshot-2026-10-02" in notes
    assert "Reviewer: reviewer@example.org" in notes


def test_refuses_to_replace_existing_match(tmp_path: Path) -> None:
    args = make_args(tmp_path, apply=True)

    def requester(_method: str, _url: str, _data: bytes | None, _timeout: float) -> Any:
        return preview(target_id=173)

    with pytest.raises(RuntimeError, match="refusing to replace the match"):
        record_no_match(args, requester)


def test_refuses_ambiguous_source_value(tmp_path: Path) -> None:
    args = make_args(tmp_path)

    def requester(_method: str, _url: str, _data: bytes | None, _timeout: float) -> Any:
        return preview() * 2

    with pytest.raises(RuntimeError, match="found 2"):
        record_no_match(args, requester)


def test_requires_explicit_review_approval_before_apply(tmp_path: Path) -> None:
    args = make_args(tmp_path, apply=True)
    args.approve_no_match = False

    with pytest.raises(ValueError, match="requires --approve-no-match"):
        record_no_match(args, lambda *request: preview())


def test_requires_allocation_strategy_confirmation_before_apply(tmp_path: Path) -> None:
    args = make_args(tmp_path, apply=True)
    args.confirm_allocation_strategy = False

    with pytest.raises(ValueError, match="requires --confirm-allocation-strategy"):
        record_no_match(args, lambda *request: preview())
