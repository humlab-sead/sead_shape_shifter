# Enhancement Suggestions

- Add "parent" property to entity definitions to enable inheritence
  of properties, eliminating redundancy and improving maintainability.
  If a parent entity is specified, the child entity should inherit all
  properties from the parent unless explicitly overridden.
- Introduce support for string concatenation in "extra_columns" in entity definitions. As a starting point,
  support string concatenation using a syntax like:
  
  ```yaml
  extra_columns:
    full_name: ["first_name", " ", "last_name"]
  ```
