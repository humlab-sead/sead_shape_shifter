#!/usr/bin/env bash
# Regression test for container/scripts/deploy/manage_container_release.sh.
#
# The test runs entirely against temporary directories and local fixtures served
# through file:// URLs, so it needs no root access and no network. It covers the
# plan's install, failure, selection, and refusal cases.
#
# Usage: bash container/tests/test_release_manager.sh
set -euo pipefail

g_test_dir="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
g_container_dir="$(CDPATH='' cd -- "$g_test_dir/.." && pwd)"
g_manager="$g_container_dir/scripts/deploy/manage_container_release.sh"

g_failures=0
g_last_output=""

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

assert_file() {
  if [[ -f "$1" ]]; then pass "$2"; else fail "$2: missing file $1"; fi
}

assert_no_path() {
  if [[ ! -e "$1" ]]; then pass "$2"; else fail "$2: unexpected path $1"; fi
}

assert_dir() {
  if [[ -d "$1" ]]; then pass "$2"; else fail "$2: missing directory $1"; fi
}

assert_contains() {
  local haystack="$1" needle="$2" label="$3"
  if [[ "$haystack" == *"$needle"* ]]; then pass "$label"; else
    fail "$label: output did not contain '$needle'"
    printf '  output:\n%s\n' "$haystack" >&2
  fi
}

assert_executable() {
  if [[ -x "$1" ]]; then pass "$2"; else fail "$2: not executable: $1"; fi
}

assert_not_user_writable() {
  local dir="$1" label="$2" hits
  hits="$(find "$dir" -perm /022 -print -quit 2>/dev/null || true)"
  if [[ -n "$hits" ]]; then
    fail "$label: group/other writable: $hits"
  else
    pass "$label"
  fi
}

assert_no_staging() {
  local dir="$1" label="$2" hits
  hits="$(find "$dir" -maxdepth 1 -name '.staging.*' -print -quit 2>/dev/null || true)"
  if [[ -n "$hits" ]]; then
    fail "$label: staging directory was not cleaned up: $hits"
  else
    pass "$label"
  fi
}

# --- Fixtures ---------------------------------------------------------------

g_tmp="$(mktemp -d)"
cleanup() { rm -rf "$g_tmp"; }
trap cleanup EXIT

g_release_root="$g_tmp/release-root"
g_repo="humlab-sead/sead_shape_shifter"
g_asset_base="$g_tmp/assets"
g_api_base="$g_tmp/api"
g_home_root="$g_tmp/homes"
g_asset_url="file://$g_asset_base"
g_api_url="file://$g_api_base"
g_git_url=""

g_home_one="$g_home_root/user-one"
g_home_two="$g_home_root/user-two"
mkdir -p "$g_home_one/config" "$g_home_two/config" "$g_asset_base" "$g_api_base"

printf 'GIT_REF=main\nIMAGE_NAME=shape-shifter:latest\n' > "$g_home_one/config/deployment.env"
printf 'GIT_REF=main\nIMAGE_NAME=shape-shifter:latest\n' > "$g_home_two/config/deployment.env"

env_snapshot() { sha256sum "$1/config/deployment.env" | cut -d' ' -f1; }

releases_dir() { printf '%s/%s/container-releases\n' "$g_release_root" "$1"; }
tag_dir() { printf '%s/%s/container-releases/%s\n' "$g_release_root" "$1" "$2"; }
selector() { printf '%s/%s/container-current\n' "$g_release_root" "$1"; }
previous_file() { printf '%s/%s/container-previous\n' "$g_release_root" "$1"; }
home_link() { printf '%s/%s/container\n' "$g_home_root" "$1"; }

run_mgr() {
  env SHAPE_SHIFTER_RELEASE_TEST_MODE=1 \
    SHAPE_SHIFTER_RELEASE_ROOT="$g_release_root" \
    SHAPE_SHIFTER_RELEASE_REPO="$g_repo" \
    SHAPE_SHIFTER_RELEASE_ASSET_BASE_URL="$g_asset_url" \
    SHAPE_SHIFTER_RELEASE_API_BASE_URL="$g_api_url" \
    SHAPE_SHIFTER_RELEASE_GIT_BASE_URL="$g_git_url" \
    SHAPE_SHIFTER_RELEASE_TEST_HOME_ROOT="$g_home_root" \
    bash "$g_manager" "$@"
}

