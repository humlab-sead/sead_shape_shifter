"""Tests for pure fixed-entity mapping change calculation.

Covers the missing-value rule, invalid changed IDs, unusable keys, ordered
default keys, eligibility, unchanged rows, deliberate edits, row removal, and
row key changes. Every case asserts the exact change set and that the input
mapping catalog is not mutated.
"""

from datetime import datetime, timezone

import pytest

from src.reconciliation.fixed_entity_mapping_changes import (
    FixedEntityMappingChangeError,
    LinkDelete,
    LinkUpsert,
    RowSnapshot,
    apply_fixed_row_change_set,
    compute_fixed_row_change_set,
    default_local_key,
    ordered_key_columns,
)
from src.reconciliation.mapping_model import EntityMapping, EntityType, Link, LinkSource, MappingCatalog, Metadata, encode_local_key

CREATED = datetime(2026, 1, 1, tzinfo=timezone.utc)
LOCAL_KEY = ["site_code", "sample_code"]
PUBLIC_ID = "sample_id"
COLUMNS = [PUBLIC_ID, "site_code", "sample_code"]
_UNSET = object()


def _link(
    target_id: int,
    *,
    source: LinkSource = LinkSource.MANUAL,
    created_by: str = "tester",
) -> Link:
    return Link(
        target_id=target_id,
        source=source,
        created_by=created_by,
        committed_at=CREATED,
        created_at=CREATED,
    )


def _entry(
    links: dict[str, Link] | None = None,
    *,
    local_key: str | list[str] | None = None,
    public_id: str = PUBLIC_ID,
) -> EntityMapping:
    return EntityMapping(
        local_key=local_key if local_key is not None else LOCAL_KEY,
        public_id=public_id,
        entity_type=EntityType.PRIMARY,
        links=dict(links or {}),
    )


def _key(site_code: str, sample_code: str) -> str:
    return encode_local_key(LOCAL_KEY, [site_code, sample_code])


def _catalog(entry: EntityMapping | None = None) -> MappingCatalog:
    return MappingCatalog(
        metadata=Metadata(project="test", created_at=CREATED, updated_at=CREATED),
        entities={"samples": entry} if entry is not None else {},
    )


def _snapshot(rows: list[list[object]], columns: list[str] | None = None) -> RowSnapshot:
    return RowSnapshot(columns=list(columns or COLUMNS), values=[list(row) for row in rows])


def _compute(
    previous: RowSnapshot | None,
    current: RowSnapshot | None,
    *,
    existing_entry: object = _UNSET,
    keys: object = _UNSET,
    public_id: str | None = PUBLIC_ID,
    materialized: bool = False,
    entity_type: str | None = "fixed",
):
    if existing_entry is _UNSET:
        existing_entry = _entry()
    if keys is _UNSET:
        keys = LOCAL_KEY
    return compute_fixed_row_change_set(
        entity_name="samples",
        entity_type=entity_type,
        materialized=materialized,
        keys=keys,
        public_id=public_id,
        existing_entry=existing_entry,  # type: ignore[arg-type]
        previous=previous,
        current=current,
    )


# ---------------------------------------------------------------------------
# Shared ordered default key
# ---------------------------------------------------------------------------


class TestDefaultLocalKey:
    def test_single_key_returns_scalar(self) -> None:
        assert default_local_key(["sample_code"]) == "sample_code"

    def test_multiple_keys_preserve_declared_order(self) -> None:
        assert default_local_key(["site_code", "sample_code"]) == ["site_code", "sample_code"]

    def test_string_key_returns_scalar(self) -> None:
        assert default_local_key("sample_code") == "sample_code"

    def test_empty_and_absent_keys_return_empty_list(self) -> None:
        assert default_local_key([]) == []
        assert default_local_key(None) == []

    def test_ordered_key_columns_filters_non_strings(self) -> None:
        assert ordered_key_columns(["a", 5, "b"]) == ["a", "b"]  # type: ignore[list-item]


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------


