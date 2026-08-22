# LunarMarch

LunarMarch is a Luna-first orchestration skill for research, focused coding tasks, independent review, and resumable multi-phase projects.

```text
parent authority
  ├─ Scout fan-out (read-only research)
  ├─ Builder → Reviewer → Fixer loop
  ├─ Sentinel (long waits and monitoring)
  └─ phase barrier → Auditor → parent acceptance
                         │
                  objective integrity gate
```

GPT-5.6 Luna performs the high-volume work. The parent model keeps decomposition, ambiguity resolution, risk decisions, and final acceptance. Deterministic helpers bind contracts and prove lifecycle, hashes, source movement, declared write scope, and acceptance-command results.

## Why another orchestrator?

Existing projects each solve a valuable portion of the problem. LunarMarch combines their strongest general ideas into a small Codex-native system:

- immutable attempts and objective gates for trustworthy long runs;
- risk-aware Luna routing and independent reviews;
- scalable read-only fan-out with bounded concurrency;
- explicit lifecycle, retry budgets, recovery, and phase barriers;
- one contract format shared by research and implementation.

See [references/influences.md](references/influences.md) for the projects studied and the design boundary.

## Current status

Version `0.1.0` includes the skill, contract schema, Luna `codex exec` transport, durable run state, scope snapshots, integrity gates, recovery-safe status, examples, and offline tests. The first model-backed Task evaluation completed successfully on 2026-08-22; see [references/live-test-results-2026-08-22.md](references/live-test-results-2026-08-22.md).

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

The launcher requires an installed, authenticated Codex CLI with access to `gpt-5.6-luna`. Run `python3 -m unittest discover -s tests -v` for offline verification. CI repeats compilation, the command-interface smoke check, and the full offline suite on Python 3.11–3.13.

The model-backed procedure is documented in [references/live-test.md](references/live-test.md). It uses a disposable intentionally-failing fixture, a Luna Builder, a fresh Luna Reviewer, objective gates, and explicit parent acceptance.

## Installation as a skill

For every local Codex chat:

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

## License

MIT