# Runs the manager with unreachable sources, to prove an operation needs no
# download.
run_mgr_offline() {
  env SHAPE_SHIFTER_RELEASE_TEST_MODE=1 \
    SHAPE_SHIFTER_RELEASE_ROOT="$g_release_root" \
    SHAPE_SHIFTER_RELEASE_REPO="$g_repo" \
    SHAPE_SHIFTER_RELEASE_ASSET_BASE_URL="file://$g_tmp/no-such-assets" \
    SHAPE_SHIFTER_RELEASE_API_BASE_URL="file://$g_tmp/no-such-api" \
    SHAPE_SHIFTER_RELEASE_TEST_HOME_ROOT="$g_home_root" \
    bash "$g_manager" "$@"
}

expect_ok() {
  local label="$1"
  shift
  if g_last_output="$(run_mgr "$@" 2>&1)"; then
    pass "$label"
  else
    fail "$label: command failed"
    printf '  output:\n%s\n' "$g_last_output" >&2
  fi
}

expect_fail() {
  local label="$1"
  shift
  if g_last_output="$(run_mgr "$@" 2>&1)"; then
    fail "$label: expected failure but the command succeeded"
  else
    pass "$label"
  fi
}

expect_fail_offline() {
  local label="$1"
  shift
  if g_last_output="$(run_mgr_offline "$@" 2>&1)"; then
    fail "$label: expected failure but the command succeeded"
  else
    pass "$label"
  fi
}

expect_ok_offline() {
  local label="$1"
  shift
  if g_last_output="$(run_mgr_offline "$@" 2>&1)"; then
    pass "$label"
  else
    fail "$label: command failed without network access"
    printf '  output:\n%s\n' "$g_last_output" >&2
  fi
}

fixture_sha() { printf '%s' "$1" | sha1sum | cut -c1-40; }

# Path of the bare git repository used as a local git remote for a version.
git_fixture_bare() { printf '%s/git-remote-%s.git\n' "$g_tmp" "$1"; }

# Builds a bare git repository whose annotated tag container-vVERSION points at
# a real commit, so the git-based source-commit resolution can be exercised
# without the GitHub API. Prints the peeled commit.
make_git_fixture() {
  local version="$1"
  local tag="container-v$version"
  local work="$g_tmp/git-work-$version"
  local bare
  bare="$(git_fixture_bare "$version")"
  rm -rf "$work" "$bare"
  mkdir -p "$work"
  git -C "$work" init -q
  git -C "$work" config user.email test@example.invalid
  git -C "$work" config user.name "Test Fixture"
  printf 'fixture %s\n' "$version" > "$work/FIXTURE"
  git -C "$work" add FIXTURE
  git -C "$work" commit -q -m "fixture $tag"
  git -C "$work" tag -a "$tag" -m "fixture $tag"
  git -C "$work" init -q --bare "$bare"
  git -C "$work" push -q "$bare" HEAD:refs/heads/main --tags
  git -C "$bare" rev-parse "$tag^{commit}"
}

# Builds a complete release fixture for VERSION and records its API metadata.
make_release() {
  local version="$1"
  local tag="container-v$version"
  local build="$g_tmp/build-$version"
  local out_dir="$g_asset_base/$tag"
  rm -rf "$build"
  mkdir -p "$build/container" "$out_dir"
  cp -a "$g_container_dir/." "$build/container/"
  printf '%s\n' "$version" > "$build/container/VERSION"
  (cd "$build" && tar -czf "$out_dir/$tag.tar.gz" container)
  (cd "$out_dir" && sha256sum "$tag.tar.gz" > "$tag.tar.gz.sha256")
  write_peeled_api "$version"
}