class TestEligibility:
    def test_non_fixed_entity_is_not_eligible(self) -> None:
        result = _compute(_snapshot([]), _snapshot([]), entity_type="entity")
        assert result.eligible is False
        assert result.is_empty is True

    def test_non_materialized_fixed_without_entry_is_not_eligible(self) -> None:
        result = _compute(_snapshot([]), _snapshot([]), materialized=False, existing_entry=None)
        assert result.eligible is False
        assert result.is_empty is True

    def test_materialized_fixed_without_entry_proposes_entry_with_ordered_keys(self) -> None:
        result = _compute(
            None,
            _snapshot([[5, "S", "A"]]),
            keys=["site_code", "sample_code"],
            materialized=True,
            existing_entry=None,
        )
        assert result.eligible is True
        assert result.creates_entry is True
        assert result.proposed_entry is not None
        assert result.proposed_entry.local_key == ["site_code", "sample_code"]
        assert result.proposed_entry.public_id == PUBLIC_ID
        assert [upsert.key for upsert in result.upserts] == [_key("S", "A")]

    def test_materialized_fixed_without_entry_and_without_keys_is_rejected(self) -> None:
        with pytest.raises(FixedEntityMappingChangeError, match="entity.keys"):
            _compute(None, _snapshot([[5, "S", "A"]]), keys=[], materialized=True, existing_entry=None)

    def test_non_materialized_fixed_with_existing_entry_is_eligible(self) -> None:
        result = _compute(
            _snapshot([[5, "S", "A"]]),
            _snapshot([[5, "S", "A"]]),
            existing_entry=_entry({_key("S", "A"): _link(5)}),
            materialized=False,
        )
        assert result.eligible is True
        assert result.creates_entry is False


# ---------------------------------------------------------------------------
# Missing-value rule and invalid IDs
# ---------------------------------------------------------------------------


class TestMissingValues:
    @pytest.mark.parametrize("blank", [None, float("nan"), "", "   "])
    def test_non_blank_to_blank_clears_the_link(self, blank: object) -> None:
        entry = _entry({_key("S", "A"): _link(5)})
        result = _compute(_snapshot([[5, "S", "A"]]), _snapshot([[blank, "S", "A"]]), existing_entry=entry)
        assert result.upserts == ()
        assert result.deletes == (
            LinkDelete(
                key=_key("S", "A"),
                previous_saved_id=5,
                new_saved_id=None,
                row_removed=False,
                previous_link=entry.links[_key("S", "A")],
                row_index=0,
            ),
        )

    @pytest.mark.parametrize("blank", [None, float("nan"), "", "   "])
    def test_blank_to_blank_keeps_a_sidecar_only_link(self, blank: object) -> None:
        entry = _entry({_key("S", "A"): _link(5)})
        result = _compute(_snapshot([[blank, "S", "A"]]), _snapshot([[blank, "S", "A"]]), existing_entry=entry)
        assert result.is_empty is True

    @pytest.mark.parametrize("blank", [None, float("nan"), "", "   "])
    def test_unchanged_blank_rows_keep_a_link(self, blank: object) -> None:
        entry = _entry({_key("S", "A"): _link(5)})
        result = _compute(_snapshot([[blank, "S", "A"]]), _snapshot([[blank, "S", "A"]]), existing_entry=entry)
        assert result.is_empty is True

    def test_zero_is_a_valid_target(self) -> None:
        result = _compute(None, _snapshot([[0, "S", "A"]]))
        assert result.upserts == (
            LinkUpsert(key=_key("S", "A"), target_id=0, previous_saved_id=None, new_saved_id=0, previous_link=None, row_index=0),
        )

    def test_unchanged_zero_row_with_missing_link_adds(self) -> None:
        result = _compute(_snapshot([[0, "S", "A"]]), _snapshot([[0, "S", "A"]]), existing_entry=_entry())
        assert [upsert.target_id for upsert in result.upserts] == [0]

    def test_bool_id_is_rejected(self) -> None:
        with pytest.raises(FixedEntityMappingChangeError, match="invalid mapping target"):
            _compute(None, _snapshot([[True, "S", "A"]]))

    def test_float_id_is_rejected(self) -> None:
        with pytest.raises(FixedEntityMappingChangeError, match="invalid mapping target"):
            _compute(None, _snapshot([[5.0, "S", "A"]]))

    def test_invalid_string_id_is_rejected(self) -> None:
        with pytest.raises(FixedEntityMappingChangeError, match="invalid mapping target"):
            _compute(None, _snapshot([["abc", "S", "A"]]))

    def test_changed_invalid_id_is_rejected(self) -> None:
        entry = _entry({_key("S", "A"): _link(5)})
        with pytest.raises(FixedEntityMappingChangeError, match="invalid mapping target"):
            _compute(_snapshot([[5, "S", "A"]]), _snapshot([["abc", "S", "A"]]), existing_entry=entry)


# ---------------------------------------------------------------------------
# Unusable keys and columns
# ---------------------------------------------------------------------------


