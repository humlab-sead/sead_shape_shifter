#!/usr/bin/env bash
# Regression test for the container lifecycle dispatcher and its Make callers.
#
# The test exercises scripts/container.sh (and the Makefile targets that call it)
# against a temporary home whose ~/container is a symlink into a physical release
# directory, exactly as the release manager sets it up after Phase 2.
#
# `podman` and `podman-compose` are replaced with stubs on PATH that record their
# argv and exit 0, so the test never builds an image, starts a container, or
# touches a real deployment. Every assertion is about the command the dispatcher
# constructs, its exit status, its diagnostics, and that it writes nothing into
# the release.
#
# Usage: bash container-host/tests/test_lifecycle.sh
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

# True when the recorded stub log holds a line matching the string.
log_has() { grep -qF -- "$1" "$g_stub_log"; }

reset_log() { : > "$g_stub_log"; }

tree_checksum() {
  find "$g_release" -type f -o -type l | sort | xargs sha256sum 2>/dev/null | sha256sum | cut -d' ' -f1
}

# --- Fixture ---------------------------------------------------------------

g_tmp="$(mktemp -d)"
cleanup() { rm -rf "$g_tmp"; }
trap cleanup EXIT

g_home="$g_tmp/home"
g_release="$g_tmp/opt/shape-shifter/testuser/container-releases/container-v0.1.0/container"
g_stub_bin="$g_tmp/bin"
g_stub_log="$g_tmp/stub-invocations.log"
g_stub_pid="$g_tmp/stub-pid"
g_logs_marker="$g_tmp/logs-started"
g_int_marker="$g_tmp/logs-interrupted"

mkdir -p "$g_home" "$(dirname -- "$g_release")" "$g_stub_bin"
: > "$g_stub_log"

# The release carries the real deployment bundle, so the dispatcher and Makefile
# under test are the ones shipped in the archive.
cp -a "$g_container_dir/." "$g_release/"
ln -sfn "$g_release" "$g_home/container"

# Configuration and runtime data live outside the release, as the loader expects.
mkdir -p "$g_home/config"
printf 'SHAPE_SHIFTER_ENVIRONMENT=production\n' > "$g_home/config/backend.env"
mkdir -p "$g_home/container-data"/{projects,shared,logs,output,backups,tmp,state}

cat > "$g_stub_bin/podman" <<'STUB'
#!/usr/bin/env bash
printf 'podman %s\n' "$*" >> "${STUB_LOG}"
case "$1" in
  --version) echo "podman version 5.7.0"; exit 0 ;;
  image) exit 0 ;;
  ps) echo "shape-shifter  Up 2 minutes  127.0.0.1:8012->8012/tcp"; exit 0 ;;
  inspect) echo "healthy"; exit 0 ;;
esac
exit 0
STUB

cat > "$g_stub_bin/podman-compose" <<'STUB'
#!/usr/bin/env bash
printf 'podman-compose %s\n' "$*" >> "${STUB_LOG}"
case "$1" in
  --version) echo "podman-compose version 1.0.6"; exit 0 ;;
esac
# Record identity so the logs case can prove the dispatcher was replaced.
for arg in "$@"; do
  if [[ "$arg" == "logs" ]]; then
    printf '%s %s\n' "$$" "$PPID" > "${STUB_PID}"
    : > "${STUB_LOGS_MARKER}"
    trap 'echo interrupted > "${STUB_INT_MARKER}"; exit 130' INT
    while :; do sleep 0.2; done
  fi
done
exit 0
STUB

chmod +x "$g_stub_bin/podman" "$g_stub_bin/podman-compose"

cat > "$g_stub_bin/systemctl" <<'STUB'
#!/usr/bin/env bash
printf 'systemctl %s\n' "$*" >> "${STUB_LOG}"
exit 0
STUB

chmod +x "$g_stub_bin/systemctl"