# Writes API fixtures for an annotated tag whose peeled commit is a fixture SHA.
write_peeled_api() {
  local version="$1"
  local tag="container-v$version"
  local tag_object_sha commit ref_dir tag_dir_json rel_dir
  tag_object_sha="$(fixture_sha "tag-object:$tag")"
  commit="$(fixture_sha "commit:$tag")"
  ref_dir="$g_api_base/repos/$g_repo/git/ref/tags"
  tag_dir_json="$g_api_base/repos/$g_repo/git/tags"
  rel_dir="$g_api_base/repos/$g_repo/releases/tags"
  mkdir -p "$ref_dir" "$tag_dir_json" "$rel_dir"
  printf '{"ref":"refs/tags/%s","object":{"sha":"%s","type":"tag","url":"x"}}\n' \
    "$tag" "$tag_object_sha" > "$ref_dir/$tag"
  printf '{"sha":"%s","tag":"%s","object":{"sha":"%s","type":"commit","url":"x"},"tagger":{},"message":"m"}\n' \
    "$tag_object_sha" "$tag" "$commit" > "$tag_dir_json/$tag_object_sha"
  printf '{"tag_name":"%s","body":"Container release.\\n\\n- Source commit: %s\\n"}\n' \
    "$tag" "$commit" > "$rel_dir/$tag"
  printf '%s\n' "$commit"
}

# Writes only the release-notes fixture, to exercise the source-commit fallback.
write_notes_api() {
  local version="$1"
  local commit="$2"
  local tag="container-v$version"
  local rel_dir="$g_api_base/repos/$g_repo/releases/tags"
  mkdir -p "$rel_dir"
  printf '{"tag_name":"%s","body":"Container release.\\n\\n- Source commit: %s\\n"}\n' \
    "$tag" "$commit" > "$rel_dir/$tag"
}

# Replaces the checksum asset with a wrong but well-formed value.
corrupt_checksum() {
  local version="$1"
  local tag="container-v$version"
  printf 'deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef  %s.tar.gz\n' \
    "$tag" > "$g_asset_base/$tag/$tag.tar.gz.sha256"
}

echo "== Invalid tag syntax is refused =="
expect_fail "install latest is refused" install user-one latest
expect_fail "install main is refused" install user-one main
expect_fail "install container-v0.9 is refused" install user-one container-v0.9
expect_fail "install container-0.9.0 is refused" install user-one container-0.9.0
assert_no_path "$(releases_dir user-one)/container-v0.9.0" "invalid tag creates no release directory"

echo
echo "== Install a complete release without activating =="
commit_090="$(make_release 0.9.0 | tail -n1)"
env_before="$(env_snapshot "$g_home_one")"
expect_ok "install container-v0.9.0" install user-one container-v0.9.0
bundle_090="$(tag_dir user-one container-v0.9.0)/container"
assert_file "$bundle_090/Makefile" "installed bundle contains the deployment files"
assert_file "$(tag_dir user-one container-v0.9.0)/release-info" "release metadata is recorded"
assert_contains "$g_last_output" "$commit_090" "install reports the resolved source commit"
assert_eq "$commit_090" "$(sed -n 's/^COMMIT=//p' "$(tag_dir user-one container-v0.9.0)/release-info")" "metadata records the peeled source commit"
assert_eq "0.9.0" "$(tr -d '[:space:]' < "$bundle_090/VERSION")" "installed VERSION matches the tag"
assert_not_user_writable "$(tag_dir user-one container-v0.9.0)" "installed content is not writable by group/other"
assert_executable "$bundle_090/scripts/container.sh" "installed scripts keep execute permission"
assert_no_path "$(selector user-one)" "install does not create the selector"
assert_no_path "$(home_link user-one)" "install does not create ~/container"
assert_eq "$env_before" "$(env_snapshot "$g_home_one")" "install leaves deployment.env unchanged"

echo
echo "== Reinstalling the same tag does not overwrite it =="
expect_ok "reinstall the same tag is idempotent" install user-one container-v0.9.0
assert_contains "$g_last_output" "already installed" "reinstall reports the existing release"

