/**
 * Return a suggestion only when it adds text beyond the message.
 *
 * Validators sometimes write the same detail into both fields, which makes the
 * interface show one long value list twice. A suggestion that repeats the
 * message adds no information, so callers treat it as absent.
 *
 * @param message - Validation message shown to the user.
 * @param suggestion - Suggested fix supplied by the validator.
 * @returns The trimmed suggestion when it adds information, otherwise null.
 */
export function distinctSuggestion(message?: string | null, suggestion?: string | null): string | null {
  const trimmedSuggestion = (suggestion ?? '').trim()
  if (!trimmedSuggestion) {
    return null
  }

  const normalizedSuggestion = normalize(trimmedSuggestion)
  if (!normalizedSuggestion) {
    return null
  }

  const normalizedMessage = normalize(message)
  if (normalizedSuggestion === normalizedMessage || normalizedMessage.includes(normalizedSuggestion)) {
    return null
  }

  return trimmedSuggestion
}

/**
 * Lowercase, collapse whitespace, and drop trailing punctuation so two copies of
 * the same sentence compare equal.
 */
function normalize(value?: string | null): string {
  return (value ?? '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .replace(/[\s.;:,]+$/, '')
    .trim()
}