class TestUnusableInput:
    def test_missing_stored_column_is_rejected(self) -> None:
        with pytest.raises(FixedEntityMappingChangeError, match="missing stored mapping column"):
            _compute(None, _snapshot([[5, "S", "A"]], columns=["site_code", "sample_code"]))

    def test_missing_key_component_is_rejected(self) -> None:
        with pytest.raises(FixedEntityMappingChangeError, match="missing key value"):
            _compute(None, _snapshot([[5, None, "A"]]))

    def test_blank_key_component_is_rejected(self) -> None:
        with pytest.raises(FixedEntityMappingChangeError, match="missing key value"):
            _compute(None, _snapshot([[5, "S", "   "]]))

    def test_duplicate_encoded_key_is_rejected(self) -> None:
        with pytest.raises(FixedEntityMappingChangeError, match="share the same encoded key"):
            _compute(None, _snapshot([[5, "S", "A"], [6, "S", "A"]]))

    def test_row_width_mismatch_is_rejected(self) -> None:
        with pytest.raises(FixedEntityMappingChangeError, match="has 2 values but 3 columns"):
            _compute(None, _snapshot([[5, "S"]]))


# ---------------------------------------------------------------------------
# Change classification
# ---------------------------------------------------------------------------


class TestChangeClassification:
    def test_unchanged_row_retains_existing_manual_link(self) -> None:
        entry = _entry({_key("S", "A"): _link(5)})
        result = _compute(_snapshot([[5, "S", "A"]]), _snapshot([[5, "S", "A"]]), existing_entry=entry)
        assert result.is_empty is True
        assert entry.links[_key("S", "A")].committed_at == CREATED

    def test_unchanged_row_retains_older_manual_target(self) -> None:
        entry = _entry({_key("S", "A"): _link(7)})
        result = _compute(_snapshot([[5, "S", "A"]]), _snapshot([[5, "S", "A"]]), existing_entry=entry)
        assert result.is_empty is True

    def test_unchanged_row_retains_reconciliation_link(self) -> None:
        entry = _entry({_key("S", "A"): _link(9, source=LinkSource.RECONCILIATION)})
        result = _compute(_snapshot([[5, "S", "A"]]), _snapshot([[5, "S", "A"]]), existing_entry=entry)
        assert result.is_empty is True

    def test_unchanged_row_with_missing_link_adds_a_manual_link(self) -> None:
        result = _compute(_snapshot([[5, "S", "A"]]), _snapshot([[5, "S", "A"]]), existing_entry=_entry())
        assert result.upserts == (
            LinkUpsert(key=_key("S", "A"), target_id=5, previous_saved_id=5, new_saved_id=5, previous_link=None, row_index=0),
        )

    def test_new_row_adds_a_manual_link(self) -> None:
        result = _compute(None, _snapshot([[5, "S", "A"]]))
        assert [upsert.key for upsert in result.upserts] == [_key("S", "A")]

    def test_id_edit_replaces_a_reconciliation_link(self) -> None:
        entry = _entry({_key("S", "A"): _link(5, source=LinkSource.RECONCILIATION)})
        result = _compute(_snapshot([[5, "S", "A"]]), _snapshot([[6, "S", "A"]]), existing_entry=entry)
        assert result.deletes == ()
        assert result.upserts[0].target_id == 6
        assert result.upserts[0].previous_link is entry.links[_key("S", "A")]

    def test_previously_blank_to_non_blank_adds_a_manual_link(self) -> None:
        entry = _entry({_key("S", "A"): _link(3, source=LinkSource.IMPORT)})
        result = _compute(_snapshot([[None, "S", "A"]]), _snapshot([[5, "S", "A"]]), existing_entry=entry)
        assert result.deletes == ()
        assert result.upserts[0].target_id == 5

    def test_matching_manual_link_is_retained_without_replacement(self) -> None:
        entry = _entry({_key("S", "A"): _link(5)})
        result = _compute(_snapshot([[None, "S", "A"]]), _snapshot([[5, "S", "A"]]), existing_entry=entry)
        assert result.is_empty is True

    def test_row_removal_deletes_any_link(self) -> None:
        entry = _entry({_key("S", "A"): _link(5, source=LinkSource.RECONCILIATION)})
        result = _compute(_snapshot([[5, "S", "A"]]), _snapshot([]), existing_entry=entry)
        assert len(result.deletes) == 1
        assert result.deletes[0].key == _key("S", "A")
        assert result.deletes[0].row_removed is True
        assert result.deletes[0].new_saved_id is None
        assert result.deletes[0].previous_link is entry.links[_key("S", "A")]

    def test_key_change_is_removal_plus_addition(self) -> None:
        entry = _entry({_key("S", "A"): _link(5)})
        result = _compute(_snapshot([[5, "S", "A"]]), _snapshot([[5, "S", "B"]]), existing_entry=entry)
        assert [upsert.key for upsert in result.upserts] == [_key("S", "B")]
        assert [delete.key for delete in result.deletes] == [_key("S", "A")]

    def test_single_local_key_is_encoded_as_a_scalar(self) -> None:
        entry = _entry(local_key="site_code")
        result = compute_fixed_row_change_set(
            entity_name="samples",
            entity_type="fixed",
            materialized=False,
            keys=["site_code"],
            public_id=PUBLIC_ID,
            existing_entry=entry,
            previous=None,
            current=RowSnapshot(columns=[PUBLIC_ID, "site_code"], values=[[5, "A"]]),
        )

        assert [upsert.key for upsert in result.upserts] == ["A"]

    def test_input_entry_links_are_not_mutated(self) -> None:
        link = _link(5)
        entry = _entry({_key("S", "A"): link})
        _compute(_snapshot([[5, "S", "A"]]), _snapshot([[6, "S", "A"]]), existing_entry=entry)
        assert entry.links == {_key("S", "A"): link}
        assert link.source == LinkSource.MANUAL


