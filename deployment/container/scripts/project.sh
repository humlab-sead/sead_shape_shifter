#!/usr/bin/env bash
# Administer Shape Shifter project folders and their authorization records.
#
# Usage: project.sh <adopt|move> [options]
#
# One entry point for the two project operations, so the shared project-path and
# authorization helpers live in one place. Each action keeps its own validation
# and safeguards:
#
#   adopt   Writes one minimal manifest (a project resource plus one owner grant)
#           for a folder that was copied into the projects directory, imports it
#           through the supported authorization.sh wrapper, and verifies it.
#
#   move    Moves a project folder and updates its authorization locator in
#           place, keeping the resource UUID and its grants. It preflights the
#           folder and the authorization state, supports dry-run and
#           confirmation, and restores the folder if the authorization change
#           fails.
#
# Both actions talk to the running container through authorization.sh in this
# directory.
set -euo pipefail

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
AUTH_WRAPPER="$SCRIPT_DIR/authorization.sh"

# shellcheck source=_load-env.sh
. "$SCRIPT_DIR/_load-env.sh"
# _load-env.sh resolves CONTAINER_DATA_DIR; podman-compose.yml mounts
# $CONTAINER_DATA_DIR/projects at /app/projects.
PROJECTS_DIR="${CONTAINER_DATA_DIR}/projects"

