#!/usr/bin/env bash
# Regression test for deployment/container/scripts/rename-user.sh.
#
# The test never touches a real deployment, container, authorization store, or
# NGINX file. It builds a temporary home with a stub authorization wrapper that
# keeps roles and grants as tab-separated files, plus fixture configuration
# files, and then checks that:
#   - usage and principal validation reject bad input before changing anything;
#   - --dry-run prints the plan and changes no state or configuration file;
#   - a move grants the new principal before revoking the old one;
#   - roles, grants, group membership, authorization.env, backend.env, and the
#     manifest all end up naming only the new principal;
#   - the database and configuration backups are written;
#   - an unresolved reference to the old principal fails the run.
#
# Usage: bash deployment/container-host/tests/test_rename_user.sh
set -euo pipefail

g_test_dir="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
g_container_dir="$(CDPATH='' cd -- "$g_test_dir/../../../deployment/container" && pwd)"

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

assert_not_contains() {
  local haystack="$1" needle="$2" label="$3"
  if [[ "$haystack" != *"$needle"* ]]; then
    pass "$label"
  else
    fail "$label: output unexpectedly contained '$needle'"
  fi
}

assert_file_contains() {
  local file="$1" needle="$2" label="$3"
  if grep -qF -- "$needle" "$file"; then
    pass "$label"
  else
    fail "$label: $file does not contain '$needle'"
  fi
}

assert_file_lacks() {
  local file="$1" needle="$2" label="$3"
  if grep -qF -- "$needle" "$file"; then
    fail "$label: $file still contains '$needle'"
  else
    pass "$label"
  fi
}

# --- Fixture ---------------------------------------------------------------

g_tmp="$(mktemp -d)"
cleanup() { rm -rf "$g_tmp"; }
trap cleanup EXIT

g_home="$g_tmp/home"
g_root="$g_home/container"
g_scripts="$g_root/scripts"
g_config="$g_home/config"
g_state="$g_tmp/state"

mkdir -p "$g_scripts" "$g_config/groups.d" "$g_state" "$g_home/container-data"
: > "$g_state/roles"
: > "$g_state/grants"
: > "$g_state/resources"
: > "$g_state/calls"

cp "$g_container_dir/scripts/rename-user.sh" "$g_scripts/rename-user.sh"
cp "$g_container_dir/scripts/_load-env.sh" "$g_scripts/_load-env.sh"
cp "$g_container_dir/.env.example" "$g_root/.env.example"

# Roles state: PRINCIPAL<TAB>ROLE
cat > "$g_state/roles" <<'EOF'
alice	admin
alice	project_maintainer
bob	project_maintainer
EOF

# Grants state: SUBJECT<TAB>ROLE<TAB>RESOURCE_ID
cat > "$g_state/grants" <<'EOF'
principal:alice	owner	r1
principal:alice	viewer	r2
group:editors	viewer	r2
EOF

# Resources state: TYPE:LOCATOR<TAB>RESOURCE_ID
cat > "$g_state/resources" <<'EOF'
project:P1	r1
project:P2	r2
EOF

cat > "$g_config/groups.d/shape-shifter.conf" <<'EOF'
# Group membership for the test deployment.
alice    sead-admins;
bob      sead-admins;
EOF

cat > "$g_config/authorization.env" <<'EOF'
AUTH_PASSWORD=unused
AUTH_USERS="alice bob"
ADMIN_AUTH_USER=alice
ADMIN_AUTH_PASSWORD=unused
PROJECT_MAINTAINERS="alice"
PROJECT_CREATOR_AND_OPERATOR="bob"
DEPLOY_USER=test-shape-shifter.sead.se
AUTHORIZATION_ACTOR=test-shape-shifter.sead.se
AUTHORIZATION_MANIFEST=authorization-manifest.yaml
EOF

cat > "$g_config/backend.env" <<'EOF'
SHAPE_SHIFTER_ENVIRONMENT=production
SHAPE_SHIFTER_AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS=["alice","bob"]
EOF

cat > "$g_config/authorization-manifest.yaml" <<'EOF'
administrators:
  - alice
  - bob
resources:
  - resource_type: project
    locator: P1
    grants:
      - principal_id: alice
        role: owner
  - resource_type: shared_data_source
    locator: sead-options
    grants:
      - subject_type: everyone
        subject_id: authenticated
        role: reader
EOF

cat > "$g_scripts/authorization.sh" <<'STUB'
#!/usr/bin/env bash
# Fake authorization CLI. State lives in $STUB_STATE as tab-separated files:
#   roles:     PRINCIPAL<TAB>ROLE
#   grants:    SUBJECT<TAB>ROLE<TAB>RESOURCE_ID
#   resources: TYPE:LOCATOR<TAB>RESOURCE_ID
set -euo pipefail
state="${STUB_STATE:?STUB_STATE is required}"
cmd="${1:-}"
shift || true
roles="$state/roles"
grants="$state/grants"
resources="$state/resources"

