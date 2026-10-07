#!/usr/bin/env bash
# Adopt an already-copied project folder into Shape Shifter authorization.
#
# Copying a project folder into the projects directory makes its YAML visible on
# disk, but the centralized authorization system also needs a `project` resource
# record and an owner grant before any principal can read it. This script writes a
# minimal manifest (one resource + one owner grant) and imports it through the
# supported `authorization.sh import-manifest` wrapper.
#
# Usage:
#   adopt-project.sh --project <name-or-path> --owner <principal> [--role <role>] [--dry-run]
#
#   <name-or-path> is relative to the projects directory, e.g. "P" or "arbodat/P".
#   "/" becomes the ":" API separator used by the locator.
#   <principal> is the case-sensitive principal ID nginx forwards (the htpasswd
#   username on a Basic-auth site). It must already resolve at the proxy.
set -euo pipefail

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
AUTH_WRAPPER="$SCRIPT_DIR/authorization.sh"

PROJECT=""
OWNER=""
ROLE="owner"
DRY_RUN=false

usage() {
    cat <<'EOF'
Usage: adopt-project.sh --project <name-or-path> --owner <principal> [options]

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
            usage; exit 0 ;;
        *)
            echo "Unknown argument: $1" >&2; usage; exit 1 ;;
    esac
done

[[ -n "$PROJECT" ]] || { echo "--project is required." >&2; usage; exit 1; }
[[ -n "$OWNER" ]] || { echo "--owner is required." >&2; usage; exit 1; }
[[ "$ROLE" == "owner" ]] || { echo "Only 'owner' is supported for initial adoption." >&2; exit 1; }

# Locator uses the API separator ':' for nested paths, matching
# ProjectNameMapper.to_api_name(). A top-level folder "P" stays "P".
LOCATOR="${PROJECT//\//:}"

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
