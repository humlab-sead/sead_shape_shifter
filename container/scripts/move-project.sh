#!/usr/bin/env bash
# Move a Shape Shifter project folder and keep its authorization.
#
# A project's authorization resource is addressed by a locator derived from its
# folder path, and its grants attach to the resource UUID. Renaming the folder on
# disk changes the locator, so the old locator stops resolving and the grants are
# left behind unless the resource record is moved with it. This script moves the
# folder and then calls `authorization.sh move-resource`, which updates the locator
# in place and keeps the resource UUID, so existing grants continue to apply.
#
# The application must be running, because authorization.sh talks to the container.
# If the moved project was the active editing project, restart the container
# afterwards so application state does not keep the old locator.
#
# Usage:
#   move-project.sh --project <name-or-path> --to <name-or-path> [--dry-run] [--yes]
#
#   Both values are relative to the projects directory, e.g. "P" or "arbodat/P".
#   "/" and ":" are both accepted, so "arbodat/P" and "arbodat:P" mean the same.
#   The folder must already exist at --project and must not exist at --to.
set -euo pipefail

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
AUTH_WRAPPER="$SCRIPT_DIR/authorization.sh"

# shellcheck source=load-env.sh
. "$SCRIPT_DIR/load-env.sh"
# load-env.sh resolves CONTAINER_DATA_DIR; podman-compose.yml mounts
# $CONTAINER_DATA_DIR/projects at /app/projects.
PROJECTS_DIR="${CONTAINER_DATA_DIR}/projects"

PROJECT=""
TARGET=""
DRY_RUN=false
ASSUME_YES=false

usage() {
    cat <<'EOF'
Usage: move-project.sh --project <name-or-path> --to <name-or-path> [options]

Move a project folder and update its authorization locator in place. The
resource UUID is kept, so existing grants continue to apply. Requires
authorization.sh in the same directory and a running container.

Required:
  --project NAME   Current project name or path relative to the projects
                   directory (e.g. "P" or "arbodat/P").
  --to NAME        New project name or path relative to the projects directory.

Options:
  --dry-run        Print the planned folder move and authorization change without
                   changing anything.
  --yes, -y        Do not prompt before the folder move.
  -h, --help       Show this help.

Notes:
  "/" and ":" are both accepted as path separators, matching the ":" API
  separator used by the locator.

  If the folder was already moved by hand, update authorization directly with:
    container/scripts/authorization.sh move-resource --resource-type project \
      --from-locator OLD --to-locator NEW
EOF
}

fail() {
    echo "Error: $1" >&2
    exit 1
}

# Convert a name or path to the locator form used by authorization (":" separator).
to_locator() {
    printf '%s' "${1//\//:}"
}

