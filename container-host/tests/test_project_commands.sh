#!/usr/bin/env bash
# Regression test for the consolidated project command, container/scripts/project.sh.
#
# The test never touches a real deployment, container, or authorization store. It
# builds a temporary home with a fake project tree under
# ~/container-data/projects and a sibling authorization.sh stub that keeps its
# state in plain text files. It then checks that:
#   - adopt writes one resource plus one owner grant and verifies them;
#   - adopt honours --dry-run and rejects missing or unsupported arguments;
#   - move renames the folder and keeps the resource UUID and its grants;
#   - move honours --dry-run, confirmation, and --yes;
#   - move restores the folder when the authorization change fails;
#   - an unknown or missing action exits without changing anything.
#
# Usage: bash container-host/tests/test_project_commands.sh
set -euo pipefail

g_test_dir="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
g_container_dir="$(CDPATH='' cd -- "$g_test_dir/../../container" && pwd)"

g_failures=0
g_checks=0
g_last_output=""
g_last_status=0

pass() { g_checks=$((g_checks + 1)); printf 'ok: %s\n' "$*"; }

fail() {
  g_checks=$((g_checks + 1))
  g_failures=$((g_failures + 1))
  printf 'FAIL: %s\n' "$*" >&2
}

assert_eq() {
  local expected="$1" actual="$2" label="$3"
  if [[ "$expected" == "$actual" ]]; then
    pass "$label"
  else
    fail "$label: expected '$expected', got '$actual'"
  fi
}

assert_contains() {
  local haystack="$1" needle="$2" label="$3"
  if [[ "$haystack" == *"$needle"* ]]; then
    pass "$label"
  else
    fail "$label: output did not contain '$needle'"
    printf '  output:\n%s\n' "$haystack" >&2
  fi
}

assert_dir() {
  if [[ -d "$1" ]]; then pass "$2"; else fail "$2: missing directory $1"; fi
}

assert_no_dir() {
  if [[ ! -e "$1" ]]; then pass "$2"; else fail "$2: unexpected path $1"; fi
}

# --- Fixture ---------------------------------------------------------------

g_tmp="$(mktemp -d)"
cleanup() { rm -rf "$g_tmp"; }
trap cleanup EXIT

g_home="$g_tmp/home"
g_root="$g_home/container"
g_scripts="$g_root/scripts"
g_state="$g_tmp/state"
g_projects="$g_home/container-data/projects"

mkdir -p "$g_scripts" "$g_state" "$g_projects"
: > "$g_state/resources"
: > "$g_state/grants"

# The command under test is the shipped one, with the shipped loader and the
# bundled deployment template, so the projects directory resolves from ~HOME.
cp "$g_container_dir/scripts/project.sh" "$g_scripts/project.sh"
cp "$g_container_dir/scripts/_load-env.sh" "$g_scripts/_load-env.sh"
cp "$g_container_dir/.env.example" "$g_root/.env.example"

cat > "$g_scripts/authorization.sh" <<'STUB'
#!/usr/bin/env bash
# Fake authorization CLI. State lives in $STUB_STATE as tab-separated files:
#   resources: LOCATOR<TAB>RESOURCE_ID
#   grants:    SUBJECT<TAB>RESOURCE_ID<TAB>ROLE
set -euo pipefail
state="${STUB_STATE:?STUB_STATE is required}"
cmd="${1:-}"
shift || true

