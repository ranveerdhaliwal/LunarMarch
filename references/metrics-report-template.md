# LunarMarch metrics report template

Use this template when another chat completes a LunarMarch run. Keep the report in this repository, but keep disposable run state and secrets outside the source tree.

## Which file should I use?

- One Builder, Reviewer, or research run: copy this template to `references/live-test-results-YYYY-MM-DD.md`.
- A repeated comparison of context, models, prompts, or transports: create `evals/<series>/results/YYYY-MM-DD-<short-name>.md`. Add machine-readable per-trial data beside it as JSON or CSV.
- A durable run's raw evidence stays in its separate run root. Link that path from the report instead of copying `state.json`, prompts, credentials, or full logs into the repository.

Useful existing examples:

- [Live Luna smoke](live-test-results-2026-08-23.md) shows a concise Builder, Reviewer, gate, and acceptance report.
- [Context efficiency result](../evals/context-efficiency/results/2026-08-22-contract-v-padding.md) shows aggregate token metrics, per-trial rows, controls, and limits.
- [Testing and evaluation record](testing-and-evaluation.md) explains how the individual reports fit together.

## Copyable report

```markdown
# <short result title>: <YYYY-MM-DD>

## Outcome

- Status: <complete | partial | blocked | failed>
- Model: <model identifier>
- Transport: <codex | opencode | native | other>
- Effort or variant: <value | not applicable>
- Task or fixture: <short name>
- Parent decision: <accepted | needs fixer | not accepted | not applicable>
- Attempts: <number, including retries>
- Quality or gate result: <short result, for example 5/5 checks and gate clear>

## Token usage

| Metric | Value |
|---|---:|
| Input tokens | <number or not reported> |
| Cached input tokens | <number or not reported> |
| Uncached input tokens | <number or not reported> |
| Output tokens | <number or not reported> |
| Reasoning tokens | <number or not reported> |
| Total tokens | <number or not reported> |
| Uncached input plus output | <uncached input tokens + output tokens, or not reported> |

## Evidence

- Duration: <seconds or not reported>
- Checks: <passed>/<declared>, with the command or grader name
- Changed paths: <paths or none>
- Reviewer: <role, model, and result>
- Raw run root: `<path>`
- Commit or fixture fingerprint: `<hash or not applicable>`

## Findings and limits

- <one or two concise findings>
- <what this result does not prove>
```

## Rules for trustworthy metrics

1. Record the model, transport, effort or variant, and attempt count before interpreting quality.
2. Use provider-reported token fields. Never estimate tokens from character count or prose length.
3. Write `not reported` when telemetry is unavailable. Do not turn missing usage into zero.
4. Keep Luna, DeepSeek, and other provider series separate unless the comparison was predeclared and uses the same fixture, grader, tools, and acceptance rule.
5. Include retries, failures, timeouts, and infrastructure problems in the attempt count.
6. Separate mechanical facts from semantic judgment. A clear gate is evidence, not automatic acceptance.
7. Do not commit API keys, full conversation history, private prompts, or unbounded logs.
8. Do not use the Unicode em dash character (U+2014). Keep the report short and human-readable.
