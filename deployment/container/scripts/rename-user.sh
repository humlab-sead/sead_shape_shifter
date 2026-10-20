#!/usr/bin/env bash
# Rename one Shape Shifter principal in a deployed environment.
#
# The NGINX htpasswd account name is the authorization principal ID that the
# backend reads from X-Authenticated-User, so renaming an account in htpasswd
# alone leaves every stored role and grant pointing at the old name. This script
# moves one principal in a single pass:
#
#   1. Back up the authorization database and the configuration files it edits.
#   2. Grant every deployment role and resource grant the old name holds to the
#      new name, then revoke the old ones. Grants are added before revocations,
#      so the final-administrator and final-owner protections never block the
#      move.
#   3. Rewrite the principal in the group membership file, authorization.env,
#      backend.env, and the reviewed authorization manifest, then import the
#      manifest so any record that was missing is added.
#   4. Report anything that still names the old principal.
#
# The htpasswd account and the installed NGINX group file live outside the
# deployment user's home, so they change only when --delete-htpasswd and
# --apply-nginx are given. Otherwise the script prints the exact commands.
set -euo pipefail

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
AUTH_WRAPPER="$SCRIPT_DIR/authorization.sh"

# shellcheck source=_load-env.sh
. "$SCRIPT_DIR/_load-env.sh"

ENV_FILE="$CONFIG_DIR/authorization.env"
GROUPS_FILE="$CONFIG_DIR/groups.d/shape-shifter.conf"
BACKEND_ENV_FILE="$CONFIG_DIR/backend.env"
INSTALLED_GROUPS_FILE="${INSTALLED_GROUPS_FILE:-/etc/nginx/authz/groups.d/shape-shifter.conf}"
HTPASSWD_FILE="${HTPASSWD_FILE:-/etc/nginx/htpasswd/shape-shifter}"
BACKUP_DIR="${AUTHORIZATION_BACKUP_DIR:-$DATA_DIR/backups}"

FROM_USER=""
TO_USER=""
ACTOR=""
MANIFEST_FILE=""
CONFIG_BACKUP_DIR=""
DRY_RUN=false
ASSUME_YES=false
APPLY_NGINX=false
DELETE_HTPASSWD=false

usage() {
    cat <<'EOF'
Usage: rename-user.sh <from-principal> <to-principal> [options]

Move one Shape Shifter principal from one account name to another. The old name
must not be in use afterwards; the new name must already exist as the NGINX
htpasswd account, or be created before the next login.

Options:
  --actor PRINCIPAL     Actor recorded on authorization changes (default: the
                        new principal).
  --apply-nginx         Install the group membership file to
                        /etc/nginx/authz/groups.d/ and reload NGINX. Requires
                        sudo.
  --delete-htpasswd     Delete the old htpasswd account after the move. Requires
                        sudo. The new account is never created or changed.
  --dry-run             Print every command and file change without applying it.
  --yes                 Skip the confirmation prompt.
  -h, --help            Show this help.

Reads CONFIG_DIR/authorization.env, CONFIG_DIR/groups.d/shape-shifter.conf,
CONFIG_DIR/backend.env, and the manifest named by AUTHORIZATION_MANIFEST.
Run as the deployment user from the deployment's container directory, so the
authorization wrapper reaches the running container.

Example:
  container/scripts/rename-user.sh roger roger@humlab.gu.se --dry-run
  container/scripts/rename-user.sh roger roger@humlab.gu.se --yes --apply-nginx
EOF
}

fail() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

warn() {
    printf 'warning: %s\n' "$*" >&2
}

# Run a command, or print it when the caller asked for a dry run.
perform() {
    if [[ "$DRY_RUN" == true ]]; then
        printf '  [dry-run] %s\n' "$*"
        return 0
    fi
    printf '  %s\n' "$*"
    "$@"
}

confirm() {
    if [[ "$ASSUME_YES" == true || "$DRY_RUN" == true ]]; then
        return 0
    fi
    local answer
    read -r -p "$1 [y/N] " answer || return 1
    [[ "$answer" =~ ^[Yy]$ ]]
}