# Every invocation runs with the stubs first on PATH, the temporary home, and the
# marker paths exported. HOME matters because the loader and the Makefile resolve
# configuration and data paths from it.
#
# BASH_ENV and ENV are unset for the child: a shell that sources a startup file
# can re-export PATH and drop the stub directory, which would send the test at
# the real Podman. Unsetting them is a no-op where they are already unset.
dsn() {
  env -u BASH_ENV -u ENV -u XDG_CONFIG_HOME \
    HOME="$g_home" PATH="$g_stub_bin:$PATH" \
    STUB_LOG="$g_stub_log" STUB_PID="$g_stub_pid" \
    STUB_LOGS_MARKER="$g_logs_marker" STUB_INT_MARKER="$g_int_marker" \
    "$@"
}

run_dispatcher() {
  local output status
  set +e
  output="$(cd "$g_home" && dsn bash "$g_release/scripts/container.sh" "$@" 2>&1)"
  status=$?
  set -e
  g_last_output="$output"
  g_last_status="$status"
}

run_make() {
  local output status
  set +e
  output="$(cd "$g_home" && dsn make --no-print-directory -C "$g_home/container" "$@" 2>&1)"
  status=$?
  set -e
  g_last_output="$output"
  g_last_status="$status"
}

# Runs an arbitrary command with the same stubbed environment, used for env
# overrides such as a custom SERVICE_NAME.
run_with_stubs() {
  local output status
  set +e
  output="$(cd "$g_home" && dsn "$@" 2>&1)"
  status=$?
  set -e
  g_last_output="$output"
  g_last_status="$status"
}

before_checksum="$(tree_checksum)"

echo "== up builds the documented compose invocation =="
reset_log
run_dispatcher up
assert_eq "0" "$g_last_status" "up exits 0"
assert_contains "$g_last_output" "Container started" "up reports the container started"
assert_contains "$g_last_output" "http://localhost:8012" "up prints the published port"
if log_has "podman-compose -f podman-compose.yml -p shapeshifter up -d --no-build"; then
  pass "up runs podman-compose up -d --no-build with the compose file and project"
else
  fail "up did not run the documented compose invocation"
  cat "$g_stub_log" >&2
fi

echo
echo "== down stops the container =="
reset_log
run_dispatcher down
assert_eq "0" "$g_last_status" "down exits 0"
assert_contains "$g_last_output" "Container stopped" "down reports the container stopped"
if log_has "podman-compose -f podman-compose.yml -p shapeshifter down"; then
  pass "down runs podman-compose down"
else
  fail "down did not run podman-compose down"
fi

echo
echo "== restart stops then starts =="
reset_log
run_dispatcher restart
assert_eq "0" "$g_last_status" "restart exits 0"
down_line="$(grep -n 'podman-compose .* down$' "$g_stub_log" | head -n1 | cut -d: -f1)"
up_line="$(grep -n 'podman-compose .* up -d --no-build' "$g_stub_log" | head -n1 | cut -d: -f1)"
if [[ -n "$down_line" && -n "$up_line" && "$down_line" -lt "$up_line" ]]; then
  pass "restart runs down before up"
else
  fail "restart did not run down before up"
  cat "$g_stub_log" >&2
fi

echo
echo "== status inspects the container =="
reset_log
run_dispatcher status
assert_eq "0" "$g_last_status" "status exits 0"
if log_has "podman ps -a --filter=name=shape-shifter"; then
  pass "status lists the container by name"
else
  fail "status did not query podman ps for the container name"
fi
if log_has "podman inspect shape-shifter"; then
  pass "status inspects the container for health"
else
  fail "status did not inspect the container"
fi

echo
echo "== logs follows the container log in place =="
reset_log
rm -f "$g_stub_pid" "$g_logs_marker" "$g_int_marker"
# The command is backgrounded directly rather than through the dsn function, so
# its PID is the dispatcher's own PID and the exec can be measured. Job control
# is enabled so the background process keeps SIGINT deliverable; without it, a
# non-interactive shell makes background children ignore SIGINT, and the trap in
# the stub could never fire.
set +e
set -m
env -u BASH_ENV -u ENV \
  HOME="$g_home" PATH="$g_stub_bin:$PATH" \
  STUB_LOG="$g_stub_log" STUB_PID="$g_stub_pid" \
  STUB_LOGS_MARKER="$g_logs_marker" STUB_INT_MARKER="$g_int_marker" \
  bash "$g_release/scripts/container.sh" logs >"$g_tmp/logs.out" 2>&1 &
