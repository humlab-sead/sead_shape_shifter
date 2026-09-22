#!/usr/bin/env bash
# Download the UCanAccess JDBC driver JARs into <container>/lib/ucanaccess.
# Required for MS Access (.mdb/.accdb) data sources.
#
# This is the single installed copy of the dependency. A standalone image build
# reads it beside the Containerfile, and a workdir build stages it into the
# repository-root build context (see scripts/build.sh). Local development runs
# that start from the repository root read lib/ucanaccess there, so run this
# script from the repository checkout and copy the result when a local run needs
# it. The directory stays inside the checkout on purpose: it is a build
# dependency, not runtime configuration or mutable state, and its relocation is
# a separate change.
set -euo pipefail

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET_DIR="$ROOT_DIR/lib/ucanaccess"

if ! command -v unzip >/dev/null 2>&1; then
  echo "error: unzip is required" >&2
  exit 1
fi

download_tool=""
if command -v curl >/dev/null 2>&1; then
  download_tool="curl"
elif command -v wget >/dev/null 2>&1; then
  download_tool="wget"
else
  echo "error: curl or wget is required" >&2
  exit 1
fi

mkdir -p "$ROOT_DIR/lib"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

echo "Downloading UCanAccess..."
if [ "$download_tool" = "curl" ]; then
  curl -L -o "$tmp_dir/ucanaccess.zip" "https://sourceforge.net/projects/ucanaccess/files/latest/download"
else
  wget -O "$tmp_dir/ucanaccess.zip" "https://sourceforge.net/projects/ucanaccess/files/latest/download"
fi

unzip -q "$tmp_dir/ucanaccess.zip" -d "$tmp_dir/extracted"
download_folder="$(ls "$tmp_dir/extracted" | head -n 1)"

# Replace the installed copy only after the download and extraction succeed, so a
# failed download leaves the existing dependency in place.
rm -rf "$TARGET_DIR"
mkdir -p "$ROOT_DIR/lib"
mv "$tmp_dir/extracted/${download_folder}" "$TARGET_DIR"

echo "UCanAccess installed in $TARGET_DIR"