# A principal ID reaches NGINX, space-separated roster values, JSON arrays, and
# the group file, so accept only the characters an account name can contain.
# Restricting the set also keeps the rewrites below free of quoting and
# regular-expression surprises.
validate_principal() {
    local label="$1" value="$2"
    [[ -n "$value" ]] || fail "$label must not be empty"
    [[ ${#value} -le 255 ]] || fail "$label is longer than 255 characters"
    if [[ ! "$value" =~ ^[A-Za-z0-9][A-Za-z0-9._@+-]*$ ]]; then
        fail "$label is not a valid principal ID: '$value' (allowed: letters, digits, '.', '_', '@', '+', '-')"
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --actor)
            [[ $# -ge 2 ]] || fail "--actor requires a value"
            ACTOR="$2"
            shift 2
            ;;
        --apply-nginx) APPLY_NGINX=true; shift ;;
        --delete-htpasswd) DELETE_HTPASSWD=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --yes) ASSUME_YES=true; shift ;;
        -h|--help) usage; exit 0 ;;
        --) shift; break ;;
        -*) fail "unknown option: $1" ;;
        *)
            if [[ -z "$FROM_USER" ]]; then
                FROM_USER="$1"
            elif [[ -z "$TO_USER" ]]; then
                TO_USER="$1"
            else
                fail "unexpected argument: $1"
            fi
            shift
            ;;
    esac
done

[[ -n "$FROM_USER" && -n "$TO_USER" ]] || { usage >&2; exit 2; }
validate_principal "the old principal" "$FROM_USER"
validate_principal "the new principal" "$TO_USER"
[[ "$FROM_USER" != "$TO_USER" ]] || fail "the old and new principal are identical"
ACTOR="${ACTOR:-$TO_USER}"
validate_principal "the actor" "$ACTOR"

command -v podman >/dev/null || fail "podman is required"
[[ -x "$AUTH_WRAPPER" ]] || fail "authorization wrapper is missing or not executable: $AUTH_WRAPPER"

