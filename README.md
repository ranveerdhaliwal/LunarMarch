# LunarMarch

LunarMarch is a Luna-first, provider-aware orchestration skill for research, focused coding tasks, independent review, and resumable multi-phase projects.

```text
parent authority
  ├─ Scout fan-out (read-only research)
  ├─ Builder → Reviewer → Fixer loop
  ├─ Sentinel (long waits and monitoring)
  └─ phase barrier → Auditor → parent acceptance
                         │
                  objective integrity gate
```

GPT-5.6 Luna remains the in-house default. The same durable core can now launch DeepSeek and other provider models through OpenCode. The parent model keeps decomposition, ambiguity resolution, risk decisions, and final acceptance; deterministic helpers bind contracts and prove lifecycle, hashes, source movement, declared write scope, and acceptance-command results regardless of transport.

## Why another orchestrator?

Existing projects each solve a valuable portion of the problem. LunarMarch combines their strongest general ideas into a small transport-neutral core with first-class Codex integration:

- immutable attempts and objective gates for trustworthy long runs;
- risk-aware Luna routing and independent reviews;
- scalable read-only fan-out with bounded concurrency;
- explicit lifecycle, retry budgets, recovery, and phase barriers;
- one contract format shared by research and implementation.

See [references/influences.md](references/influences.md) for the projects studied and the design boundary.

## Current status

Version `0.2.0` includes the skill, contract schema, Codex and OpenCode worker transports, durable run state, scope snapshots, integrity gates, checkpointed evaluations, recovery-safe status, examples, and offline tests. The first model-backed Task evaluation completed successfully on 2026-08-22; a one-call Luna smoke also succeeded on 2026-08-23. See [the first Task result](references/live-test-results-2026-08-22.md) and [the latest smoke result](references/live-test-results-2026-08-23.md). The complete verification record, including all 35 automated tests, live trials, invalidated diagnostics, evaluator hardening, limitations, and reproduction commands, is in [references/testing-and-evaluation.md](references/testing-and-evaluation.md).

## Quick start

```bash
python3 scripts/lunarmarch.py init \
  --project-root /absolute/project \
  --run-root /absolute/project-run \
  --goal "Add cursor pagination" \
  --mode task

python3 scripts/lunarmarch.py add-task \
  --run-root /absolute/project-run \
  --spec examples/task-contract.json

python3 scripts/lunarmarch.py launch \
  --run-root /absolute/project-run \
  --task-id users-pagination \
  --role builder \
  --run-checks
```

The default path requires an installed, authenticated Codex CLI with access to `gpt-5.6-luna`. Run `python3 -m unittest discover -s tests -v` for offline verification. CI repeats compilation, the command-interface smoke check, and the full offline suite on Python 3.11-3.13.

To use DeepSeek through OpenCode instead:

```bash
python3 scripts/lunarmarch.py launch \
  --run-root /absolute/project-run \
  --task-id users-pagination \
  --role builder \
  --transport opencode \
  --model deepseek/deepseek-v4-flash \
  --run-checks
```

OpenCode stores the DeepSeek credential; LunarMarch never reads or records the API key. LunarMarch workers require that saved OpenCode credential because their child environment excludes API keys. See [references/providers.md](references/providers.md) for setup, the Sol-orchestrator/DeepSeek-worker design, permission differences, and how to add another transport.

The OpenCode adapter is covered by fake-CLI integration and permission-policy tests. No paid DeepSeek call was made in this repository yet; the first authenticated smoke test remains pending until a key and OpenCode installation are available.

DeepSeek can also be configured directly as a Codex model using DeepSeek's official Codex integration. After that one-time local setup, pass `--transport codex --model deepseek-v4-flash` to LunarMarch. This is useful for a native Codex smoke test, while the OpenCode transport remains the better default for provider-neutral worker routing. The direct setup changes global `~/.codex` configuration, so review it and preserve the generated backup before switching back to Luna.

The model-backed procedure is documented in [references/live-test.md](references/live-test.md). It uses a disposable intentionally-failing fixture, a Luna Builder, a fresh Luna Reviewer, objective gates, and explicit parent acceptance.

