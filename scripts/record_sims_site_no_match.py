#!/usr/bin/env python3
"""Record and verify a reviewer-approved site no-match in Shape Shifter."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen


def parse_snapshot_time(value: str) -> str:
    """Return a timezone-aware snapshot timestamp in ISO format."""
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("snapshot time must be ISO 8601") from exc

    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise argparse.ArgumentTypeError("snapshot time must include a timezone")
    return timestamp.isoformat()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Record a reviewed site no-match in Shape Shifter. This updates the "
            "project reconciliation mapping; it does not allocate a SIMS identity."
        )
    )
    parser.add_argument("--base-url", required=True, help="Shape Shifter API URL, for example http://127.0.0.1:8012")
    parser.add_argument("--environment", required=True, choices=("disposable", "staging"))
    parser.add_argument("--project", required=True, help="Shape Shifter project name")
    parser.add_argument("--target-field", required=True, help="Configured site reconciliation field")
    parser.add_argument("--source-value", required=True, help="Exact source value to mark as unmatched")
    parser.add_argument("--snapshot-id", required=True, help="Identifier for the SEAD snapshot used for review")
    parser.add_argument("--snapshot-at", required=True, type=parse_snapshot_time, help="Timezone-aware ISO 8601 snapshot time")
    parser.add_argument("--site-row-count", required=True, type=int, help="Site row count from the same snapshot")
    parser.add_argument("--reviewer", required=True, help="Name or review identifier")
    parser.add_argument("--reason", required=True, help="Why the reviewed source has no valid SEAD match")
    parser.add_argument(
        "--evidence",
        required=True,
        type=Path,
        help="Non-empty file containing the reconciliation candidates and review notes",
    )
    parser.add_argument(
        "--approve-no-match",
        action="store_true",
        help="Confirm that a reviewer examined the candidates and approved no match",
    )
    parser.add_argument(
        "--confirm-allocation-strategy",
        action="store_true",
        help="Confirm the effective target-model strategy permits allocation after this no-match",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the no-match mapping; without this flag the command only checks and prints a dry run",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15,
        help="HTTP request timeout in seconds (default: 15)",
    )
    return parser


def validate_args(args: argparse.Namespace) -> bytes:
    if args.site_row_count < 1:
        raise ValueError("--site-row-count must be greater than zero")
    if not args.source_value.strip():
        raise ValueError("--source-value must not be empty")
    if not args.reviewer.strip():
        raise ValueError("--reviewer must not be empty")
    if not args.reason.strip():
        raise ValueError("--reason must not be empty")
    if args.timeout <= 0:
        raise ValueError("--timeout must be greater than zero")
    parsed_url = urlsplit(args.base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
        raise ValueError("--base-url must be an absolute HTTP or HTTPS URL")
    if parsed_url.username or parsed_url.password or parsed_url.query or parsed_url.fragment:
        raise ValueError("--base-url must not contain credentials, a query, or a fragment")
    if parsed_url.scheme != "https" and parsed_url.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("non-loopback API URLs must use HTTPS")
    if args.environment == "disposable":
        host = parsed_url.hostname.lower()
        if host not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("disposable environment requires a loopback --base-url")
    if args.apply and not args.approve_no_match:
        raise ValueError("--apply requires --approve-no-match")
    if args.approve_no_match and not args.apply:
        raise ValueError("--approve-no-match requires --apply")
    if args.apply and not args.confirm_allocation_strategy:
        raise ValueError("--apply requires --confirm-allocation-strategy")
    if args.confirm_allocation_strategy and not args.apply:
        raise ValueError("--confirm-allocation-strategy requires --apply")
    if not args.evidence.is_file():
        raise ValueError(f"evidence file not found: {args.evidence}")

    evidence = args.evidence.read_bytes()
    if not evidence.strip():
        raise ValueError(f"evidence file is empty: {args.evidence}")
    return evidence


def mapping_url(base_url: str, project: str, target_field: str) -> str:
    project_path = quote(project, safe="")
    field_path = quote(target_field, safe="")
    return f"{base_url.rstrip('/')}/api/v1/projects/{project_path}/reconciliation/site/{field_path}"


def request_json(method: str, url: str, data: bytes | None, timeout: float) -> Any:
    headers = {"Accept": "application/json"}
    token = os.environ.get("SHAPE_SHIFTER_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Shape Shifter returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Shape Shifter API: {exc.reason}") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Shape Shifter returned invalid JSON for {method} {url}") from exc


def find_source_row(preview: Any, target_field: str, source_value: str) -> dict[str, Any]:
    if not isinstance(preview, list):
        raise RuntimeError("reconciliation preview response must be a JSON array")

    matches = [row for row in preview if isinstance(row, dict) and row.get(target_field) == source_value]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one preview row for {target_field}={source_value!r}; found {len(matches)}")
    row = matches[0]
    if "target_id" not in row or "will_not_match" not in row:
        raise RuntimeError("preview row does not include target_id and will_not_match status")
    if not isinstance(row["will_not_match"], bool):
        raise RuntimeError("preview row has an invalid will_not_match status")
    return row


def make_notes(args: argparse.Namespace, evidence_hash: str) -> str:
    return (
        "Reviewer-approved no-match for SIMS site allocation verification\n"
        f"Reviewer: {args.reviewer.strip()}\n"
        f"Environment: {args.environment}\n"
        f"SEAD snapshot: {args.snapshot_id}\n"
        f"Snapshot time: {args.snapshot_at}\n"
        f"SEAD site row count: {args.site_row_count}\n"
        f"Reconciliation evidence: {args.evidence.name} (SHA-256 {evidence_hash})\n"
        f"Decision reason: {args.reason.strip()}"
    )


def record_no_match(
    args: argparse.Namespace,
    requester: Callable[[str, str, bytes | None, float], Any] = request_json,
) -> str:
    evidence = validate_args(args)
    evidence_hash = hashlib.sha256(evidence).hexdigest()
    endpoint = mapping_url(args.base_url, args.project, args.target_field)
    preview_url = f"{endpoint}/preview"

    initial_preview = requester("GET", preview_url, None, args.timeout)
    current_row = find_source_row(initial_preview, args.target_field, args.source_value)
    notes = make_notes(args, evidence_hash)

    if current_row["target_id"] is not None:
        raise RuntimeError(f"source value already maps to target_id={current_row['target_id']}; refusing to replace the match")

    if current_row["will_not_match"]:
        if current_row.get("notes") == notes:
            return "This exact reviewer-approved no-match is already recorded and verified."
        raise RuntimeError("source value is already marked unmatched with different notes; review it manually")

    if not args.apply:
        return (
            "Dry run passed: one source row exists, it has no target ID, and no no-match decision is recorded. "
            "No changes were made. Re-run with --approve-no-match --apply to record the decision."
        )

    mark_url = f"{endpoint}/mark-unmatched?{urlencode({'source_value': args.source_value, 'notes': notes})}"
    requester("POST", mark_url, b"", args.timeout)

    verified_preview = requester("GET", preview_url, None, args.timeout)
    verified_row = find_source_row(verified_preview, args.target_field, args.source_value)
    if verified_row["target_id"] is not None or verified_row["will_not_match"] is not True:
        raise RuntimeError("post-write verification failed: row is not marked unmatched without a target ID")
    if verified_row.get("notes") != notes:
        raise RuntimeError("post-write verification failed: reviewer and snapshot notes do not match")

    return "Recorded and verified reviewer-approved no-match in the Shape Shifter project mapping."


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = record_no_match(args)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(result)
    print(f"Project: {args.project} | Entity: site | Field: {args.target_field}")
    print(f"Source: {args.source_value!r} | Snapshot: {args.snapshot_id} at {args.snapshot_at}")
    if args.apply:
        print("This records the reconciliation decision only; it does not call SIMS or allocate an ID.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
