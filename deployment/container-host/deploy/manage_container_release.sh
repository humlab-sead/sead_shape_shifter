#!/usr/bin/env bash
# DEPRECATED: this release manager is retired. Environments now keep a manual
# copy of the deployment/container/ tree in ~/container, and the planned
# replacement is pulling CI-built images from GHCR by digest
# (docs/proposals/GHCR_IMAGE_RELEASE.md). No host installs this script any
# more; it is kept only as a reference for the archive-verification logic the
# GHCR flow may reuse. Do not extend it.
#
# Install, select, and report Shape Shifter container releases for one
# deployment user per invocation.
#
# This is the administrator-owned host script. Install it once per host under
# /usr/local/sbin/ from a reviewed copy; it never runs from, and is never
# replaced by, an environment's selected bundle.
#
# Each user's releases live under
#   /opt/shape-shifter/<user>/container-releases/<tag>/container
# and the selected release is chosen through
#   /opt/shape-shifter/<user>/container-current -> .../<tag>/container
# with the user's home pointing at the selector:
#   ~/container -> /opt/shape-shifter/<user>/container-current
#
# Installing a release does not select it. Activating a release changes only
# that user's selector and keeps the previous selection for rollback. The
# container tag and source commit are recorded separately from the application
# image settings (GIT_REF, IMAGE_NAME), which this script never changes.
#
# `install` validates a downloaded archive with this script's own code: it
# verifies the checksum, rejects unsafe paths, checks the expected archive root
# and the recorded version, and checks a required-file list. It never executes
# anything from the candidate archive.
#
# Usage:
#   manage_container_release.sh install  USER container-vX.Y.Z
#   manage_container_release.sh activate USER container-vX.Y.Z
#   manage_container_release.sh rollback USER
#   manage_container_release.sh status   USER
#
# Run as root. See deployment/container/DEPLOYMENT.md for the operator workflow.
#
# Requires curl, tar, sha256sum, mktemp, flock and bash. `git` is optional: it
# resolves the tag's source commit without the GitHub API, which is rate-limited
# per network address.

set -euo pipefail

# --- Fixed production settings ---------------------------------------------
# Production use always uses these paths and repository. The test-only
# overrides below are reachable only when SHAPE_SHIFTER_RELEASE_TEST_MODE=1, so
# an ordinary invocation cannot be redirected to another storage path, another
# repository, or a non-root caller.
readonly g_release_root_default="/opt/shape-shifter"
readonly g_release_repo_default="humlab-sead/sead_shape_shifter"

if [[ "${SHAPE_SHIFTER_RELEASE_TEST_MODE:-0}" == "1" ]]; then
  g_test_mode=true
  : "${SHAPE_SHIFTER_RELEASE_ROOT:?SHAPE_SHIFTER_RELEASE_ROOT is required in test mode}"
  : "${SHAPE_SHIFTER_RELEASE_ASSET_BASE_URL:?SHAPE_SHIFTER_RELEASE_ASSET_BASE_URL is required in test mode}"
  g_release_root="$SHAPE_SHIFTER_RELEASE_ROOT"
  g_release_repo="${SHAPE_SHIFTER_RELEASE_REPO:-$g_release_repo_default}"
  g_asset_base_url="$SHAPE_SHIFTER_RELEASE_ASSET_BASE_URL"
  g_api_base_url="${SHAPE_SHIFTER_RELEASE_API_BASE_URL:-}"
  g_git_base_url="${SHAPE_SHIFTER_RELEASE_GIT_BASE_URL:-}"
  g_test_home_root="${SHAPE_SHIFTER_RELEASE_TEST_HOME_ROOT:-}"
else
  g_test_mode=false
  g_release_root="$g_release_root_default"
  g_release_repo="$g_release_repo_default"
  g_asset_base_url="https://github.com/$g_release_repo/releases/download"
  g_api_base_url="https://api.github.com"
  g_git_base_url="https://github.com/$g_release_repo.git"
  g_test_home_root=""
fi

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

note() {
  printf '%s\n' "$*"
}

