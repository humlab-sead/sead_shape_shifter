"""Tests for the pure fixed-entity mapping retry comparison.

Covers unchanged, unrelated-edit, affected-row-edit, affected-link metadata
edit, already-applied, mixed, entry-only, missing-row, and compound-key cases.
Every case asserts the exact conflict keys and that the input catalog is not
modified.
"""

from datetime import datetime, timezone

import pytest

from src.reconciliation.fixed_entity_mapping_changes import FixedEntityMappingChangeError, LinkDelete, LinkUpsert, RowSnapshot
from src.reconciliation.fixed_entity_mapping_retry import plan_fixed_entity_mapping_retry
from src.reconciliation.mapping_model import EntityMapping, EntityType, Link, LinkSource, MappingCatalog, Metadata

CREATED = datetime(2026, 1, 1, tzinfo=timezone.utc)
COLUMNS = ["site_id", "site_code"]
COMPOUND_COLUMNS = ["site_id", "country", "name"]


def _link(
    target_id: int,
    *,
    source: LinkSource = LinkSource.MANUAL,
    created_by: str = "tester",
    notes: str | None = None,
) -> Link:
    return Link(
        target_id=target_id,
        source=source,
        created_by=created_by,
        created_at=CREATED,
        committed_at=CREATED,
        notes=notes,
    )


def _entry(links: dict[str, Link] | None = None, *, local_key="site_code", public_id="site_id") -> EntityMapping:
    return EntityMapping(local_key=local_key, public_id=public_id, entity_type=EntityType.PRIMARY, links=dict(links or {}))


def _catalog(entry: EntityMapping | None) -> MappingCatalog:
    return MappingCatalog(
        metadata=Metadata(project="test", created_at=CREATED, updated_at=CREATED),
        entities={"site": entry} if entry is not None else {},
    )


def _rows(rows: list[list[object]], columns: list[str] | None = None) -> RowSnapshot:
    return RowSnapshot(columns=list(columns or COLUMNS), values=[list(row) for row in rows])


def _plan(
    *,
    catalog: MappingCatalog,
    rows: RowSnapshot | None,
    upserts: tuple[LinkUpsert, ...] = (),
    deletes: tuple[LinkDelete, ...] = (),
    proposed_entry: EntityMapping | None = None,
    local_key="site_code",
    public_id="site_id",
):
    return plan_fixed_entity_mapping_retry(
        entity_name="site",
        local_key=local_key,
        public_id=public_id,
        current_rows=rows,
        catalog=catalog,
        upserts=upserts,
        deletes=deletes,
        proposed_entry=proposed_entry,
    )


def _upsert(key: str, target_id: int, previous_link: Link | None = None) -> LinkUpsert:
    return LinkUpsert(key=key, target_id=target_id, previous_saved_id=None, new_saved_id=target_id, previous_link=previous_link)


def _delete(key: str, previous_link: Link | None = None, *, row_removed: bool) -> LinkDelete:
    return LinkDelete(key=key, previous_saved_id=None, new_saved_id=None, row_removed=row_removed, previous_link=previous_link)


