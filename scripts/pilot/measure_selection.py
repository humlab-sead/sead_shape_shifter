"""Time interactive record selection through the Shape Shifter backend.

The Phase 4 gate for each pilot type is: at least 100 representative searches
after warm-up, measured through the Shape Shifter backend, with p95 at or below
2,000 ms. This script runs that measurement and reports median and p95 per type,
plus empty-result and failure counts so a failure can be attributed to the
service rather than to the client.

Queries are derived from the live browse list for the type, so the workload
reflects real labels rather than invented text. Each type gets the same mix of
whole-label, mid-label, single-word, and no-match queries.

The target backend must be the Shape Shifter service, not the Authority Service
directly. The Phase 1 contract excludes direct-Authority timing as gate evidence,
because the budget describes what a reviewer waits for.

Usage:
    python3 scripts/pilot/measure_selection.py --runs 100
    python3 scripts/pilot/measure_selection.py --label rtt-100ms \
        --json-out measurements/rtt-100.json
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

DEFAULT_BUDGET_MS = 2000.0
DEFAULT_RUNS = 100
WARMUP_RUNS = 10
TIMEOUT_SECONDS = 60.0

# The pilot specifications. Each entry is (project, entity, target field,
# service type) and must exist in the environment under test.
PILOT_SPECS: tuple[tuple[str, str, str, str], ...] = (
    ("arbodat-pilot", "feature_type", "feature_type_name", "feature_type"),
    ("arbodat-pilot", "location", "location_name", "country"),
)


@dataclass
class Timing:
    """One measured search."""

    query: str
    kind: str
    seconds: float
    item_count: int
    status: int = 200


@dataclass
class TypeResult:
    """Collected timings for one pilot type."""

    service_type: str
    timings: list[Timing] = field(default_factory=list)

    def percentile(self, fraction: float) -> float:
        """Return the requested percentile, using nearest-rank selection."""
        if not self.timings:
            return 0.0
        values = sorted(timing.seconds for timing in self.timings)
        index = min(len(values) - 1, max(0, int(round(fraction * (len(values) - 1)))))
        return values[index]

    def summary(self) -> dict[str, Any]:
        """Return the reported figures for this type.

        `empty_results` counts searches that succeeded and matched nothing, so it
        describes how often a real query misses rather than how often the service
        failed. `failures` counts requests that did not return 200; those are also
        excluded from being counted as empty matches.
        """
        values = [timing.seconds for timing in self.timings]
        return {
            "service_type": self.service_type,
            "count": len(values),
            "median_ms": round(statistics.median(values) * 1000, 1) if values else None,
            "p95_ms": round(self.percentile(0.95) * 1000, 1),
            "min_ms": round(min(values) * 1000, 1) if values else None,
            "max_ms": round(max(values) * 1000, 1) if values else None,
            "empty_results": sum(1 for timing in self.timings if timing.status == 200 and timing.item_count == 0),
            "failures": sum(1 for timing in self.timings if timing.status != 200),
        }


def request_json(url: str, payload: dict[str, Any] | None, method: str) -> tuple[int, Any]:
    """Send one JSON request and return the status and decoded body.

    Returns status 0 when the request could not be completed, so a connection
    failure is reported as a failed sample rather than aborting the run.
    """
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    http_request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(http_request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, None
    except (urllib.error.URLError, TimeoutError):
        return 0, None


def browse_labels(base_url: str, project: str, entity: str, target_field: str) -> list[str]:
    """Return the labels the type can match, taken from its complete list."""
    url = f"{base_url}/api/v1/projects/{project}/reconciliation/{entity}/{target_field}/selection/browse"
    status, body = request_json(url, None, "GET")
    if status != 200 or not isinstance(body, dict):
        raise SystemExit(f"browse failed for {entity}/{target_field}: status={status}")
    labels = [item.get("name") for item in body.get("items", []) if item.get("name")]
    if not labels:
        raise SystemExit(f"browse returned no labels for {entity}/{target_field}")
    return labels


def build_queries(labels: list[str], count: int, seed: int) -> list[tuple[str, str]]:
    """Build a representative query mix from live labels.

    The mix is 40% whole labels, 30% mid-label fragments, 20% single words, and
    10% queries that should match nothing. A search box sees all four kinds, so
    timing only whole labels would overstate how fast the path feels.
    """
    generator = random.Random(seed)
    quota_exact = int(count * 0.4)
    quota_partial = int(count * 0.3)
    quota_word = int(count * 0.2)
    quota_miss = count - quota_exact - quota_partial - quota_word

    queries: list[tuple[str, str]] = []
    queries.extend((label, "exact") for label in generator.choices(labels, k=quota_exact))

    for _ in range(quota_partial):
        label = generator.choice(labels)
        if len(label) > 4:
            start = generator.randint(0, len(label) - 4)
            queries.append((label[start : start + 4], "partial"))
        else:
            queries.append((label, "partial"))

    words = [word for label in labels for word in label.split() if len(word) > 3]
    for _ in range(quota_word):
        queries.append((generator.choice(words) if words else "zz", "word"))

    for index in range(quota_miss):
        queries.append((f"zzqmiss{index}x", "no_match"))

    generator.shuffle(queries)
    return queries


def measure_type(base_url: str, spec: tuple[str, str, str, str], runs: int, seed: int) -> TypeResult:
    """Warm up, then time `runs` searches for one specification."""
    project, entity, target_field, service_type = spec
    url = f"{base_url}/api/v1/projects/{project}/reconciliation/{entity}/{target_field}/selection/search"
    queries = build_queries(browse_labels(base_url, project, entity, target_field), runs, seed)

    # Warm-up keeps first-request costs, such as loading the project or opening a
    # connection, out of the measured distribution.
    for query, _kind in queries[:WARMUP_RUNS]:
        request_json(url, {"query": query}, "POST")

    result = TypeResult(service_type=service_type)
    for query, kind in queries:
        started = time.perf_counter()
        status, body = request_json(url, {"query": query}, "POST")
        elapsed = time.perf_counter() - started
        items = body.get("items", []) if isinstance(body, dict) else []
        result.timings.append(Timing(query=query, kind=kind, seconds=elapsed, item_count=len(items), status=status))
    return result


def build_summary(results: list[TypeResult], label: str, budget_ms: float) -> dict[str, Any]:
    """Assemble the JSON summary for one run."""
    return {
        "label": label,
        "budget_p95_ms": budget_ms,
        "types": [result.summary() for result in results],
    }


def report(summary: dict[str, Any]) -> int:
    """Print the summary and return non-zero when a type misses the budget."""
    print(json.dumps(summary, indent=2))

    failed = False
    for type_summary in summary["types"]:
        p95 = type_summary["p95_ms"]
        within_budget = p95 is not None and p95 <= summary["budget_p95_ms"]
        if not within_budget:
            failed = True
        print(
            f"{type_summary['service_type']:<14} n={type_summary['count']:<4} "
            f"median={type_summary['median_ms']} ms  p95={p95} ms  "
            f"max={type_summary['max_ms']} ms  {'PASS' if within_budget else 'FAIL'}",
            file=sys.stderr,
        )
    return 1 if failed else 0


def main() -> int:
    """Run the measurement for every pilot type."""
    parser = argparse.ArgumentParser(description="Time interactive selection through the Shape Shifter backend.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8026", help="Shape Shifter backend base URL")
    parser.add_argument("--label", default="unnamed", help="Environment label recorded with the results")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS, help=f"Measured searches per type (default: {DEFAULT_RUNS})")
    parser.add_argument(
        "--budget-ms", type=float, default=DEFAULT_BUDGET_MS, help=f"p95 budget in milliseconds (default: {DEFAULT_BUDGET_MS:.0f})"
    )
    parser.add_argument("--seed", type=int, default=20261120, help="Query-selection seed, so a run is reproducible")
    parser.add_argument("--json-out", help="Write the summary JSON to this path")
    args = parser.parse_args()

    results = [measure_type(args.base_url, spec, args.runs, args.seed + index) for index, spec in enumerate(PILOT_SPECS)]
    summary = build_summary(results, args.label, args.budget_ms)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)

    return report(summary)


if __name__ == "__main__":
    raise SystemExit(main())
