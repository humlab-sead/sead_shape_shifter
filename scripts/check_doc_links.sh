#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failed=0

while IFS= read -r document; do
    [[ -f "$repo_root/$document" ]] || continue

    while IFS= read -r link; do
        [[ -n "$link" ]] || continue
        case "$link" in
            \#*|http://*|https://*|mailto:*|/*) continue ;;
        esac

        target="${link%%\?*}"
        target="${target%%\#*}"
        [[ -n "$target" ]] || continue

        document_dir="$(dirname "$repo_root/$document")"
        resolved="$document_dir/$target"
        if [[ ! -e "$resolved" ]]; then
            printf 'Broken link: %s -> %s\n' "$document" "$link" >&2
            failed=1
        fi
    done < <(perl -ne 'while (/\]\(([^)]+)\)/g) { print "$1\n"; }' "$repo_root/$document")
done < <(
    {
        printf '%s\n' README.md
        # Git pathspec wildcards also cross directory separators, so "docs/*.md"
        # alone would reach into docs/proposals/. Keep only the documents that
        # sit directly in docs/ and deployment/container/.
        git -C "$repo_root" ls-files 'docs/*.md' 'deployment/container/*.md' \
            | awk -F/ 'NF == 2 || ($1 == "deployment" && NF == 3)'
    } | sort -u
)

if [[ "$failed" -ne 0 ]]; then
    exit 1
fi

printf 'Documentation links are valid.\n'
