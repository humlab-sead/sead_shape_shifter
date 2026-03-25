"""Test circular dependency handling with defer_dependency flag.

This module tests the ability to handle circular FK references between entities
using the defer_dependency flag. Without this flag, circular references should
fail (current behavior). With the flag, circular references should be resolved
via the final linking pass.
"""

import pytest

from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from tests.decorators import with_test_config

# pylint: disable=unused-argument


class TestCircularDependency:
    """Test circular dependency handling with defer_dependency flag."""

    @pytest.mark.asyncio
    @with_test_config
    async def test_circular_dependency_without_defer_flag_should_fail(self, test_provider):
        """Test that circular dependencies fail without defer_dependency flag (current behavior)."""

        # Setup: Create two entities with circular FK references
        # abundance -> analysis_entity (FK)
        # analysis_entity -> abundance (append source)
        # Both are fixed entities so they both go through dependency resolution
        config = {
            "entities": {
                "abundance": {
                    "type": "fixed",
                    "keys": ["abundance_id"],
                    "public_id": "abundance_id",
                    "columns": ["abundance_id", "taxon_id", "analysis_entity_id"],
                    "values": [
                        [1, 101, 1],
                        [2, 102, 2],
                    ],
                    "foreign_keys": [
                        {
                            "entity": "analysis_entity",  # FK to analysis_entity - creates circular dep
                            "local_keys": ["analysis_entity_id"],
                            "remote_keys": ["analysis_entity_id"],
                            # defer_dependency: false (default)
                        }
                    ],
                },
                "analysis_entity": {
                    "type": "fixed",
                    "keys": ["analysis_entity_id"],
                    "public_id": "analysis_entity_id",
                    "columns": ["analysis_entity_id"],
                    "values": [],  # Empty fixed entity
                    "append": [
                        {
                            "source": "abundance",  # Append from abundance - creates circular dep
                            "columns": ["analysis_entity_id"],
                        },
                    ],
                },
            },
        }

        project = ShapeShiftProject(cfg=config, filename="test-circular.yml")

        # Execute: Try to normalize - should fail with circular dependency error
        with pytest.raises(ValueError, match="Circular or unresolved dependencies detected"):
            normalizer = ShapeShifter(project=project)
            await normalizer.normalize()

    @pytest.mark.asyncio
    @with_test_config
    async def test_circular_dependency_with_defer_flag_should_succeed(self, test_provider):
        """Test that circular dependencies succeed with defer_dependency: true."""

        # Setup: Same circular reference but with defer_dependency: true
        config = {
            "entities": {
                "abundance": {
                    "type": "fixed",
                    "keys": ["abundance_id"],
                    "public_id": "abundance_id",
                    "columns": ["abundance_id", "taxon_id", "analysis_entity_id"],
                    "values": [
                        [1, 101, 1],
                        [2, 102, 2],
                    ],
                    "foreign_keys": [
                        {
                            "entity": "analysis_entity",
                            "local_keys": ["analysis_entity_id"],
                            "remote_keys": ["analysis_entity_id"],
                            "defer_dependency": True,  # Allow forward FK reference
                        }
                    ],
                },
                "analysis_entity": {
                    "type": "fixed",
                    "keys": ["analysis_entity_id"],
                    "public_id": "analysis_entity_id",
                    "columns": ["analysis_entity_id"],
                    "values": [],
                    "append": [
                        {
                            "source": "abundance",
                            "columns": ["analysis_entity_id"],
                        },
                    ],
                },
            },
        }

        project = ShapeShiftProject(cfg=config, filename="test-circular.yml")

        # Execute: Normalize should succeed
        normalizer = ShapeShifter(project=project)
        result = await normalizer.normalize()

        # Verify: Both entities should be created
        assert "abundance" in result.table_store
        assert "analysis_entity" in result.table_store

        # Verify: analysis_entity should have rows from abundance
        analysis_entity_df = result.table_store["analysis_entity"]
        assert len(analysis_entity_df) == 2
        assert set(analysis_entity_df["analysis_entity_id"].values) == {1, 2}

        # Verify: abundance should have FK link to analysis_entity resolved
        abundance_df = result.table_store["abundance"]
        assert len(abundance_df) == 2
        # FK should be preserved (analysis_entity_id exists)
        assert "analysis_entity_id" in abundance_df.columns

    @pytest.mark.asyncio
    @with_test_config
    async def test_complex_circular_dependency_with_three_entities(self, test_provider):
        """Test circular dependency with three entities: A -> B -> C -> A."""

        config = {
            "data_sources": {
                "test_source": {
                    "driver": "fixed",
                    "data": {
                        "entity_a": [
                            {"a_id": 1, "b_id": 1},
                            {"a_id": 2, "b_id": 2},
                        ],
                        "entity_b": [
                            {"b_id": 1, "c_id": 1},
                            {"b_id": 2, "c_id": 2},
                        ],
                    },
                }
            },
            "entities": {
                "entity_a": {
                    "source": "test_source",
                    "keys": ["a_id"],
                    "public_id": "a_id",
                    "foreign_keys": [
                        {
                            "entity": "entity_b",
                            "local_keys": ["b_id"],
                            "remote_keys": ["b_id"],
                            "defer_dependency": True,  # Defer to break cycle
                        }
                    ],
                },
                "entity_b": {
                    "source": "test_source",
                    "keys": ["b_id"],
                    "public_id": "b_id",
                    "foreign_keys": [
                        {
                            "entity": "entity_c",
                            "local_keys": ["c_id"],
                            "remote_keys": ["c_id"],
                            "defer_dependency": True,  # Defer to break cycle
                        }
                    ],
                },
                "entity_c": {
                    "type": "fixed",
                    "keys": ["c_id"],
                    "public_id": "c_id",
                    "values": [],
                    "append": [
                        {
                            "source": "entity_a",
                            "columns": ["a_id"],
                            "mapping": [{"a_id": "c_id"}],  # Map a_id -> c_id
                        },
                    ],
                },
            },
        }

        project = ShapeShiftProject(cfg=config, filename="test-circular.yml")

        # Execute: Should succeed with deferred dependencies
        normalizer = ShapeShifter(project=project)
        result = await normalizer.normalize()

        # Verify: All entities created
        assert "entity_a" in result.table_store
        assert "entity_b" in result.table_store
        assert "entity_c" in result.table_store

        # Verify: entity_c has rows from entity_a
        entity_c_df = result.table_store["entity_c"]
        assert len(entity_c_df) == 2
        assert set(entity_c_df["c_id"].values) == {1, 2}

    @pytest.mark.asyncio
    @with_test_config
    async def test_backwards_compatibility_default_defer_false(self, test_provider):
        """Test that defer_dependency defaults to False (backward compatible)."""

        # Setup: Simple FK without defer_dependency specified
        config = {
            "data_sources": {
                "test_source": {
                    "driver": "fixed",
                    "data": {
                        "parent": [
                            {"parent_id": 1, "name": "Parent 1"},
                            {"parent_id": 2, "name": "Parent 2"},
                        ],
                        "child": [
                            {"child_id": 1, "parent_id": 1},
                            {"child_id": 2, "parent_id": 2},
                        ],
                    },
                }
            },
            "entities": {
                "parent": {
                    "source": "test_source",
                    "keys": ["parent_id"],
                    "public_id": "parent_id",
                },
                "child": {
                    "source": "test_source",
                    "keys": ["child_id"],
                    "public_id": "child_id",
                    "foreign_keys": [
                        {
                            "entity": "parent",
                            "local_keys": ["parent_id"],
                            "remote_keys": ["parent_id"],
                            # defer_dependency not specified - should default to False
                        }
                    ],
                },
            },
        }

        project = ShapeShiftProject(cfg=config, filename="test-circular.yml")

        # Execute: Should work normally (parent processed before child)
        normalizer = ShapeShifter(project=project)
        result = await normalizer.normalize()

        # Verify: Both entities created with proper dependency order
        assert "parent" in result.table_store
        assert "child" in result.table_store

        # Verify: FK linked correctly
        child_df = result.table_store["child"]
        assert "parent_id" in child_df.columns
        assert len(child_df) == 2

    @pytest.mark.asyncio
    @with_test_config
    async def test_defer_dependency_with_multiple_fks(self, test_provider):
        """Test entity with multiple FKs, some deferred and some not."""

        config = {
            "data_sources": {
                "test_source": {
                    "driver": "fixed",
                    "data": {
                        "lookup_1": [
                            {"lookup_1_id": 1, "name": "Lookup 1"},
                        ],
                        "main_entity": [
                            {"main_id": 1, "lookup_1_id": 1, "circular_id": 1},
                        ],
                    },
                }
            },
            "entities": {
                "lookup_1": {
                    "source": "test_source",
                    "keys": ["lookup_1_id"],
                    "public_id": "lookup_1_id",
                },
                "main_entity": {
                    "source": "test_source",
                    "keys": ["main_id"],
                    "public_id": "main_id",
                    "foreign_keys": [
                        {
                            "entity": "lookup_1",
                            "local_keys": ["lookup_1_id"],
                            "remote_keys": ["lookup_1_id"],
                            # defer_dependency: false (default) - normal FK
                        },
                        {
                            "entity": "circular_entity",
                            "local_keys": ["circular_id"],
                            "remote_keys": ["circular_id"],
                            "defer_dependency": True,  # Deferred FK (circular)
                        },
                    ],
                },
                "circular_entity": {
                    "type": "fixed",
                    "keys": ["circular_id"],
                    "public_id": "circular_id",
                    "values": [],
                    "append": [
                        {
                            "source": "main_entity",
                            "columns": ["circular_id"],
                        },
                    ],
                },
            },
        }

        project = ShapeShiftProject(cfg=config, filename="test-circular.yml")

        # Execute: Should succeed
        normalizer = ShapeShifter(project=project)
        result = await normalizer.normalize()

        # Verify: All entities created
        assert "lookup_1" in result.table_store
        assert "main_entity" in result.table_store
        assert "circular_entity" in result.table_store

        # Verify: Dependency order respected (lookup_1 before main_entity)
        # but circular_entity deferred
        main_df = result.table_store["main_entity"]
        assert "lookup_1_id" in main_df.columns
        assert "circular_id" in main_df.columns

        circular_df = result.table_store["circular_entity"]
        assert len(circular_df) == 1
        assert set(circular_df["circular_id"].values) == {1}

    @pytest.mark.asyncio
    @with_test_config
    async def test_final_linking_pass_convergence(self, test_provider):
        """Test that final linking pass converges for valid configurations."""

        # Setup: Configuration that requires multiple linking passes
        config = {
            "data_sources": {
                "test_source": {
                    "driver": "fixed",
                    "data": {
                        "source_a": [
                            {"a_id": 1, "shared_id": 1},
                        ],
                        "source_b": [
                            {"b_id": 1, "shared_id": 1},
                        ],
                    },
                }
            },
            "entities": {
                "entity_a": {
                    "source": "test_source:source_a",
                    "keys": ["a_id"],
                    "public_id": "a_id",
                    "foreign_keys": [
                        {
                            "entity": "shared_entity",
                            "local_keys": ["shared_id"],
                            "remote_keys": ["shared_id"],
                            "defer_dependency": True,
                        }
                    ],
                },
                "entity_b": {
                    "source": "test_source:source_b",
                    "keys": ["b_id"],
                    "public_id": "b_id",
                    "foreign_keys": [
                        {
                            "entity": "shared_entity",
                            "local_keys": ["shared_id"],
                            "remote_keys": ["shared_id"],
                            "defer_dependency": True,
                        }
                    ],
                },
                "shared_entity": {
                    "type": "fixed",
                    "keys": ["shared_id"],
                    "public_id": "shared_id",
                    "values": [],
                    "append": [
                        {
                            "source": "entity_a",
                            "columns": ["shared_id"],
                        },
                        {
                            "source": "entity_b",
                            "columns": ["shared_id"],
                        },
                    ],
                },
            },
        }

        project = ShapeShiftProject(cfg=config, filename="test-circular.yml")

        # Execute: Should converge
        normalizer = ShapeShifter(project=project)
        result = await normalizer.normalize()

        # Verify: All entities created
        assert "entity_a" in result.table_store
        assert "entity_b" in result.table_store
        assert "shared_entity" in result.table_store

        # Verify: shared_entity has unique values from both sources
        shared_df = result.table_store["shared_entity"]
        assert len(shared_df) == 1  # Should deduplicate shared_id=1
        assert set(shared_df["shared_id"].values) == {1}