echo
echo "== An existing but invalid tag directory is refused =="
mkdir -p "$(tag_dir user-one container-v9.9.9)/container"
printf 'marker\n' > "$(tag_dir user-one container-v9.9.9)/container/MARKER"
make_release 9.9.9 >/dev/null
expect_fail "existing invalid tag directory is refused" install user-one container-v9.9.9
assert_file "$(tag_dir user-one container-v9.9.9)/container/MARKER" "the existing directory is left untouched"

echo
echo "== Failure cases preserve the selection and clean up =="
make_release 0.9.1 >/dev/null
corrupt_checksum 0.9.1
expect_fail "checksum mismatch is refused" install user-one container-v0.9.1
assert_no_path "$(tag_dir user-one container-v0.9.1)" "checksum failure installs nothing"
assert_no_staging "$(releases_dir user-one)" "checksum failure cleans up staging"

make_release 0.13.1 >/dev/null
mkdir -p "$g_asset_base/container-v0.13.0"
cp "$g_asset_base/container-v0.13.1/container-v0.13.1.tar.gz" "$g_asset_base/container-v0.13.0/container-v0.13.0.tar.gz"
(cd "$g_asset_base/container-v0.13.0" && sha256sum container-v0.13.0.tar.gz > container-v0.13.0.tar.gz.sha256)
write_peeled_api 0.13.0 >/dev/null
expect_fail "archive version that does not match the tag is refused" install user-one container-v0.13.0
assert_no_path "$(tag_dir user-one container-v0.13.0)" "version mismatch installs nothing"

# Incomplete archive: the bundle is missing a required deployment file.
incomplete_build="$g_tmp/incomplete-0.14.0"
rm -rf "$incomplete_build"
mkdir -p "$incomplete_build/container" "$g_asset_base/container-v0.14.0"
cp -a "$g_container_dir/." "$incomplete_build/container/"
printf '0.14.0\n' > "$incomplete_build/container/VERSION"
rm -f "$incomplete_build/container/Makefile"
(cd "$incomplete_build" && tar -czf "$g_asset_base/container-v0.14.0/container-v0.14.0.tar.gz" container)
(cd "$g_asset_base/container-v0.14.0" && sha256sum container-v0.14.0.tar.gz > container-v0.14.0.tar.gz.sha256)
write_peeled_api 0.14.0 >/dev/null
expect_fail "archive missing a required file is refused" install user-one container-v0.14.0
assert_no_path "$(tag_dir user-one container-v0.14.0)" "incomplete archive installs nothing"

# Absolute path entry.
abs_build="$g_tmp/abs-0.15.0"
rm -rf "$abs_build"
mkdir -p "$abs_build/container" "$g_asset_base/container-v0.15.0"
printf '0.15.0\n' > "$abs_build/container/VERSION"
printf 'payload\n' > "$g_tmp/abs-payload"
(cd "$abs_build" && tar -czPf "$g_asset_base/container-v0.15.0/container-v0.15.0.tar.gz" container/VERSION "$g_tmp/abs-payload")
(cd "$g_asset_base/container-v0.15.0" && sha256sum container-v0.15.0.tar.gz > container-v0.15.0.tar.gz.sha256)
write_peeled_api 0.15.0 >/dev/null
expect_fail "archive with an absolute path is refused" install user-one container-v0.15.0
assert_contains "$g_last_output" "absolute path" "absolute-path archive reports the reason"
assert_no_path "$(tag_dir user-one container-v0.15.0)" "unsafe archive installs nothing"

# Parent-traversal entry.
trav_build="$g_tmp/trav-0.16.0"
rm -rf "$trav_build"
mkdir -p "$trav_build/container" "$g_asset_base/container-v0.16.0"
printf '0.16.0\n' > "$trav_build/container/VERSION"
printf 'payload\n' > "$trav_build/PAYLOAD"
(cd "$trav_build" && tar -czf "$g_asset_base/container-v0.16.0/container-v0.16.0.tar.gz" \
  --transform 's|^PAYLOAD$|container/../PAYLOAD|' container/VERSION PAYLOAD)