arg() {
  local name="$1"
  shift
  while [[ $# -gt 0 ]]; do
    if [[ "$1" == "$name" ]]; then printf '%s' "${2:-}"; return 0; fi
    shift
  done
  return 1
}

resource_id_for() {
  awk -F'\t' -v key="$1" '$1 == key { print $2 }' "$resources"
}

echo "$cmd $*" >> "$state/calls"

case "$cmd" in
list-application-roles)
  awk -F'\t' '{ print $1, $2, "2026-01-01T00:00:00+00:00", "by", "tester" }' "$roles"
  ;;
list-grants)
  awk -F'\t' '{ print $1, $2, $3 }' "$grants"
  ;;
list-resources)
  awk -F'\t' '{ print $1, "active", $2 }' "$resources"
  ;;
grant-application-role)
  principal="$(arg --principal-id "$@")"
  role="$(arg --role "$@")"
  if ! awk -F'\t' -v p="$principal" -v r="$role" '$1 == p && $2 == r { found = 1 } END { exit(found ? 0 : 1) }' "$roles"; then
    printf '%s\t%s\n' "$principal" "$role" >> "$roles"
  fi
  ;;
revoke-application-role)
  principal="$(arg --principal-id "$@")"
  role="$(arg --role "$@")"
  awk -F'\t' -v p="$principal" -v r="$role" '!($1 == p && $2 == r)' "$roles" > "$roles.new"
  mv "$roles.new" "$roles"
  ;;
grant | revoke)
  resource_key="$(arg --resource-type "$@")/$(arg --locator "$@")"
  resource_key="${resource_key/\//:}"
  subject="$(arg --subject-type "$@"):$(arg --subject-id "$@")"
  role="$(arg --role "$@")"
  id="$(resource_id_for "$resource_key")"
  [[ -n "$id" ]] || { echo "stub: unknown resource $resource_key" >&2; exit 1; }
  if [[ "$cmd" == "grant" ]]; then
    if ! awk -F'\t' -v s="$subject" -v r="$role" -v i="$id" '$1 == s && $2 == r && $3 == i { found = 1 } END { exit(found ? 0 : 1) }' "$grants"; then
      printf '%s\t%s\t%s\n' "$subject" "$role" "$id" >> "$grants"
    fi
  else
    awk -F'\t' -v s="$subject" -v r="$role" -v i="$id" '!($1 == s && $2 == r && $3 == i)' "$grants" > "$grants.new"
    mv "$grants.new" "$grants"
  fi
  ;;
backup)
  echo "Authorization backup written to $state/authorization-backup.sqlite3"
  ;;
import-manifest)
  echo "Applied: manifest imported from ${1:-missing}"
  ;;
*)
  echo "stub: unknown command '$cmd'" >&2
  exit 64
  ;;
esac
STUB
chmod +x "$g_scripts/authorization.sh"

run_rename() {
  local output status
  set +e
  output="$(cd "$g_home" && env -u BASH_ENV -u ENV HOME="$g_home" STUB_STATE="$g_state" \
    bash "$g_scripts/rename-user.sh" "$@" 2>&1 </dev/null)"
  status=$?
  set -e
  g_last_output="$output"
  g_last_status="$status"
}

reset_state() {
  cat > "$g_state/roles" <<'EOF'
alice	admin
alice	project_maintainer
bob	project_maintainer
EOF
  cat > "$g_state/grants" <<'EOF'
principal:alice	owner	r1
principal:alice	viewer	r2
group:editors	viewer	r2
EOF
  : > "$g_state/calls"
}

# --- Argument validation ---------------------------------------------------

echo "== argument validation =="

run_rename --help
assert_eq "0" "$g_last_status" "--help exits 0"
assert_contains "$g_last_output" "Usage: rename-user.sh" "--help prints usage"

run_rename alice
assert_eq "2" "$g_last_status" "a missing new principal exits 2"

run_rename alice alice
assert_eq "1" "$g_last_status" "identical principals are rejected"

run_rename 'bad user' bob
assert_eq "1" "$g_last_status" "a principal with a space is rejected"
assert_contains "$g_last_output" "not a valid principal ID" "the rejection names the invalid value"

assert_eq "" "$(tr -d '\n' < "$g_state/calls")" "validation makes no authorization calls"

# --- Dry run ---------------------------------------------------------------

echo "== dry run =="

env_before="$(cat "$g_config/authorization.env")"
manifest_before="$(cat "$g_config/authorization-manifest.yaml")"

run_rename alice 'alice@example.org' --dry-run
assert_eq "0" "$g_last_status" "--dry-run exits 0"
assert_contains "$g_last_output" "[dry-run]" "the plan shows the commands it would run"
assert_contains "$g_last_output" "alice@example.org" "the plan names the new principal"

