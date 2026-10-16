#!/usr/bin/env bash
# Report broken relative Markdown links in the given files.
#
# Usage: check_relative_links.sh <file> [<file>...]
#
# Resolves each "](target)" link against the file's own directory, matching the
# repository checker in scripts/check_doc_links.sh. Skips fragments, absolute
# paths, and external schemes. Exits non-zero when any link is broken.

set -euo pipefail

if [[ $# -eq 0 ]]; then
    printf 'usage: check_relative_links.sh <file> [<file>...]\n' >&2
    exit 2
fi

failed=0

for document in "$@"; do
    if [[ ! -f "$document" ]]; then
        printf 'Missing file: %s\n' "$document" >&2
        failed=1
        continue
    fi

    document_dir="$(dirname "$document")"

    while IFS= read -r link; do
        [[ -n "$link" ]] || continue

        case "$link" in
            \#*|http://*|https://*|mailto:*|/*) continue ;;
        esac

        target="${link%%\?*}"
        target="${target%%\#*}"
        [[ -n "$target" ]] || continue

        if [[ ! -e "$document_dir/$target" ]]; then
            printf 'Broken link: %s -> %s\n' "$document" "$link" >&2
            failed=1
        fi
    done < <(perl -ne 'while (/\]\(([^)]+)\)/g) { print "$1\n"; }' "$document")
done

if [[ "$failed" -ne 0 ]]; then
    exit 1
fi

printf 'Relative links are valid.\n'