usage() {
  cat <<'EOF'
Usage: manage_container_release.sh <command> [arguments]

Manage Shape Shifter container releases for one deployment user. Run as root.

Commands:
  install  USER container-vX.Y.Z   Download, verify, and install an exact
                                   release without selecting it
  activate USER container-vX.Y.Z   Select an already-installed release for USER
  rollback USER                    Select the release USER used before the
                                   current one (no download)
  status   USER                    Report the selected tag and source commit,
                                   the container link, and the application
                                   image settings

The container tag names a GitHub container release; it is not the application
image ref. Installing or selecting a release never changes GIT_REF, IMAGE_NAME,
~/config, or ~/container-data.

A downloaded archive is validated with this script's own checksum, path-safety,
expected-root/version, and required-file checks; no file from the archive is
ever executed.
EOF
}

require_root() {
  if [[ "$g_test_mode" == "true" ]]; then
    return 0
  fi
  [[ "$(id -u)" -eq 0 ]] || die "run this script as root (for example: sudo $0 ...)"
}

require_commands() {
  local tool
  for tool in curl tar sha256sum mktemp flock bash; do
    command -v "$tool" >/dev/null 2>&1 || die "required command is missing: $tool"
  done
  if [[ "$g_test_mode" != "true" ]]; then
    command -v getent >/dev/null 2>&1 || die "required command is missing: getent"
  fi
}

user_exists() {
  if [[ -n "$g_test_home_root" ]]; then
    return 0
  fi
  getent passwd "$1" >/dev/null 2>&1
}

user_uid() {
  if [[ -n "$g_test_home_root" ]]; then
    printf '1000\n'
    return 0
  fi
  getent passwd "$1" | cut -d: -f3
}

resolve_user_home() {
  if [[ -n "$g_test_home_root" ]]; then
    printf '%s/%s\n' "$g_test_home_root" "$1"
    return 0
  fi
  getent passwd "$1" | cut -d: -f6
}

validate_user() {
  local user="$1" uid home
  [[ "$user" =~ ^[a-z_][a-z0-9_.-]*$ ]] || die "invalid deployment user name: '$user'"
  [[ "$user" != "root" ]] || die "refusing to manage root as a deployment user"
  user_exists "$user" || die "no such user: $user"
  uid="$(user_uid "$user")"
  [[ "$uid" != "0" ]] || die "refusing to manage a user with uid 0: $user"
  home="$(resolve_user_home "$user")"
  [[ -n "$home" && -d "$home" ]] || die "deployment user $user has no home directory ($home)"
}

validate_tag() {
  local tag="$1"
  [[ "$tag" =~ ^container-v[0-9]+\.[0-9]+\.[0-9]+$ ]] ||
    die "invalid release tag '$tag': expected an exact container-vX.Y.Z tag"
}

tag_version() {
  printf '%s\n' "${1#container-v}"
}

user_dir_for() {
  printf '%s/%s\n' "$g_release_root" "$1"
}

releases_dir_for() {
  printf '%s/%s/container-releases\n' "$g_release_root" "$1"
}

tag_dir_for() {
  printf '%s/%s/container-releases/%s\n' "$g_release_root" "$1" "$2"
}

selector_for() {
  printf '%s/%s/container-current\n' "$g_release_root" "$1"
}

previous_file_for() {
  printf '%s/%s/container-previous\n' "$g_release_root" "$1"
}

lock_file_for() {
  printf '%s/%s/container-release.lock\n' "$g_release_root" "$1"
}

# Holds the per-user lock for the rest of the run, so two operations on the same
# user cannot interleave.
lock_user() {
  local lock_file="$1"
  exec 9>"$lock_file"
  flock 9
}

