import { describe, expect, it } from 'vitest'
import { distinctSuggestion } from '../validationSuggestion'

describe('distinctSuggestion', () => {
  it('keeps a suggestion that adds information', () => {
    const suggestion = distinctSuggestion(
      "2 foreign key value(s) not found in 'customers' (a, b)",
      'Correct the local values or check that the referenced entity exposes the matching keys.'
    )

    expect(suggestion).toBe('Correct the local values or check that the referenced entity exposes the matching keys.')
  })

  it('drops a suggestion that repeats the message', () => {
    expect(distinctSuggestion('Natural keys are not unique', 'Natural keys are not unique.')).toBeNull()
  })

  it('drops a suggestion already quoted in the message', () => {
    expect(distinctSuggestion('3 duplicate key(s) found. Sample: a, b', '3 duplicate key(s) found')).toBeNull()
  })

  it('drops blank suggestions', () => {
    expect(distinctSuggestion('Message', '   ')).toBeNull()
    expect(distinctSuggestion('Message', null)).toBeNull()
    expect(distinctSuggestion('Message', undefined)).toBeNull()
  })

  it('returns the trimmed suggestion text when it is distinct', () => {
    expect(distinctSuggestion('Message', '  Check the loader.  ')).toBe('Check the loader.')
  })
})