class TestApplyFixedRowChangeSet:
    @pytest.mark.parametrize(
        ("previous_rows", "current_rows", "initial_links", "expected_keys", "expected_targets", "expected_changed"),
        [
            (None, [[5, "S", "A"]], {}, {_key("S", "A")}, {_key("S", "A"): 5}, True),
            (
                [[5, "S", "A"]],
                [[6, "S", "A"]],
                {_key("S", "A"): _link(5, source=LinkSource.RECONCILIATION)},
                {_key("S", "A")},
                {_key("S", "A"): 6},
                True,
            ),
            ([[5, "S", "A"]], [[None, "S", "A"]], {_key("S", "A"): _link(5)}, set(), {}, True),
            ([[5, "S", "A"]], [], {_key("S", "A"): _link(5)}, set(), {}, True),
            (
                [[5, "S", "A"]],
                [[5, "S", "B"]],
                {_key("S", "A"): _link(5)},
                {_key("S", "B")},
                {_key("S", "B"): 5},
                True,
            ),
        ],
        ids=["add", "edit", "clear", "remove", "key-change"],
    )
    def test_applies_exact_affected_key_operations(
        self, previous_rows, current_rows, initial_links, expected_keys, expected_targets, expected_changed
    ) -> None:
        entry = _entry(initial_links)
        catalog = _catalog(entry)
        changes = _compute(
            _snapshot(previous_rows) if previous_rows is not None else None,
            _snapshot(current_rows),
            existing_entry=entry,
        )

        changed = apply_fixed_row_change_set(catalog, changes, created_by="sync", committed_at=CREATED)

        assert changed is expected_changed
        assert set(catalog.entities["samples"].links) == expected_keys
        assert {key: link.target_id for key, link in catalog.entities["samples"].links.items()} == expected_targets
        for key, link in initial_links.items():
            if key in expected_keys and link.source != LinkSource.MANUAL:
                continue
            if key in expected_keys and expected_targets[key] == link.target_id:
                assert catalog.entities["samples"].links[key] == link

    def test_creates_proposed_entry_even_when_no_link_is_added(self) -> None:
        changes = _compute(None, _snapshot([]), materialized=True, existing_entry=None)
        catalog = _catalog()

        changed = apply_fixed_row_change_set(catalog, changes, created_by="sync", committed_at=CREATED)

        assert changed is True
        assert catalog.entities["samples"].local_key == LOCAL_KEY
        assert catalog.entities["samples"].links == {}

    def test_noop_preserves_matching_manual_link_metadata(self) -> None:
        link = Link(
            target_id=5,
            source=LinkSource.MANUAL,
            confidence=0.8,
            created_at=CREATED,
            committed_at=CREATED,
            notes="keep",
            created_by="original",
            reviewed_by="reviewer",
        )
        entry = _entry({_key("S", "A"): link})
        catalog = _catalog(entry)
        changes = _compute(_snapshot([[None, "S", "A"]]), _snapshot([[5, "S", "A"]]), existing_entry=entry)

        changed = apply_fixed_row_change_set(catalog, changes, created_by="sync", committed_at=datetime(2026, 2, 1, tzinfo=timezone.utc))

        assert changed is False
        assert catalog.entities["samples"].links[_key("S", "A")] == link

    def test_ineligible_change_set_does_not_change_catalog(self) -> None:
        catalog = _catalog()
        changes = _compute(None, None, entity_type="entity", existing_entry=None)

        changed = apply_fixed_row_change_set(catalog, changes, created_by="sync", committed_at=CREATED)

        assert changed is False
        assert catalog.entities == {}