# Resolve the reviewed manifest the same way the bootstrap does: a relative name
# lives below CONFIG_DIR. Read the value without sourcing authorization.env so
# the passwords it holds never enter this process environment.
manifest_name="$(sed -n 's/^AUTHORIZATION_MANIFEST=//p' "$ENV_FILE" 2>/dev/null | tail -n1 || true)"
manifest_name="${manifest_name%\"}"
manifest_name="${manifest_name#\"}"
manifest_name="${manifest_name%\'}"
manifest_name="${manifest_name#\'}"
if [[ -n "$manifest_name" ]]; then
    if [[ "$manifest_name" == /* ]]; then
        MANIFEST_FILE="$manifest_name"
    else
        MANIFEST_FILE="$CONFIG_DIR/$manifest_name"
    fi
fi

printf 'Renaming principal: %s -> %s\n' "$FROM_USER" "$TO_USER"
printf 'Configuration directory: %s\n' "$CONFIG_DIR"

# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

# These reads fail the script when the container is not running, which is the
# intended preflight: every authorization change goes through the wrapper.
roles_output="$("$AUTH_WRAPPER" list-application-roles)"
grants_output="$("$AUTH_WRAPPER" list-grants)"
resources_output="$("$AUTH_WRAPPER" list-resources)"

mapfile -t ROLES < <(awk -v principal="$FROM_USER" '$1 == principal { print $2 }' <<<"$roles_output" | sort -u)
mapfile -t GRANTS < <(awk -v subject="principal:$FROM_USER" '$1 == subject { print $2, $3 }' <<<"$grants_output" | sort -u)

# resource_id -> "resource_type:locator", so a grant can be reissued by locator.
declare -A RESOURCE_KEY=()
while IFS=$'\t' read -r resource_id resource_key; do
    [[ -n "$resource_id" ]] || continue
    RESOURCE_KEY["$resource_id"]="$resource_key"
done < <(awk '$2 == "active" { print $3 "\t" $1 }' <<<"$resources_output")

printf '\nPlan:\n'
if [[ ${#ROLES[@]} -eq 0 ]]; then
    printf '  deployment roles: none\n'
else
    printf '  deployment roles: %s\n' "${ROLES[*]}"
fi
if [[ ${#GRANTS[@]} -eq 0 ]]; then
    printf '  resource grants: none\n'
else
    printf '  resource grants: %d\n' "${#GRANTS[@]}"
    for entry in "${GRANTS[@]}"; do
        read -r role resource_id <<<"$entry"
        printf '    %s on %s\n' "$role" "${RESOURCE_KEY[$resource_id]:-resource $resource_id (not active)}"
    done
fi
if [[ -z "$MANIFEST_FILE" ]]; then
    printf '  manifest: not configured in %s\n' "$ENV_FILE"
elif [[ -f "$MANIFEST_FILE" ]]; then
    printf '  manifest: %s\n' "$MANIFEST_FILE"
else
    printf '  manifest: missing at %s\n' "$MANIFEST_FILE"
fi

# ---------------------------------------------------------------------------
# Backups
# ---------------------------------------------------------------------------

CONFIG_FILES=("$GROUPS_FILE" "$ENV_FILE" "$BACKEND_ENV_FILE")
if [[ -n "$MANIFEST_FILE" ]]; then
    CONFIG_FILES+=("$MANIFEST_FILE")
fi

printf '\nBacking up:\n'
perform "$AUTH_WRAPPER" backup

CONFIG_BACKUP_DIR="$BACKUP_DIR/rename-user-$FROM_USER-$(date +%Y%m%d-%H%M%S)"
config_backup_needed=false
for file in "${CONFIG_FILES[@]}"; do
    [[ -f "$file" ]] && config_backup_needed=true
done
if [[ "$config_backup_needed" == true ]]; then
    if [[ "$DRY_RUN" == true ]]; then
        printf '  [dry-run] would copy configuration files to %s\n' "$CONFIG_BACKUP_DIR"
    else
        mkdir -p "$CONFIG_BACKUP_DIR"
        for file in "${CONFIG_FILES[@]}"; do
            [[ -f "$file" ]] || continue
            cp -p "$file" "$CONFIG_BACKUP_DIR/"
            printf '  backed up %s\n' "$file"
        done
    fi
fi

# ---------------------------------------------------------------------------
# Authorization records
# ---------------------------------------------------------------------------

if ! confirm "Move ${#ROLES[@]} role(s) and ${#GRANTS[@]} grant(s) from $FROM_USER to $TO_USER?"; then
    printf 'Cancelled.\n'
    exit 1
fi

moved_roles=0
if [[ ${#ROLES[@]} -gt 0 ]]; then
    printf '\nDeployment roles:\n'
    for role in "${ROLES[@]}"; do
        # Grant first: revoking a final administrator would be refused.
        perform "$AUTH_WRAPPER" grant-application-role --principal-id "$TO_USER" --role "$role" --actor "$ACTOR"
        perform "$AUTH_WRAPPER" revoke-application-role --principal-id "$FROM_USER" --role "$role" --actor "$ACTOR" --yes
        moved_roles=$((moved_roles + 1))
    done
fi

moved_grants=0
if [[ ${#GRANTS[@]} -gt 0 ]]; then
    printf '\nResource grants:\n'
    for entry in "${GRANTS[@]}"; do
        read -r role resource_id <<<"$entry"
        resource_key="${RESOURCE_KEY[$resource_id]:-}"
        if [[ -z "$resource_key" ]]; then
            warn "skipping $role on resource $resource_id: the resource is not active"
            continue
        fi
        resource_type="${resource_key%%:*}"
        locator="${resource_key#*:}"
        # Grant first: revoking a final project owner would be refused.
        perform "$AUTH_WRAPPER" grant --resource-type "$resource_type" --locator "$locator" \
            --subject-type principal --subject-id "$TO_USER" --role "$role" --actor "$ACTOR"
        perform "$AUTH_WRAPPER" revoke --resource-type "$resource_type" --locator "$locator" \
            --subject-type principal --subject-id "$FROM_USER" --role "$role" --actor "$ACTOR" --yes
        moved_grants=$((moved_grants + 1))
    done
fi

# ---------------------------------------------------------------------------
# Configuration files
# ---------------------------------------------------------------------------

# Replace a temp file's contents while keeping the original file's owner, group,
# and mode. The temporary file only supplies the new text.
replace_contents() {
    local target="$1" replacement="$2"
    cat "$replacement" > "$target"
    rm -f "$replacement"
}

# Rewrite one principal ID inside the value of one KEY=value line. The value is
# split on characters that cannot appear in a principal ID, so only a complete
# token is replaced and quotes or space-separated rosters keep their shape.
rewrite_env_value() {
    local file="$1" key="$2"
    [[ -f "$file" ]] || return 0
    if ! grep -qE "^${key}=" "$file"; then
        return 0
    fi
    printf '  %s: %s\n' "$(basename "$file")" "$key"
    if [[ "$DRY_RUN" == true ]]; then
        return 0
    fi
    local tmp
    tmp="$(mktemp "${file}.XXXXXX")"
    awk -v key="$key" -v from="$FROM_USER" -v to="$TO_USER" '
        index($0, key "=") == 1 {
            value = substr($0, length(key) + 2)
            out = ""
            token = ""
            for (i = 1; i <= length(value); i++) {
                c = substr(value, i, 1)
                if (c ~ /[A-Za-z0-9._@+-]/) {
                    token = token c
                    continue
                }
                if (token != "") {
                    out = out (token == from ? to : token)
                    token = ""
                }
                out = out c
            }
            if (token != "") {
                out = out (token == from ? to : token)
            }
            print key "=" out
            next
        }
        { print }
    ' "$file" > "$tmp"
    replace_contents "$file" "$tmp"
}

# Rewrite the account name that starts a membership line. Alignment and group
# IDs on the line are left as they are.
rewrite_groups_file() {
    local file="$1"
    [[ -f "$file" ]] || { warn "group membership file not found: $file"; return 0; }
    printf '  %s: member line\n' "$(basename "$file")"
    if [[ "$DRY_RUN" == true ]]; then
        return 0
    fi
    local tmp
    tmp="$(mktemp "${file}.XXXXXX")"
    awk -v from="$FROM_USER" -v to="$TO_USER" '
        {
            line = $0
            if (match(line, /^[[:space:]]*[^[:space:]]+/)) {
                token = substr(line, 1, RLENGTH)
                rest = substr(line, RLENGTH + 1)
                name = token
                sub(/^[[:space:]]+/, "", name)
                if (name == from) {
                    print substr(token, 1, length(token) - length(name)) to rest
                    next
                }
            }
            print line
        }
    ' "$file" > "$tmp"
    replace_contents "$file" "$tmp"
}

# Rewrite administrators list items and grant subjects in the reviewed manifest.
# Only the administrators section is allowed to hold a bare principal item, so a
# project locator or comment is never touched.
rewrite_manifest_file() {
    local file="$1"
    [[ -f "$file" ]] || { warn "authorization manifest not found: $file"; return 0; }
    printf '  %s: administrators and grant subjects\n' "$(basename "$file")"
    if [[ "$DRY_RUN" == true ]]; then
        return 0
    fi
    local tmp
    tmp="$(mktemp "${file}.XXXXXX")"
    awk -v from="$FROM_USER" -v to="$TO_USER" '
        function rewrite(line, pattern,   prefix, value) {
            if (line ~ pattern) {
                match(line, pattern)
                prefix = substr(line, 1, RLENGTH)
                value = substr(line, RLENGTH + 1)
                gsub(/[[:space:]]+$/, "", value)
                if (value == from) {
                    return prefix to
                }
            }
            return line
        }
        {
            if ($0 ~ /^[^[:space:]#]/) {
                section = $0
                sub(/:.*/, "", section)
            }
            out = $0
            if (section == "administrators") {
                out = rewrite(out, "^[[:space:]]*-[[:space:]]*")
            }
            out = rewrite(out, "^[[:space:]]*(-[[:space:]]+)?principal_id:[[:space:]]*")
            out = rewrite(out, "^[[:space:]]*(-[[:space:]]+)?subject_id:[[:space:]]*")
            print out
        }
    ' "$file" > "$tmp"
    replace_contents "$file" "$tmp"
}

