
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

### Bugs

FIXME: Projects are sometimes stored with resolved values.
FIXME: #219 Inline data source configurations raised an error.

### Tech debts:


### New features

 - [] TODO: [Frontend/Backend] Edit data source configuration in a dual-mode editor (Form/YAML).
 - [] TODO: Add additional frontend/backend options (e.g., themes, temp directory, logging level, etc.)
 - [] TODO: Add capability to generate a default reconciliation YAML based on service manifest received from calling services /reconcile endpoint.
 - [] TODO: #68 Add a "finally" step that removes intermediate tables and columns.
 - [] TODO: #66 Introduce a "transformations" section with more advance columnar transforms (e.g. toWSG84).
 - [] TODO: #69 Add "parent" property to entity definitions.
 - [] TODO: #67 Introduce support for string concatenation in "extra_columns".
 - [] TODO: Add capability to duplicate an existing configuration.
 - [] TODO: #108 Add tiny DSL Expression Support in extra_columns
 - [] TODO: Introduce optional support for types for entity fields
          (e.g., string, integer, date) and support type conversions in extra_columns.
 - [] TODO: Improve multiuser support (working on same project)
 - [] TODO: Add more reconciliation entity types, and non-SEAD types (e.g. Geonames, RAÄ-lämningsnummer)
 - [] TODO: NOT WORTH THE EFFORT! Improve user experience (Add new edge/relationship in dependency graph)
 - [] TODO: Improve in-system help (full User Guide, more context sensitive help)
 - [] TODO: Improve UX suggestions when editing entity (awareness of availiable tables, columns etc)
 - [] TODO: Auto-save feature in YAML editing mode (trigger after 2 seconds of inactivity)
 - [] TODO: Consider limiting "@value:" directive usage to only refer to non-directive keys.
 - [] TODO: Consnider moving specifications/base/get_entity_columns it to TableConfig
            Note that columns avaliable at a specifik FK's linking includes result columns from previous linked FKs.

### TODO: #108 Tiny DSL Expression Support in extra_columns DETAILS

The "extra_colums" key in an entity's specification provides a way of adding new columns to the resulting DataFrame. The extra_columns value is a dict, where each key is the name of the new column, and the value is the initial value of the new column. The value can be a constant, or anoother column in the source or DataFrame.

It would be useful to support simple expressions in the key's value, e.g. create a fullname column for two first/last name columns. The expressions could translate to Pandas operations, or a python function that transforms the Pandas DataFrame.

Please suggest a YAML-notation for the expression in the extra-columns section for this feature, and how it could be implemented.. Try to make this feature simple but useful.


Feature Idea

Add expressions under extra_columns using a tiny DSL in YAML, e.g.
```yml
extra_columns:
  fullname: "{row.first_name} + ' ' + {row.last_name}"
  initials: "concat(initials, first_name[:1], last_name[:1])"
```
where {row.X} refers to source/df fields and helpers (like concat or slicing) map to Pandas-friendly Python.

Implementation path:
 - Interpret the string by formatting it inside a sandboxed helper that injects the current pandas.Series (row) or even the whole DataFrame.
 - For column-wise expressions, leverage df.eval/df.assign after prepping a safe namespace with allowed functions (concat, upper, etc.).
 - For more complex transformations, allow users to specify "lambda df: df['a'] + df['b']" (evaluated via eval with a restricted globals containing only helpers and pd).
- Keep simple by defaulting to expressions evaluated per-row via df.eval or df.assign, with ability to refer to any existing column.

Next steps:

1. Decide whether expressions should be evaluated row-by-row (via df.assign(extra=...)) or on the whole DataFrame.
2. Implement parsing/evaluation in the pipeline step where extra_columns currently get applied (likely near the Filter/Link stage).
3. Add tests covering constant, direct column reference, and expression cases.
Expression Detection

Treat every extra_columns value as a string; interpret it as an expression only if it uses a special marker (e.g., starts with expr: or contains {/} tokens). Anything else stays literal.
Recommended rule: if the string matches expr:<python> (e.g., fullname: "expr:df['first_name'] + ' ' + df['last_name']"), run it through the expression evaluator; otherwise just assign the string directly.
This keeps defaults simple (constants work out of the box) while giving a clear hint when evaluation is intended.

Using "expr: python-pandas-row-expression" sounds great. It might be a bit complicated for non-technical users, thoght. Can you suggest a layer/notation above these expressions that exposes the most common e.g. string expressions,a nd that "ompiles" into these pandas expressions? E.g. "= <user-friendly-expression>" by the backend compiles to "expr:<corresponding-python-expression>". In such a case, non-tech user can add simple expressions, but we still have a super-user option.

Expression DSL

Introduce a mini DSL for extra_columns like:

extra_columns:
  fullname: "=concat(first_name, ' ', last_name)"
  initials: "=upper(substr(first_name, 0, 1)) + upper(substr(last_name, 0, 1))"
  source_note: "expr:df['city'] + ' (' + df['code'] + ')'"
Strings starting with = are treated as friendly expressions; strings starting with expr: are raw pandas expressions for power users. Anything else stays constant.

