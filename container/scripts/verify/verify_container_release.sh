#!/usr/bin/env bash
# Validate the inputs and output of a container release.
#
# Checks used by the container-release workflow, before PR validation and again
# before publication:
#   - container/VERSION exists and holds a plain X.Y.Z version;
#   - the version strictly increases over the highest existing container-v* tag;
#   - every required deployment file is present in the container/ tree;
#   - the release archive unpacks under a single container/ directory and
#     contains the same required files, with no .git or secrets inside;
#   - optionally, the revision under review already contains origin/main, so a
#     promotion branch has merged main as the release policy requires.
#
# The script reads files and git metadata only. It never publishes, tags, or
# changes anything.
#
# Usage:
#   verify_container_release.sh dir [options]      check the container/ tree
#   verify_container_release.sh archive FILE       check a built archive
#
# Options for dir:
#   --container-dir DIR   container directory to check (default: alongside this script)
#   --git-dir DIR         git repository used for tag and ancestry checks
#                         (default: repository containing the container directory)
#   --require-main-merged fail unless origin/main is an ancestor of HEAD
#
# Exit status: 0 when every check passes, 1 on the first failed check.

set -euo pipefail

# Files that must appear in both the container/ tree and the release archive.
# The archive is the complete tracked container/ bundle, so .containerignore
# (image-build context only) must not be applied to it.
REQUIRED_FILES=(
	VERSION
	README.md
	DEPLOYMENT.md
	Makefile
	podman-compose.yml
	Containerfile
	.env.example
	.containerignore
	scripts/load-env.sh
	scripts/env-config.sh
	scripts/setup.sh
	scripts/build.sh
	scripts/backup.sh
	scripts/healthcheck.sh
	service/shape-shifter.service
	resources/backend.env.example
	resources/.pgpass.example
	resources/authorization.env.example
)

die() {
	echo "FAIL: $*" >&2
	exit 1
}

ok() {
	echo "ok: $*"
}

script_dir() {
	cd "$(dirname "${BASH_SOURCE[0]}")" && pwd
}

# Read and validate the version string in container/VERSION.
read_version() {
	local container_dir="$1" version_file version
	version_file="$container_dir/VERSION"
	[[ -f "$version_file" ]] || die "container/VERSION is missing"
	version="$(tr -d '[:space:]' <"$version_file")"
	[[ -n "$version" ]] || die "container/VERSION is empty"
	[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] ||
		die "container/VERSION '$version' is not a plain X.Y.Z version"
	echo "$version"
}

# Highest released container version from container-v* tags, empty when none.
highest_tagged_version() {
	git -C "$1" tag -l 'container-v*' |
		sed 's/^container-v//' |
		grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' |
		sort -V |
		tail -n 1 || true
}

# Compare two X.Y.Z versions: returns 0 when $1 > $2.
version_gt() {
	local highest
	highest="$(printf '%s\n%s\n' "$1" "$2" | sort -V | tail -n 1)"
	[[ "$highest" == "$1" && "$1" != "$2" ]]
}

check_dir() {
	local container_dir="$1" git_dir="$2" require_main_merged="$3"
	local version previous

	version="$(read_version "$container_dir")"
	ok "container/VERSION is $version"

	local required_file
	for required_file in "${REQUIRED_FILES[@]}"; do
		[[ -e "$container_dir/$required_file" ]] ||
			die "required deployment file missing: container/$required_file"
	done
	ok "all ${#REQUIRED_FILES[@]} required deployment files are present"

	if [[ -n "$git_dir" ]]; then
		previous="$(highest_tagged_version "$git_dir")"
		if [[ -n "$previous" ]]; then
			version_gt "$version" "$previous" ||
				die "version $version does not strictly increase over the last container-v$previous tag"
			ok "version $version increases over container-v$previous"
		else
			ok "no previous container-v* tag; $version is the first container release"
		fi
		if git -C "$git_dir" rev-parse -q --verify "refs/tags/container-v$version" >/dev/null; then
			die "tag container-v$version already exists; the version must be new"
		fi
		if [[ "$require_main_merged" == "true" ]]; then
			git -C "$git_dir" merge-base --is-ancestor origin/main HEAD 2>/dev/null ||
				die "the reviewed revision does not contain origin/main; merge main into the promotion branch"
			ok "origin/main is merged into the reviewed revision"
		fi
	else
		ok "skipping tag checks: no git repository provided"
	fi
}

check_archive() {
	local archive="$1"
	[[ -f "$archive" ]] || die "archive not found: $archive"

	local entries top
	entries="$(tar -tzf "$archive")"
	[[ -n "$entries" ]] || die "archive is empty: $archive"
	top="$(echo "$entries" | cut -d/ -f1 | sort -u)"
	[[ "$top" == "container" ]] ||
		die "archive must unpack under a single container/ directory, found: $top"

	if printf '%s\n' "$entries" | grep -qE '(^|/)\.git/'; then
		die "archive must not contain .git content"
	fi

	local version required_file
	printf '%s\n' "$entries" | grep -qxF 'container/VERSION' ||
		die "archive is missing container/VERSION"
	version="$(tar -xzOf "$archive" container/VERSION | tr -d '[:space:]')"
	[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] ||
		die "archive container/VERSION '$version' is not a plain X.Y.Z version"

	for required_file in "${REQUIRED_FILES[@]}"; do
		printf '%s\n' "$entries" | grep -qxF "container/$required_file" ||
			die "archive is missing container/$required_file"
	done
	ok "archive container-v layout is valid for version $version with all required files"
}

main() {
	local mode="${1:-}"
	shift || true
	case "$mode" in
	dir)
		local container_dir="" git_dir="" require_main_merged="false"
		while [[ $# -gt 0 ]]; do
			case "$1" in
			--container-dir) container_dir="$2"; shift 2 ;;
			--git-dir) git_dir="$2"; shift 2 ;;
			--require-main-merged) require_main_merged="true"; shift ;;
			*) die "unknown option for dir mode: $1" ;;
			esac
		done
		[[ -n "$container_dir" ]] || container_dir="$(dirname "$(dirname "$(script_dir)")")"
		if [[ -z "$git_dir" ]]; then
			git_dir="$(git -C "$container_dir" rev-parse --show-toplevel 2>/dev/null || true)"
		fi
		check_dir "$container_dir" "$git_dir" "$require_main_merged"
		;;
	archive)
		local archive="${1:-}"
		[[ -n "$archive" ]] || die "archive mode needs the archive file path"
		check_archive "$archive"
		;;
	*)
		sed -n '3,26p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
		exit 2
		;;
	esac
	echo "container release checks passed"
}

main "$@"