printf '\nConfiguration files:\n'
rewrite_groups_file "$GROUPS_FILE"
for key in AUTH_USERS ADMIN_AUTH_USER PROJECT_MAINTAINERS PROJECT_CREATOR_AND_OPERATOR AUTHORIZATION_ACTOR; do
    rewrite_env_value "$ENV_FILE" "$key"
done
for key in SHAPE_SHIFTER_AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS SHAPE_SHIFTER_DEVELOPMENT_PRINCIPAL_ID; do
    rewrite_env_value "$BACKEND_ENV_FILE" "$key"
done
if [[ -n "$MANIFEST_FILE" ]]; then
    rewrite_manifest_file "$MANIFEST_FILE"
    perform "$AUTH_WRAPPER" import-manifest "$MANIFEST_FILE"
fi

# ---------------------------------------------------------------------------
# Host-level files
# ---------------------------------------------------------------------------

printf '\nHost-level files:\n'
if [[ "$APPLY_NGINX" == true ]]; then
    perform sudo install -m 640 -o root -g www-data "$GROUPS_FILE" "$INSTALLED_GROUPS_FILE"
    perform sudo nginx -t
    perform sudo systemctl reload nginx
else
    printf '  not installed (pass --apply-nginx to do it here):\n'
    printf '    sudo install -m 640 -o root -g www-data %q %q\n' "$GROUPS_FILE" "$INSTALLED_GROUPS_FILE"
    printf '    sudo nginx -t && sudo systemctl reload nginx\n'