case "$cmd" in
import-manifest)
  manifest="${1:-}"
  [[ -f "$manifest" ]] || { echo "import-manifest: no manifest" >&2; exit 1; }
  locator="$(grep -o '"locator": "[^"]*"' "$manifest" | head -n1 | sed 's/.*"locator": "//; s/"$//')"
  subject="$(grep -o '"subject_id": "[^"]*"' "$manifest" | head -n1 | sed 's/.*"subject_id": "//; s/"$//')"
  role="$(grep -o '"role": "[^"]*"' "$manifest" | head -n1 | sed 's/.*"role": "//; s/"$//')"
  id="res-$(( $(wc -l < "$state/resources") + 1 ))"
  printf '%s\t%s\n' "$locator" "$id" >> "$state/resources"
  printf '%s\t%s\t%s\n' "$subject" "$id" "$role" >> "$state/grants"
  echo "imported $locator"
  ;;
list-resources)
  json=false
  [[ "${1:-}" == "--json" ]] && json=true
  while IFS=$'\t' read -r loc id; do
    [[ -n "$loc" ]] || continue
    if [[ "$json" == true ]]; then
      printf '{ "locator": "%s" }\n' "$loc"
    else
      printf 'project:%s active %s\n' "$loc" "$id"
    fi
  done < "$state/resources"
  ;;
list-grants)
  json=false
  [[ "${1:-}" == "--json" ]] && json=true
  while IFS=$'\t' read -r sub id role; do
    [[ -n "$sub" ]] || continue
    if [[ "$json" == true ]]; then
      printf '{ "subject_id": "%s" }\n' "$sub"
    else
      printf 'principal %s %s %s\n' "$sub" "$id" "$role"
    fi
  done < "$state/grants"
  ;;
move-resource)
  from="" to=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
    --from-locator) from="${2:-}"; shift 2 ;;
    --to-locator) to="${2:-}"; shift 2 ;;
    *) shift ;;
    esac
  done
  if [[ "${STUB_MOVE_FAIL:-0}" == "1" ]]; then
    echo "move-resource: simulated failure" >&2
    exit 1
  fi
  tmp="$(mktemp)"
  while IFS=$'\t' read -r loc id; do
    [[ -n "$loc" ]] || continue
    if [[ "$loc" == "$from" ]]; then
      printf '%s\t%s\n' "$to" "$id" >> "$tmp"
    else
      printf '%s\t%s\n' "$loc" "$id" >> "$tmp"
    fi
  done < "$state/resources"
  mv "$tmp" "$state/resources"
  echo "moved $from -> $to"
  ;;
*)
  echo "stub: unknown command '$cmd'" >&2
  exit 64
  ;;
esac
STUB
chmod +x "$g_scripts/authorization.sh"

PROJECT_ENV=()
PROJECT_STDIN=""

run_project() {
  local output status
  local -a env_args=(env -u BASH_ENV -u ENV HOME="$g_home" STUB_STATE="$g_state")
  env_args+=("${PROJECT_ENV[@]}")
  set +e
  if [[ -n "$PROJECT_STDIN" ]]; then
    output="$(cd "$g_home" && "${env_args[@]}" bash "$g_scripts/project.sh" "$@" 2>&1 <<<"$PROJECT_STDIN")"
  else
    output="$(cd "$g_home" && "${env_args[@]}" bash "$g_scripts/project.sh" "$@" 2>&1 </dev/null)"
  fi
  status=$?
  set -e
  g_last_output="$output"
  g_last_status="$status"
}

resource_id_for() {
  awk -F'\t' -v loc="$1" '$1 == loc { print $2 }' "$g_state/resources"
}

resource_count() { grep -c . "$g_state/resources" || true; }

grant_count_for() { awk -F'\t' -v id="$1" '$2 == id' "$g_state/grants" | grep -c . || true; }

make_project_folder() {
  mkdir -p "$g_projects/$1"
  printf 'name: %s\n' "${1##*/}" > "$g_projects/$1/shapeshifter.yml"
}

echo "== adopt creates one resource and one owner grant =="
run_project adopt --project P --owner alice
assert_eq "0" "$g_last_status" "adopt exits 0"
assert_contains "$g_last_output" "alice now owns project 'P'" "adopt reports the new owner"
assert_eq "P" "$(awk -F'\t' '{print $1}' "$g_state/resources")" "adopt records the resource locator"
assert_eq "alice" "$(awk -F'\t' '{print $1}' "$g_state/grants")" "adopt records the owner grant"
assert_eq "owner" "$(awk -F'\t' '{print $3}' "$g_state/grants")" "adopt records the owner role"

echo
echo "== adopt maps a nested path to a colon locator =="
run_project adopt --project arbodat/Q --owner bob
assert_eq "0" "$g_last_status" "adopt with a nested path exits 0"
assert_eq "arbodat:Q" "$(awk -F'\t' 'END {print $1}' "$g_state/resources")" "adopt uses ':' for a nested path"

echo
echo "== adopt --dry-run changes nothing =="
before_resources="$(resource_count)"
before_grants="$(grep -c . "$g_state/grants" || true)"
run_project adopt --project DRY --owner carol --dry-run
assert_eq "0" "$g_last_status" "adopt --dry-run exits 0"
assert_contains "$g_last_output" "Dry run: no changes made" "adopt --dry-run announces the dry run"
assert_eq "$before_resources" "$(resource_count)" "adopt --dry-run adds no resource"
assert_eq "$before_grants" "$(grep -c . "$g_state/grants" || true)" "adopt --dry-run adds no grant"

echo
echo "== adopt rejects missing and unsupported input =="
run_project adopt --project NOOWNER
assert_eq "1" "$g_last_status" "adopt without --owner fails"
assert_contains "$g_last_output" "--owner is required." "adopt without --owner names the missing option"

