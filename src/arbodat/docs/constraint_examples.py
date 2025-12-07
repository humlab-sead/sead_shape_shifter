"""
Example configuration showing foreign key constraints usage.

This demonstrates how to add constraints to foreign key relationships
to enforce data integrity during the normalization process.
"""

# Example 1: Basic many-to-one with strict matching
EXAMPLE_SAMPLE_TO_DATASET = """
sample:
  surrogate_id: sample_id
  keys: ["sample_name", "dataset_name"]
  columns: ["sample_name", "dataset_name", "depth", "thickness"]
  foreign_keys:
    - entity: dataset
      local_keys: ["dataset_name"]
      remote_keys: ["dataset_name"]
      constraints:
        # Each sample belongs to exactly one dataset
        cardinality: many_to_one
        # All samples must have a valid dataset
        require_all_left_matched: true
        # No null dataset names allowed
        allow_null_keys: false
"""

# Example 2: Optional reference with quality monitoring
EXAMPLE_SITE_TO_LOCATION = """
site:
  surrogate_id: site_id
  keys: ["site_name"]
  columns: ["site_name", "location_name", "latitude", "longitude"]
  foreign_keys:
    - entity: location
      local_keys: ["location_name"]
      remote_keys: ["location_name"]
      how: left  # Optional reference
      constraints:
        cardinality: many_to_one
        # At least 90% of sites should have a location
        min_match_rate: 0.90
        # Never multiply rows
        max_row_increase_pct: 0
        # Location can be null
        allow_null_keys: true
"""

# Example 3: One-to-one strict relationship
EXAMPLE_EMPLOYEE_TO_DETAILS = """
employee:
  surrogate_id: employee_id
  keys: ["employee_code"]
  columns: ["employee_code", "name", "department"]
  foreign_keys:
    - entity: employee_details
      local_keys: ["employee_code"]
      remote_keys: ["employee_code"]
      constraints:
        # Exactly one detail record per employee
        cardinality: one_to_one
        # Every employee must have details
        require_all_left_matched: true
        # Every detail record must be used
        require_all_right_matched: true
        # Both sides must be unique
        require_unique_left: true
        require_unique_right: true
        # No nulls allowed
        allow_null_keys: false
"""

# Example 4: Controlled one-to-many expansion
EXAMPLE_ORDER_TO_ITEMS = """
order:
  surrogate_id: order_id
  keys: ["order_number"]
  columns: ["order_number", "order_date", "customer"]
  foreign_keys:
    - entity: order_item
      local_keys: ["order_number"]
      remote_keys: ["order_number"]
      constraints:
        cardinality: one_to_many
        # Limit expansion (assume max 20 items per order on average)
        max_row_increase_pct: 2000  # 20x expansion
        # All orders must have at least one item
        require_all_left_matched: true
        # Alert if row increase is suspiciously high
        max_row_increase_abs: 50000
"""

# Example 5: Multiple constraints for robust validation
EXAMPLE_COMPLEX = """
feature:
  surrogate_id: feature_id
  keys: ["feature_name", "site_name"]
  columns: ["feature_name", "site_name", "feature_type"]
  foreign_keys:
    # Link to site (required, many-to-one)
    - entity: site
      local_keys: ["site_name"]
      remote_keys: ["site_name"]
      constraints:
        cardinality: many_to_one
        require_all_left_matched: true
        require_unique_right: true
        allow_null_keys: false
        allow_row_decrease: false
    
    # Link to feature type (optional reference data)
    - entity: feature_type
      local_keys: ["feature_type"]
      remote_keys: ["type_name"]
      how: left
      constraints:
        cardinality: many_to_one
        min_match_rate: 0.95  # 95% should have a type
        max_row_increase_pct: 0
        require_unique_right: true
"""

# Example 6: Gradual constraint adoption
EXAMPLE_MIGRATION = """
# Start with basic cardinality
sample:
  foreign_keys:
    - entity: dataset
      local_keys: ["dataset_name"]
      remote_keys: ["dataset_name"]
      constraints:
        cardinality: many_to_one

# Then add match requirements after testing
sample:
  foreign_keys:
    - entity: dataset
      local_keys: ["dataset_name"]
      remote_keys: ["dataset_name"]
      constraints:
        cardinality: many_to_one
        min_match_rate: 0.99  # Monitor match rate

# Finally add strict constraints once data is clean
sample:
  foreign_keys:
    - entity: dataset
      local_keys: ["dataset_name"]
      remote_keys: ["dataset_name"]
      constraints:
        cardinality: many_to_one
        require_all_left_matched: true
        allow_null_keys: false
"""
