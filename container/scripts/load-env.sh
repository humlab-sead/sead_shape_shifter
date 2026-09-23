#!/usr/bin/env bash
# Applies CONFIG_DIR/deployment.env to the environment of the script that
# sources it, and resolves the paths that deployment depends on.
#
# Source this file; do not execute it, because it must change the environment of
# the caller:
#     # shellcheck source=load-env.sh
#     . "$(dirname "${BASH_SOURCE[0]}")/load-env.sh"
#
# Values already present in the environment are left alone, so an explicit
# `VAR=value ./script.sh` still wins over deployment.env. Set ENV_FILE to read a
# different file. A missing file is not an error, because commands validate the
# files they need when they run.
#
# Paths: CONFIG_DIR defaults to ~/config and DATA_DIR to ~/container-data, next
# to the checkout. A relative override names a path next to the checkout, so
# DATA_DIR=../container-data and DATA_DIR=container-data both mean
# ~/container-data. CONTAINER_DATA_DIR, which podman-compose.yml mounts,
# follows DATA_DIR unless it is set explicitly. The same rule is implemented in
# container/Makefile (`resolve_path`), and both must stay in step.

_shapeshifter_env_dir="$(
    CDPATH=''
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd
)"
_shapeshifter_checkout_parent="$(
    CDPATH=''
    cd -- "$_shapeshifter_env_dir/.." && pwd
)"
_shapeshifter_config_input="${CONFIG_DIR:-$HOME/config}"

case "$_shapeshifter_config_input" in
    /*) _shapeshifter_config_file_dir="$_shapeshifter_config_input" ;;
    *) _shapeshifter_config_file_dir="$_shapeshifter_checkout_parent/${_shapeshifter_config_input#./}" ;;
esac

_shapeshifter_env_file="${ENV_FILE:-$_shapeshifter_config_file_dir/deployment.env}"

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

CONFIG_DIR="${CONFIG_DIR:-$HOME/config}"
DATA_DIR="${DATA_DIR:-$HOME/container-data}"

case "$CONFIG_DIR" in
    /*) ;;
    *) CONFIG_DIR="$_shapeshifter_checkout_parent/${CONFIG_DIR#./}" ;;
esac

case "$DATA_DIR" in
    /*) ;;
    *) DATA_DIR="$_shapeshifter_checkout_parent/${DATA_DIR#./}" ;;
esac

# CONTAINER_DATA_DIR is what podman-compose.yml mounts. It follows DATA_DIR
# unless deployment.env or the caller set it explicitly, and a relative value
# resolves by the same rule as CONFIG_DIR and DATA_DIR.
_shapeshifter_container_data_input="${CONTAINER_DATA_DIR:-$DATA_DIR}"
case "$_shapeshifter_container_data_input" in
    /*) CONTAINER_DATA_DIR="$_shapeshifter_container_data_input" ;;
    *) CONTAINER_DATA_DIR="$_shapeshifter_checkout_parent/${_shapeshifter_container_data_input#./}" ;;
esac

export CONFIG_DIR DATA_DIR CONTAINER_DATA_DIR

unset _shapeshifter_env_dir _shapeshifter_checkout_parent _shapeshifter_config_input _shapeshifter_config_file_dir _shapeshifter_env_file _shapeshifter_line _shapeshifter_key _shapeshifter_value _shapeshifter_container_data_input
