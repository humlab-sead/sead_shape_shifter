# Three-Tier Identity System - Summary

## Critical Insight: FK Column Naming

**When child tables join parent tables via foreign keys:**
- FK column **name** = parent's `public_id` (e.g., `site_id`, `location_id`)
- FK column **values** = parent's `system_id` values (1, 2, 3...)

This means:
- `system_id` is **standardized to always be "system_id"** (no configuration needed)
- `public_id` is **required** because it defines FK column names in child tables
- Foreign key resolution pulls parent's `system_id` values into child's `{parent.public_id}` column

## Identity Types

1. **Local Identity** (`system_id`)
   - Always named "system_id" (standardized)
   - Auto-populated with sequence 1, 2, 3...
   - Used for internal foreign key relationships
   - Config field optional (defaults to "system_id")

2. **Source Business Keys** (`keys`)  
   - **Uses existing `keys` field** (no new field needed)
   - Business/natural keys that uniquely identify entities in source data
   - Example: `keys: [bygd, raa_nummer]`
   - Used for duplicate detection and reconciliation

3. **Target System Identity** (`public_id`)
   - **Required field** - specifies FK column name
   - Defines what FK columns are named in child tables
   - Example: `public_id: site_id` means child tables get `site_id` FK column
   - Column values can be assigned for reconciliation with target system

## Configuration Example

```yaml
entities:
  site:
    type: fixed
    # system_id: system_id  # Optional - always defaults to "system_id"
    public_id: site_id      # Required - defines FK column name
    keys: [bygd, raa_nummer]
    columns: [site_name, latitude_dd, longitude_dd]
    
    values:
      - system_id: 1        # Local ID (always this column name)
        bygd: "Bkaker"
        raa_nummer: "274939"
        site_id: 6745       # Target ID (column name = public_id value)
        site_name: "Bkaker"
        latitude_dd: 23.2
        longitude_dd: 61.2

  location:
    type: fixed
    public_id: location_id
    keys: [location_type, location_name]
    columns: [latitude, longitude]
    
    values:
      - system_id: 1
        location_type: "settlement"
        location_name: "Main area"
        location_id: 4521
        latitude: 59.123
        longitude: 18.456

  site_location:
    type: entity
    source: source_data
    public_id: site_location_id
    columns: [bygd, raa_nummer, location_type, location_name]
    
    foreign_keys:
      - entity: site
        local_keys: [bygd, raa_nummer]
        remote_keys: [bygd, raa_nummer]
      - entity: location
        local_keys: [location_type, location_name]
        remote_keys: [location_type, location_name]
```

**After FK resolution**, `site_location` will have:
- `system_id` = 1, 2, 3... (auto-numbered)
- `bygd`, `raa_nummer`, `location_type`, `location_name` (original columns)
- `site_id` (FK column from site.public_id, values from site.system_id)
- `location_id` (FK column from location.public_id, values from location.system_id)

## Benefits of This Design

✅ **Standardized local IDs** - `system_id` always named "system_id" (one less thing to configure)  
✅ **Clear FK naming** - FK columns automatically named after parent's `public_id`  
✅ **Target system alignment** - `public_id` matches target system PK names  
✅ **No new field** - Uses existing `keys` field, reducing complexity  
✅ **Backward compatible** - `keys` already exists in the model  
✅ **Intuitive** - FK column names match what they'll be in target database  

## Implementation Impact

The simplification reduces Phase 1 effort from 9 days to ~8 days because:
- No need to add `domain_keys` field to models
- No need to update Pydantic schemas with new field
- Just need to clarify `keys` purpose in documentation
- UI already has `keys` input - just update labels/tooltips

## Full Implementation Plan

See `docs/IMPLEMENTATION_PLAN_THREE_TIER_IDENTITY.md` for complete details.

**Note**: The implementation plan document still references `domain_keys` in some code examples - these should be mentally replaced with `keys` when implementing.