(cd "$g_asset_base/container-v0.16.0" && sha256sum container-v0.16.0.tar.gz > container-v0.16.0.tar.gz.sha256)
write_peeled_api 0.16.0 >/dev/null
expect_fail "archive with a parent-traversal path is refused" install user-one container-v0.16.0
assert_contains "$g_last_output" "traversal" "traversal archive reports the reason"
assert_no_path "$(tag_dir user-one container-v0.16.0)" "traversal archive installs nothing"

# Unreadable archive: an interrupted or corrupt transfer.
mkdir -p "$g_asset_base/container-v0.17.0"
printf 'not a gzip archive\n' > "$g_asset_base/container-v0.17.0/container-v0.17.0.tar.gz"
(cd "$g_asset_base/container-v0.17.0" && sha256sum container-v0.17.0.tar.gz > container-v0.17.0.tar.gz.sha256)
write_peeled_api 0.17.0 >/dev/null
expect_fail "unreadable archive is refused" install user-one container-v0.17.0
assert_no_path "$(tag_dir user-one container-v0.17.0)" "unreadable archive installs nothing"
assert_no_staging "$(releases_dir user-one)" "unreadable archive cleans up staging"

# Missing archive asset.
mkdir -p "$g_asset_base/container-v0.18.0"
(cd "$g_asset_base/container-v0.18.0" && printf 'x  container-v0.18.0.tar.gz\n' > container-v0.18.0.tar.gz.sha256)
write_peeled_api 0.18.0 >/dev/null
expect_fail "missing archive asset is refused" install user-one container-v0.18.0
assert_no_path "$(tag_dir user-one container-v0.18.0)" "missing asset installs nothing"

# Source-commit fallback through the release notes.
make_release 0.19.0 >/dev/null
notes_commit="$(fixture_sha "notes-commit:container-v0.19.0")"
rm -f "$g_api_base/repos/$g_repo/git/ref/tags/container-v0.19.0"
write_notes_api 0.19.0 "$notes_commit"
expect_ok "install resolves the commit from the release notes" install user-one container-v0.19.0
assert_eq "$notes_commit" "$(sed -n 's/^COMMIT=//p' "$(tag_dir user-one container-v0.19.0)/release-info")" "release-notes source commit is recorded"

# Source-commit resolution through git, with no GitHub API available at all.
make_release 0.20.0 >/dev/null
rm -rf "$g_api_base"
g_git_url="$(git_fixture_bare 0.20.0)"
git_commit="$(make_git_fixture 0.20.0)"
git_tag_object="$(git -C "$g_git_url" rev-parse "refs/tags/container-v0.20.0")"
expect_ok "install resolves the commit through git without the API" install user-one container-v0.20.0
assert_eq "$git_commit" "$(sed -n 's/^COMMIT=//p' "$(tag_dir user-one container-v0.20.0)/release-info")" "git resolves the annotated tag's peeled commit"
if [[ "$git_tag_object" != "$git_commit" ]]; then
  pass "the fixture tag is annotated, so the peel path was exercised"
else
  fail "the fixture tag is not annotated; the peel path was not exercised"
fi
g_git_url=""
g_api_url="file://$g_api_base"

echo
echo "== Activate, select, and roll back =="
make_release 0.10.0 >/dev/null
expect_ok "install container-v0.10.0" install user-one container-v0.10.0
expect_ok "activate container-v0.9.0" activate user-one container-v0.9.0
assert_eq "container-v0.9.0" "$(basename "$(dirname "$(readlink "$(selector user-one)")")")" "selector points at container-v0.9.0"
assert_eq "$(selector user-one)" "$(readlink "$(home_link user-one)")" "the home container link points at the selector"
assert_eq "$(tag_dir user-one container-v0.9.0)/container" "$(readlink -f "$(home_link user-one)")" "the home container link resolves into the selected release"
assert_contains "$g_last_output" "selected tag:      container-v0.9.0" "activate reports the selected tag"

expect_ok "activate container-v0.10.0" activate user-one container-v0.10.0
assert_eq "container-v0.9.0" "$(cat "$(previous_file user-one)")" "activation records the previous tag"

