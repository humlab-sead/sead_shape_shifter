"""End-to-end integration tests for the internal DuckDB SQL loader.

These tests exercise the full normalization pipeline: two upstream fixed
entities are resolved first, then a `type: sql` entity with
`data_source: "@internal"` joins them through the in-memory DuckDB workspace.
"""

import pandas as pd
import pytest

from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from tests.decorators import with_test_config

# pylint: disable=redefined-outer-name, unused-argument


def _internal_join_config() -> dict:
    """A project with two fixed entities and an @internal SQL entity joining them."""
    return {
        "entities": {
            "site": {
                "type": "fixed",
                "keys": ["site_id"],
                "public_id": "site_id",
                "columns": ["site_id", "site_name"],
                "values": [[1, "Alpha"], [2, "Beta"]],
            },
            "sample": {
                "type": "fixed",
                "keys": ["sample_id"],
                "public_id": "sample_id",
                "columns": ["sample_id", "site_id"],
                "values": [[10, 1], [11, 1], [12, 2]],
            },
            "site_sample_count": {
                "type": "sql",
                "data_source": "@internal",
                "depends_on": ["site", "sample"],
                "columns": ["site_name", "sample_count"],
                "keys": ["site_name"],
                "query": """
                    SELECT s.site_name AS site_name, COUNT(sa.sample_id) AS sample_count
                    FROM site s
                    JOIN sample sa ON sa.site_id = s.site_id
                    GROUP BY s.site_name
                    ORDER BY s.site_name
                """,
            },
        }
    }


class TestInternalDuckDbNormalize:
    """Integration tests that run the whole pipeline over the internal workspace."""

    @pytest.mark.asyncio
    @with_test_config
    async def test_internal_sql_entity_join_through_normalize(self, test_provider):
        """An @internal SQL entity joins two upstream entities end-to-end."""
        project = ShapeShiftProject(cfg=_internal_join_config(), filename="test-duckdb-internal.yml")
        normalizer = ShapeShifter(project=project)

        await normalizer.normalize()

        result: pd.DataFrame = normalizer.table_store["site_sample_count"]
        by_name = result.set_index("site_name")["sample_count"].to_dict()

        assert by_name["Alpha"] == 2
        assert by_name["Beta"] == 1

    @pytest.mark.asyncio
    @with_test_config
    async def test_internal_sentinel_needs_no_data_source_declaration(self, test_provider):
        """`@internal` is a reserved sentinel and is not declared in options.data_sources."""
        project = ShapeShiftProject(cfg=_internal_join_config(), filename="test-duckdb-internal.yml")

        with pytest.raises(ValueError, match="not found in configuration"):
            project.get_data_source("@internal")

        normalizer = ShapeShifter(project=project)
        await normalizer.normalize()
        assert "site_sample_count" in normalizer.table_store

    @pytest.mark.asyncio
    @with_test_config
    async def test_reference_to_unprocessed_entity_fails_clearly(self, test_provider):
        """A query over an entity absent from the workspace fails naming the missing table."""
        cfg = _internal_join_config()
        cfg["entities"]["site_sample_count"]["query"] = "SELECT * FROM not_a_processed_entity"
        project = ShapeShiftProject(cfg=cfg, filename="test-duckdb-internal.yml")
        normalizer = ShapeShifter(project=project)

        with pytest.raises(Exception, match="not_a_processed_entity"):
            await normalizer.normalize()
