#!/usr/bin/env bash
# Configuration helpers shared by the build, bootstrap and deploy scripts.
#
# Source this file; it defines functions and changes no variables:
#     # shellcheck source=env-config.sh
#     . "$(dirname "${BASH_SOURCE[0]}")/env-config.sh"
#
# It complements load-env.sh, which reads container/.env into the environment.
# This file derives values from a git ref and writes values into .env, so a
# deployment keeps the repository, branch, image and port it was created with
# instead of falling back to the defaults on the next `make build`.

# Prints the image tag that scripts/build.sh publishes for a git ref:
#   v1.2.0          a release tag keeps its own name
#   main, or empty  latest
#   any other ref   the ref with unsupported characters replaced by '-'
# Keeping the rule here stops the build and the deploy scripts from disagreeing
# about which image a branch produces.
shapeshifter_tag_for_ref() {
    local ref="${1:-}"
    if [[ "$ref" =~ ^v[0-9]+\.[0-9]+\.[0-9]+ ]]; then
        printf '%s\n' "$ref"
    elif [ -z "$ref" ] || [ "$ref" = "main" ]; then
        printf 'latest\n'
    else
        printf '%s\n' "$(printf '%s' "$ref" | sed 's/[^a-zA-Z0-9._-]/-/g')"
    fi
}

# Prints the full image reference (name:tag) that a build of REF publishes.
# The second argument is the image name without a tag; it defaults to
# shape-shifter.
shapeshifter_image_for_ref() {
    local ref="${1:-}"
    local name="${2:-shape-shifter}"
    printf '%s:%s\n' "$name" "$(shapeshifter_tag_for_ref "$ref")"
}

# Sets KEY=VALUE in an env file, replacing an existing assignment or appending a
# new one. Creates the file when it is absent. Other lines are preserved.
shapeshifter_env_file_set() {
    local file="$1"
    local key="$2"
    local value="$3"
    local tmp

    tmp="$(mktemp)"
    if [ -f "$file" ]; then
        # Drop the current assignment, if any, then append the new value.
        grep -v -E "^[[:space:]]*${key}[[:space:]]*=" "$file" > "$tmp" || true
    fi
    printf '%s=%s\n' "$key" "$value" >> "$tmp"
    mv "$tmp" "$file"
}
