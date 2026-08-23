# Live Luna evaluation: 2026-08-22

## Outcome

The first model-backed Task run completed and was semantically accepted after a fresh read-only Luna review.

- Model: `gpt-5.6-luna`, high effort
- Fixture: disposable `/tmp/lunarmarch-live/project`
- Objective: implement `clamp_count`
- Final checks: 5 of 5 passed
- Final Builder gate: clear
- Reviewer gate: clear, no project changes
- Durable run status: complete
- Offline regression suite after fixes: 18 tests passed

## Attempt record

1. `builder-1` failed before model execution because the launcher combined two mutually exclusive Codex CLI options. The terminal and gate preserved the failure.
2. `builder-2` reached the corrected command but the containing app sandbox denied the nested Codex process access to its state database. The launch was retried with narrow permission for the disposable fixture.
3. `builder-3` implemented the function and passed all five checks. Its gate correctly rejected an undeclared Python cache artifact exposed by inconsistent Git snapshot filtering.
4. `builder-4` independently confirmed the implementation with five passing checks. Its gate was clear after cache filtering was corrected.
5. `reviewer-1` remained read-only, reran the five declared tests, added equal-bound and negative-value probes, reported no defects, and received a clear gate. The parent inspected the implementation and accepted the task.

## Changes driven by the evaluation

- Writer launches now use `--approve-for-me` without the conflicting explicit sandbox flag.
- Read-only launches retain an explicit read-only sandbox and never receive automatic write approval.
- Git and filesystem snapshots now consistently ignore `__pycache__`, `.pyc`, and `.pyo` artifacts.
- Regression tests cover both transport policies and Git-based Python cache filtering.

The disposable run remains under `/tmp/lunarmarch-live` for local inspection. It is evidence from one bounded smoke test, not a general quality benchmark for Luna.
