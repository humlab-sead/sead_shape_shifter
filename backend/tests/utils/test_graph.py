"""Tests for graph utility functions."""

import pytest

from backend.app.utils.graph import calculate_depths, find_cycles, topological_sort


class TestFindCycles:
    """Tests for cycle detection."""

    def test_no_cycles(self):
        """Test graph with no cycles."""
        dependency_map = {
            "a": [],
            "b": ["a"],
            "c": ["b"],
        }
        cycles = find_cycles(dependency_map)
        assert cycles == []

    def test_simple_cycle(self):
        """Test graph with simple cycle."""
        dependency_map = {
            "a": ["b"],
            "b": ["a"],
        }
        cycles = find_cycles(dependency_map)
        assert len(cycles) == 1
        assert "a" in cycles[0]
        assert "b" in cycles[0]

    def test_self_cycle(self):
        """Test entity that depends on itself."""
        dependency_map = {
            "a": ["a"],
        }
        cycles = find_cycles(dependency_map)
        assert len(cycles) == 1
        assert cycles[0] == ["a", "a"]

    def test_complex_cycle(self):
        """Test graph with complex cycle."""
        dependency_map = {
            "a": ["b"],
            "b": ["c"],
            "c": ["a"],
            "d": [],
        }
        cycles = find_cycles(dependency_map)
        assert len(cycles) == 1
        # Cycle should contain a, b, c
        cycle_set = set(cycles[0])
        assert "a" in cycle_set
        assert "b" in cycle_set
        assert "c" in cycle_set

    def test_multiple_cycles(self):
        """Test graph with multiple independent cycles."""
        dependency_map = {
            "a": ["b"],
            "b": ["a"],
            "c": ["d"],
            "d": ["c"],
        }
        cycles = find_cycles(dependency_map)
        # Should find both cycles
        assert len(cycles) == 2


class TestTopologicalSort:
    """Tests for topological sorting."""

    def test_linear_dependencies(self):
        """Test simple linear dependency chain."""
        dependency_map = {
            "a": [],
            "b": ["a"],
            "c": ["b"],
        }
        result = topological_sort(dependency_map)
        # Reverse topological order: leaves first (c), then b, then roots (a)
        assert result == ["c", "b", "a"]

    def test_no_dependencies(self):
        """Test graph with no dependencies."""
        dependency_map = {
            "a": [],
            "b": [],
            "c": [],
        }
        result = topological_sort(dependency_map)
        assert len(result) == 3
        assert set(result) == {"a", "b", "c"}

    def test_diamond_dependency(self):
        """Test diamond-shaped dependency."""
        dependency_map = {
            "a": [],
            "b": ["a"],
            "c": ["a"],
            "d": ["b", "c"],
        }
        result = topological_sort(dependency_map)
        # Reverse topological: d is leaf (first), a is root (last)
        assert result[0] == "d"
        assert result[-1] == "a"
        # b and c come between d and a
        assert result.index("d") < result.index("b")
        assert result.index("d") < result.index("c")

    def test_complex_graph(self):
        """Test complex dependency graph."""
        dependency_map = {
            "entity1": [],
            "entity2": ["entity1"],
            "entity3": ["entity1"],
            "entity4": ["entity2", "entity3"],
            "entity5": ["entity4"],
        }
        result = topological_sort(dependency_map)
        # Reverse topological: dependents come BEFORE dependencies
        for entity, deps in dependency_map.items():
            entity_idx = result.index(entity)
            for dep in deps:
                dep_idx = result.index(dep)
                assert entity_idx < dep_idx, f"{entity} (dependent) should come before {dep} (dependency)"


class TestCalculateDepths:
    """Tests for depth calculation."""

    def test_linear_chain(self):
        """Test depth calculation for linear chain."""
        dependency_map = {
            "a": [],
            "b": ["a"],
            "c": ["b"],
        }
        topological_order = ["c", "b", "a"]  # Reverse topological order
        depths = calculate_depths(dependency_map, topological_order)

        # Depth increases toward dependencies (roots)
        assert depths["c"] == 0  # Leaf
        assert depths["b"] == 1  # Mid-level
        assert depths["a"] == 2  # Root (most depended upon)

    def test_no_dependencies(self):
        """Test depth for entities with no dependencies."""
        dependency_map = {
            "a": [],
            "b": [],
            "c": [],
        }
        topological_order = ["a", "b", "c"]
        depths = calculate_depths(dependency_map, topological_order)

        # All should have depth 0
        assert depths["a"] == 0
        assert depths["b"] == 0
        assert depths["c"] == 0

    def test_diamond_dependency(self):
        """Test depth calculation for diamond dependency."""
        dependency_map = {
            "a": [],
            "b": ["a"],
            "c": ["a"],
            "d": ["b", "c"],
        }
        topological_order = ["d", "b", "c", "a"]  # Reverse topological
        depths = calculate_depths(dependency_map, topological_order)

        assert depths["d"] == 0  # Leaf
        assert depths["b"] == 1
        assert depths["c"] == 1
        assert depths["a"] == 2  # Root

    def test_with_cycles_fallback(self):
        """Test depth calculation when cycles exist (uses heuristic)."""
        dependency_map = {
            "a": ["b"],
            "b": ["a"],
            "c": [],
        }
        # When cycles exist, topological_order is None
        depths = calculate_depths(dependency_map, None)

        # Heuristic: nodes with dependencies get depth 1
        assert depths["a"] == 1
        assert depths["b"] == 1
        assert depths["c"] == 0

    def test_complex_graph(self):
        """Test depth calculation for complex graph."""
        dependency_map = {
            "base1": [],
            "base2": [],
            "derived1": ["base1"],
            "derived2": ["base1", "base2"],
            "final": ["derived1", "derived2"],
        }
        topological_order = ["final", "derived2", "derived1", "base2", "base1"]  # Reverse topological
        depths = calculate_depths(dependency_map, topological_order)

        assert depths["final"] == 0  # Leaf
        assert depths["derived1"] == 1
        assert depths["derived2"] == 1
        assert depths["base1"] == 2  # Root (most depended upon)
        assert depths["base2"] == 2  # Root