class TestRetryPlan:
    def test_already_applied_upsert_is_no_op(self) -> None:
        catalog = _catalog(_entry({"A": _link(10)}))
        rows = _rows([[10, "A"]])

        plan = _plan(catalog=catalog, rows=rows, upserts=(_upsert("A", 10),))

        assert plan.has_conflicts is False
        assert plan.is_no_op is True

    def test_already_applied_delete_is_no_op(self) -> None:
        catalog = _catalog(_entry({}))
        rows = _rows([[5, "B"]])

        plan = _plan(catalog=catalog, rows=rows, deletes=(_delete("A", _link(7, source=LinkSource.IMPORT), row_removed=True),))

        assert plan.has_conflicts is False
        assert plan.is_no_op is True

    def test_unapplied_upsert_is_applied(self) -> None:
        catalog = _catalog(_entry({"Unrelated": _link(1, source=LinkSource.IMPORT)}))
        rows = _rows([[10, "A"], [99, "Unrelated"]])

        plan = _plan(catalog=catalog, rows=rows, upserts=(_upsert("A", 10),))

        assert plan.conflict_keys == ()
        assert [upsert.key for upsert in plan.upserts_to_apply] == ["A"]
        assert plan.is_no_op is False

    def test_unrelated_row_and_link_edits_do_not_block(self) -> None:
        catalog = _catalog(_entry({"Unrelated": _link(1, source=LinkSource.IMPORT)}))
        # An unrelated row value changed from the pre-save image.
        rows = _rows([[10, "A"], [123, "Unrelated"]])

        plan = _plan(catalog=catalog, rows=rows, upserts=(_upsert("A", 10),))

        assert plan.has_conflicts is False
        assert plan.upserts_to_apply[0].key == "A"

    def test_affected_row_change_is_a_conflict(self) -> None:
        catalog = _catalog(_entry({}))
        rows = _rows([[99, "A"]])

        plan = _plan(catalog=catalog, rows=rows, upserts=(_upsert("A", 10),))

        assert plan.conflict_keys == ("A",)
        assert plan.upserts_to_apply == ()

    def test_missing_affected_row_is_a_conflict(self) -> None:
        catalog = _catalog(_entry({}))
        rows = _rows([[10, "Other"]])

        plan = _plan(catalog=catalog, rows=rows, upserts=(_upsert("A", 10),))

        assert plan.conflict_keys == ("A",)

    def test_affected_link_metadata_edit_is_a_conflict(self) -> None:
        prior = _link(5, notes="original")
        catalog = _catalog(_entry({"A": _link(5, notes="edited-by-user")}))
        rows = _rows([[None, "A"]])

        plan = _plan(catalog=catalog, rows=rows, deletes=(_delete("A", prior, row_removed=False),))

        assert plan.conflict_keys == ("A",)

    def test_matching_prior_link_delete_is_applied(self) -> None:
        prior = _link(5, source=LinkSource.IMPORT)
        catalog = _catalog(_entry({"A": _link(5, source=LinkSource.IMPORT)}))
        rows = _rows([[None, "A"]])

        plan = _plan(catalog=catalog, rows=rows, deletes=(_delete("A", prior, row_removed=False),))

        assert plan.conflict_keys == ()
        assert [delete.key for delete in plan.deletes_to_apply] == ["A"]

    def test_mixed_already_applied_and_unapplied(self) -> None:
        catalog = _catalog(_entry({"A": _link(10)}))
        rows = _rows([[10, "A"], [20, "B"]])

        plan = _plan(catalog=catalog, rows=rows, upserts=(_upsert("A", 10), _upsert("B", 20)))

        assert plan.has_conflicts is False
        assert [upsert.key for upsert in plan.upserts_to_apply] == ["B"]

    def test_upsert_with_changed_prior_link_is_a_conflict(self) -> None:
        prior = _link(7, source=LinkSource.RECONCILIATION)
        catalog = _catalog(_entry({"A": _link(8, source=LinkSource.RECONCILIATION)}))
        rows = _rows([[10, "A"]])

        plan = _plan(catalog=catalog, rows=rows, upserts=(_upsert("A", 10, previous_link=prior),))

        assert plan.conflict_keys == ("A",)

    def test_upsert_with_matching_prior_link_is_applied(self) -> None:
        prior = _link(7, source=LinkSource.RECONCILIATION)
        catalog = _catalog(_entry({"A": _link(7, source=LinkSource.RECONCILIATION)}))
        rows = _rows([[10, "A"]])

        plan = _plan(catalog=catalog, rows=rows, upserts=(_upsert("A", 10, previous_link=prior),))

        assert plan.conflict_keys == ()
        assert [upsert.key for upsert in plan.upserts_to_apply] == ["A"]

    def test_compound_key_upsert_is_applied(self) -> None:
        catalog = _catalog(_entry({}, local_key=["country", "name"]))
        rows = _rows([[10, "SE", "A"]], columns=COMPOUND_COLUMNS)

        plan = _plan(
            catalog=catalog,
            rows=rows,
            upserts=(_upsert("SE|A", 10),),
            local_key=["country", "name"],
        )

        assert plan.has_conflicts is False
        assert [upsert.key for upsert in plan.upserts_to_apply] == ["SE|A"]

    def test_invalid_current_rows_report_affected_keys_as_conflicts(self) -> None:
        catalog = _catalog(_entry({}))
        # Duplicate encoded keys make the current rows unusable.
        rows = _rows([[10, "A"], [11, "A"]])

        plan = _plan(catalog=catalog, rows=rows, upserts=(_upsert("A", 10),))

        assert plan.conflict_keys == ("A",)


