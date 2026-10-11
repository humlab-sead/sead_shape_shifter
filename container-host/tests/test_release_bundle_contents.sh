#!/usr/bin/env bash
# Check that the release bundle carries only deployment-user runtime contents and
# that host tooling and release checks live in the source-only container-host/
# tree. Read-only: it inspects the working tree and needs no root or network.
#
# Usage: bash container-host/tests/test_release_bundle_contents.sh
set -euo pipefail

g_test_dir="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
g_repo_root="$(CDPATH='' cd -- "$g_test_dir/../.." && pwd)"
g_container_dir="$g_repo_root/container"
g_host_dir="$g_repo_root/container-host"

g_failures=0
g_checks=0

pass() { g_checks=$((g_checks + 1)); printf 'ok: %s\n' "$*"; }

fail() {
  g_checks=$((g_checks + 1))
  g_failures=$((g_failures + 1))
  printf 'FAIL: %s\n' "$*" >&2
}

assert_file() {
  if [[ -f "$1" ]]; then pass "$2"; else fail "$2: missing file $1"; fi
}

assert_no_path() {
  if [[ ! -e "$1" ]]; then pass "$2"; else fail "$2: unexpected path $1"; fi
}

echo "== the release bundle carries only runtime contents =="
for absent in container/scripts/deploy container/scripts/verify container/tests; do
  assert_no_path "$g_repo_root/$absent" "$absent is not in the bundle"
done

runtime_files=(
  VERSION
  README.md
  DEPLOYMENT.md
  Makefile
  podman-compose.yml
  Containerfile
  .env.example
  .containerignore
  scripts/container.sh
  scripts/load-env.sh
  scripts/env-config.sh
  scripts/setup.sh
  scripts/build.sh
  scripts/backup.sh
  scripts/healthcheck.sh
  scripts/service.sh
  service/shape-shifter.service
  resources/backend.env.example
  resources/.pgpass.example
  resources/authorization.env.example
)
missing=0
for rel in "${runtime_files[@]}"; do
  if [[ ! -f "$g_container_dir/$rel" ]]; then
    fail "container/$rel is missing from the bundle"
    missing=1
  fi
done
if [[ "$missing" -eq 0 ]]; then
  pass "container/ holds all ${#runtime_files[@]} runtime files"
fi

echo
echo "== host tooling lives in the source-only tree =="
host_deploy_files=(
  manage_container_release.sh
  deploy_environment.sh
  install_systemd_service.sh
  install_nginx_reverse_proxy.sh
  bootstrap-authentication-and-authorization.sh
  nginx-shape-shifter.conf.template
  sync-to-deploy
)
for rel in "${host_deploy_files[@]}"; do
  assert_file "$g_host_dir/deploy/$rel" "container-host/deploy/$rel exists"
done
assert_no_path "$g_host_dir/deploy/deploy_all_environments.sh" "deploy_all_environments.sh is removed"
assert_no_path "$g_host_dir/deploy/deploy_single_environment.sh" "deploy_single_environment.sh is renamed"

assert_file "$g_host_dir/verify/verify_container_release.sh" "container-host/verify holds the release checker"
assert_file "$g_host_dir/verify/README.md" "container-host/verify holds its README"
if grep -qF -- 'verify_container_release.sh' "$g_host_dir/verify/README.md"; then
  pass "the verification README names the release checker"
else
  fail "the verification README does not name the release checker"
fi

echo
echo "== the runtime helper a host tool needs is still in the bundle =="
assert_file "$g_container_dir/scripts/load-env.sh" "container/scripts/load-env.sh exists for the NGINX installer"

echo
echo "== no removed tooling hides anywhere in the bundle =="
for removed in verify_container_release.sh deploy_all_environments.sh deploy_single_environment.sh; do
  if find "$g_container_dir" -name "$removed" -print -quit | grep -q .; then
    fail "container/ still contains $removed"
  else
    pass "container/ contains no $removed"
  fi
done

echo
if ((g_failures > 0)); then
  printf '%d release bundle contents check(s) failed\n' "$g_failures" >&2
  exit 1
fi
echo "All release bundle contents checks passed"