expect_ok_offline "rollback works without a download" rollback user-one
assert_eq "container-v0.9.0" "$(basename "$(dirname "$(readlink "$(selector user-one)")")")" "rollback selects the previous tag"
assert_eq "container-v0.10.0" "$(cat "$(previous_file user-one)")" "rollback records the tag it replaced"

echo
echo "== Two environments stay independent =="
expect_ok "install container-v0.10.0 for user-two" install user-two container-v0.10.0
expect_ok "activate container-v0.10.0 for user-two" activate user-two container-v0.10.0
assert_eq "container-v0.9.0" "$(basename "$(dirname "$(readlink "$(selector user-one)")")")" "user-one selection is unchanged"
assert_eq "container-v0.10.0" "$(basename "$(dirname "$(readlink "$(selector user-two)")")")" "user-two selection is independent"
assert_eq "$(env_snapshot "$g_home_one")" "$env_before" "activation leaves GIT_REF and IMAGE_NAME unchanged"
assert_no_path "$(g_home_root/user-one/container-data)" "activation creates no runtime data"

echo
echo "== Refusals leave the selection intact =="
expect_fail "activate an uninstalled tag is refused" activate user-one container-v8.8.8
assert_eq "container-v0.9.0" "$(basename "$(dirname "$(readlink "$(selector user-one)")")")" "uninstalled tag leaves the selection unchanged"

expect_fail "rollback without a recorded previous tag is refused" rollback user-two

rm -f "$(home_link user-two)"
mkdir -p "$(home_link user-two)"
printf 'keep\n' > "$(home_link user-two)/KEEP"
expect_fail "a real ~/container directory is refused" activate user-two container-v0.9.0
assert_file "$(home_link user-two)/KEEP" "the real directory is left intact"
assert_eq "container-v0.10.0" "$(basename "$(dirname "$(readlink "$(selector user-two)")")")" "a refused activation leaves the selection unchanged"

rm -rf "$(home_link user-two)"
ln -s "$g_tmp/unrelated-target" "$(home_link user-two)"
expect_fail "an unrelated ~/container symlink is refused" activate user-two container-v0.9.0
assert_eq "$g_tmp/unrelated-target" "$(readlink "$(home_link user-two)")" "the unrelated symlink is left intact"

echo
echo "== Status is read-only and survives a broken bundle =="
printf 'GIT_REF=%s\nIMAGE_NAME=shape-shifter:latest\n' "\$(touch $g_tmp/pwned)" > "$g_home_one/config/deployment.env"
expect_ok "status reports the selection" status user-one
assert_contains "$g_last_output" "selected tag:      container-v0.9.0" "status reports the selected tag"
assert_contains "$g_last_output" "source commit:     $commit_090" "status reports the source commit"
assert_contains "$g_last_output" "GIT_REF:           \$(touch $g_tmp/pwned)" "status reads GIT_REF without evaluating it"
assert_contains "$g_last_output" "IMAGE_NAME:        shape-shifter:latest" "status reports IMAGE_NAME separately"
assert_no_path "$g_tmp/pwned" "status does not evaluate deployment.env"

mv "$(tag_dir user-one container-v0.9.0)/container" "$(tag_dir user-one container-v0.9.0)/container.moved"
expect_ok "status works when the selected bundle is missing" status user-one
assert_contains "$g_last_output" "selected tag:      container-v0.9.0" "status still reports the selected tag"
assert_contains "$g_last_output" "selected bundle:   missing" "status reports the missing bundle"
mv "$(tag_dir user-one container-v0.9.0)/container.moved" "$(tag_dir user-one container-v0.9.0)/container"

echo
echo "== Production mode requires root and ignores test overrides =="
if out="$(env -u SHAPE_SHIFTER_RELEASE_TEST_MODE \
  SHAPE_SHIFTER_RELEASE_ROOT="$g_release_root" \
  bash "$g_manager" status user-one 2>&1)"; then
  fail "production mode without root should fail"
else
  pass "production mode without root is refused"
  assert_contains "$out" "root" "production refusal names the root requirement"
fi

echo
if ((g_failures > 0)); then
  printf '%d release manager check(s) failed\n' "$g_failures" >&2
  exit 1
fi
echo "All release manager checks passed"
