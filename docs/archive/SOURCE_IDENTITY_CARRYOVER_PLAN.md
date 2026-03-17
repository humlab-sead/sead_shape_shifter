# Source Identity in Derived Entities

## Summary

Derived entities should expose the source entity's `public_id` as an ordinary selectable column.

When that column is selected, the extracted values must come from the source entity's `system_id`.

This matches the existing foreign key model:

- column name follows the parent entity's `public_id`
- stored values are the parent entity's `system_id`

## Expected Behavior

Given:

```yaml
site:
  public_id: site_id

site_property:
  type: entity
  source: site
  public_id: site_property_id
  columns: [site_id, property_name, property_value]
```

the derived `site_property.site_id` column should be populated from `site.system_id` during subsetting.

The child entity still keeps its own `system_id`.

Resulting meaning:

- `site_property.system_id` = local identity of the derived row
- `site_property.site_id` = reference to the parent `site` row via `site.system_id`

## Rationale

This is the same semantic model already used by foreign key linking.

The system already treats a parent entity's `public_id` as the child-visible column name while storing the parent's local `system_id` as the value. Derived entities should follow the same rule by default.

This avoids forcing users to model parent references through business keys or explicit `extra_columns` workarounds.

## Scope

This behavior applies to derived entities with a `source` entity.

If the source entity has a `public_id`, that `public_id` should be available in the derived entity's `columns` field and resolved from the source entity's `system_id` during extraction.

This is a default behavior, not an optional feature.

## UI Note

The editor should expose the source entity's `public_id`, not its `system_id`.

That can look surprising at first, because the displayed column name suggests a public identifier while the stored values are actually local `system_id` values. This is already how FK columns behave in the system, so the behavior is conceptually consistent, but the UI should make that relationship clear.

## Constraint

The derived entity's own `public_id` and the source entity's `public_id` cannot serve the same role.

The source entity's `public_id` is a parent reference column in the child.

The derived entity's own `public_id` remains its target-schema identity column.