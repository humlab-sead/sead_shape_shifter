
### Resources

**GitHub Copilot Chat - Prompt Engineering:**
- [Asking GitHub Copilot Questions in Your IDE](https://docs.github.com/en/copilot/using-github-copilot/asking-github-copilot-questions-in-your-ide) - Official guide on asking questions in VS Code
- [Prompt Engineering for GitHub Copilot](https://docs.github.com/en/copilot/using-github-copilot/prompt-engineering-for-github-copilot) - Best practices for writing effective prompts
- [VS Code Copilot Chat Documentation](https://code.visualstudio.com/docs/copilot/copilot-chat) - Guide covering slash commands (`/explain`, `/fix`, `/tests`) and context participants (`#file`, `#selection`, `@workspace`)
- [How to write better prompts for GitHub Copilot - The GitHub Blog](https://github.blog/developer-skills/github/how-to-write-better-prompts-for-github-copilot/?ref_product=copilot&ref_type=engagement&ref_style=text)

**Quick Tips:**

- Use `/help` in Copilot Chat to see all available commands
- Use '/code-review' in Copilot chat to do av review of (un-commited?) changes
- Reference files with `#file:path/to/file.ts`
- Use `@workspace` to search across the entire workspace
- Structure prompts: [Context] + [Specific Task] + [Constraints/Format]

---

### Tech debts:

### New features

 - [] TODO: [Frontend/Backend] Edit data source configuration in a dual-mode editor (Form/YAML).
 - [] TODO: Add capability to generate a default reconciliation YAML based on service manifest received from calling services /reconcile endpoint.
 - [] TODO: #68 Add a "finally" step that removes intermediate tables and columns.
 - [] TODO: #69 Add "parent" property to entity definitions.
 - [] TODO: Introduce optional support for types for entity fields
          (e.g., string, integer, date) and support type conversions in extra_columns.
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
```

### FIXME: Buggar

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


### TODO: We need a single source of truth for specifying projekts
We can't duplicate "where p.Projekt in ('19_0013', '19_0014', '22_0005', '18_0025', '22_0015');" wverywhjere

### FIXME: Fix arbodat project (CHANGELOG)

  - A site can have many projects: property "Projekt" is removed from "site.columns" and "site.sql"
  - A site can only have one site type: change "site.sql" to group by "Fustel", then take max "FustelTyp"
  - Assume "Fustel" is unique
  - Pull "Fustel" into "feature"
  - Pull "Fustel" into "sample_group"
  - Property "CoordSys" varies over "Projekt" in "Projekte", FD-check fails
    Fix:
      select distinct p.Fustel, coalesce([EVNr], '') as [EVNr], b.FustelTyp, c.KoordSys, p.rWert, p.hWert, p.[üNN]
      from Projekte as p
      inner join (
        select Projekt, max(FustelTyp) as FustelTyp
        from Befunde group by Projekt
      ) as b on p.Projekt = b.Projekt
      left join(
        select Projekt, max(KoordSys) as KoordSys
        from Projekte
        group by Projekt  
      ) c on c.[Projekt] = p.[Projekt]
      where p.Projekt in ('19_0013', '19_0014', '22_0005', '18_0025', '22_0015');
  - FIXME: FD checks fails for Abodat ["Blake"]



# FIXME: Verify that graphify wiki is automatically updated by hook!

# Copilot Tips

## Reduce Costs

1. Keep sessions short and focused (you can limit #request in settings.json)
1. Minimize referenced context size (open files, selected code, codebase scans)
1. Disable agent-tools you are not using (enable per session even)
1. Use cheap models for simple tasks
1. Auto only selects cheap models!
1. Use code completion!!!


## Increase Code Quality

1. Add carefully curated instructions files (*.instructions.md, AGENTS.md etc)
1. Make instructions discoverable (from README.md, master agent file)
1. Create a change request (proposal)
1. Create phase plan
1. Create iteration plan per phase
1. Keep documententation up-to-date (no stale documents)
1. Add a knowledge graph that agent can use (e.g. `graphify` or `serena`)
1. Use plan mode before youe use agent for larger tasks!!!


##  Copilot CLI

/ide    # connects to vscode (auto when workspaces matches)

https://spark-note.com/en/blog/serena-vs-graphify-search-comparison/
https://medium.com/manomano-tech/project-aegis-benchmarking-ai-agents-and-why-serena-is-our-new-must-have-311673db35dd

# rtk installed

λ brew install rtk
λ rtk init -g --copilot
[rtk] /!\ No hook installed — run `rtk init -g` for automatic token savings
[ok] Added Copilot user-level instructions to /home/roger/.copilot/copilot-instructions.md

GitHub Copilot global integration installed (user-scoped).

  Hook config:    /home/roger/.copilot/hooks/rtk-rewrite.json
  Instructions:   /home/roger/.copilot/copilot-instructions.md

  Applies to all Copilot CLI sessions on this machine.
  Restart your Copilot CLI session to activate.

.codex/config.toml
[shell_environment_policy]
inherit = "all"

[shell_environment_policy.set]
PATH = "/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:/home/roger/.local/bin:/home/roger/.pyenv/shims:/home/roger/.pyenv/bin:/home/roger/source/sead_shape_shifter/.venv/bin:/usr/local/bin:/usr/bin:/bin"

[projects."/home/roger/source/sead_shape_shifter"]
trust_level = "trusted"

[projects."/home/roger/source/sead_query_api"]
trust_level = "trusted"


openai_base_url = "http://localhost:8787/v1"

## Add PATH for non-interactive shells (needed for vscode Codex extension, remote SSH)
.pam.environment

PATH OVERRIDE=/home/roger/source/sead_shape_shifter/.venv/bin:/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:/home/roger/.dotnet/tools:/home/roger/.local/bin:/home/roger/bin/go/bin:/home/roger/.npm/lib/bin:/home/roger/bin:/usr/local/bin:/usr/bin:/bin


# TODO: BUGCEP_IMPORT_MIGRATION


We need to create a handoff for the next phase of this migration of BugsCEP importer. Please suggest what this handoff should include.

1. Create add a new proposal named BUGCEP_IMPORT_MIGRATION.md to new folder sead_shape_shifter/docs/proposals/BUGCEP_IMPORT_MIGRATION/ and using instructions in sead_shape_shifter/.github/instructions/proposal-writing-guide.instructions.md. The goal of the proposal is to create a new BugsCEP importer using the reconciliation policy YAML files.   
2. Craete a machine-readable document that an AI coding agent can use to more easy get up-to-speed in this migration work.


# TODO: test Github Copilot /code-review chat command

Rules in semantic_rules.yml that are not implemented in a specification:
entity.xlsx.requires_filename
entity.openpyxl.requires_filename
entity.csv.requires_filename
entity.tsv.requires_filename
entity.duckdb.requires_query
entity.duckdb.requires_depends_on
entity.xlsx.filename_must_exist
entity.openpyxl.filename_must_exist
entity.csv.filename_must_exist
