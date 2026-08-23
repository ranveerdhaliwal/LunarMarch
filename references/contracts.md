# Contracts and evidence

Use `schemas/task-contract.schema.json` as the wire format. Contracts are immutable after registration.

Required semantics:

- `task_id`: stable identifier within the run.
- `phase`: phase identifier; use `main` for a single task.
- `objective`: one independently reviewable outcome.
- `role_hint`: expected first worker role.
- `risk`: `trivial`, `routine`, `medium`, or `high`.
- `allowed_paths`: exact path prefixes or glob patterns a writer may change. Read-only roles ignore this field and must produce no project changes.
- `acceptance_commands`: commands that mechanically support acceptance. They run only when `launch --run-checks` is explicit.
- `requirements`: semantic acceptance criteria.
- `inputs`: existing files or artifacts the worker should consume.
- `non_goals`: explicit exclusions that prevent scope absorption.
- `depends_on`: task IDs that must be semantically accepted first.
- `protected_invariants` (optional): known security, compatibility, or behavioral properties that must survive the task.
- `invariant_commands` (optional): focused deterministic probes for protected invariants. LunarMarch records their baseline result when reserving an attempt and reruns them as launcher checks.
- `max_reviewer_attempts` (optional): a task-local Reviewer attempt cap from one through eight. A normal change task should usually use two: initial review and post-Fixer review.

An attempt contains:

```text
prompt.md
baseline.json
reservation.json
worker.log
report.md
terminal-scope.json
terminal-project.json
terminal.json
gate.json
```

The reservation binds contract, prompt, role, transport, model, effort or variant, sandbox policy, and baseline by hash. The terminal binds the frozen post-attempt source movement, full project snapshot, and command results. Gate verification detects mutation of these artifacts, undeclared writes, read-only-role writes, missing reports, worker failure, and failed or missing acceptance commands.

Invariant commands should be short and deterministic. Their baseline runs before the source snapshot is captured. A passing baseline followed by a failed post-work result is a protected-invariant regression and fails the gate, even when the changed file is inside `allowed_paths`. A failing baseline remains visible as a warning, not proof that the worker caused it.

Gate results contain `clear`, `errors`, `warnings`, and the exact frozen changed paths. `clear: true` only establishes objective integrity. A Reviewer and parent still judge engineering meaning.

## Result summary format

Worker and parent-facing results should stay short and readable. Start with the model, effort or variant, transport, attempts, gate or quality result, and token usage. When available, report `input_tokens`, `cached_input_tokens`, `uncached_input_tokens`, `output_tokens`, `reasoning_tokens`, `total_tokens`, and `uncached_input_plus_output`. Use `not reported` when the provider does not expose usage. Never use the Unicode em dash character (U+2014); use ordinary punctuation or a normal hyphen.
