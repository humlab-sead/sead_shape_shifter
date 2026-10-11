#!/usr/bin/env bash
# Regression test for the home-relative deployment path contract.
#
# The test never touches the repository or a real deployment home. It builds a
# temporary home, a versioned release directory shaped like
# /opt/shape-shifter/<user>/container-releases/<tag>/container, and a ~/container
# symlink pointing into it. It then checks that scripts/load-env.sh and the
# Makefile resolve CONFIG_DIR, DATA_DIR and CONTAINER_DATA_DIR identically from
# the deployment user's home for defaults, relative overrides, absolute
# overrides, and environment-over-file precedence, and that a relative override
# never resolves inside the selected release directory.
#
# Usage: bash container/tests/test_path_resolution.sh
set -euo pipefail

g_test_dir="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
g_container_dir="$(CDPATH='' cd -- "$g_test_dir/.." && pwd)"

g_failures=0
g_last_resolution=""

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  g_failures=$((g_failures + 1))
}

pass() {
  printf 'ok: %s\n' "$*"
}

assert_eq() {
  local expected="$1" actual="$2" label="$3"
  if [[ "$expected" == "$actual" ]]; then
    pass "$label"
  else
    fail "$label: expected '$expected', got '$actual'"
  fi
}

value_of() {
  printf '%s\n' "$g_last_resolution" | sed -n "s/^$1=//p"
}

g_tmp="$(mktemp -d)"
cleanup() { rm -rf "$g_tmp"; }
trap cleanup EXIT

g_home="$g_tmp/home"
g_release="$g_tmp/opt/shape-shifter/testuser/container-releases/container-v0.1.0/container"
mkdir -p "$g_home" "$(dirname -- "$g_release")"

# The release carries the real deployment bundle, so the Makefile and the
# scripts under test are the ones shipped in the archive.
cp -a "$g_container_dir/." "$g_release/"

# ~/container selects the release, exactly as the release manager sets it up.
ln -sfn "$g_release" "$g_home/container"

write_deployment_env() {
  local dir="$1"
  shift
  mkdir -p "$dir"
  printf '%s\n' "$@" > "$dir/deployment.env"
}

# Resolves the three paths through the sourced loader and prints KEY=value lines.
loader_resolve() {
  env HOME="$g_home" "$@" bash -c '
    . "$1/scripts/load-env.sh" || exit 1
    printf "CONFIG_DIR=%s\n" "$CONFIG_DIR"
    printf "DATA_DIR=%s\n" "$DATA_DIR"
    printf "CONTAINER_DATA_DIR=%s\n" "$CONTAINER_DATA_DIR"
  ' _ "$g_home/container" | sort
}

# Resolves the same paths from the Makefile variable database.
make_resolve() {
  env HOME="$g_home" "$@" make --no-print-directory -C "$g_home/container" -p 2>/dev/null \
    | grep -E '^(CONFIG_DIR|DATA_DIR|CONTAINER_DATA_DIR) :=' \
    | sed 's/^\([A-Z_]*\) := /\1=/' \
    | sort
}

# Compares the loader and the Makefile for one set of overrides, then keeps the
# loader result for value assertions.
check_case() {
  local label="$1"
  shift
  local loader_out make_out
  loader_out="$(loader_resolve "$@")"
  make_out="$(make_resolve "$@")"
  if [[ "$loader_out" == "$make_out" ]]; then
    pass "$label: load-env.sh and the Makefile agree"
  else
    fail "$label: load-env.sh and the Makefile disagree"
    printf '  loader:\n%s\n' "$loader_out" >&2
    printf '  make:\n%s\n' "$make_out" >&2
  fi
  g_last_resolution="$loader_out"
}

assert_outside_release() {
  local label="$1" value="$2"
  case "$value" in
    "$g_release"*) fail "$label: resolved inside the selected release ($value)" ;;
    *) pass "$label" ;;
  esac
}

echo "== Defaults (no deployment.env) =="
rm -rf "$g_home/config" "$g_home/relconf" "$g_home/container-data" "$g_home/reldata"
check_case "defaults"
assert_eq "$g_home/config" "$(value_of CONFIG_DIR)" "default CONFIG_DIR is under \$HOME"
assert_eq "$g_home/container-data" "$(value_of DATA_DIR)" "default DATA_DIR is under \$HOME"
assert_eq "$g_home/container-data" "$(value_of CONTAINER_DATA_DIR)" "default CONTAINER_DATA_DIR follows DATA_DIR"

