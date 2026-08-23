# Live Luna smoke result — 2026-08-23

## Outcome

The current Codex installation successfully launched `gpt-5.6-luna` through LunarMarch after the disposable run was retried with permission for Codex's local state database.

- Model: `gpt-5.6-luna`
- Codex CLI: `0.149.0-alpha.4.1`
- Transport: direct `codex`
- Effort: `high`
- Fixture: disposable `/tmp/lunarmarch-luna-smoke-20260823/project`
- Objective: implement `clamp_count` in `counter.py`
- Luna Builder calls that reached the model: 1
- Declared checks: 5 of 5 passed
- Changed paths: `counter.py` only
- Builder mechanical gate: clear
- Full independent Reviewer: not run in this quick smoke, to keep usage bounded

## Attempt record

1. `builder-1` failed before model execution because the containing app sandbox made Codex's local state database read-only. No report was produced and no project files changed.
2. `builder-2` was retried with the narrow permission required for Codex's local state. Luna implemented the function, all five declared tests passed, and the Builder gate was clear.

The first failure is an environment permission issue, not evidence of a Luna or LunarMarch model failure. The durable run preserved both attempts under `/tmp/lunarmarch-luna-smoke-20260823/run` for inspection.

## Interpretation boundary

This verifies that the installed Codex CLI can resolve and execute `gpt-5.6-luna` through LunarMarch, that the direct worker transport records terminal evidence, and that the mechanical gate works. It does not establish general Luna quality, cost, or reliability. A later full task test should add the independent Reviewer and parent acceptance steps from [live-test.md](live-test.md).