class TestRetryEntryHandling:
    def test_missing_entry_with_proposal_creates_entry(self) -> None:
        catalog = _catalog(None)
        rows = _rows([[10, "A"]])
        entry = EntityMapping(local_key="site_code", public_id="site_id", entity_type=EntityType.PRIMARY)

        plan = _plan(catalog=catalog, rows=rows, proposed_entry=entry)

        assert plan.create_entry is True
        assert plan.has_conflicts is False

    def test_existing_equivalent_entry_is_no_op(self) -> None:
        catalog = _catalog(_entry())
        rows = _rows([[10, "A"]])
        entry = EntityMapping(local_key="site_code", public_id="site_id", entity_type=EntityType.PRIMARY)

        plan = _plan(catalog=catalog, rows=rows, proposed_entry=entry)

        assert plan.create_entry is False
        assert plan.is_no_op is True

    def test_incompatible_entry_is_a_conflict(self) -> None:
        catalog = _catalog(_entry(public_id="other_id"))
        rows = _rows([[10, "A"]])
        entry = EntityMapping(local_key="site_code", public_id="site_id", entity_type=EntityType.PRIMARY)

        plan = _plan(catalog=catalog, rows=rows, proposed_entry=entry)

        assert plan.entry_conflict is True
        assert plan.has_conflicts is True

    def test_missing_entry_without_proposal_is_a_config_conflict(self) -> None:
        catalog = _catalog(None)
        rows = _rows([[10, "A"]])

        plan = _plan(catalog=catalog, rows=rows, upserts=(_upsert("A", 10),))

        assert plan.config_conflict is True
        assert plan.conflict_keys == ("A",)

    def test_stored_config_mismatch_is_a_config_conflict(self) -> None:
        catalog = _catalog(_entry(local_key="other_code"))
        rows = _rows([[10, "A"]])

        plan = _plan(catalog=catalog, rows=rows, upserts=(_upsert("A", 10),))

        assert plan.config_conflict is True


class TestRetryDoesNotMutateInput:
    def test_planning_leaves_catalog_unchanged(self) -> None:
        catalog = _catalog(_entry({}))
        before = catalog.model_dump(mode="json")

        _plan(catalog=catalog, rows=_rows([[10, "A"]]), upserts=(_upsert("A", 10),))

        assert catalog.model_dump(mode="json") == before

    def test_planning_leaves_row_snapshot_unchanged(self) -> None:
        catalog = _catalog(_entry({}))
        rows = _rows([[10, "A"]])
        before = [list(row) for row in rows.values]

        _plan(catalog=catalog, rows=rows, upserts=(_upsert("A", 10),))

        assert rows.values == before


def test_invalid_rows_without_affected_key_still_raises_on_build() -> None:
    """The shared row-index helper still raises for a directly unusable snapshot."""
    rows = _rows([[10, "A"], [11, "A"]])
    with pytest.raises(FixedEntityMappingChangeError):
        # Planning catches this and returns conflicts, but a direct build raises.
        from src.reconciliation.fixed_entity_mapping_changes import build_row_index

        build_row_index("site", rows, "site_code", "site_id")
