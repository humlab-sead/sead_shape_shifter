#!/usr/bin/env bash
# Shows the status of the local development setup and lists actions the user should take.
#
# Checks the graphify knowledge graph (tool, git hooks, freshness of the code graph, the LLM-based
# results and the wiki), the repository git hooks, branch promotion, the SEAD schema reference and
# leftover files. Read-only: it changes no files, does not fetch from GitHub and does not connect to
# a database, so branch comparisons use the state from the last `git fetch`.
#
# Each line is `ok`, `action` (something to do, with the command) or `note` (good to know).
# Exits 0, or 1 when STATUS_STRICT=1 is set and at least one action is listed.

set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 2

if [[ -t 1 ]]; then
  green=$'\e[32m' yellow=$'\e[33m' blue=$'\e[34m' bold=$'\e[1m' dim=$'\e[2m' reset=$'\e[0m'
else
  green="" yellow="" blue="" bold="" dim="" reset=""
fi

actions=0
notes=0

section() { printf '\n%s%s%s\n' "$bold" "$1" "$reset"; }
ok() { printf '  %sok%s      %s\n' "$green" "$reset" "$1"; }
action() {
  actions=$((actions + 1))
  printf '  %saction%s  %s\n' "$yellow" "$reset" "$1"
  [[ -n "${2:-}" ]] && printf '          %s-> %s%s\n' "$dim" "$2" "$reset"
  return 0
}
note() {
  notes=$((notes + 1))
  printf '  %snote%s    %s\n' "$blue" "$reset" "$1"
  [[ -n "${2:-}" ]] && printf '          %s-> %s%s\n' "$dim" "$2" "$reset"
  return 0
}

# Prints the modification time of a file in seconds since the epoch, or 0 when it does not exist.
mtime() { [[ -e "$1" ]] && stat -c %Y "$1" || echo 0; }
when() { date -d "@$1" '+%Y-%m-%d %H:%M'; }

graph_dir="graphify-out"
graph="$graph_dir/graph.json"
last_commit=$(git log -1 --format=%ct 2>/dev/null || echo 0)

printf '%sShape Shifter status%s %s(read-only; branch data as of the last git fetch)%s\n' "$bold" "$reset" "$dim" "$reset"

# --- graphify ------------------------------------------------------------------------------
section "graphify knowledge graph"
if ! command -v graphify >/dev/null 2>&1; then
  action "graphify is not installed or not on PATH" "make install-graphify"
