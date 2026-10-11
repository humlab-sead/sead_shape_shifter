#!/usr/bin/env bash
# Applies CONFIG_DIR/deployment.env to the environment of the script that
# sources it, and resolves the paths that deployment depends on.
#
# Source this file; do not execute it, because it must change the environment of
# the caller:
#     # shellcheck source=_load-env.sh
#     . "$(dirname "${BASH_SOURCE[0]}")/_load-env.sh"
#
# Values already present in the environment are left alone, so an explicit
# `VAR=value ./script.sh` still wins over deployment.env. Set ENV_FILE to read a
# different file. A missing file is not an error, because commands validate the
# files they need when they run.
#
# A shared deployment value that deployment.env does not set falls back to the
# bundled .env.example template, so a checkout that has not run `make setup` and
# an initialized deployment resolve the same defaults. The template is parsed as
# plain KEY=value lines and is never executed. Precedence, highest first:
#   1. the environment    VAR=value ./script.sh
#   2. ENV_FILE (CONFIG_DIR/deployment.env)
#   3. the bundled .env.example template
#
# Paths: CONFIG_DIR defaults to ~/config and DATA_DIR to ~/container-data. A
# relative override names a path under the deployment user's home, so
# DATA_DIR=container-data and DATA_DIR=./container-data both mean
# ~/container-data, and an absolute override is used unchanged. Resolving
# relative overrides from $HOME rather than from the selected release directory
# keeps configuration and data outside the release even when ~/container is a
# symlink into a versioned release. CONTAINER_DATA_DIR, which
# podman-compose.yml mounts, follows DATA_DIR unless it is set explicitly. The
# same rule is implemented in container/Makefile (`resolve_path`), and both must
# stay in step.

# Exports each KEY=value assignment in a file only when the variable is not
# already set, so the environment keeps precedence over any file. Comments,
# blank lines, malformed keys, and Windows line endings are handled the same way
# for deployment.env and the bundled template.
_shapeshifter_read_env_file() {
    local _file="$1" _line _key _value
    [ -f "$_file" ] || return 0
    while IFS= read -r _line || [ -n "$_line" ]; do
        case "$_line" in
            '' | '#'*) continue ;;
        esac
        _key="${_line%%=*}"
        _value="${_line#*=}"
        # Tolerate files saved with Windows line endings.
        _value="${_value%$'\r'}"
        # Skip malformed lines rather than exporting an unusable variable name.
        case "$_key" in
            '' | *[!A-Za-z0-9_]*) continue ;;
        esac
        if [ -z "${!_key:-}" ]; then
            export "$_key=$_value"
        fi
    done < "$_file"
}

_shapeshifter_script_dir="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
_shapeshifter_env_template="$_shapeshifter_script_dir/../.env.example"

_shapeshifter_config_input="${CONFIG_DIR:-$HOME/config}"

case "$_shapeshifter_config_input" in
    /*) _shapeshifter_config_file_dir="$_shapeshifter_config_input" ;;
    *) _shapeshifter_config_file_dir="$HOME/${_shapeshifter_config_input#./}" ;;
esac

_shapeshifter_env_file="${ENV_FILE:-$_shapeshifter_config_file_dir/deployment.env}"

# Read deployment.env first, then the bundled template, so the file beats the
# template and the environment beats both.
_shapeshifter_read_env_file "$_shapeshifter_env_file"
_shapeshifter_read_env_file "$_shapeshifter_env_template"

CONFIG_DIR="${CONFIG_DIR:-$HOME/config}"
DATA_DIR="${DATA_DIR:-$HOME/container-data}"

case "$CONFIG_DIR" in
    /*) ;;
    *) CONFIG_DIR="$HOME/${CONFIG_DIR#./}" ;;
esac

case "$DATA_DIR" in
    /*) ;;
    *) DATA_DIR="$HOME/${DATA_DIR#./}" ;;
esac

# CONTAINER_DATA_DIR is what podman-compose.yml mounts. It follows DATA_DIR
# unless deployment.env or the caller set it explicitly, and a relative value
# resolves by the same rule as CONFIG_DIR and DATA_DIR.
_shapeshifter_container_data_input="${CONTAINER_DATA_DIR:-$DATA_DIR}"
case "$_shapeshifter_container_data_input" in
    /*) CONTAINER_DATA_DIR="$_shapeshifter_container_data_input" ;;
    *) CONTAINER_DATA_DIR="$HOME/${_shapeshifter_container_data_input#./}" ;;
esac

export CONFIG_DIR DATA_DIR CONTAINER_DATA_DIR

unset -f _shapeshifter_read_env_file
unset _shapeshifter_script_dir _shapeshifter_env_template _shapeshifter_config_input _shapeshifter_config_file_dir _shapeshifter_env_file _shapeshifter_container_data_input
