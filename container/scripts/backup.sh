#!/usr/bin/env bash
# Back up the deployment data: projects, shared data, environment and state.
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="${DATA_DIR:-$ROOT_DIR/../container-data}"

timestamp="$(date +%Y%m%d_%H%M%S)"
backup_dir="${DATA_DIR}/backups/backup_${timestamp}"
mkdir -p "$backup_dir"

echo "Creating backup: ${backup_dir}"
cp -r "${DATA_DIR}/projects" "$backup_dir/" 2>/dev/null || true
cp -r "${DATA_DIR}/shared" "$backup_dir/" 2>/dev/null || true
cp -r "${DATA_DIR}/state" "$backup_dir/" 2>/dev/null || true
cp "${DATA_DIR}/backend.env" "$backup_dir/" 2>/dev/null || true
if [ -f "${DATA_DIR}/.pgpass/.pgpass" ]; then
  mkdir -p "$backup_dir/.pgpass"
  cp "${DATA_DIR}/.pgpass/.pgpass" "$backup_dir/.pgpass/" 2>/dev/null || true
fi

echo "Backup complete"
