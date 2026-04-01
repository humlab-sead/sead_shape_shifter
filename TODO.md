
### Resources

**GitHub Copilot Chat - Prompt Engineering:**
- [Asking GitHub Copilot Questions in Your IDE](https://docs.github.com/en/copilot/using-github-copilot/asking-github-copilot-questions-in-your-ide) - Official guide on asking questions in VS Code
- [Prompt Engineering for GitHub Copilot](https://docs.github.com/en/copilot/using-github-copilot/prompt-engineering-for-github-copilot) - Best practices for writing effective prompts
- [VS Code Copilot Chat Documentation](https://code.visualstudio.com/docs/copilot/copilot-chat) - Guide covering slash commands (`/explain`, `/fix`, `/tests`) and context participants (`#file`, `#selection`, `@workspace`)
- [How to write better prompts for GitHub Copilot - The GitHub Blog](https://github.blog/developer-skills/github/how-to-write-better-prompts-for-github-copilot/?ref_product=copilot&ref_type=engagement&ref_style=text)

**Quick Tips:**

- Use `/help` in Copilot Chat to see all available commands
- Reference files with `#file:path/to/file.ts`
- Use `@workspace` to search across the entire workspace
- Structure prompts: [Context] + [Specific Task] + [Constraints/Format]

---

### Tech debts:

### New features

 - [] TODO: [Frontend/Backend] Edit data source configuration in a dual-mode editor (Form/YAML).
 - [] TODO: Add additional frontend/backend options (e.g., themes, temp directory, logging level, etc.)
 - [] TODO: Add capability to generate a default reconciliation YAML based on service manifest received from calling services /reconcile endpoint.
 - [] TODO: #68 Add a "finally" step that removes intermediate tables and columns.
 - [] TODO: #66 Introduce a "transformations" section with more advance columnar transforms (e.g. toWSG84).
 - [] TODO: #69 Add "parent" property to entity definitions.
 - [] TODO: #108 Add tiny DSL Expression Support in extra_columns
 - [] TODO: Introduce optional support for types for entity fields
          (e.g., string, integer, date) and support type conversions in extra_columns.
 - [] TODO: Improve multiuser support (working on same project)
 - [] TODO: Add more reconciliation entity types, and non-SEAD types (e.g. Geonames, RAÄ-lämningsnummer)
 - [] TODO: Improve UX suggestions when editing entity (awareness of availiable tables, columns etc)
 - [] TODO: Consider limiting "@value:" directive usage to only refer to non-directive keys.
 - [] TODO: Consnider moving specifications/base/get_entity_columns it to TableConfig
            Note that columns avaliable at a specifik FK's linking includes result columns from previous linked FKs.


### TODO: Generate default reconciliation YAML from manifest 
- Calls `/reconcile` endpoint and scaffolds YAML
- Reconciliation system already exists with full implementation

### TODO: #68 Add "finally" cleanup step 
- Drops intermediate tables/columns after processing
- Fits naturally after Store phase

### TODO: #66 Transformations section (toWGS84, etc.) - **Data Quality Feature**
- Coordinate transformations, case normalization, etc.
- Consider using existing libraries (pyproj for coords)

### TODO: #67 String concatenation in extra_columns - **Subset of #108**

### TODO: Add optional types for entity fields - **Type Safety**
- Schema validation + conversions in extra_columns

### TODO: Improve multiuser support - **Complex Feature**
- Requires conflict resolution, locking, real-time sync

### TODO: Add more reconciliation entity types - **Domain-Specific**
- Geonames, RAÄ, etc.

### TODO: Introduce entity type "file" for entities based on files,
Type of files could be csv, excel, json, xml etc, and specified in e.g a "file_type" field.
This would give a more plugin friendly way of adding file based entities.

### TODO: #213 Copy SQL feature from Schema Explorer.
Add a convenience function for copying an SQL select statement to the clipboard for selected entity in schema explorer. This is useful when a user want to create an SQL select in the entity editor based on a table in the specified data source. This could also possibly be extended to a "picker" in the entity editor that allows users to select a table from the data source and automatically generate a select statement for that table.

### TODO: Add a "Test Query" button in the entity editor.
Should open a modal with a Monaco Editor for SQL editing, allowing users to test SQL queries against the data source directly from the entity editor. This would provide a more integrated experience for users working with SQL entities.

### TODO: Edit @value directive
The "@value: dot-path" is directive that expands a key's value by replacing the directive with the value referenced by the dot-path. A dict {"a": "@value: b.c", "b": {"c": "hello"}}, will be resolved to  {"a":  "hello", "b": {"c": "hello"}}. This feature was introduced since e.g. the number of business keys for an entity can be close to 10 keys. The core layer resolves the @value directive using logic fould in #file:utility.py, so project YAML files can contain these directives, and they are expandad when the project is resolved at the API/core boundry.

The current rudimentary syntax of expressions allowed in the @value-directive is stems from the need of simplifying complex compound keys which are resolved to a list of strings. This feature is useful for other use cases as well, though.

THie only operator allowed/implemented is current the "+" operator, which in this syntax is a list append operation, and which always resolves to a list of strings.


```
    1. Simple value:    "@value: path.to.value" 
    2. Prepend:         "['a', 'b'] + @value: path.to.list"
    3. Append:          "@value: path.to.list + ['c', 'd']"
    4. Multiple values: "@value: path1 + @value: path2"
    5. Chaining:        "['a'] + @value: path1 + @value: path2 + ['b']"
```

The UX currently has very limited support for edititing this kind of expression. Some support exists in the Foreign Key editor (but I'm not sure it works). It would be of very high value if we could add at least a basic support for these references for the Columns field, the Business Key field, and the remote/local fields in the Foreign Key editor.

These are some requirements/fingerpointers given that we are editing the values V for (dict-) key K (e.g. editing of "columns" in an entity's YAML).

 - If the user has picked/entered only primitive values, than the V stored in the YAML, unchanged to current implementation, is a list of those values:
     K: ["v1", "v2", "v3", ...]
 - If the user has added a single "@value: dot.path", and noting more, than this string is stored as "K: "@value: dot.path". 

How to deal with more complex expressions involving both primtime values and references is more open for suggestions. One way would be to store them like a list such as:
  K: ['a', 'b'] + @value: path.to.list"
which is equalent to:
  K:
    - 'a'
    - 'b'
    - @value: dot.path"

The system most then resolve the reference so the end result is a flattened list, i.e. use append or add depending what the reference resolved to.

Given the context, we should be able to constrict valid dot.path, e.g. when picking column given a source entity. We also need to add a validation that checks for "dangling" references in the project.

What are your thought? How would an implementation plan look like? 

### FIXME: Store resolved bug

We have a bug related to the recently fixes related to the "@value" directive. All "@value" directives have been resolved in the stored (on disk) file


### FIXME: Entity not persisted ** CAN NOT REPRODUCE! ***

There is new bug related to saving project/entity most likely caused by recent changes. 

1. I open this entity in the Entity Editor:

```
name: abundance_element
type: sql
system_id: system_id
keys:
  - RTyp
columns:
  - Resttyp
  - RTypGrup
  - RTypNr
public_id: abundance_element_id
data_source: arbodat_lookup
query: select [RTyp], [Resttyp], [RTypGrup], [RTypNr] from [RTyp];
foreign_keys:
  - entity: abundance_element_group
    local_keys:
      - RTypGrup
    remote_keys:
      - RTypGrup
depends_on:
  - abundance_element_group
extra_columns:
  element_name: RTyp
  element_description: Resttyp
```

2. Add "@value:entities.abundance.keys" to "keys". Opening YAML tab shows as expected that '@value:entities.abundance.keys' has been added to keys.

```
name: abundance_element
type: sql
system_id: system_id
keys:
  - RTyp
  - '@value:entities.abundance.keys'
columns:
...
```

3. Press SAVE in entity editor
   ==> Status message that entity has been saved successfully
   ==> Button "SAVE CHANGES" in project details view becomes enabled. This is not expected.

4. Verify entity in project detail views YAML tab shows expected values:

```
name: abundance_element
type: sql
system_id: system_id
keys:
  - RTyp
  - '@value:entities.abundance.keys'
columns:
...
```

5. Verify YAML on disk

### TODO: Fixes related to task status

In the graph view, when changing "Color by" from "Entity Type" to "Task Status", only entities with types "Done" or "Ignored" changes color. All other entities remain colored by entity type.

We have four task status values: "todo", "ongoing", "done" and "ignored". The shapeshifter.tasks.yml has keys "required_entities", "completed" and "ignored". The mapping of "todo" and "ongoing" to "required_entities" is unclear.

I think we should use the keys "todo", "ongoing", "done" and "ignored" in shapeshifter.tasks.yml.

The keys should have the following semantics:
 - "todo": initial state, an entity that don't yet exists in the project file: COLOR: yellowish?
 - "ongoing": if entity exists, but "done" or "ignored": COLOR: bluish?
 - "ignored": entity is ignored by task system's definition of done: COLOR: greyish
 - "done": end state, entity is finalized. COLOR: greenish

With this semantics, we need to add placeholder nodes in the graph for "todo" entities.
Possibly, also, we need to simple ways of adding/removing "todo" entities.
Or, possibly, we could allow user to edit "shapeshifter.tasks.yml"

I think these changes (and bugfixes) would increase the usability of the task feature.
What do you think?

### TODO: Consider adding a trash bin when deleteing projects (move instead of delete)
### TODO: Change "optimistic locking" concurrency strategy

When saving project YAML, the system compares client's project's version number to server side version number. If the version
number differs, the the client's updates are discarded. We should instead use a merging strategy as the default 
concurrency resolver. If client's project only differ

### TODO: File location resolution fails if project's folder name differs from metadata.name

if project not in folder "xyz" then this fails with FileLoader raising FileNotFoundError:

```shapeshifter.yml
metadata:
  name: xyz
  ...
entities:
  abc:
    ...
    options:
      filename: abc.xlsx
      location: local
      sheet_name: Sheet1

### Buggar

site_location, och site_property har varningen "returns no data" där motsvarande SQL-frågor ger resultat när de körs i query tester (utan semikolon)  
site_natural_region har samma varning, men där ska ingen data vara så det är ok

Samma tre entities har också samma error "Local foreign key columns not found in data: EVNr, Fustel", vilket jag gissar är relaterat till varningen ovan.

18 entities har varningen (här för abundance): Could not validate entity: ShapeShift failed for abundance: You are trying to merge on str and int64 columns for key 'Fustel'. If you wish to proceed you should use pd.concat

T.ex. abundance har ej Fustel, så det är oklart för mig var felet uppstår.

Har du några idéer tankar kring vad jag kan göra åt dessa fel? Jag kollar också på relative ages/relative dating. I relative dating får jag också  felet när jag försöker göra en preview: InternalServerError

ShapeShift failed for relative_dating: You are trying to merge on str and int64 columns for key 'Fustel'. If you wish to proceed you should use pd.concat
Current phase 9 in target_models/docs/SEAD_V2_IMPLEMENTATION_PLAN.md  is out-of-scope for this proposal. Please streamline these three proposal to have a more focused scoping:
1. proposal docs/proposals/TARGET_MODEL_SPECIFICATION_FORMAT.md shoudld be focused on the target model specification format only, and it's semantics. No design, or implementation detail and no implementation planning details.
2. docs/proposals/TARGET_SCHEMA_AWARE_VALIDATION.md is focusing on the requirements and design of logic that implement's 1ö
3. target_models/docs/SEAD_V2_IMPLEMENTATION_PLAN.md is focused on the development of the SEAD target model specification YAML file only.
