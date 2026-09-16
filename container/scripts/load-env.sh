#!/usr/bin/env bash
# Applies container/.env to the environment of the script that sources it.
#
# Source this file; do not execute it, because it must change the environment of
# the caller:
#     # shellcheck source=load-env.sh
#     . "$(dirname "${BASH_SOURCE[0]}")/load-env.sh"
#
# Values already present in the environment are left alone, so an explicit
# `VAR=value ./script.sh` still wins over .env. Set ENV_FILE to read a different
# file. A missing file is not an error, because the scripts fall back to their
# own defaults.

_shapeshifter_env_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
_shapeshifter_env_file="${ENV_FILE:-$_shapeshifter_env_dir/.env}"

if [ -f "$_shapeshifter_env_file" ]; then
    while IFS= read -r _shapeshifter_line || [ -n "$_shapeshifter_line" ]; do
        case "$_shapeshifter_line" in
            '' | '#'*) continue ;;
        esac
        _shapeshifter_key="${_shapeshifter_line%%=*}"
        _shapeshifter_value="${_shapeshifter_line#*=}"
        # Tolerate files saved with Windows line endings.
        _shapeshifter_value="${_shapeshifter_value%$'\r'}"
        # Skip malformed lines rather than exporting an unusable variable name.
        case "$_shapeshifter_key" in
            '' | *[!A-Za-z0-9_]*) continue ;;
        esac
        if [ -z "${!_shapeshifter_key:-}" ]; then
            export "$_shapeshifter_key=$_shapeshifter_value"
        fi
    done < "$_shapeshifter_env_file"
fi

# DATA_DIR is documented relative to the container directory. Resolve it here so
# the scripts behave the same whatever directory they are started from.
case "${DATA_DIR:-}" in
    '' | /*) ;;
    *)
        DATA_DIR="$_shapeshifter_env_dir/${DATA_DIR#./}"
        export DATA_DIR
        ;;
esac

unset _shapeshifter_env_dir _shapeshifter_env_file _shapeshifter_line _shapeshifter_key _shapeshifter_value
