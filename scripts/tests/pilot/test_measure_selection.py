"""Tests for the Phase 4 pilot measurement tooling.

These cover the parts that decide whether a measurement is trustworthy: the query
mix, the percentile calculation, the budget verdict, and the delay proxy's
argument handling. They do not contact a running service; the live runs are
recorded in the Phase 4 baseline instead.
"""

from __future__ import annotations

import pytest

from scripts.pilot import delay_proxy, measure_selection
from scripts.pilot.measure_selection import Timing, TypeResult, build_queries, build_summary, report

LABELS = ["Midden", "Castle", "Water basin", "Hearth", "Pit", "Ditch", "Post hole", "Well", "Oven", "Kiln"]


class TestBuildQueries:
    """The query mix must reflect real search usage, not only whole labels."""

    def test_returns_the_requested_count(self) -> None:
        queries = build_queries(LABELS, 100, seed=1)
        assert len(queries) == 100

    def test_covers_every_query_kind(self) -> None:
        kinds = {kind for _query, kind in build_queries(LABELS, 100, seed=1)}
        assert kinds == {"exact", "partial", "word", "no_match"}

    def test_is_reproducible_for_a_seed(self) -> None:
        assert build_queries(LABELS, 40, seed=7) == build_queries(LABELS, 40, seed=7)

    def test_differs_between_seeds(self) -> None:
        assert build_queries(LABELS, 40, seed=7) != build_queries(LABELS, 40, seed=8)

    def test_short_labels_do_not_break_partial_queries(self) -> None:
        queries = build_queries(["a", "bc"], 20, seed=3)
        assert all(query for query, _kind in queries)


class TestTypeResult:
    """Percentiles and summaries must describe the measured samples."""

    def _result(self, seconds: list[float]) -> TypeResult:
        result = TypeResult(service_type="feature_type")
        result.timings = [Timing(query=f"q{index}", kind="exact", seconds=value, item_count=1) for index, value in enumerate(seconds)]
        return result

    def test_p95_uses_nearest_rank(self) -> None:
        result = self._result([float(value) / 1000 for value in range(1, 101)])
        assert round(result.percentile(0.95) * 1000) == 95

    def test_median_matches_statistics(self) -> None:
        result = self._result([0.010, 0.020, 0.030])
        assert result.summary()["median_ms"] == pytest.approx(20.0)

    def test_empty_result_reports_zero_percentile(self) -> None:
        assert self._result([]).percentile(0.95) == 0.0

    def test_counts_empty_results_and_failures(self) -> None:
        result = TypeResult(service_type="country")
        result.timings = [
            Timing(query="a", kind="exact", seconds=0.05, item_count=0),
            Timing(query="b", kind="exact", seconds=0.05, item_count=0, status=500),
            Timing(query="c", kind="exact", seconds=0.05, item_count=3),
        ]
        summary = result.summary()
        # A failed request is counted as a failure, not as a search that missed.
        assert summary["empty_results"] == 1
        assert summary["failures"] == 1

    def test_summary_rounds_milliseconds(self) -> None:
        summary = self._result([0.01234]).summary()
        assert summary["min_ms"] == pytest.approx(12.3)
        assert summary["max_ms"] == pytest.approx(12.3)


class TestReport:
    """The exit code is what makes a run usable in a check."""

    def _summary(self, p95_ms: float, budget_ms: float) -> dict[str, object]:
        result = TypeResult(service_type="feature_type")
        result.timings = [
            Timing(query="a", kind="exact", seconds=p95_ms / 1000, item_count=1),
            Timing(query="b", kind="exact", seconds=p95_ms / 1000, item_count=1),
        ]
        return build_summary([result], "test", budget_ms)

    def test_passes_within_budget(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert report(self._summary(100.0, 2000.0)) == 0
        assert "PASS" in capsys.readouterr().err

    def test_fails_above_budget(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert report(self._summary(3000.0, 2000.0)) == 1
        assert "FAIL" in capsys.readouterr().err

    def test_summary_records_the_label_and_budget(self) -> None:
        summary = build_summary([], "rtt-100ms", 2000.0)
        assert summary["label"] == "rtt-100ms"
        assert summary["budget_p95_ms"] == 2000.0
        assert summary["types"] == []


class TestSplitUpstream:
    """The proxy must accept the host:port forms the pilot uses."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("pilot-authority:8000", ("pilot-authority", 8000)),
            ("127.0.0.1:5432", ("127.0.0.1", 5432)),
            ("pilot-authority", ("pilot-authority", 8000)),
        ],
    )
    def test_parses_upstream(self, value: str, expected: tuple[str, int]) -> None:
        assert delay_proxy.split_upstream(value) == expected


class TestPilotSpecs:
    """The harness must measure both pilot types."""

    def test_includes_feature_type_and_country(self) -> None:
        service_types = {spec[3] for spec in measure_selection.PILOT_SPECS}
        assert service_types == {"feature_type", "country"}
