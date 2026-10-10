
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

### TODO: [Frontend/Backend] Edit data source configuration in a dual-mode editor (Form/YAML).

### TODO: Add capability to generate a default reconciliation YAML based on service manifest received from calling services /reconcile endpoint.


### TODO: Generate default reconciliation YAML from manifest 
- Calls `/reconcile` endpoint and scaffolds YAML
- Reconciliation system already exists with full implementation

### TODO: #68 Add "finally" cleanup step 
- Drops intermediate tables/columns after processing
- Fits naturally after Store phase

### TODO: Add optional types for entity fields - **Type Safety**
- Schema validation + conversions in extra_columns

### TODO: Add more reconciliation entity types - **Domain-Specific**
- Geonames, RAÄ, etc.

### TODO: Introduce entity type "file" for entities based on files,
Type of files could be csv, excel, json, xml etc, and specified in e.g a "file_type" field.
This would give a more plugin friendly way of adding file based entities.


### TODO: We need a single source of truth for specifying projekts
We can't duplicate "where p.Projekt in ('19_0013', '19_0014', '22_0005', '18_0025', '22_0015');" wverywhjere


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