dispatcher_pid=$!
set +m
set -e
for _ in $(seq 1 50); do
  [[ -f "$g_logs_marker" ]] && break
  sleep 0.1
done
if [[ -f "$g_logs_marker" ]]; then
  pass "logs reaches the compose logs -f invocation"
else
  fail "logs never invoked compose logs"
fi
if [[ -f "$g_stub_log" && -s "$g_stub_log" ]]; then
  assert_eq "podman-compose -f podman-compose.yml -p shapeshifter logs -f" "$(tail -n1 "$g_stub_log")" "logs passes logs -f to compose"
fi

if [[ -f "$g_stub_pid" ]]; then
  read -r stub_pid stub_ppid < "$g_stub_pid"
  assert_eq "$dispatcher_pid" "$stub_pid" "logs replaces the dispatcher process (exec), leaving its PID unchanged"
  if [[ "$stub_ppid" == "$dispatcher_pid" ]]; then
    fail "the log follower is a child of the dispatcher, so exec did not replace it"
  else
    pass "the log follower is the dispatcher process itself, not a child"
  fi
else
  fail "the compose stub did not record its identity"
fi

# A SIGINT sent to the dispatcher PID reaches the follower only when the follower
# is that process, which is what makes log following interruptible.
if [[ -f "$g_stub_pid" ]]; then
  kill -INT "$dispatcher_pid" 2>/dev/null || true
  for _ in $(seq 1 50); do
    [[ -f "$g_int_marker" ]] && break
    sleep 0.1
  done
  if [[ -f "$g_int_marker" ]]; then
    pass "a SIGINT on the dispatcher PID interrupts log following"
  else
    fail "SIGINT did not reach the log follower, so following is not interruptible"
  fi
fi
# Never leave the follower running, even if an assertion above failed.
kill -TERM "$dispatcher_pid" 2>/dev/null || true
for _ in $(seq 1 30); do
  kill -0 "$dispatcher_pid" 2>/dev/null || break
  sleep 0.1
done
kill -KILL "$dispatcher_pid" 2>/dev/null || true
wait "$dispatcher_pid" 2>/dev/null || true

echo
echo "== empty and unknown actions fail clearly =="
reset_log
run_dispatcher ""
assert_eq "64" "$g_last_status" "an empty action exits 64"
assert_contains "$g_last_output" "Usage:" "an empty action prints usage"
assert_eq "" "$(cat "$g_stub_log")" "an empty action runs no compose command"

reset_log
run_dispatcher bogus
assert_eq "64" "$g_last_status" "an unknown action exits 64"
assert_contains "$g_last_output" "unknown action 'bogus'" "an unknown action names the offending action"
assert_contains "$g_last_output" "Usage:" "an unknown action prints usage"
assert_eq "" "$(cat "$g_stub_log")" "an unknown action runs no compose command"

echo
echo "== help succeeds without touching the deployment =="
reset_log
run_dispatcher help
assert_eq "0" "$g_last_status" "help exits 0"
assert_contains "$g_last_output" "Actions:" "help lists the available actions"
assert_eq "" "$(cat "$g_stub_log")" "help runs no compose command"

echo
echo "== a missing data directory fails with the named setting =="
mv "$g_home/container-data" "$g_home/container-data.moved"
reset_log
run_dispatcher up
assert_eq "1" "$g_last_status" "up fails when the data directory is missing"
assert_contains "$g_last_output" "data directory does not exist" "the failure names the missing data directory"
assert_contains "$g_last_output" "CONFIG_DIR=" "the failure prints the resolved CONFIG_DIR"
assert_contains "$g_last_output" "under your home directory" "the failure explains how a relative DATA_DIR resolves"
mv "$g_home/container-data.moved" "$g_home/container-data"