else
  ok "graphify $(graphify --version 2>/dev/null | awk '{print $NF}') installed"

  missing_hooks=$(graphify hook status 2>/dev/null | awk -F': ' '/^post-(commit|checkout|merge|rewrite):/ && $2 !~ /^installed/ {print $1}' | tr '\n' ' ')
  if [[ -n "$missing_hooks" ]]; then
    action "graphify git hooks missing: ${missing_hooks% }" "make install-hooks"
  else
    ok "graphify git hooks installed (code graph rebuilds after commit, checkout, merge, rebase)"
  fi

  lock="$graph_dir/.rebuild.lock"
  rebuild_running=false
  if [[ -f "$lock" ]] && kill -0 "$(head -1 "$lock" 2>/dev/null)" 2>/dev/null; then
    rebuild_running=true
    note "a background graph rebuild is running"
  fi

  if [[ ! -f "$graph" ]]; then
    action "no graph yet ($graph is missing)" "make update-graphify, then make semantic-graphify GRAPHIFY_CONCURRENCY=1"
  else
    graph_time=$(mtime "$graph")
    if (( graph_time < last_commit )) && ! $rebuild_running; then
      action "code graph ($(when "$graph_time")) is older than the latest commit ($(when "$last_commit"))" "make update-graphify"
    else
      ok "code graph is up to date ($(when "$graph_time"))"
    fi

    log="${HOME}/.cache/graphify-rebuild.log"
    if [[ -f "$log" ]] && (( $(mtime "$log") > graph_time )) && tail -n 40 "$log" | grep -qE 'Traceback|[Ee]rror'; then
      note "the last background rebuild logged an error" "see $log"
    fi

    # The LLM step (make semantic-graphify) is the only one that indexes Markdown documents.
    semantic_time=$(mtime "$graph_dir/.graphify_analysis.json")
    if (( semantic_time == 0 )); then
      action "documents have never been indexed (no LLM-based run yet)" "make semantic-graphify GRAPHIFY_CONCURRENCY=1"
    else
      # Count only files graphify indexes: .graphifyignore uses .gitignore syntax, so git can apply it.
      changed_docs=$(git log --since="@$semantic_time" --format= --name-only -- '*.md' 2>/dev/null | sort -u | while read -r f; do
        [[ -f "$f" ]] && echo "$f"
      done | { git -c core.excludesFile=.graphifyignore check-ignore --no-index --verbose --non-matching --stdin 2>/dev/null || true; } \
        | awk -F'\t' '$1 == "::" {n++} END {print n + 0}')
      if (( changed_docs > 0 )); then
        action "$changed_docs Markdown file(s) committed since the last LLM-based run ($(when "$semantic_time"))" \
          "make semantic-graphify GRAPHIFY_CONCURRENCY=1"
      else
        ok "documents indexed; no Markdown changes since the last LLM-based run ($(when "$semantic_time"))"
      fi
    fi

    unnamed=$(python3 -I - "$graph" "$graph_dir/.graphify_labels.json" 2>/dev/null <<'EOF'
import json, sys
graph = json.load(open(sys.argv[1]))
try:
    labels = json.load(open(sys.argv[2]))
except OSError:
    labels = {}
communities = {node.get("community") for node in graph.get("nodes", [])}
unnamed = sum(1 for c in communities if labels.get(str(c), f"Community {c}") == f"Community {c}")
print(unnamed, len(communities))
EOF
    )
    read -r unnamed total_communities <<< "${unnamed:-}"
    # Every hook rebuild regroups communities and leaves new ones unnamed, so a few unnamed
    # communities are normal; ask for an LLM-based run only when more than a quarter are unnamed.
    if [[ "${unnamed:-}" =~ ^[0-9]+$ && "${total_communities:-}" =~ ^[0-9]+$ ]]; then
      if (( unnamed * 4 > total_communities )); then
        action "$unnamed of $total_communities communities have no name" "make semantic-graphify GRAPHIFY_CONCURRENCY=1"
      elif (( unnamed > 0 )); then
        note "$unnamed of $total_communities communities have no name (normal after code-only rebuilds)"
      else
        ok "all $total_communities communities are named"
      fi
    fi

    wiki="$graph_dir/wiki/index.md"
    if [[ ! -f "$wiki" ]]; then
      action "the wiki has not been built" "make graphify-wiki"
    elif (( $(mtime "$wiki") < graph_time )); then
      action "the wiki ($(when "$(mtime "$wiki")")) is older than the graph" "make graphify-wiki"
    else
      ok "wiki is up to date"
    fi
  fi

  snapshots=$(find "$graph_dir" -maxdepth 1 -type d -name '20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]' 2>/dev/null | wc -l)
  if (( snapshots > 0 )); then
    note "$snapshots dated backup folder(s) in $graph_dir/ ($(du -shc "$graph_dir"/20??-??-?? 2>/dev/null | tail -1 | cut -f1))" \
      "delete them if not needed: rm -r $graph_dir/20??-??-??"
  fi
  if [[ -z "${GRAPHIFY_NO_BACKUP:-}" ]]; then
    note "GRAPHIFY_NO_BACKUP is not set, so graphify writes a dated backup folder on each LLM-based run" \
      "export GRAPHIFY_NO_BACKUP=1 in your shell profile"
  fi
fi

