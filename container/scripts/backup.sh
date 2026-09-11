#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="${DATA_DIR:-$ROOT_DIR/../container-data}"

timestamp="$(date +%Y%m%d_%H%M%S)"
backup_dir="${DATA_DIR}/backups/backup_${timestamp}"
mkdir -p "$backup_dir"

echo "Creating backup: ${backup_dir}"
cp -r "${DATA_DIR}"/projects "$backup_dir/" 2>/dev/null || true
cp -r "${DATA_DIR}"/shared "$backup_dir/" 2>/dev/null || true
cp "${DATA_DIR}"/backend.env "$backup_dir/" 2>/dev/null || true

echo "✓ Backup complete"
