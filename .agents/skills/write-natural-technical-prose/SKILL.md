---
name: write-natural-technical-prose
description: Write and revise non-code text for software work in a natural human voice while preserving technical precision. Use for documentation, proposals, issue and pull-request descriptions, commit messages, review comments, release notes, UI copy, and explanations written by an AI coding assistant. Apply when drafting new prose or editing text that sounds formulaic, generic, or AI-generated, in the language requested by the user.
---

# Write natural technical prose

Write as a knowledgeable colleague explaining something to another person. Favor direct, specific language over a polished but generic style. Preserve the exact meaning of technical claims; naturalness is never a reason to simplify away a condition, caveat, or distinction.

## Work from the facts

1. Identify the reader, purpose, language, and expected format from the task and surrounding material. Match an existing author's voice when editing their text.
2. Before revising, identify the claims that must survive: actors, actions, system boundaries, identifiers, numbers, dates, conditions, exceptions, status, uncertainty, and supporting evidence. Keep this inventory internal unless the user asks for it.
3. Distinguish observed behavior from an inference, a proposal, and a decision. If a fact is unknown, say so where it matters; do not fill the gap with plausible detail.
4. Draft around the reader's question or the actual decision. Put the main point early, then explain the mechanism, consequences, and limits as needed.
5. Reread the result against the source. Check that every important claim is still present and no new claim, stronger promise, changed scope, or altered technical term has slipped in.

## Sound like a person

- Use ordinary words and concrete verbs. Name the component and action instead of relying on abstractions such as “the solution facilitates improved handling.”
- Vary sentence length when it helps the flow. Keep one main idea per paragraph, but do not force every paragraph into the same shape.
- Remove filler openings, self-congratulation, repeated summaries, stock transitions, inflated adjectives, and conclusions that merely restate the heading.
- Prefer a sentence that explains the causal link over a slogan or a neat contrast. Avoid rhetorical questions and symmetrical “not X, but Y” constructions unless the distinction is genuinely needed.
- Use headings, bullets, and tables when they help someone scan or compare information. Do not turn a short explanation into a template with many empty sections.
- Allow a measured first-person voice in comments, reviews, or proposals when it fits the author's role. Do not simulate personal experience, emotion, or authority the writer does not have.
- Follow the requested language and its normal idiom. Avoid literal translations of English technical prose into another language; retain established technical terms where translation would obscure meaning.

## Keep the engineering meaning intact

- Preserve literal names of APIs, functions, files, flags, configuration keys, fields, error messages, versions, and states. Use code formatting for identifiers when it improves recognition.
- Keep modal force: “must,” “should,” “may,” “can,” and “will” carry different commitments. Preserve explicit requirements and the difference between current behavior and proposed behavior.
- State the conditions under which a claim holds. Keep relevant quantities, units, thresholds, examples, and edge cases.
- Attribute evidence accurately. A test passing supports what it tested; it does not prove unrelated behavior. Say “appears,” “likely,” or “we have not verified” when the evidence calls for it.
- Retain links and citations with their claims. Do not invent references or quietly remove a limitation to make the prose smoother.
- Do not edit code, commands, schemas, protocol payloads, or quoted text under this skill unless the user specifically asks. Improve the surrounding prose instead.

## Adapt to the artifact

- For a proposal, make the problem, intended behavior, scope, tradeoffs, and open decisions explicit. Do not present a proposal as implemented.
- For a pull request or issue, say what changed or failed, where, why it matters, and how it was checked. Keep the level of detail proportionate to the change.
- For documentation, lead with what a reader needs to do or understand. Put prerequisites and exceptions next to the step or claim they qualify.
- For UI text, use the user's vocabulary and the available space. Make the next action and its consequence clear.
- For a review, separate a finding from its evidence and suggested fix. Use a direct, collegial tone without weakening a concrete problem.

## Revision test

Read the draft once for voice and once for accuracy. Ask: Would a colleague say this naturally? Can the reader tell exactly what happens, when, and in which system? Has any uncertainty become certainty? Are all identifiers and constraints still correct? Revise until both voice and meaning hold.

Example:

> Formulaic: “The proposed enhancement will leverage the reconciliation API to facilitate a seamless browsing experience for end users.”
>
> Natural and precise: “Shape Shifter will request classifier values through the Authority Service's reconciliation API. Reviewers can search and filter the returned values before choosing one. The proposal does not add direct database access.”

Use the second form only when those details are actually supported by the task. Specificity must come from evidence, not invention.
