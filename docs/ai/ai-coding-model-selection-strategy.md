# AI Coding Model Selection Strategy

**Context:** Copilot Pro+, local Qwen3.8-27B-FP8, and external DeepSeek V4.1 Flash  
**Reviewed:** 23 September 2026

## Executive Recommendation

Use **GPT-6 Luna as the main Copilot model**, including for planning and substantial coding. Use local Qwen for work it completes reliably; DeepSeek Flash for an external alternative or second review; and GPT-6 Sol for difficult or consequential changes. Select for total effort per reviewed task. Only use services approved for the information's classification.

Repository-specific results, your VS Code model picker, DeepSeek billing channel, and your Copilot billing arrangement remain unverified. [Supported models](https://docs.github.com/en/copilot/reference/ai-models/supported-models), [billing](https://docs.github.com/en/copilot/concepts/billing-and-usage/individuals/billing).

## Recommended Model Set

| Model                   | Role                 | Best use / boundary                                                                                    |
|-------------------------|----------------------|--------------------------------------------------------------------------------------------------------|
| **Qwen3.8-27B-FP8**     | Local executor       | Clear changes, tests, documentation, or local-only work; consider compute and review time.             |
| **GPT-6 Luna**          | Main Copilot model   | Design, repository investigation, plans, coding, and debugging; raise reasoning effort when justified. |
| **DeepSeek V4.1 Flash** | External alternative | A different approach or reviewer, subject to service approval. Its API model ID is `deepseek-flash`.   |
| **GPT-6 Sol**           | Selective escalation | Hard architecture, migrations, security changes, coupled failures, and consequential review.           |

OpenAI reports **66.6% for Luna** and **68.8% for Sol** on DeepSWE 1.1, both at *maximum reasoning*. Luna therefore merits trials on longer repository tasks, but Copilot and your repositories may differ from that evaluation. [OpenAI's evaluation and caveat](https://openai.com/index/introducing-gpt-6-sol-and-luna/).

## Development-Cycle Routing

| Stage                     | Default                                                              | Escalate when / to                                                                                                   |
|---------------------------|----------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| Proposal and requirements | Luna, ordinary or high reasoning                                     | Sol for consequential architecture, security, or unresolved trade-offs.                                              |
| Phase plan                | Luna, high reasoning where needed                                    | Sol if migration boundaries or dependencies remain uncertain.                                                        |
| Phase task plan           | Luna with repository inspection and baseline checks                  | Sol for complex data flow or cross-system contracts; mark the plan Draft if its findings cannot be verified.         |
| Implementation            | Qwen for clear small tasks; Luna for substantial or multi-file tasks | DeepSeek Flash for a different approach; Sol when the design or root cause remains unclear.                          |
| Testing and documentation | Qwen or Luna                                                         | Luna/Sol if test expectations require new design decisions.                                                          |
| Debugging and review      | Luna; use DeepSeek Flash as a different model family when useful     | Sol for high-impact changes or repeated evidence-based failures. Built-in Copilot code review selects its own model. |

## Cost and Evidence

Under **AI-credit billing**, Copilot Pro+ lists **7,000 credits monthly** ($0.01 per credit). An existing annual subscription may use **legacy request-based billing**; check your account before using credit estimates. Included credits are an allowance, not a new charge per request. [GitHub billing](https://docs.github.com/en/copilot/concepts/billing-and-usage/individuals/billing), [legacy note](https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing).

| Illustrative task         | Assumed uncached input / output |    Luna |   Sol |     DeepSeek Flash, direct API |
|---------------------------|--------------------------------:|--------:|------:|-------------------------------:|
| Bounded implementation    |                 20k / 3k tokens | $0.0035 | $0.07 | $0.0048 off-peak; $0.0096 peak |
| Repository-heavy planning |               100k / 10k tokens |  $0.015 | $0.30 |   $0.021 off-peak; $0.042 peak |

These hypothetical examples exclude reasoning tokens, caching, cache writes, tool loops, retries, and review. Copilot dollars indicate **credit-equivalent usage**; DeepSeek figures assume separately billed direct API use. Cache hits may change the ranking. Measure representative tasks before claiming the lowest cost per successful, reviewed task. [Copilot prices](https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing), [DeepSeek prices](https://api-docs.deepseek.com/quick_start/pricing/).

## Models to Skip by Default

| Model or group                                          | Prefer             | Why                                                                                                    |
|---------------------------------------------------------|--------------------|--------------------------------------------------------------------------------------------------------|
| GPT-5.6 Luna and overlapping lightweight Copilot models | GPT-6 Luna         | Luna fills the default role at lower published rates; revisit if your tasks show a specific advantage. |
| GPT-5.6 Sol/Terra and older expensive general models    | GPT-6 Sol          | No distinct routine role in this shortlist.                                                            |
| Claude Sonnet 5, Grok, Gemini, and Kimi models          | Existing shortlist | Keep as candidates for a demonstrated specialty, not permanent daily choices.                          |
| Opus, Fable, and Astra tiers                            | Sol                | Too expensive for this Pro+ strategy without a proven benefit on a specific task.                      |
| DeepSeek V4 Pro                                         | DeepSeek Flash     | Higher listed API rates; no established advantage for your workflow.                                   |

## Reasoning and Escalation

Start Luna at ordinary reasoning, use **high** for uncertain planning or multi-file changes, and try **maximum** on a difficult task when the extra usage is justified. The published 66.6% result used maximum; it is not a claim about Luna's ordinary setting. GitHub warns that higher reasoning and extended context increase credit use. [GitHub model capabilities](https://docs.github.com/en/copilot/reference/ai-models/supported-models).

Give an execution agent one bounded task at a time. After one evidence-based repair attempt, escalate if tests still fail. Stop and report if actual repository state contradicts a validated plan, a contract must change, or a new design decision is required. Use human review and appropriate validation for every consequential change.

## Sources

- [GitHub Copilot models and pricing](https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing)
- [GitHub Copilot supported models](https://docs.github.com/en/copilot/reference/ai-models/supported-models)
- [GitHub Copilot individual billing](https://docs.github.com/en/copilot/concepts/billing-and-usage/individuals/billing)
- [OpenAI GPT-6 Sol and Luna announcement](https://openai.com/index/introducing-gpt-6-sol-and-luna/)
- [DeepSeek API models and pricing](https://api-docs.deepseek.com/quick_start/pricing/)