# --- repository setup ----------------------------------------------------------------------
section "Repository setup"
if [[ -x .venv/bin/python ]]; then
  ok "project .venv exists"
else
  action "the project .venv is missing" "make install"
fi
hooks_dir=$(git rev-parse --git-path hooks)
if [[ -f "$hooks_dir/pre-commit" ]] && grep -q "pre-commit" "$hooks_dir/pre-commit"; then
  ok "pre-commit hook installed"
else
  action "pre-commit hook is not installed" "make install-hooks"
fi
dirty=$(git status --porcelain --untracked-files=no | wc -l)
branch=$(git branch --show-current)
if (( dirty > 0 )); then
  note "on ${branch:-detached HEAD} with $dirty uncommitted change(s) to tracked files"
else
  ok "on ${branch:-detached HEAD}, no uncommitted changes to tracked files"
fi

# --- branches and promotion ----------------------------------------------------------------
section "Branches (as of the last git fetch)"
ahead() { git rev-list --count "$1..$2" 2>/dev/null || echo "?"; }
if git rev-parse -q --verify origin/dev >/dev/null && git rev-parse -q --verify origin/staging >/dev/null; then
  dev_ahead=$(ahead origin/staging origin/dev)
  staging_ahead=$(ahead origin/main origin/staging)
  if [[ "$dev_ahead" != "0" ]]; then
    action "dev has $dev_ahead commit(s) not in staging" "scripts/workflow/promote_dev_to_staging.sh prepare"
  else
    ok "staging contains everything in dev"
  fi
  if [[ "$staging_ahead" != "0" ]]; then
    action "staging has $staging_ahead commit(s) not in main" "open a staging -> main promotion PR (see scripts/README.md)"
  else
    ok "main contains everything in staging"
  fi
  for local_branch in dev staging main; do
    if git rev-parse -q --verify "$local_branch" >/dev/null && [[ "$(ahead "$local_branch" "origin/$local_branch")" != "0" ]]; then
      note "local $local_branch is behind origin/$local_branch" "git fetch origin $local_branch:$local_branch (or git pull on that branch)"
    fi
  done
else
  note "origin/dev or origin/staging not found locally" "git fetch origin"
fi

# --- SEAD schema reference -----------------------------------------------------------------
section "SEAD schema reference"
if [[ -f docs/sead/columns.csv ]]; then
  if python3 scripts/target_model/generate_sead_schema_reference.py --check >/dev/null 2>&1; then
    ok "docs/sead/SCHEMA.md matches docs/sead/columns.csv"
  else
    action "docs/sead/SCHEMA.md does not match docs/sead/columns.csv" "make sead-schema-docs"
  fi
  csv_commit=$(git log -1 --format=%ct -- docs/sead/columns.csv 2>/dev/null || echo 0)
  if (( csv_commit > 0 )) && (( $(date +%s) - csv_commit > 30 * 86400 )); then
    note "docs/sead/columns.csv was last committed $(when "$csv_commit"), over 30 days ago" "make sead-schema"
  else
    ok "docs/sead/columns.csv exported within the last 30 days"
  fi
else
  action "docs/sead/columns.csv is missing" "make sead-schema"
fi

# --- leftovers -----------------------------------------------------------------------------
section "Leftover files"
legacy=$(git ls-files --others --exclude-standard -- 'docs/whats-new/PRs/PR_*.txt' | wc -l)
if (( legacy > 0 )); then
  note "$legacy untracked PR description draft(s) in docs/whats-new/PRs/; promotion PRs no longer use them" \
    "delete them unless you are still publishing one: git ls-files --others -- 'docs/whats-new/PRs/PR_*.txt'"
else
  ok "no untracked PR description drafts"
fi

printf '\n%s%d action(s), %d note(s)%s\n' "$bold" "$actions" "$notes" "$reset"
if [[ "${STATUS_STRICT:-}" == "1" ]] && (( actions > 0 )); then
  exit 1
fi
exit 0