Backend implementation: parse the string when it’s added to the DataFrame. If the value starts with expr:, strip the prefix and run it through df.assign(**{name: eval(expr, safe_globals, {"df": df})}). If it starts with =, feed it to a small compiler that replaces helper names with pandas operations (e.g., concat(a, b) → df['a'].astype(str) + df['b'].astype(str), upper(x) → df['x'].str.upper(), substr(x, start, length) → df['x'].str[start:start+length], ifnull(x, default) etc.), then evaluate the resulting pandas expression in the same safe context. Constants remain untouched.

Keep helper mappings simple so non-technical users can combine columns with string functions; expose more via extending the compiler (e.g., additional helpers for dates or math).


### TODO: #124 Reconciliation editor extra_columns complaint - **Easy Fix**
- The reconciliation editor validation is likely too strict
- Simple fix: Update schema/validation to allow `extra_columns` property
---

### TODO: Generate default reconciliation YAML from manifest - **Smart Feature**
- Calls `/reconcile` endpoint and scaffolds YAML
- Reconciliation system already exists with full implementation

### TODO: #68 Add "finally" cleanup step - **Pipeline Feature**
- Drops intermediate tables/columns after processing
- Fits naturally after Store phase

### TODO: #108 Tiny DSL for extra_columns - **HIGH VALUE but Complex**
- Detailed spec already exists in TODO.md
- Two-tier approach is smart: `=concat(...)` for users, `expr:...` for power users

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

### TODO: Improve UX suggestions when editing entity - **Context-Aware Editor**
- Show available tables/columns from data source
- Could integrate with existing YAML intelligence

Add capability to upload Excel files (.xls, .xlsx) to the data source files directory defined by SHAPE_SHIFTER_DATA_SOURCE_FILES_DIR in the .env file. The uploaded Excel files should be accessible for use in entity configurations within the Shape Shifter application.

### TODO: Introduce entity type "file" for entities based on files,
Type of files could be csv, excel, json, xml etc, and specified in e.g a "file_type" field.
This would give a more plugin friendly way of adding file based entities.

### TODO: #202 Improve FK editing user experience

We can improve the user experience when editing FKs. Currently, thw system offers no assistance when entering local and remote FK. 

I think the system could offer picklists of available local and remote columns. This picklist should include all columns from each entity that is a candidate for the FK relationship, i.e. all columns in columns, keys nd extra_columns, any columns that are generated during normalization (e.g. result of unnesting unnested columns (value id, value vars, id_vars), FK-columns and FK's extra columns etc), system_id, public_id.
The candidate columns can be computed without doing the full normalization, by analyzing the entity definitions and their relationships.

A special case is if the user wants to use a "@value"-directive to point to e.g. another YAML-key in the project. To keep it aimple "@value: entities.**local/remote-entity-name**.keys" could be added to the picklist.
One could also for flexibility allow the user to enter arbitrary YAML-path i.e. a åath that doesn't exist in the picklist.
If a "@value" is used, that can be the only value, and should be a string (not a list). This will be resolved at runtime to the actual column(s).

The "
### TODO: #213 Copy SQL feature from Schema Explorer.
Add a convenience function for copying an SQL select statement to the clipboard for selected entity in schema explorer. This is useful when a user want to create an SQL select in the entity editor based on a table in the specified data source. This could also possibly be extended to a "picker" in the entity editor that allows users to select a table from the data source and automatically generate a select statement for that table.

### TODO: Add a "Test Query" button in the entity editor.
Should open a modal with a Monaco Editor for SQL editing, allowing users to test SQL queries against the data source directly from the entity editor. This would provide a more integrated experience for users working with SQL entities.

### TODO: Save custom graph layout in separate file


### TODO: #221 System fails to find ingesters folder
The system currently fails to find the ingesters folder when running in Docker. Cause: the ingesters folder is not copied to the Docker image, we need to copy the ingesters folder to the Docker image in the Dockerfile, and set environment variables accordingly.
Wouldn't the simple solution be to only have resolved path in core layer? I code think a rule if "location" in "options", "filename" = strip_filenames_path(filename). Or is that do hacky? I could think adding a  simple mechanism for adding type specific mappings. 

### FIXME:


We need to review how **"filename"** entity's "options" dict id handled. This value holds the filename of of the source file for file based entities (csv, xlsx).
Currently, this file can be in two places: in a **global store** or **locally** in the project's folder.
- The location to the global store is defined in GLOBAL_DATA_DIR, which is a path relative to the **application root**.
- The project's local folder is the project root folder + project's path given by it's name (nested folders separated by ":")
Note that the "filename" and "location" information is used by the file based data loaders.

Initially, we encoded the local/public location by prepending "${GLOBAL_DATA_DIR}/" to the value in "filename".
The filename was the supposed to be resolved in the I/O-layer (read/write). This didn't work well, so it was changed to
a more straightforward approach by adding a "location" key next to "filename" indicating storage location
and that can take values "local" or "global". The problem is that the codebase now contains hacks in
several places which mixes the two approaches. We don't need to store "${GLOBAL_DATA_DIR}/" anymore but
that happens still in e.g. _resolve_file_paths_in_entity in backend/app/api/v1/endpoints/entities.py.
The resolve logic also exists in several places. I'm also unsure if the location property 
survives the mapping "API => core => API"

Please review this and propose a more robust handling.  We could e.g. consider centralizing the logic to the file based loader class
but somehow still various parts of the system need's a resolved filename.