begin_command() {
  local user="$1"
  require_root
  require_commands
  validate_user "$user"
  [[ "$g_release_root" == /* ]] || die "release root must be an absolute path: $g_release_root"
  local user_dir
  user_dir="$(user_dir_for "$user")"
  mkdir -p "$user_dir"
  chmod 755 "$user_dir" 2>/dev/null || true
  lock_user "$(lock_file_for "$user")"
}

api_get() {
  curl -fsSL --max-time 60 -H 'Accept: application/vnd.github+json' "$1"
}

download_asset() {
  local url="$1" dest="$2"
  curl -fsSL --max-time 900 -o "$dest" "$url"
}

# Resolves the source commit for an exact container tag. `git ls-remote` reads
# the annotated tag's peeled commit without the GitHub API, so it is tried
# first: the API is rate-limited per network address and needs no token here.
# The API tag lookup and the source commit recorded in the release notes are the
# fallbacks, and the release notes are used when git is unavailable.
resolve_source_commit() {
  local tag="$1" commit="" ls_out="" ref_json="" ref_type="" tag_object_sha="" tag_json=""

  if [[ -n "$g_git_base_url" ]] && command -v git >/dev/null 2>&1; then
    ls_out="$(git ls-remote --tags "$g_git_base_url" "refs/tags/$tag*" 2>/dev/null || true)"
    if [[ -n "$ls_out" ]]; then
      # An annotated tag has a separate tag object; the peel entry is the commit.
      commit="$(awk -v p="refs/tags/$tag^{}" '$2 == p { print $1 }' <<<"$ls_out" | head -n1)"
      if [[ -z "$commit" ]]; then
        commit="$(awk -v p="refs/tags/$tag" '$2 == p { print $1 }' <<<"$ls_out" | head -n1)"
      fi
    fi
  fi

  if [[ -z "$commit" && -n "$g_api_base_url" ]]; then
    ref_json="$(api_get "$g_api_base_url/repos/$g_release_repo/git/ref/tags/$tag" 2>/dev/null || true)"
    if [[ -n "$ref_json" ]]; then
      ref_type="$(sed -n 's/.*"object":{[^}]*"type":"\([a-z]*\)".*/\1/p' <<<"$ref_json" | head -n1)"
      tag_object_sha="$(sed -n 's/.*"object":{[^}]*"sha":"\([0-9a-fA-F]\{7,40\}\)".*/\1/p' <<<"$ref_json" | head -n1)"
      if [[ "$ref_type" == "commit" && -n "$tag_object_sha" ]]; then
        commit="$tag_object_sha"
      elif [[ "$ref_type" == "tag" && -n "$tag_object_sha" ]]; then
        tag_json="$(api_get "$g_api_base_url/repos/$g_release_repo/git/tags/$tag_object_sha" 2>/dev/null || true)"
        if [[ -n "$tag_json" ]]; then
          commit="$(sed -n 's/.*"object":{[^}]*"sha":"\([0-9a-fA-F]\{7,40\}\)".*/\1/p' <<<"$tag_json" | head -n1)"
        fi
      fi
    fi
  fi

  if [[ -z "$commit" && -n "$g_api_base_url" ]]; then
    local release_json
    release_json="$(api_get "$g_api_base_url/repos/$g_release_repo/releases/tags/$tag" 2>/dev/null || true)"
    if [[ -n "$release_json" ]]; then
      commit="$(sed -n 's/.*Source commit: *\([0-9a-fA-F]\{7,40\}\).*/\1/p' <<<"$release_json" | head -n1)"
    fi
  fi

  [[ -n "$commit" ]] || return 1
  printf '%s\n' "$commit" | tr 'A-F' 'a-f'
}

# Rejects an archive that is unreadable or would extract outside its target
# directory.
check_archive_safety() {
  local archive="$1" entry
  tar -tzf "$archive" >/dev/null 2>&1 || die "release archive is unreadable: $archive"
  while IFS= read -r entry; do
    [[ -n "$entry" ]] || continue
    case "$entry" in
      /*) die "release archive contains an absolute path: $entry" ;;
    esac
    case "/$entry/" in
      */../*) die "release archive contains a parent-traversal path: $entry" ;;
    esac
  done < <(tar -tzf "$archive")
}

archive_version() {
  tar -xzOf "$1" container/VERSION | tr -d '[:space:]'
}

# Files every release bundle must contain. This is the manager's own trusted copy
# of the release contract: a downloaded archive is checked against this list, and
# no file from the candidate archive is ever executed. Keep it in step with the
# container-release workflow's required-file contract.
readonly g_required_files=(
	VERSION
	README.md
	DEPLOYMENT.md
	Makefile
	podman-compose.yml
	Containerfile
	.env.example
	.containerignore
	scripts/container.sh
	scripts/_load-env.sh
	scripts/_env-config.sh
	scripts/project.sh
	scripts/authorization.sh
	scripts/rename-user.sh
	scripts/setup.sh
	scripts/build.sh
	scripts/backup.sh
	scripts/healthcheck.sh
	service/shape-shifter.service
	resources/backend.env.example
	resources/.pgpass.example
	resources/authorization.env.example
)

# True when a tag directory holds a complete, tag-consistent, verified release.
validate_installed() {
  local tag_dir="$1" tag="$2"
  local bundle="$tag_dir/container" info="$tag_dir/release-info" required_file

  [[ -d "$bundle" && -f "$info" ]] || return 1
  [[ "$(sed -n 's/^TAG=//p' "$info" | head -n1)" == "$tag" ]] || return 1
  [[ -n "$(sed -n 's/^COMMIT=//p' "$info" | head -n1)" ]] || return 1
  [[ -f "$bundle/VERSION" ]] || return 1
  [[ "$(tr -d '[:space:]' < "$bundle/VERSION")" == "$(tag_version "$tag")" ]] || return 1

  for required_file in "${g_required_files[@]}"; do
    [[ -e "$bundle/$required_file" ]] || return 1
  done
  return 0
}

apply_install_permissions() {
  local tag_dir="$1"
  if [[ "$(id -u)" -eq 0 ]]; then
    chown -R root:root "$tag_dir"
  fi
  # Owner (root) keeps read/write; the deployment user can read and execute but
  # not write. X preserves execute bits on files that already have them.
  chmod -R u=rwX,go=rX "$tag_dir"
}

# Remove the install's own temporary state on any failure. The values are
# globals so the EXIT trap still sees them after a function returns.
g_install_staging=""
g_install_tag_dir=""
g_install_created_tag_dir=false
g_install_complete=false

install_cleanup_on_exit() {
  [[ "$g_install_complete" == "true" ]] && return 0
  [[ -n "$g_install_staging" ]] && rm -rf "$g_install_staging"
  [[ "$g_install_created_tag_dir" == "true" && -n "$g_install_tag_dir" ]] && rm -rf "$g_install_tag_dir"
  return 0
}

install_release() {
  local user="$1" tag="$2"
  begin_command "$user"
  validate_tag "$tag"

  local version releases_dir tag_dir
  version="$(tag_version "$tag")"
  releases_dir="$(releases_dir_for "$user")"
  tag_dir="$(tag_dir_for "$user" "$tag")"

  if [[ -e "$tag_dir" ]]; then
    if validate_installed "$tag_dir" "$tag"; then
      note "release $tag is already installed for $user and is valid; nothing to do"
      return 0
    fi
    die "an installed directory already exists at $tag_dir but does not validate; an administrator must review and remove it before reinstalling"
  fi

  mkdir -p "$releases_dir"
  chmod 755 "$releases_dir" 2>/dev/null || true

  g_install_tag_dir="$tag_dir"
  g_install_created_tag_dir=false
  g_install_complete=false
  g_install_staging="$(mktemp -d "$releases_dir/.staging.XXXXXX")" ||
    die "could not create a staging directory under $releases_dir"
  trap install_cleanup_on_exit EXIT

  local staging="$g_install_staging"
  local archive="$staging/$tag.tar.gz"
  local checksum="$staging/$tag.tar.gz.sha256"

  note "Downloading $tag from $g_asset_base_url/$tag ..."
  download_asset "$g_asset_base_url/$tag/$tag.tar.gz" "$archive" ||
    die "could not download the release archive for $tag"
  download_asset "$g_asset_base_url/$tag/$tag.tar.gz.sha256" "$checksum" ||
    die "could not download the release checksum for $tag"

  (cd "$staging" && sha256sum -c "$tag.tar.gz.sha256") ||
    die "checksum verification failed for $tag"

  check_archive_safety "$archive"

  local archive_ver
  archive_ver="$(archive_version "$archive" 2>/dev/null)" ||
    die "release archive for $tag is incomplete or unreadable"
  [[ "$archive_ver" == "$version" ]] ||
    die "release archive version $archive_ver does not match tag $tag"

  local extract_dir="$staging/extract"
  mkdir -p "$extract_dir"
  tar -xzf "$archive" -C "$extract_dir" ||
    die "could not extract the release archive for $tag"
  [[ -d "$extract_dir/container" ]] ||
    die "release archive for $tag does not contain a single container/ root"

  local commit
  commit="$(resolve_source_commit "$tag")" ||
    die "could not resolve the source commit for $tag: git ls-remote and the GitHub API both failed, and the GitHub API may be rate-limited for this network"

  local required_file
  for required_file in "${g_required_files[@]}"; do
    [[ -e "$extract_dir/container/$required_file" ]] ||
      die "release archive for $tag is missing required file: container/$required_file"
  done

  mkdir -p "$tag_dir" || die "could not create $tag_dir"
  g_install_created_tag_dir=true

  mv "$extract_dir/container" "$tag_dir/container" ||
    die "could not install the release bundle for $tag"
  printf 'TAG=%s\nVERSION=%s\nCOMMIT=%s\n' "$tag" "$version" "$commit" > "$tag_dir/release-info" ||
    die "could not record release metadata for $tag"

  apply_install_permissions "$tag_dir" ||
    die "could not set ownership and permissions for $tag"

  g_install_complete=true
  rm -rf "$staging"
  g_install_staging=""
  note "Installed $tag for $user at $tag_dir/container (source commit $commit)"
  note "Installation does not select the release; use 'activate $user $tag' to select it."
}

selector_tag() {
  local user="$1" target parent
  target="$(readlink -- "$(selector_for "$user")" 2>/dev/null || true)"
  [[ -n "$target" ]] || return 1
  parent="$(dirname -- "$target")"
  [[ "$(basename -- "$parent")" =~ ^container-v[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
  printf '%s\n' "$(basename -- "$parent")"
}

container_link_state() {
  local home_dir="$1" selector="$2"
  local link="$home_dir/container"
  if [[ -L "$link" ]]; then
    local target
    target="$(readlink -- "$link")"
    if [[ "$target" == "$selector" ]] || [[ "$(readlink -f -- "$link")" == "$(readlink -f -- "$selector")" ]]; then
      printf 'selects the release manager (%s)\n' "$selector"
    else
      printf 'unrelated symlink -> %s\n' "$target"
    fi
  elif [[ -e "$link" ]]; then
    printf 'real directory (not managed)\n'
  else
    printf 'absent\n'
  fi
}

# Fails when ~/container is a real directory or an unrelated symlink, before any
# selection change. An administrator must review and move such a path.
check_container_link() {
  local home_dir="$1" selector="$2"
  local link="$home_dir/container"
  if [[ -L "$link" ]]; then
    local target
    target="$(readlink -- "$link")"
    if [[ "$target" == "$selector" ]] || [[ "$(readlink -f -- "$link")" == "$(readlink -f -- "$selector")" ]]; then
      return 0
    fi
    die "refusing to change $link: it is a symlink to $target, not to $selector"
  fi
  if [[ -e "$link" ]]; then
    die "refusing to replace $link: an administrator must review and move the existing path before activation"
  fi
  return 0
}

ensure_container_link() {
  local home_dir="$1" selector="$2"
  local link="$home_dir/container"
  [[ -L "$link" ]] && return 0
  ln -s -- "$selector" "$link"
}

switch_selector() {
  local user="$1" tag="$2" selector tmp
  selector="$(selector_for "$user")"
  tmp="$selector.tmp.$$"
  rm -f "$tmp"
  ln -s -- "$(tag_dir_for "$user" "$tag")/container" "$tmp"
  mv -T -- "$tmp" "$selector"
}

activate_release() {
  local user="$1" tag="$2"
  begin_command "$user"
  validate_tag "$tag"

  local home_dir tag_dir selector current_tag
  home_dir="$(resolve_user_home "$user")"
  tag_dir="$(tag_dir_for "$user" "$tag")"
  selector="$(selector_for "$user")"

  [[ -d "$tag_dir" ]] ||
    die "release $tag is not installed for $user; run 'install $user $tag' first"
  validate_installed "$tag_dir" "$tag" ||
    die "installed release $tag for $user is incomplete or inconsistent; reinstall it before activating"

  current_tag="$(selector_tag "$user" 2>/dev/null || true)"
  check_container_link "$home_dir" "$selector"

  switch_selector "$user" "$tag"
  ensure_container_link "$home_dir" "$selector"

  if [[ -n "$current_tag" && "$current_tag" != "$tag" ]]; then
    printf '%s\n' "$current_tag" > "$(previous_file_for "$user")"
  fi

  note "Activated $tag for $user"
  note ""
  status_release_impl "$user"
}

rollback_release() {
  local user="$1"
  begin_command "$user"

  local home_dir selector previous_file previous_tag tag_dir current_tag
  home_dir="$(resolve_user_home "$user")"
  selector="$(selector_for "$user")"
  previous_file="$(previous_file_for "$user")"

  [[ -f "$previous_file" ]] ||
    die "no previous release is recorded for $user; nothing to roll back to"
  previous_tag="$(head -n1 "$previous_file" | tr -d '[:space:]')"
  validate_tag "$previous_tag" || die "recorded previous tag is invalid: '$previous_tag'"

  tag_dir="$(tag_dir_for "$user" "$previous_tag")"
  [[ -d "$tag_dir" ]] ||
    die "previous release $previous_tag is no longer installed for $user"
  validate_installed "$tag_dir" "$previous_tag" ||
    die "previous release $previous_tag is incomplete or inconsistent for $user"

  current_tag="$(selector_tag "$user" 2>/dev/null || true)"
  check_container_link "$home_dir" "$selector"

  switch_selector "$user" "$previous_tag"
  ensure_container_link "$home_dir" "$selector"

  if [[ -n "$current_tag" && "$current_tag" != "$previous_tag" ]]; then
    printf '%s\n' "$current_tag" > "$previous_file"
  else
    rm -f "$previous_file"
  fi

  note "Rolled back $user to $previous_tag"
  note ""
  status_release_impl "$user"
}

status_release_impl() {
  local user="$1" user_dir home_dir selector link previous_file
  user_dir="$(user_dir_for "$user")"
  home_dir="$(resolve_user_home "$user")"
  selector="$(selector_for "$user")"
  link="$home_dir/container"
  previous_file="$(previous_file_for "$user")"

  local selected_tag="(none)" commit="(unknown)" bundle_state="missing"
  if selected_tag="$(selector_tag "$user" 2>/dev/null)"; then
    local info
    info="$(tag_dir_for "$user" "$selected_tag")/release-info"
    if [[ -f "$info" ]]; then
      commit="$(sed -n 's/^COMMIT=//p' "$info" | head -n1)"
      [[ -n "$commit" ]] || commit="(unknown)"
    fi
    if [[ -d "$(tag_dir_for "$user" "$selected_tag")/container" ]]; then
      bundle_state="present"
    else
      bundle_state="missing"
    fi
  else
    selected_tag="(none)"
  fi

  local previous_tag="(none)"
  if [[ -f "$previous_file" ]]; then
    previous_tag="$(head -n1 "$previous_file" | tr -d '[:space:]')"
    [[ -n "$previous_tag" ]] || previous_tag="(none)"
  fi

  # Read the application image settings as plain values. deployment.env is never
  # sourced here, and these values are reported separately from the release.
  local deployment_env="$home_dir/config/deployment.env"
  local git_ref="(unset)" image_name="(unset)"
  if [[ -f "$deployment_env" ]]; then
    git_ref="$(sed -n 's/^[[:space:]]*GIT_REF[[:space:]]*=[[:space:]]*//p' "$deployment_env" | tail -n1)"
    image_name="$(sed -n 's/^[[:space:]]*IMAGE_NAME[[:space:]]*=[[:space:]]*//p' "$deployment_env" | tail -n1)"
    [[ -n "$git_ref" ]] || git_ref="(unset)"
    [[ -n "$image_name" ]] || image_name="(unset)"
  fi

  note "user:              $user"
  note "storage:           $user_dir"
  note "selected tag:      $selected_tag"
  note "source commit:     $commit"
  note "selected bundle:   $bundle_state"
  note "previous tag:      $previous_tag"
  note "container link:    $(container_link_state "$home_dir" "$selector")"
  note "GIT_REF:           $git_ref"
  note "IMAGE_NAME:        $image_name"
}

status_release() {
  local user="$1"
  begin_command "$user"
  status_release_impl "$user"
}

main() {
  local command="${1:-}"
  case "$command" in
    install)
      shift
      [[ $# -eq 2 ]] || { usage >&2; exit 64; }
      install_release "$1" "$2"
      ;;
    activate)
      shift
      [[ $# -eq 2 ]] || { usage >&2; exit 64; }
      activate_release "$1" "$2"
      ;;
    rollback)
      shift
      [[ $# -eq 1 ]] || { usage >&2; exit 64; }
      rollback_release "$1"
      ;;
    status)
      shift
      [[ $# -eq 1 ]] || { usage >&2; exit 64; }
      status_release "$1"
      ;;
    help | -h | --help)
      usage
      ;;
    '')
      usage >&2
      exit 64
      ;;
    *)
      printf 'error: unknown command: %s\n' "$command" >&2
      usage >&2
      exit 64
      ;;
  esac
}

main "$@"