# Convert a name or path to a relative filesystem path with the "/" separator.
# Rejects empty values, absolute paths, and any ".." component so a move cannot
# escape the projects directory.
to_relative_path() {
    local value="${1//:/\/}"
    if [[ -z "$value" || "$value" == /* || "$value" == *..* ]]; then
        fail "Invalid project name or path: '$1'"
    fi
    printf '%s' "$value"
}

# Read authorization state through the container wrapper. These stay as plain
# functions so callers can capture them with a simple "$(name)" substitution.
authorization_resources() {
    "$AUTH_WRAPPER" list-resources
}

authorization_grants() {
    "$AUTH_WRAPPER" list-grants
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project)
            [[ $# -ge 2 ]] || fail "--project requires a value."
            PROJECT="$2"; shift 2 ;;
        --to)
            [[ $# -ge 2 ]] || fail "--to requires a value."
            TARGET="$2"; shift 2 ;;
        --dry-run)
            DRY_RUN=true; shift ;;
        --yes|-y)
            ASSUME_YES=true; shift ;;
        -h|--help)
            usage; exit 0 ;;
        *)
            echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
    esac
done

[[ -n "$PROJECT" ]] || { echo "--project is required." >&2; usage >&2; exit 1; }
[[ -n "$TARGET" ]] || { echo "--to is required." >&2; usage >&2; exit 1; }

LOCATOR_FROM="$(to_locator "$PROJECT")"
LOCATOR_TO="$(to_locator "$TARGET")"
[[ "$LOCATOR_FROM" != "$LOCATOR_TO" ]] || fail "--project and --to must differ."

SOURCE_REL="$(to_relative_path "$PROJECT")"
TARGET_REL="$(to_relative_path "$TARGET")"
SOURCE_PATH="$PROJECTS_DIR/$SOURCE_REL"
TARGET_PATH="$PROJECTS_DIR/$TARGET_REL"

# --- Filesystem preflight -----------------------------------------------------

[[ -d "$SOURCE_PATH" ]] || fail "Project folder not found: $SOURCE_PATH"
[[ -f "$SOURCE_PATH/shapeshifter.yml" ]] || fail "Not a project folder (no shapeshifter.yml): $SOURCE_PATH"
if [[ -e "$TARGET_PATH" ]]; then
    fail "Target already exists: $TARGET_PATH"
fi
case "$TARGET_PATH/" in
    "$SOURCE_PATH"/*) fail "Target is inside the source folder: $TARGET_PATH" ;;
esac

# --- Authorization preflight --------------------------------------------------

resources_before="$(authorization_resources)"
from_line="$(printf '%s\n' "$resources_before" | grep -F "project:${LOCATOR_FROM} active" || true)"
[[ -n "$from_line" ]] || fail "No active project authorization resource: project:${LOCATOR_FROM}"
if printf '%s\n' "$resources_before" | grep -F "project:${LOCATOR_TO} active" >/dev/null; then
    fail "An active project authorization resource already uses locator: project:${LOCATOR_TO}"
fi
RESOURCE_ID="${from_line##* }"

grants_before="$(authorization_grants)"
grant_count_before="$(printf '%s\n' "$grants_before" | grep -cF " ${RESOURCE_ID}" || true)"

echo "Move plan:"
echo "  folder:      $SOURCE_PATH"
echo "            -> $TARGET_PATH"
echo "  authorization: project:${LOCATOR_FROM} -> project:${LOCATOR_TO} (resource_id ${RESOURCE_ID})"
echo "  grants kept: ${grant_count_before}"
echo

if [[ "$DRY_RUN" == true ]]; then
    echo "Dry run: no changes made. Would run:"
    echo "  mv \"$SOURCE_PATH\" \"$TARGET_PATH\""
    echo "  $AUTH_WRAPPER move-resource --resource-type project --from-locator $LOCATOR_FROM --to-locator $LOCATOR_TO --yes"
    exit 0
fi

if [[ "$ASSUME_YES" != true ]]; then
    read -r -p "Move project '${LOCATOR_FROM}' to '${LOCATOR_TO}'? [y/N] " confirmation
    [[ "$confirmation" =~ ^[Yy]$ ]] || { echo "Move cancelled."; exit 0; }
fi

# --- Apply --------------------------------------------------------------------

mkdir -p "$(dirname "$TARGET_PATH")"
mv "$SOURCE_PATH" "$TARGET_PATH"

if ! "$AUTH_WRAPPER" move-resource \
    --resource-type project \
    --from-locator "$LOCATOR_FROM" \
    --to-locator "$LOCATOR_TO" \
    --yes; then
    echo "Authorization move failed; restoring folder." >&2
    mv "$TARGET_PATH" "$SOURCE_PATH"
    fail "Rolled back folder move; authorization is unchanged."
fi

# --- Verify -------------------------------------------------------------------

resources_after="$(authorization_resources)"
if printf '%s\n' "$resources_after" | grep -F "project:${LOCATOR_FROM} active" >/dev/null; then
    fail "Old locator is still active: project:${LOCATOR_FROM}"
fi
printf '%s\n' "$resources_after" | grep -F "project:${LOCATOR_TO} active" >/dev/null \
    || fail "New locator not active: project:${LOCATOR_TO}"

grants_after="$(authorization_grants)"
grant_count_after="$(printf '%s\n' "$grants_after" | grep -cF " ${RESOURCE_ID}" || true)"
[[ "$grant_count_after" == "$grant_count_before" ]] \
    || fail "Grant count changed for resource ${RESOURCE_ID}: ${grant_count_before} -> ${grant_count_after}"

echo "Done. Project moved to '${LOCATOR_TO}' with ${grant_count_after} grant(s) kept."
echo "Restart the container if this project was the active editing project."