assert_eq "$env_before" "$(cat "$g_config/authorization.env")" "--dry-run leaves authorization.env unchanged"
assert_eq "$manifest_before" "$(cat "$g_config/authorization-manifest.yaml")" "--dry-run leaves the manifest unchanged"
assert_file_contains "$g_state/roles" "alice	admin" "--dry-run leaves the role store unchanged"
assert_eq "list-application-roles list-grants list-resources " "$(tr -s ' \n' ' ' < "$g_state/calls")" \
  "--dry-run makes only read-only calls"

# --- Apply -----------------------------------------------------------------

echo "== apply =="

run_rename alice 'alice@example.org' --yes
assert_eq "0" "$g_last_status" "the move exits 0"
assert_contains "$g_last_output" "Done. alice -> alice@example.org" "the move reports completion"

assert_file_contains "$g_state/roles" "alice@example.org	admin" "the new principal receives the admin role"
assert_file_contains "$g_state/roles" "alice@example.org	project_maintainer" "the new principal receives project_maintainer"
assert_file_lacks "$g_state/roles" "alice	" "the old principal holds no roles"
assert_file_contains "$g_state/roles" "bob	project_maintainer" "an unrelated principal keeps its roles"

assert_file_contains "$g_state/grants" "principal:alice@example.org	owner	r1" "the new principal receives the owner grant"
assert_file_contains "$g_state/grants" "principal:alice@example.org	viewer	r2" "the new principal receives the viewer grant"
assert_file_lacks "$g_state/grants" "principal:alice	" "the old principal holds no grants"
assert_file_contains "$g_state/grants" "group:editors	viewer	r2" "a group grant is untouched"

grant_line="$(grep -n "grant-application-role --principal-id alice@example.org --role admin" "$g_state/calls" | cut -d: -f1)"
revoke_line="$(grep -n "revoke-application-role --principal-id alice --role admin" "$g_state/calls" | cut -d: -f1)"
if [[ -n "$grant_line" && -n "$revoke_line" && "$grant_line" -lt "$revoke_line" ]]; then
  pass "grants are added before revocations"
else
  fail "grants are added before revocations (grant line '$grant_line', revoke line '$revoke_line')"
fi

assert_file_contains "$g_config/groups.d/shape-shifter.conf" "alice@example.org    sead-admins;" "the group membership line uses the new name"
assert_file_lacks "$g_config/groups.d/shape-shifter.conf" "alice    sead-admins;" "the group membership line drops the old name"
assert_file_contains "$g_config/groups.d/shape-shifter.conf" "bob      sead-admins;" "other group members are untouched"

assert_file_contains "$g_config/authorization.env" 'AUTH_USERS="alice@example.org bob"' "AUTH_USERS is rewritten"
assert_file_contains "$g_config/authorization.env" "ADMIN_AUTH_USER=alice@example.org" "ADMIN_AUTH_USER is rewritten"
assert_file_contains "$g_config/authorization.env" 'PROJECT_MAINTAINERS="alice@example.org"' "PROJECT_MAINTAINERS is rewritten"
assert_file_contains "$g_config/authorization.env" 'PROJECT_CREATOR_AND_OPERATOR="bob"' "an unrelated roster is untouched"

assert_file_contains "$g_config/backend.env" 'SHAPE_SHIFTER_AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS=["alice@example.org","bob"]' \
  "the bootstrap administrator list is rewritten"

assert_file_contains "$g_config/authorization-manifest.yaml" "  - alice@example.org" "the manifest administrator item is rewritten"
assert_file_contains "$g_config/authorization-manifest.yaml" "      - principal_id: alice@example.org" "the manifest grant subject is rewritten"
assert_file_contains "$g_config/authorization-manifest.yaml" "        subject_id: authenticated" "an everyone grant is untouched"
assert_file_contains "$g_config/authorization-manifest.yaml" "    locator: P1" "resource locators are untouched"

assert_contains "$g_last_output" "manifest imported" "the manifest is imported after the rewrite"

backup_dir="$(find "$g_home/container-data/backups" -maxdepth 1 -name 'rename-user-alice-*' -type d | head -n1)"
if [[ -n "$backup_dir" ]]; then
  pass "a configuration backup directory is created"
else
  fail "a configuration backup directory is created"
fi
if [[ -n "$backup_dir" && -f "$backup_dir/authorization.env" && -f "$backup_dir/authorization-manifest.yaml" ]]; then
  pass "the backup holds the edited configuration files"
else
  fail "the backup holds the edited configuration files"
fi

# --- Verification failure --------------------------------------------------

echo "== unresolved references =="

reset_state
printf 'UNHANDLED_ROSTER="alice"\n' >> "$g_config/authorization.env"

run_rename alice 'alice@example.org' --yes
assert_eq "1" "$g_last_status" "an unresolved reference fails the run"
assert_contains "$g_last_output" "still mentions alice" "the warning names the remaining reference"

# --- Result ----------------------------------------------------------------

printf '\n%s checks, %s failure(s)\n' "$g_checks" "$g_failures"
[[ "$g_failures" -eq 0 ]]
