#!/usr/bin/env bash
# Regression test for the verification-script inventory and its safeguards.
#
# Two properties are enforced, both read-only:
#   1. Every tracked file under container/scripts/verify/ is named in README.md
#      on a table row that also states a disposition (retain, consolidate, move,
#      or retire). This keeps PH3-AC-2 assessable from one place.
#   2. The safeguards on the state-changing and interactive checks are intact:
#      rollback_exercise.sh still asks for confirmation unless --yes is given,
#      and both orchestrators still treat authenticated access and rollback as
#      opt-in flags rather than default behavior.
#
# The test never executes a verification script; it reads files only.
#
# Usage: bash container/tests/test_verify_inventory.sh
set -euo pipefail

g_test_dir="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
g_repo_root="$(CDPATH='' cd -- "$g_test_dir/../.." && pwd)"
g_verify_dir="$g_repo_root/container/scripts/verify"
g_readme="$g_verify_dir/README.md"

g_failures=0
g_checks=0

pass() { g_checks=$((g_checks + 1)); printf 'ok: %s\n' "$*"; }

fail() {
  g_checks=$((g_checks + 1))
  g_failures=$((g_failures + 1))
  printf 'FAIL: %s\n' "$*" >&2
}

assert_file_contains() {
  local file="$1" pattern="$2" label="$3"
  if grep -qF -- "$pattern" "$file"; then
    pass "$label"
  else
    fail "$label: $file does not contain '$pattern'"
  fi
}

echo "== the verification README exists and states dispositions =="
if [[ -f "$g_readme" ]]; then
  pass "container/scripts/verify/README.md exists"
else
  fail "container/scripts/verify/README.md is missing"
  printf '%d verification inventory check(s) failed\n' "$g_failures" >&2
  exit 1
fi

# A disposition row is a table row that names the file and one of the four
# allowed dispositions.
disposition_ok() {
  local basename="$1"
  awk -v name="$basename" '
    /^\|/ && index($0, "`" name "`") > 0 &&
    ($0 ~ /retain/ || $0 ~ /consolidate/ || $0 ~ /move/ || $0 ~ /retire/) { found = 1 }
    END { exit(found ? 0 : 1) }
  ' "$g_readme"
}

echo
echo "== every tracked verification file has a disposition row =="
g_missing=0
while IFS= read -r tracked; do
  basename="$(basename -- "$tracked")"
  if disposition_ok "$basename"; then
    pass "$basename has a disposition row"
  else
    fail "$basename has no README table row stating a disposition"
    g_missing=$((g_missing + 1))
  fi
done < <(cd "$g_repo_root" && git ls-files 'container/scripts/verify/*.sh' 'container/scripts/verify/*.sql')

if ((g_missing == 0)); then
  pass "all tracked verification files are documented with a disposition"
fi

echo
echo "== the inventory covers the files the plan names =="
# These two were undocumented before Phase 3 and are the reason the check exists.
assert_file_contains "$g_readme" '`verify_container_release.sh`' "the active release check is documented"
assert_file_contains "$g_readme" '`verify_readonly_role.sql`' "the SQL input of the grants check is documented"

echo
echo "== rollback_exercise.sh keeps its confirmation safeguard =="
g_rollback="$g_verify_dir/rollback_exercise.sh"
assert_file_contains "$g_rollback" 'read -r -p' "rollback_exercise.sh prompts before changing state"
assert_file_contains "$g_rollback" 'g_confirmed=false' "rollback_exercise.sh defaults to unconfirmed"
assert_file_contains "$g_rollback" '--yes' "rollback_exercise.sh still accepts an explicit --yes"

echo
echo "== the orchestrators keep authenticated access and rollback opt-in =="
g_run="$g_verify_dir/run_deployment_verification.sh"
assert_file_contains "$g_run" 'g_run_authenticated=false' "run_deployment_verification.sh defaults authenticated access to off"
assert_file_contains "$g_run" 'g_run_rollback=false' "run_deployment_verification.sh defaults rollback to off"
assert_file_contains "$g_run" '--authenticated' "run_deployment_verification.sh still accepts --authenticated"
assert_file_contains "$g_run" '--rollback' "run_deployment_verification.sh still accepts --rollback"

g_complete="$g_verify_dir/complete_test_deployment_verification.sh"
assert_file_contains "$g_complete" 'RUN_AUTHENTICATED=false' "complete_test_deployment_verification.sh defaults authenticated access to off"
assert_file_contains "$g_complete" 'RUN_ROLLBACK=false' "complete_test_deployment_verification.sh defaults rollback to off"
assert_file_contains "$g_complete" '--authenticated' "complete_test_deployment_verification.sh still accepts --authenticated"
assert_file_contains "$g_complete" '--rollback' "complete_test_deployment_verification.sh still accepts --rollback"

echo
if ((g_failures > 0)); then
  printf '%d verification inventory check(s) failed\n' "$g_failures" >&2
  exit 1
fi
echo "All verification inventory checks passed"