usage() {
    cat <<'EOF'
Usage: project.sh <adopt|move> [options]

Actions:
  adopt   Create a project resource and owner grant for a folder that was
          copied into the projects directory.
  move    Move a project folder and update its authorization locator in place.

Run 'project.sh adopt --help' or 'project.sh move --help' for action options.
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

# ---------------------------------------------------------------------------
# adopt
# ---------------------------------------------------------------------------

adopt_usage() {
    cat <<'EOF'
Usage: project.sh adopt --project <name-or-path> --owner <principal> [options]

Create an authorization resource and owner grant for a project folder that was
copied into the projects directory. Requires authorization.sh in the same
directory.

Required:
  --project NAME       Project name or path relative to the projects directory
                       (e.g. "P" or "arbodat/P"). "/" becomes the ":" API separator.
  --owner PRINCIPAL    Case-sensitive principal ID to grant owner.

Options:
  --role ROLE          Resource role to grant (default: owner). Owner may only be
                       granted to a principal, never group or everyone.
  --dry-run            Print the manifest and commands without changing anything.
  -h, --help           Show this help.
EOF
}

run_adopt() {
    local PROJECT="" OWNER="" ROLE="owner" DRY_RUN=false
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --project)
                [[ $# -ge 2 ]] || { echo "--project requires a value." >&2; exit 1; }
                PROJECT="$2"; shift 2 ;;
            --owner)
                [[ $# -ge 2 ]] || { echo "--owner requires a value." >&2; exit 1; }
                OWNER="$2"; shift 2 ;;
            --role)
                [[ $# -ge 2 ]] || { echo "--role requires a value." >&2; exit 1; }
                ROLE="$2"; shift 2 ;;
            --dry-run)
                DRY_RUN=true; shift ;;
            -h|--help)
                adopt_usage; exit 0 ;;
            *)
                echo "Unknown argument: $1" >&2; adopt_usage >&2; exit 1 ;;
        esac
    done

    [[ -n "$PROJECT" ]] || { echo "--project is required." >&2; adopt_usage >&2; exit 1; }
    [[ -n "$OWNER" ]] || { echo "--owner is required." >&2; adopt_usage >&2; exit 1; }
    [[ "$ROLE" == "owner" ]] || { echo "Only 'owner' is supported for initial adoption." >&2; exit 1; }

    # Locator uses the API separator ':' for nested paths, matching
    # ProjectNameMapper.to_api_name(). A top-level folder "P" stays "P".
    local LOCATOR
    LOCATOR="$(to_locator "$PROJECT")"

    # Keep the manifest path out of the local scope: the EXIT trap runs after the
    # function returns and must still resolve the variable.
    manifest_file="$(mktemp --suffix=.json)"
    trap 'rm -f "$manifest_file"' EXIT

    # "administrators" is a required manifest key; leave it empty so no admin role
    # is created or changed. owner may only be granted to a principal.
    cat > "$manifest_file" <<JSON
{
  "administrators": [],
  "resources": [
    {
      "resource_type": "project",
      "locator": "${LOCATOR}",
      "grants": [
        { "subject_type": "principal", "subject_id": "${OWNER}", "role": "${ROLE}" }
      ]
    }
  ]
}
JSON

    echo "Manifest:"
    cat "$manifest_file"
    echo

    if [[ "$DRY_RUN" == true ]]; then
        echo "Dry run: no changes made. Would run:"
        echo "  $AUTH_WRAPPER import-manifest $manifest_file"
        exit 0
    fi

    "$AUTH_WRAPPER" import-manifest "$manifest_file"

    echo
    echo "Verifying..."
    "$AUTH_WRAPPER" list-resources --json | grep -F "\"locator\": \"${LOCATOR}\"" >/dev/null \
        && echo "  resource: active (locator '${LOCATOR}')" \
        || { echo "  ERROR: resource '${LOCATOR}' not found in list-resources" >&2; exit 1; }
    "$AUTH_WRAPPER" list-grants --json | grep -F "\"subject_id\": \"${OWNER}\"" >/dev/null \
        && echo "  grant: ${OWNER} ${ROLE}" \
        || { echo "  ERROR: no grant found for principal '${OWNER}'" >&2; exit 1; }

    echo "Done. $OWNER now owns project '${LOCATOR}'."
}

# ---------------------------------------------------------------------------
# move
# ---------------------------------------------------------------------------

move_usage() {
    cat <<'EOF'
Usage: project.sh move --project <name-or-path> --to <name-or-path> [options]

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

run_move() {
    local PROJECT="" TARGET="" DRY_RUN=false ASSUME_YES=false
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
                move_usage; exit 0 ;;
            *)
                echo "Unknown argument: $1" >&2; move_usage >&2; exit 1 ;;
        esac
    done

    [[ -n "$PROJECT" ]] || { echo "--project is required." >&2; move_usage >&2; exit 1; }
    [[ -n "$TARGET" ]] || { echo "--to is required." >&2; move_usage >&2; exit 1; }

    local LOCATOR_FROM LOCATOR_TO SOURCE_REL TARGET_REL SOURCE_PATH TARGET_PATH
    LOCATOR_FROM="$(to_locator "$PROJECT")"
    LOCATOR_TO="$(to_locator "$TARGET")"
    [[ "$LOCATOR_FROM" != "$LOCATOR_TO" ]] || fail "--project and --to must differ."

    SOURCE_REL="$(to_relative_path "$PROJECT")"
    TARGET_REL="$(to_relative_path "$TARGET")"
    SOURCE_PATH="$PROJECTS_DIR/$SOURCE_REL"
    TARGET_PATH="$PROJECTS_DIR/$TARGET_REL"

    # --- Filesystem preflight -------------------------------------------------

    [[ -d "$SOURCE_PATH" ]] || fail "Project folder not found: $SOURCE_PATH"
    [[ -f "$SOURCE_PATH/shapeshifter.yml" ]] || fail "Not a project folder (no shapeshifter.yml): $SOURCE_PATH"
    if [[ -e "$TARGET_PATH" ]]; then
        fail "Target already exists: $TARGET_PATH"
    fi
    case "$TARGET_PATH/" in
        "$SOURCE_PATH"/*) fail "Target is inside the source folder: $TARGET_PATH" ;;
    esac

    # --- Authorization preflight ----------------------------------------------

    local resources_before from_line RESOURCE_ID grants_before grant_count_before
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
        local confirmation
        read -r -p "Move project '${LOCATOR_FROM}' to '${LOCATOR_TO}'? [y/N] " confirmation
        [[ "$confirmation" =~ ^[Yy]$ ]] || { echo "Move cancelled."; exit 0; }
    fi

    # --- Apply ----------------------------------------------------------------

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

    # --- Verify ---------------------------------------------------------------

    local resources_after grants_after grant_count_after
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
}

action="${1:-}"
case "$action" in
adopt)
    shift
    run_adopt "$@"
    ;;
move)
    shift
    run_move "$@"
    ;;
help | -h | --help)
    usage
    ;;
'')
    usage >&2
    exit 64
    ;;
*)
    echo "error: unknown action '$action'" >&2
    usage >&2
    exit 64
    ;;
esac