echo
echo "== Relative overrides in deployment.env =="
write_deployment_env "$g_home/config" "DATA_DIR=reldata"
check_case "relative DATA_DIR"
assert_eq "$g_home/reldata" "$(value_of DATA_DIR)" "relative DATA_DIR resolves under \$HOME"
assert_eq "$g_home/reldata" "$(value_of CONTAINER_DATA_DIR)" "CONTAINER_DATA_DIR follows the relative DATA_DIR"
assert_outside_release "relative DATA_DIR stays outside the release" "$(value_of DATA_DIR)"

write_deployment_env "$g_home/config" "DATA_DIR=./reldata"
check_case "leading ./ DATA_DIR"
assert_eq "$g_home/reldata" "$(value_of DATA_DIR)" "DATA_DIR=./reldata resolves under \$HOME"

write_deployment_env "$g_home/config" "DATA_DIR=/srv/shape-data"
check_case "absolute DATA_DIR"
assert_eq "/srv/shape-data" "$(value_of DATA_DIR)" "absolute DATA_DIR is used unchanged"
assert_eq "/srv/shape-data" "$(value_of CONTAINER_DATA_DIR)" "CONTAINER_DATA_DIR follows the absolute DATA_DIR"

write_deployment_env "$g_home/config" "DATA_DIR=reldata" "CONTAINER_DATA_DIR=mountdata"
check_case "explicit relative CONTAINER_DATA_DIR"
assert_eq "$g_home/reldata" "$(value_of DATA_DIR)" "relative DATA_DIR resolves under \$HOME"
assert_eq "$g_home/mountdata" "$(value_of CONTAINER_DATA_DIR)" "explicit relative CONTAINER_DATA_DIR resolves under \$HOME"

echo
echo "== Precedence =="
write_deployment_env "$g_home/config" "DATA_DIR=filedata"
check_case "environment beats deployment.env" DATA_DIR=envdata
assert_eq "$g_home/envdata" "$(value_of DATA_DIR)" "environment DATA_DIR wins over deployment.env"

mkdir -p "$g_home/relconf"
write_deployment_env "$g_home/relconf" "DATA_DIR=relconf-data"
write_deployment_env "$g_home/config" "DATA_DIR=default-conf-data"
check_case "relative CONFIG_DIR override" CONFIG_DIR=relconf
assert_eq "$g_home/relconf" "$(value_of CONFIG_DIR)" "relative CONFIG_DIR resolves under \$HOME"
assert_eq "$g_home/relconf-data" "$(value_of DATA_DIR)" "the overriding CONFIG_DIR selects its own deployment.env"

check_case "absolute CONFIG_DIR override" CONFIG_DIR=/etc/shape-shifter
assert_eq "/etc/shape-shifter" "$(value_of CONFIG_DIR)" "absolute CONFIG_DIR is used unchanged"

mkdir -p "$g_tmp/alt"
printf 'DATA_DIR=envfile-data\n' > "$g_tmp/alt/mydep.env"
check_case "ENV_FILE override" ENV_FILE="$g_tmp/alt/mydep.env"
assert_eq "$g_home/envfile-data" "$(value_of DATA_DIR)" "ENV_FILE is still honoured"

echo
echo "== make info agrees with the loader =="
write_deployment_env "$g_home/config" "DATA_DIR=reldata"
make_info="$(env HOME="$g_home" make --no-print-directory -C "$g_home/container" info 2>/dev/null)"
info_config="$(printf '%s\n' "$make_info" | sed -n 's/^Config dir: *//p')"
info_data="$(printf '%s\n' "$make_info" | sed -n 's/^Data dir: *//p')"
assert_eq "$g_home/config" "$info_config" "make info Config dir is under \$HOME"
assert_eq "$g_home/reldata" "$info_data" "make info Data dir is under \$HOME"

echo
if ((g_failures > 0)); then
  printf '%d path resolution check(s) failed\n' "$g_failures" >&2
  exit 1
fi
echo "All path resolution checks passed"
