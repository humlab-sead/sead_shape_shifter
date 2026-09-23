#!/usr/bin/env bash
# Back up the deployment: mutable data, state and runtime configuration.
#
# The archive keeps the two ownership groups apart, in the same layout the
# deployment uses: mutable data and state under the archive root, runtime
# configuration under config/. Files are copied with their modes, so the
# credential files keep their restrictive permissions.
#
# Operator-provisioned authorization inputs (authorization.env, the manifest and
# groups.d/) are not copied. The live authorization policy is held in the
# backed-up state database, and those input files are provisioned by hand.
set -euo pipefail

# Load CONFIG_DIR/deployment.env values that the environment has not already
# set, and resolve the CONFIG_DIR and DATA_DIR defaults.
# shellcheck source=load-env.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/load-env.sh"

timestamp="$(date +%Y%m%d_%H%M%S)"
backup_dir="${DATA_DIR}/backups/backup_${timestamp}"
config_backup_dir="${backup_dir}/config"
mkdir -p "$config_backup_dir"
chmod 700 "$backup_dir" "$config_backup_dir"

echo "Creating backup: ${backup_dir}"
for data_item in projects shared state; do
  cp -r "${DATA_DIR}/${data_item}" "$backup_dir/" 2>/dev/null || true
done

echo "Copying runtime configuration from ${CONFIG_DIR}"
for config_file in deployment.env backend.env; do
  if [ -f "${CONFIG_DIR}/${config_file}" ]; then
    cp -p "${CONFIG_DIR}/${config_file}" "${config_backup_dir}/"
    echo "  ${config_file}"
  fi
done

# The PostgreSQL password file is mounted as a file, so it keeps its own
# directory in the archive.
if [ -f "${CONFIG_DIR}/.pgpass/.pgpass" ]; then
  mkdir -p "${config_backup_dir}/.pgpass"
  chmod 700 "${config_backup_dir}/.pgpass"
  cp -p "${CONFIG_DIR}/.pgpass/.pgpass" "${config_backup_dir}/.pgpass/"
  echo "  .pgpass/.pgpass"
fi

echo "Backup complete"