fi

if [[ "$DELETE_HTPASSWD" == true ]]; then
    perform sudo htpasswd -D "$HTPASSWD_FILE" "$FROM_USER"
else
    printf '  htpasswd account left in place (pass --delete-htpasswd to remove it):\n'
    printf '    sudo htpasswd -D %q %q\n' "$HTPASSWD_FILE" "$FROM_USER"
fi

# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

# Match a complete token, so "roger" does not match "roger@example.org".
file_mentions_token() {
    local file="$1" wanted="$2"
    awk -v wanted="$wanted" '
        {
            rest = $0
            while (match(rest, /[A-Za-z0-9._@+-]+/)) {
                if (substr(rest, RSTART, RLENGTH) == wanted) {
                    found = 1
                    exit
                }
                rest = substr(rest, RSTART + RLENGTH)
            }
        }
        END { exit(found ? 0 : 1) }
    ' "$file"
}

printf '\nSummary:\n'
printf '  roles moved: %d\n' "$moved_roles"
printf '  grants moved: %d\n' "$moved_grants"

if [[ "$DRY_RUN" == true ]]; then
    printf '  dry run: no changes were made\n'
    exit 0
fi

problems=0
remaining_roles="$(awk -v principal="$FROM_USER" '$1 == principal { print }' <<<"$("$AUTH_WRAPPER" list-application-roles)")"
if [[ -n "$remaining_roles" ]]; then
    warn "the old principal still holds deployment roles:"
    printf '%s\n' "$remaining_roles" >&2
    problems=$((problems + 1))
fi
remaining_grants="$(awk -v subject="principal:$FROM_USER" '$1 == subject { print }' <<<"$("$AUTH_WRAPPER" list-grants)")"
if [[ -n "$remaining_grants" ]]; then
    warn "the old principal still holds resource grants:"
    printf '%s\n' "$remaining_grants" >&2
    problems=$((problems + 1))
fi
for file in "${CONFIG_FILES[@]}"; do
    [[ -f "$file" ]] || continue
    if file_mentions_token "$file" "$FROM_USER"; then
        warn "still mentions $FROM_USER: $file"
        problems=$((problems + 1))
    fi
done
if [[ -f "$ENV_FILE" ]] && ! file_mentions_token "$ENV_FILE" "$TO_USER"; then
    warn "the new principal is not listed in $ENV_FILE; a later bootstrap would not create its htpasswd account"
fi

if [[ "$problems" -gt 0 ]]; then
    printf '\nThe move finished with %d unresolved reference(s). Review the warnings above before removing access.\n' "$problems" >&2
    exit 1
fi

printf '\nDone. %s -> %s\n' "$FROM_USER" "$TO_USER"
printf 'Tell the renamed user to reload the browser so sessions and operations are created under the new name.\n'
