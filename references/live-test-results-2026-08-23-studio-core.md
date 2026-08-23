# Studio Core durability march: 2026-08-23

## Outcome

- Status: complete; 2 phases and 9 tasks accepted
- Model: `gpt-5.6-luna`, Codex transport, mostly high effort
- Scope: durable API jobs, restart recovery, retention, progress storage, and invalid source-ID hardening
- Final gates: Ruff passed; 101 tests passed with 8 warnings
- Attempts: 28 total; 22 reached a model and succeeded; 6 failed before model execution
- Raw run root: `/tmp/studio-core-lunarmarch-20260823`
- H3, Music 3, ML, CUDA, and GPU workloads were excluded

## Usage

| Metric | Value |
|---|---:|
| Input tokens | 11,058,106 |
| Cached input tokens | 9,962,496 |
| Uncached input tokens | 1,095,610 |
| Output tokens | 148,520 |
| Reasoning tokens | 89,652 |
| Total tokens | 11,206,626 |
| Uncached input plus output | 1,244,130 |
| Productive worker wall time | 3,558 s |
| End-to-end run time | about 87 min |

Cached input was 90.1% of input. Report both total and uncached usage; total tokens alone substantially overstates fresh context consumption.

| Role | Calls | Total tokens | Uncached plus output | Wall time |
|---|---:|---:|---:|---:|
| Builder | 4 | 4,096,978 | 319,186 | 1,097 s |
| Fixer | 4 | 1,673,606 | 147,334 | 480 s |
| Reviewer | 12 | 4,117,062 | 592,198 | 1,510 s |
| Auditor | 2 | 1,318,980 | 185,412 | 471 s |

## Quality evidence

- Independent review found four actionable defects before acceptance: non-JSON error storage, swapped SQL insert values, a conditional-update race, and empty exceptions being marked complete.
- A phase auditor found an inherited invalid-source-ID HTTP 500; a separate repair phase changed it to a tested HTTP 400.
- Parent adjudication rejected out-of-contract audit findings and restored upload hardening after a fixer followed an incorrect compatibility concern.
- Every model-reaching attempt exited successfully. Both frozen phase snapshots matched their audit snapshots.

## Findings

1. Quality improved materially, but this run was not token-efficient enough to claim a win over a Sol-only control. Reviewer and auditor calls consumed 48.5% of total tokens and 62.5% of uncached-input-plus-output usage.
2. Repeated stale-snapshot reviews were the main avoidable cost. Prefer one same-task Fixer followed by one fresh review of the latest source.
3. Small tasks can still carry large repository-context cost. The two-file API repair used 1,888,163 total tokens, despite only 81,004 uncached input tokens.
4. Path-level gates cannot detect an unrelated regression inside an allowed file. Baseline-aware semantic review and parent inspection remain necessary.
5. Read-only Codex workers may fail before model execution when Codex cannot write its state database. The project can remain read-only while Codex state receives narrowly scoped write access.
6. Read-only workers often report tests as unverified because caches and temp directories are unwritable, even when launcher-run checks pass. Reports should distinguish worker-local checks from authoritative launcher checks.
7. The OpenCode fallback exposed two adapter issues: writable XDG temp/state locations are needed, and `--file` can consume the trailing instruction as another filename unless option parsing is terminated or reordered.

## Interpretation boundary

This is a strong workflow and defect-detection case, not a controlled model-efficiency comparison. A Sol-only run was not performed on the same frozen fixture, so no relative cost or quality claim is justified.
