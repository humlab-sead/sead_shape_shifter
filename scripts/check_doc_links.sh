#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failed=0

# Print the lines of a file that are not inside a fenced code block. Markdown
# treats fenced content as opaque, so link syntax shown as an example inside a
# fence is documentation, not a link, and cannot be a broken link. A fence opens
# with three or more backticks or tildes indented by at most three spaces, and
# closes with the same character at an equal or greater length. An unclosed
# fence runs to the end of the file.
strip_fenced_blocks() {
    awk '
        {
            line = $0
            sub(/^ {0,3}/, "", line)
            if (line ~ /^(`{3,}|~{3,})/) {
                ch = substr(line, 1, 1)
                len = 0
                while (substr(line, len + 1, 1) == ch) {
                    len++
                }
                if (!in_fence) {
                    in_fence = 1
                    fence_char = ch
                    fence_len = len
                    next
                }
                if (ch == fence_char && len >= fence_len) {
                    in_fence = 0
                    next
                }
            }
            if (!in_fence) {
                print
            }
        }
    ' "$1"
}

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
    done < <(strip_fenced_blocks "$repo_root/$document" | perl -ne 'while (/\]\(([^)]+)\)/g) { print "$1\n"; }')
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
