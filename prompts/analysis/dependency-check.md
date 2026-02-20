# Dependency Analysis Prompt

Check entity dependency graph for cycles and proper processing order.

## Prompt Template

```
Analyze entity dependencies in {PROJECT_FILE}:

### Dependency Graph Analysis
1. **Build dependency graph** from foreign_keys relationships
   - Map each entity → parent entities (via FK references)
   - Include unnest dependencies (source entities)
   - Include fixed value dependencies

2. **Cycle Detection**
   - Check for circular dependencies (A → B → C → A)
   - Identify self-referencing entities
   - Flag mutual dependencies

3. **Topological Sort**
   - Verify entities can be processed in valid order
   - Identify entities that must be processed first (no dependencies)
   - Calculate dependency depth for each entity

4. **Processing Order Validation**
   - Fixed entities should process before derived entities
   - Parent entities before children
   - Unnest source entities before target entities

### Expected Output

**Dependency Graph**:
```
entity_name:
  depends_on: [parent1, parent2, ...]
  depth: N
  type: fixed|derived
```

**Processing Order** (topologically sorted):
1. {entity1} (depth 0, no dependencies)
2. {entity2} (depth 1, depends on entity1)
3. ...

**Issues Found**:
- ❌ Circular dependencies: A → B → A
- ⚠️ Deep dependency chains (depth > 5)
- ⚠️ Missing parent entities

### Additional Checks
- [ ] All FK parent entities exist in config
- [ ] No orphaned entities (defined but never used)
- [ ] Fixed entities don't depend on derived entities
- [ ] Reconciliation doesn't create hidden dependencies
```

## Example Usage

```
Analyze entity dependencies in projects/dendro/shapeshifter.yml:
[... full analysis ...]
```

## Implementation Reference

See backend implementation:
- `backend/app/utils/graph.py` - Graph algorithms (cycle detection, topological sort)
- `backend/app/services/dependency_service.py` - Entity dependency analysis
- `src/normalizer.py` - ProcessState topological sorting

## Related Documentation
- [ARCHITECTURE.md](../../docs/ARCHITECTURE.md#core-processing-pipeline)
- [AGENTS.md](../../AGENTS.md#architecture-awareness)
