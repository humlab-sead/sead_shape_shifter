"""Test that extra_columns from one FK can be used as local_keys in subsequent FKs."""

import pandas as pd
import pytest

from src.model import ShapeShiftProject
from src.transforms.link import ForeignKeyLinker


class TestLinkExtraColumnsChain:
    """Test chaining FKs where extra_columns from FK #1 are used as local_keys in FK #2."""

    @pytest.fixture
    def project_config(self):
        """Minimal project config with chained foreign keys using extra_columns."""
        return {
            "metadata": {"name": "test", "type": "shapeshifter-project"},
            "entities": {
                # Source entity
                "dataset": {
                    "type": "fixed",
                    "source": {"Projekt": ["P1", "P2"], "Fraktion": ["F1", "F2"]},
                    "public_id": "dataset_id",
                    "keys": ["Projekt", "Fraktion"],
                },
                # Intermediate entity that will be linked first
                "_project_contact": {
                    "type": "fixed",
                    "source": {
                        "Projekt": ["P1", "P2"],
                        "contact_type": ["ArchAusg", "BotBear"],
                        "contact_name": ["Alice", "Bob"],
                    },
                    "public_id": "project_contact_id",
                    "keys": ["Projekt", "contact_type", "contact_name"],
                },
                # Final target entity
                "contact": {
                    "type": "fixed",
                    "source": {"contact_name": ["Alice", "Bob", "Charlie"], "email": ["a@test.com", "b@test.com", "c@test.com"]},
                    "public_id": "contact_id",
                    "keys": ["contact_name"],
                },
                # Entity with chained FKs: FK #1 adds contact_name via extra_columns, FK #2 uses it
                "dataset_contacts": {
                    "type": "entity",
                    "source": "dataset",
                    "public_id": "dataset_contact_id",
                    "keys": ["Projekt", "Fraktion"],
                    "foreign_keys": [
                        # FK #1: Link to _project_contact and bring contact_name as extra column
                        {
                            "entity": "_project_contact",
                            "local_keys": ["Projekt"],
                            "remote_keys": ["Projekt"],
                            "extra_columns": {"contact_name": "contact_name"},
                        },
                        # FK #2: Use contact_name (from FK #1) to link to contact
                        {"entity": "contact", "local_keys": ["contact_name"], "remote_keys": ["contact_name"]},
                    ],
                },
            },
        }

    @pytest.fixture
    def project(self, project_config):
        """Create ShapeShiftProject from config."""
        return ShapeShiftProject(cfg=project_config, filename="test.yml")

    def test_extra_columns_chain_linking(self, project):
        """Test that FK #2 can use columns added by FK #1's extra_columns."""
        # Initialize table store with source data
        table_store = {
            "dataset": pd.DataFrame({"Projekt": ["P1", "P2"], "Fraktion": ["F1", "F2"], "system_id": [1, 2]}),
            "_project_contact": pd.DataFrame(
                {
                    "Projekt": ["P1", "P2"],
                    "contact_type": ["ArchAusg", "BotBear"],
                    "contact_name": ["Alice", "Bob"],
                    "system_id": [1, 2],
                }
            ),
            "contact": pd.DataFrame(
                {"contact_name": ["Alice", "Bob", "Charlie"], "email": ["a@test.com", "b@test.com", "c@test.com"], "system_id": [1, 2, 3]}
            ),
            "dataset_contacts": pd.DataFrame({"Projekt": ["P1", "P2"], "Fraktion": ["F1", "F2"], "system_id": [1, 2]}),
        }

        # Link the entity
        linker = ForeignKeyLinker(project, table_store)
        deferred = linker.link_entity("dataset_contacts")

        # Verify linking succeeded (not deferred)
        assert not deferred

        # Verify the result has both FK columns
        result = table_store["dataset_contacts"]

        # FK #1 should have added project_contact_id and contact_name
        assert "project_contact_id" in result.columns
        assert "contact_name" in result.columns

        # FK #2 should have added contact_id
        assert "contact_id" in result.columns

        # Verify data correctness
        assert result["contact_name"].tolist() == ["Alice", "Bob"]
        assert result["project_contact_id"].tolist() == [1, 2]  # system_ids from _project_contact
        assert result["contact_id"].tolist() == [1, 2]  # system_ids from contact

    def test_extra_columns_not_available_fails_validation(self, project):
        """Test that FK #2 fails validation if FK #1 hasn't added the required column."""
        # Initialize table store without _project_contact (so FK #1 will fail)
        table_store = {
            "dataset": pd.DataFrame({"Projekt": ["P1", "P2"], "Fraktion": ["F1", "F2"], "system_id": [1, 2]}),
            # Missing _project_contact - FK #1 will be deferred
            "contact": pd.DataFrame(
                {"contact_name": ["Alice", "Bob", "Charlie"], "email": ["a@test.com", "b@test.com", "c@test.com"], "system_id": [1, 2, 3]}
            ),
            "dataset_contacts": pd.DataFrame({"Projekt": ["P1", "P2"], "Fraktion": ["F1", "F2"], "system_id": [1, 2]}),
        }

        # Link the entity
        linker = ForeignKeyLinker(project, table_store)
        deferred = linker.link_entity("dataset_contacts")

        # Verify linking was deferred (because _project_contact is missing)
        assert deferred

        # Verify FK #1 was deferred and FK #2 couldn't proceed
        result = table_store["dataset_contacts"]
        assert "contact_name" not in result.columns
        assert "contact_id" not in result.columns
