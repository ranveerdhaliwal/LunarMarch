---
name: lunar-march
description: Orchestrate research, bounded implementation, review, recovery, and long-running multi-part projects with Luna-first or OpenCode workers, durable contracts, and objective integrity gates. Use when work benefits from explicit delegation or resumable multi-step execution; do not use for a single simple action that the current agent can complete directly.
license: MIT
metadata:
  short-description: Luna-first durable task orchestration
---

# LunarMarch

Use Luna as the default high-volume workforce while the parent retains authority, decomposition, consequential judgment, and final acceptance. OpenCode is the supported provider-neutral transport for DeepSeek and future inexpensive workers; changing transport never weakens contracts, gates, or review requirements.

## Output contract

- Keep worker reports and parent summaries concise, human-readable, and evidence-first.
- Never use the Unicode em dash character (U+2014) in any LunarMarch writing. Use a comma, colon, parentheses, or a normal hyphen instead.
- Include token usage whenever the transport reports it: input, cached input, uncached input, output, reasoning, total tokens, and uncached input plus output. If a provider does not expose usage, write `not reported` rather than guessing.
- Put the model, effort or variant, transport, attempt count, quality or gate result, total tokens, and uncached input plus output near the start of a result summary.

When asked to install, share, or use LunarMarch from another chat, read [references/installation.md](references/installation.md).

## Select the smallest mode

- **Quick:** one bounded worker result with parent verification.
- **Research:** parallel read-only Scouts with distinct questions and one synthesis boundary.
- **Task:** Builder → independent Reviewer → Fixer when needed → parent decision.
- **March:** phased, resumable execution for several dependent tasks or a long-running project.

Read [references/modes.md](references/modes.md) when choosing or operating a mode. For Task or March, also read [references/contracts.md](references/contracts.md). Read [references/long-runs.md](references/long-runs.md) only for resumable runs, interruption, recovery, or phase barriers.

## Authority and evidence

- The parent owns scope, task boundaries, risk classification, acceptance, escalation, and user communication.
- Workers receive one role and one bounded contract. They never approve their own mutations or spawn workers.
- Python records facts it can prove: immutable hashes, attempt lifecycle, frozen source movement, write-boundary violations, and command exit codes. A clear mechanical gate is safe to interpret, not semantic acceptance.
- Every mutation requires review from a context that did not implement it. Use objective checks and escalate when repeated Luna attempts expose correlated uncertainty.
- Preserve authorization boundaries. Delegation does not authorize destructive operations, external writes, purchases, deployment, or scope expansion.

## Worker routing

Luna is the default worker. Use `medium` for routine research and monitoring, `high` for implementation and review, and `xhigh` only for difficult adjudication. Do not default every lane to `max`.

Prefer native delegated tasks when the active Codex surface can explicitly bind `gpt-5.6-luna` and the required sandbox. Otherwise use the external launcher:

```bash
python3 <skill>/scripts/lunarmarch.py launch \
  --run-root <run> --task-id <task> --role <role> --run-checks
```

The external launcher pins the model and reasoning effort and disables nested delegation. It is a fallback transport, not a semantic shortcut.

For DeepSeek or another OpenCode model, read [references/providers.md](references/providers.md), then launch with `--transport opencode --model provider/model`. Keep credentials in the provider or OpenCode credential store, never in contracts, prompts, run state, or repository files.

For native workers, default to no inherited conversation and send a compact, resolved task contract with exact file or artifact paths. Shared workspace files are the context plane; worker prompts are the control plane. Pass a small recent-turn window only when uncaptured conversational nuance is necessary. Pass full history only when the task genuinely depends on the conversation itself. Workers do not receive later parent discoveries automatically; send material updates explicitly.

Read [references/routing.md](references/routing.md) before premium escalation, concurrency above two writers, or transport fallback. Read [references/roles.md](references/roles.md) when authoring a worker packet.

When changing context, model, effort, or routing policy based on performance claims, read [references/context-evaluation.md](references/context-evaluation.md) and measure representative repeated trials before adopting the change.

## Durable run interface

Create run state outside the source tree when practical:

```bash
python3 <skill>/scripts/lunarmarch.py init \
  --project-root <project> --run-root <run> --goal "<goal>" --mode march

python3 <skill>/scripts/lunarmarch.py add-task \
  --run-root <run> --spec <task-contract.json>

python3 <skill>/scripts/lunarmarch.py status --run-root <run>
```

After a clean mechanical gate, inspect only the bounded worker report and decisive evidence. Record semantic acceptance explicitly:

```bash
python3 <skill>/scripts/lunarmarch.py accept \
  --run-root <run> --task-id <task> --attempt <attempt-dir>
```

Never edit `state.json`, reservations, terminal records, gates, or frozen scope artifacts by hand.

For a first model-backed evaluation, follow [references/live-test.md](references/live-test.md). It uses a disposable project and keeps live usage out of the offline test suite.

When auditing LunarMarch itself or interpreting its published evidence, read [references/testing-and-evaluation.md](references/testing-and-evaluation.md). Keep fixture-specific findings distinct from general model claims.

## Stop conditions

Continue until the requested outcome is complete or a real boundary is reached. Stop for missing authority, unsafe/destructive permission, inaccessible required systems, conflicting governing requirements, an unknown active writer, or exhausted retry/escalation budget. Do not turn ordinary worker failure into a human blocker while a safe bounded route remains.
