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

Gate results contain `clear`, `errors`, `warnings`, and the exact frozen changed paths. `clear: true` only establishes objective integrity. A Reviewer and parent still judge engineering meaning.

## Result summary format

Worker and parent-facing results should stay short and readable. Start with the model, effort or variant, transport, attempts, gate or quality result, and token usage. When available, report `input_tokens`, `cached_input_tokens`, `uncached_input_tokens`, `output_tokens`, `reasoning_tokens`, and `total_tokens`. Use `not reported` when the provider does not expose usage. Never use the Unicode em dash character (U+2014); use ordinary punctuation or a normal hyphen.