echo
echo "== Make targets operate through the symlinked selection =="
reset_log
run_make status
assert_eq "0" "$g_last_status" "make status exits 0"
if log_has "podman ps -a --filter=name=shape-shifter"; then
  pass "make status runs the dispatcher status action through ~/container"
else
  fail "make status did not reach the dispatcher"
  cat "$g_stub_log" >&2
fi

reset_log
run_make help
assert_eq "0" "$g_last_status" "make help exits 0"
assert_contains "$g_last_output" "make up" "make help lists the lifecycle targets"

reset_log
run_make down
assert_eq "0" "$g_last_status" "make down exits 0"
if log_has "podman-compose -f podman-compose.yml -p shapeshifter down"; then
  pass "make down runs the dispatcher down action"
else
  fail "make down did not reach the dispatcher"
fi

mv "$g_home/container-data" "$g_home/container-data.moved"
reset_log
run_make up
if [[ "$g_last_status" -ne 0 ]]; then
  pass "make up fails when the data directory is missing"
else
  fail "make up succeeded with a missing data directory"
fi
assert_contains "$g_last_output" "data directory does not exist" "make up surfaces the dispatcher diagnostic"
mv "$g_home/container-data.moved" "$g_home/container-data"

echo
echo "== service actions dispatch through the single entry point =="
reset_log
run_dispatcher service status
assert_eq "0" "$g_last_status" "service status exits 0"
if log_has "systemctl --user status shape-shifter"; then
  pass "service status runs systemctl --user status"
else
  fail "service status did not run the systemd status command"
  cat "$g_stub_log" >&2
fi
if grep -q '^podman \|^podman-compose ' "$g_stub_log"; then
  fail "service status invoked Podman"
  cat "$g_stub_log" >&2
else
  pass "service status does not invoke Podman"
fi

reset_log
rm -rf "$g_home/.config/systemd"
run_dispatcher service install
assert_eq "0" "$g_last_status" "service install exits 0"
if log_has "systemctl --user daemon-reload"; then
  pass "service install reloads systemd"
else
  fail "service install did not reload systemd"
  cat "$g_stub_log" >&2
fi
if [[ -f "$g_home/.config/systemd/user/shape-shifter.service" ]]; then
  pass "service install copies the unit into the user unit directory"
else
  fail "service install did not install the unit file"
fi
if grep -q '^podman \|^podman-compose ' "$g_stub_log"; then
  fail "service install invoked Podman"
  cat "$g_stub_log" >&2
else
  pass "service install does not invoke Podman"
fi

reset_log
run_with_stubs env SERVICE_NAME=shape-shifter-dev bash "$g_release/scripts/container.sh" service status
assert_eq "0" "$g_last_status" "service status with a custom unit name exits 0"
if log_has "systemctl --user status shape-shifter-dev"; then
  pass "SERVICE_NAME selects the unit to control"
else
  fail "the custom SERVICE_NAME was not used"
fi

reset_log
run_dispatcher service
assert_eq "64" "$g_last_status" "a missing service action exits 64"
assert_contains "$g_last_output" "Usage:" "a missing service action prints usage"
assert_eq "" "$(cat "$g_stub_log")" "a missing service action runs no systemd command"

reset_log
run_dispatcher service bogus
assert_eq "64" "$g_last_status" "an unknown service action exits 64"
assert_contains "$g_last_output" "unknown service action 'bogus'" "an unknown service action names it"
assert_eq "" "$(cat "$g_stub_log")" "an unknown service action runs no systemd command"

reset_log
run_make service-status
assert_eq "0" "$g_last_status" "make service-status exits 0"
if log_has "systemctl --user status shape-shifter"; then
  pass "make service-status dispatches through container.sh"
else
  fail "make service-status did not reach the systemd dispatcher"
  cat "$g_stub_log" >&2
fi

echo
echo "== lifecycle commands write nothing into the release =="
assert_eq "$before_checksum" "$(tree_checksum)" "the release tree is unchanged by every lifecycle command"

echo
if ((g_failures > 0)); then
  printf '%d lifecycle check(s) failed\n' "$g_failures" >&2
  exit 1
fi
echo "All lifecycle checks passed"
