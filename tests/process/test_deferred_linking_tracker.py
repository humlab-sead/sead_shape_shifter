"""Unit tests for DeferredLinkingTracker."""

import pytest

from src.process_state import DeferredLinkingTracker


class TestDeferredLinkingTracker:
    """Test suite for DeferredLinkingTracker class."""

    def test_initialization(self) -> None:
        """Test that DeferredLinkingTracker initializes with empty deferred set."""
        tracker = DeferredLinkingTracker()
        assert tracker.deferred == set()
        assert isinstance(tracker.deferred, set)

    def test_track_single_entity_as_deferred(self) -> None:
        """Test tracking a single entity as deferred."""
        tracker = DeferredLinkingTracker()
        tracker.track(entity_name="entity1", deferred=True)
        assert "entity1" in tracker.deferred
        assert len(tracker.deferred) == 1

    def test_track_single_entity_as_not_deferred(self) -> None:
        """Test tracking a single entity as not deferred (should not add to set)."""
        tracker = DeferredLinkingTracker()
        tracker.track(entity_name="entity1", deferred=False)
        assert "entity1" not in tracker.deferred
        assert len(tracker.deferred) == 0

    def test_track_multiple_entities_as_deferred(self) -> None:
        """Test tracking multiple entities as deferred."""
        tracker = DeferredLinkingTracker()
        tracker.track(entity_name="entity1", deferred=True)
        tracker.track(entity_name="entity2", deferred=True)
        tracker.track(entity_name="entity3", deferred=True)
        assert tracker.deferred == {"entity1", "entity2", "entity3"}
        assert len(tracker.deferred) == 3

    def test_track_mixed_deferred_status(self) -> None:
        """Test tracking entities with mixed deferred status."""
        tracker = DeferredLinkingTracker()
        tracker.track(entity_name="entity1", deferred=True)
        tracker.track(entity_name="entity2", deferred=False)
        tracker.track(entity_name="entity3", deferred=True)
        assert tracker.deferred == {"entity1", "entity3"}
        assert len(tracker.deferred) == 2

    def test_remove_deferred_entity(self) -> None:
        """Test removing an entity from deferred set by marking it as not deferred."""
        tracker = DeferredLinkingTracker()
        tracker.track(entity_name="entity1", deferred=True)
        assert "entity1" in tracker.deferred

        tracker.track(entity_name="entity1", deferred=False)
        assert "entity1" not in tracker.deferred
        assert len(tracker.deferred) == 0

    def test_remove_non_existent_entity(self) -> None:
        """Test removing an entity that was never added (discard should handle gracefully)."""
        tracker = DeferredLinkingTracker()
        # Should not raise an error
        tracker.track(entity_name="entity1", deferred=False)
        assert "entity1" not in tracker.deferred
        assert len(tracker.deferred) == 0

    def test_add_same_entity_multiple_times(self) -> None:
        """Test adding the same entity multiple times as deferred."""
        tracker = DeferredLinkingTracker()
        tracker.track(entity_name="entity1", deferred=True)
        tracker.track(entity_name="entity1", deferred=True)
        tracker.track(entity_name="entity1", deferred=True)
        # Sets should only contain unique items
        assert tracker.deferred == {"entity1"}
        assert len(tracker.deferred) == 1

    def test_toggle_entity_deferred_status(self) -> None:
        """Test toggling an entity's deferred status multiple times."""
        tracker = DeferredLinkingTracker()
        tracker.track(entity_name="entity1", deferred=True)
        assert "entity1" in tracker.deferred

        tracker.track(entity_name="entity1", deferred=False)
        assert "entity1" not in tracker.deferred

        tracker.track(entity_name="entity1", deferred=True)
        assert "entity1" in tracker.deferred

        tracker.track(entity_name="entity1", deferred=False)
        assert "entity1" not in tracker.deferred

    def test_track_with_various_entity_names(self) -> None:
        """Test tracking entities with various naming patterns."""
        tracker = DeferredLinkingTracker()
        entities = ["sample", "site_visit", "sample_data_123", "entity_with_long_name"]
        for entity in entities:
            tracker.track(entity_name=entity, deferred=True)
        assert tracker.deferred == set(entities)

    def test_track_preserves_other_deferred_entities(self) -> None:
        """Test that tracking one entity preserves others in the deferred set."""
        tracker = DeferredLinkingTracker()
        tracker.track(entity_name="entity1", deferred=True)
        tracker.track(entity_name="entity2", deferred=True)
        tracker.track(entity_name="entity3", deferred=False)
        assert tracker.deferred == {"entity1", "entity2"}

        # Now toggle entity3 to deferred
        tracker.track(entity_name="entity3", deferred=True)
        assert tracker.deferred == {"entity1", "entity2", "entity3"}

        # Remove entity1
        tracker.track(entity_name="entity1", deferred=False)
        assert tracker.deferred == {"entity2", "entity3"}

    def test_track_named_parameters(self) -> None:
        """Test that track method uses named parameters correctly."""
        tracker = DeferredLinkingTracker()
        # Test with named parameters (as they are required)
        tracker.track(entity_name="entity1", deferred=True)
        assert "entity1" in tracker.deferred
        tracker.track(entity_name="entity1", deferred=False)
        assert "entity1" not in tracker.deferred

    def test_deferred_set_is_mutable(self) -> None:
        """Test that deferred set can be directly manipulated (as it's a public attribute)."""
        tracker = DeferredLinkingTracker()
        tracker.track(entity_name="entity1", deferred=True)
        tracker.deferred.add("entity2")
        assert tracker.deferred == {"entity1", "entity2"}

        tracker.deferred.remove("entity1")
        assert tracker.deferred == {"entity2"}

    def test_track_with_empty_entity_name(self) -> None:
        """Test tracking with empty entity name (edge case)."""
        tracker = DeferredLinkingTracker()
        tracker.track(entity_name="", deferred=True)
        assert "" in tracker.deferred

    def test_track_with_special_characters_in_entity_name(self) -> None:
        """Test tracking entities with special characters in names."""
        tracker = DeferredLinkingTracker()
        special_entities = ["entity-1", "entity.2", "entity_3", "entity$4", "entity@5"]
        for entity in special_entities:
            tracker.track(entity_name=entity, deferred=True)
        assert tracker.deferred == set(special_entities)

    def test_independent_tracker_instances(self) -> None:
        """Test that independent DeferredLinkingTracker instances don't share state."""
        tracker1 = DeferredLinkingTracker()
        tracker2 = DeferredLinkingTracker()

        tracker1.track(entity_name="entity1", deferred=True)
        tracker2.track(entity_name="entity2", deferred=True)

        assert tracker1.deferred == {"entity1"}
        assert tracker2.deferred == {"entity2"}
        assert tracker1.deferred != tracker2.deferred

    def test_track_with_boolean_values(self) -> None:
        """Test that track method correctly interprets boolean values."""
        tracker = DeferredLinkingTracker()

        # Test with explicit True
        tracker.track(entity_name="entity1", deferred=True)
        assert "entity1" in tracker.deferred

        # Test with explicit False
        tracker.track(entity_name="entity2", deferred=False)
        assert "entity2" not in tracker.deferred

        # Test with boolean expressions
        tracker.track(entity_name="entity3", deferred=1 > 0)  # True
        assert "entity3" in tracker.deferred

        tracker.track(entity_name="entity4", deferred=1 < 0)  # False
        assert "entity4" not in tracker.deferred

    def test_clear_all_deferred_entities(self) -> None:
        """Test clearing all deferred entities."""
        tracker = DeferredLinkingTracker()
        tracker.track(entity_name="entity1", deferred=True)
        tracker.track(entity_name="entity2", deferred=True)
        tracker.track(entity_name="entity3", deferred=True)
        assert len(tracker.deferred) == 3

        tracker.deferred.clear()
        assert len(tracker.deferred) == 0
        assert tracker.deferred == set()

    def test_track_large_number_of_entities(self) -> None:
        """Test tracking a large number of entities."""
        tracker = DeferredLinkingTracker()
        num_entities = 1000
        for i in range(num_entities):
            tracker.track(entity_name=f"entity_{i}", deferred=True)

        assert len(tracker.deferred) == num_entities
        assert f"entity_0" in tracker.deferred
        assert f"entity_{num_entities - 1}" in tracker.deferred

    def test_is_entity_deferred_via_membership(self) -> None:
        """Test checking if an entity is deferred using membership test."""
        tracker = DeferredLinkingTracker()
        tracker.track(entity_name="entity1", deferred=True)
        tracker.track(entity_name="entity2", deferred=False)

        # Using membership operator
        assert "entity1" in tracker.deferred
        assert "entity2" not in tracker.deferred
        assert "entity3" not in tracker.deferred

    def test_get_deferred_entities_count(self) -> None:
        """Test getting the count of deferred entities."""
        tracker = DeferredLinkingTracker()
        assert len(tracker.deferred) == 0

        tracker.track(entity_name="entity1", deferred=True)
        assert len(tracker.deferred) == 1

        tracker.track(entity_name="entity2", deferred=True)
        assert len(tracker.deferred) == 2

        tracker.track(entity_name="entity1", deferred=False)
        assert len(tracker.deferred) == 1