## Measured context policy

Native workers default to no inherited conversation plus a compact resolved contract and exact workspace paths. A bundled evaluator measures whether that saves usage without degrading task quality. It uses opaque trial identities, counterbalanced order, deterministic hidden graders, authoritative terminal usage telemetry, and completeness checks. In the first clean six-pair case study, compact context used 17.9% fewer cumulative tokens; all code-behavior checks passed, but one compact worker created an undeclared report file, producing mean overall quality of 98.33 versus 100. See [the result](evals/context-efficiency/results/2026-08-22-contract-v-padding.md) and [the evaluation protocol](references/context-evaluation.md). New direct Codex worker runs also persist token fields in their terminal records. Use `not reported` when a provider does not expose usage.

### What the evidence currently says

| Question | Current evidence |
|---|---|
| Does compact resolved context save usage? | Yes on the bundled fixture: 17.9% fewer total tokens and 30.0% fewer uncached input tokens. |
| Did compact context produce incorrect code? | No. All hidden behavior, public tests, and compilation checks passed in all 12 trials. |
| Was overall execution quality identical? | No. One compact trial created an undeclared report file, so mean overall quality was 98.33 versus 100. |
| Is compact context proven universally better? | No. This is a clean but exploratory single-fixture result. |
| Why keep compact as the default? | It met the predeclared two-point quality tolerance while materially reducing usage; LunarMarch still requires complete task contracts and objective review. |

### Verification performed

- 23 orchestration and transport tests cover immutable contracts, attempt lifecycle, write boundaries, acceptance evidence, independent review, phase freezing, Codex/OpenCode launch policies, environment isolation, bounded timeouts, recovery safety, and installation behavior.
- 12 evaluator tests cover opaque trial identities, balanced ordering, packet equivalence, terminal usage parsing, malformed grader handling, missing-trial and missing-telemetry rejection, sealed checkpoint/resume, tamper rejection, end-to-end scoring, and source-repository isolation.
- One live Task evaluation exercised Builder, Reviewer, objective gates, retry recording, and parent acceptance.
- One blinded context evaluation ran 12 Luna workers in six matched pairs from a clean commit.
- An independent Luna audit found eight evaluator defects and one order-balance defect; all were corrected and covered by regression tests before the published run.

For the exact test inventory and what each check proves, read [references/testing-and-evaluation.md](references/testing-and-evaluation.md).

### Expanding to 3-5 additional fixtures

A credible next set should cover research synthesis, multi-file implementation, diagnosis from incomplete evidence, resumable multi-phase work, and reviewer/fixer recovery. It no longer needs to happen in one expensive session: create the full immutable manifest once, run one or two trials with `--max-new-trials`, then continue later with `--resume`. A useful cadence is one fixture design session followed by six two-trial checkpoints. Partial checkpoints are preserved but cannot support a quality claim until the balanced roster is complete. See [references/testing-and-evaluation.md](references/testing-and-evaluation.md#bite-sized-execution-plan).

The concrete fixture contracts, graders, success evidence, and stop conditions are written out in [references/fixture-roadmap.md](references/fixture-roadmap.md).

## Installation as a skill

For every local Codex or OpenCode chat:

```bash
python3 scripts/install_skill.py --scope user
```

For chats working inside one repository:

```bash
python3 scripts/install_skill.py --scope repo --repo-root /absolute/project
```

See [references/installation.md](references/installation.md) for discovery behavior, safe replacement, explicit invocation, and future plugin distribution.

## Safety model

LunarMarch does not grant authority. Read-only roles use a read-only sandbox; write roles require declared owned paths; destructive and external actions remain subject to the parent and user’s normal authorization boundary. Mechanical PASS never means the engineering is accepted.

## Contributing

Contributions are welcome, especially small deterministic fixtures, transport adapters, permission hardening, and independent reproductions. Contributors do not need to fund a full live benchmark: fixture design, hidden graders, fake-CLI tests, and leakage audits are useful standalone pull requests. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
