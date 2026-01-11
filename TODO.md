
# Finally cleanup step

### Bugs

 - [] FIXME: Right preview pane doesn't clear values between entities
 - [] FIXME: Active route only highlighted in navigation breadcrumbs for "Projects"
 - [] FIXME: #114 Database and port number fields in data source view are empty
 - [] FIXME: #115 Titles in data source view are displayed inconsistently
 - [] FIXME: #116 Intermittent navigation error when opening project
 - [] FIXME: #117 pening a project always creates a new session
 - [] FIXME: #118 Legend in dependency graph has transparent background.
 - [] FIXME: #119 Entity Editor layout needs improvements
 - [x] FIXME: #120 [Reconciliation] Wrong number of published entities. (Fixed: Added service manifest endpoint and real-time entity count)
 - [x] FIXME: #122 No API call made when doing alternative search in entity reconciliation editor (Fixed: Added targetField parameter)
 - [ ] FIXME: #124 Reconciliation editor complains when "extra_columns" entered in property field
 - [ ] FIXME: #126 Preview fails due to duplicate column names.

### Tech debts:

 - [ ] FIXME: #89 Test Faker or mimesis for data generation in normalization tests

### New features

 - [x] TODO: #121 Add dual-mode editing of entity reconciliation specifications (Completed: YAML/Form tabs with Monaco editor)
 - [] TODO: [Frontend/Backend] Edit data source configuration in a dual-mode editor (Form/YAML).
 - [] TODO: Add additional frontend/backend options (e.g., themes, temp directory, logging level, etc.)
 - [] TODO: Add capability to generate a default reconciliation YAML based on service manifest received from calling services /reconcile endpoint.
 - [] TODO: #68 Add a "finally" step.
 - [] TODO: #66 Introduce a "transformations" section.
 - [] TODO: #69 Add "parent" property to entity definitions.
 - [] TODO: #67 Introduce support for string concatenation in "extra_columns".
 - [] TODO: Add capability to duplicate an existing configuration.
 - [] TODO: #107 Publish frontend files via the backend (FastAPI) server for easier deployment.
 - [] TODO: #98 Enable entity to have multiple reconciliation specifications.
 - [] TODO: #104 Enable download of workflow output from frontend 
 - [] TODO: #108 Add tiny DSL Expression Support in extra_columns
 - [] TODO: Introduce optional support for types for entity fields
          (e.g., string, integer, date) and support type conversions in extra_columns.
 - [x] TODO: Add validation indicators for reconciliation specifications (Completed: Status column with comprehensive column type validation)
 - [] TODO: #123 Columns mapped to properties should be constrained by (all) avaliable columns
 - [] TODO: #125 Add capability to edit full reconciliation YAML
 - [] TODO: #127 Add three-state toggling of L/R panes in entity ediitor.
 - [] TODO: 

 qbj 

# Tiny DSL Expression Support in extra_columns

The "extra_colums" key in an entity's specification provides a way of adding new columns to the resulting DataFrame. The extra_columns value is a dict, where each key is the name of the new column, and the value is the initial value of the new column. The value can be a constant, or anoother column in the source or DataFrame.

It would be useful to support simple expressions in the key's value, e.g. create a fullname column for two first/last name columns. The expressions could translate to Pandas operations, or a python function that transforms the Pandas DataFrame.

Please suggest a YAML-notation for the expression in the extra-columns section for this feature, and how it could be implemented.. Try to make this feature simple but useful.


## Feature Idea

Add expressions under extra_columns using a tiny DSL in YAML, e.g.
```yml
extra_columns:
  fullname: "{row.first_name} + ' ' + {row.last_name}"
  initials: "concat(initials, first_name[:1], last_name[:1])"
```
where {row.X} refers to source/df fields and helpers (like concat or slicing) map to Pandas-friendly Python.

## Implementation path:
 - Interpret the string by formatting it inside a sandboxed helper that injects the current pandas.Series (row) or even the whole DataFrame.
 - For column-wise expressions, leverage df.eval/df.assign after prepping a safe namespace with allowed functions (concat, upper, etc.).
 - For more complex transformations, allow users to specify "lambda df: df['a'] + df['b']" (evaluated via eval with a restricted globals containing only helpers and pd).
- Keep simple by defaulting to expressions evaluated per-row via df.eval or df.assign, with ability to refer to any existing column.

## Next steps:

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

- TODO: #129 Add "ingestion" capability to Shape Shifter workflow (e.g sead_clearinghouse_import) 
  
The Shape Shifter application is designed to facilitate the ingestion and processing of data submissions through a structured workflow. The end result of the workflow is the generation of CSV files or Excel files that represent the data in a format suitable for database ingestion. Currently, this system targets the SEAD relational database schema. The system that imports the data produced by Shape Shifter is the SEAD Clearinghouse Import system (sead_clearinghouse_import) which is added as a project to this workspace.

I want you to analyse the sead_clearinghouse_import system, and suggest a detailed implementation plan how the sead_clearinghouse_import can be added as a final step in the Shape Shifter workflow, so that when the user clicks "Run Workflow", the data is not only processed and output as CSV/Excel files, but also automatically ingested into a SEAD database via the sead_clearinghouse_import system. It can also be an additional button "Ingest to SEAD" if that makes more sense. For simplicity, I would like to add sead_clearinghouse_import as module within the Shape Shifter backend codebase, so that the entire workflow from data ingestion to SEAD database population is handled within a single application in a mono-repo. I still want the Shape Shifter to be moduler, so I would prefer to place sead_clearinghouse_import separately e.g. in an "ingesters" subfolder with a clear interface towards the rest of the system. The functionality needed corresponds to the importer/scripts/import_excel.py script. I can imagine creating a workflow interface for ingesters that can be implemented by sead_clearinghouse_import and any future ingesters that may be added later. I also want to keep the possibility to call the workflow via a CLI script.

I want you to suggest a detailed implementation plan how to achieve this, including any necessary changes to the Shape Shifter backend codebase, any new configuration options that need to be added, and any changes to the frontend that may be required. Please provide a step-by-step plan with clear tasks and milestones.

Please takes this into account:

Ignore any code found in "deprecated" folder
Ignore "importer/configuration" since this is an exact copy of configuration module in Shape Shifter.
Avoid sharing domain model between the ingesters and the Shape Shifters. The main part of the API is the Excel file produced by Shape Shifter. You can ignore CSV output format for now. The API should have a "is_satisfied/validate" method (or endpoint) that the user via UX can call to check if the ingester accepts the Excel file.
The API could be an endpoint exposed by the backend e.g. /ingest/ingester-name" etc with a set of well defined methods. In such a case the backend need to be able to scan the system (e.g. via a Registry) for avaliable ingesters.