run_project adopt --owner dave
assert_eq "1" "$g_last_status" "adopt without --project fails"
assert_contains "$g_last_output" "--project is required." "adopt without --project names the missing option"

run_project adopt --project P --owner dave --role editor
assert_eq "1" "$g_last_status" "adopt refuses a non-owner role"
assert_contains "$g_last_output" "Only 'owner' is supported" "adopt explains the role restriction"

echo
echo "== move renames the folder and keeps the resource and grants =="
make_project_folder S
run_project adopt --project S --owner erin
move_id="$(resource_id_for S)"
grants_before="$(grant_count_for "$move_id")"
run_project move --project S --to arbodat/T --yes
assert_eq "0" "$g_last_status" "move exits 0"
assert_no_dir "$g_projects/S" "move removes the source folder"
assert_dir "$g_projects/arbodat/T" "move creates the target folder"
assert_eq "arbodat:T" "$(awk -F'\t' -v id="$move_id" '$2 == id {print $1}' "$g_state/resources")" "move updates the locator and keeps the resource UUID"
assert_eq "$grants_before" "$(grant_count_for "$move_id")" "move keeps the grant count for the resource"

echo
echo "== move --dry-run changes nothing =="
run_project move --project arbodat/T --to arbodat/U --dry-run
assert_eq "0" "$g_last_status" "move --dry-run exits 0"
assert_contains "$g_last_output" "Dry run: no changes made" "move --dry-run announces the dry run"
assert_dir "$g_projects/arbodat/T" "move --dry-run keeps the source folder"
assert_no_dir "$g_projects/arbodat/U" "move --dry-run creates no target folder"

echo
echo "== move confirms before changing anything =="
PROJECT_STDIN="n"
run_project move --project arbodat/T --to arbodat/U
PROJECT_STDIN=""
assert_eq "0" "$g_last_status" "a declined move exits 0"
assert_contains "$g_last_output" "Move cancelled." "a declined move reports the cancellation"
assert_dir "$g_projects/arbodat/T" "a declined move keeps the source folder"
assert_no_dir "$g_projects/arbodat/U" "a declined move creates no target folder"

PROJECT_STDIN="y"
run_project move --project arbodat/T --to arbodat/U
PROJECT_STDIN=""
assert_eq "0" "$g_last_status" "a confirmed move exits 0"
assert_dir "$g_projects/arbodat/U" "a confirmed move creates the target folder"

echo
echo "== move restores the folder when the authorization move fails =="
make_project_folder V
run_project adopt --project V --owner frank
rollback_id="$(resource_id_for V)"
PROJECT_ENV=(STUB_MOVE_FAIL=1)
run_project move --project V --to arbodat/W --yes
PROJECT_ENV=()
assert_eq "1" "$g_last_status" "a failed authorization move exits non-zero"
assert_contains "$g_last_output" "restoring folder" "a failed move reports the rollback"
assert_dir "$g_projects/V" "a failed move restores the source folder"
assert_no_dir "$g_projects/arbodat/W" "a failed move leaves no target folder"
assert_eq "V" "$(awk -F'\t' -v id="$rollback_id" '$2 == id {print $1}' "$g_state/resources")" "a failed move leaves the locator unchanged"

echo
echo "== move rejects invalid input =="
run_project move --project V --to V --yes
assert_eq "1" "$g_last_status" "move refuses identical locators"
assert_contains "$g_last_output" "--project and --to must differ." "move explains the identical-locator refusal"

run_project move --project V --to ../escape --yes
assert_eq "1" "$g_last_status" "move refuses a parent-traversal target"
assert_contains "$g_last_output" "Invalid project name or path" "move explains the invalid path"

run_project move --project missing --to nowhere --yes
assert_eq "1" "$g_last_status" "move fails when the source folder is missing"

echo
echo "== an unknown or missing action changes nothing =="
before_resources="$(resource_count)"
run_project
assert_eq "64" "$g_last_status" "a missing action exits 64"
assert_contains "$g_last_output" "Usage: project.sh" "a missing action prints usage"

run_project bogus
assert_eq "64" "$g_last_status" "an unknown action exits 64"
assert_contains "$g_last_output" "unknown action 'bogus'" "an unknown action names the offending action"
assert_eq "$before_resources" "$(resource_count)" "the rejected actions add no resource"

echo
if ((g_failures > 0)); then
  printf '%d project command check(s) failed\n' "$g_failures" >&2
  exit 1
fi
echo "All project command checks passed"
