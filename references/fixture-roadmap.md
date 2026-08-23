# LunarMarch fixture roadmap

This is the step-by-step queue for the next live tests. Each fixture is a separate evidence unit. Do not start the next one until the current fixture has a clear gate, an independent review, and a short written result.

## Common cadence

Use one worker call at a time when usage matters:

1. Design the disposable fixture and contract. No model usage.
2. Run fake-CLI and deterministic grader checks. No model usage.
3. Run one Luna Builder with the smallest useful task.
4. Inspect the Builder gate and report.
5. Run one independent Luna Reviewer only if the Builder result is worth reviewing.
6. Run a Fixer only when the Reviewer identifies a real defect.
7. Record the result and push the documentation before starting the next fixture.

For context-policy experiments, use the separate evaluator and its checkpointing rules. Do not combine those token-comparison trials with the task-fixture results below.

## Fixture 1 — research synthesis

**Question:** Can a worker reconcile several conflicting local sources into a useful answer without inventing facts?

**Disposable project:** a small folder containing 3–5 short source documents, one deliberately conflicting fact, and a required output template.

**Contract and grader:**

- Read-only Scout or Builder role.
- Output must contain a fact table, source citation for every claim, explicit contradictions, and an “unknown” section.
- Hidden grader checks required facts, source-to-claim mapping, contradiction handling, and absence of unsupported claims.
- Allowed paths contain only the requested answer artifact.

**Success evidence:** all deterministic checks pass, no source or answer files outside scope change, and the Reviewer finds no invented or uncited claim.

## Fixture 2 — multi-file implementation

**Question:** Can a worker change a small API across modules while preserving compatibility?

**Disposable project:** a package with an existing public function, two internal consumers, tests, and a type-check or lint command.

**Contract and grader:**

- Builder owns the implementation files and tests but not unrelated documentation.
- Hidden tests cover old call forms, new behavior, edge cases, and import compatibility.
- Acceptance runs unit tests plus the type or lint check.

**Success evidence:** public and hidden behavior passes, the diff stays within declared modules, and the independent Reviewer checks call sites rather than trusting the Builder report.

## Fixture 3 — diagnosis from incomplete evidence

**Question:** Can a read-only worker identify a root cause without making an unauthorized fix?

**Disposable project:** a small failing project with source code, tests, and incomplete logs containing one misleading symptom.

**Contract and grader:**

- Scout or Reviewer role with no write authority.
- Required report: root cause, evidence chain, ruled-out alternatives, confidence, and a proposed next action.
- Hidden grader checks causal accuracy and non-mutation.

**Success evidence:** the project snapshot is unchanged, the diagnosis identifies the seeded cause, and the report distinguishes facts from hypotheses.

## Fixture 4 — resumable multi-phase work

**Question:** Can LunarMarch resume a multi-phase effort without losing authority boundaries or accepting stale evidence?

**Disposable project:** two dependent tasks, a frozen phase boundary, and a final integration check.

**Contract and grader:**

- Phase 1 Builder completes a bounded change; an independent Reviewer accepts it.
- Freeze the phase, intentionally stop before Phase 2, then resume from the durable run root later.
- Phase 2 depends on the accepted Phase 1 task and must not run against modified frozen evidence.
- Hidden checks verify dependency status, frozen scope, resume behavior, and final integration.

**Success evidence:** restart skips completed work, rejects changed contracts or frozen artifacts, honors dependencies, and reaches a clear Auditor or parent acceptance.

## Fixture 5 — Reviewer/Fixer recovery

**Question:** Can an independent review detect and safely repair a plausible defect?

**Disposable project:** a seeded implementation that passes obvious public tests but fails one edge case.

**Contract and grader:**

- Builder or seed step creates the plausible defect.
- Reviewer must identify the exact failing behavior and provide a reproducer without changing the project.
- Fixer may change only the declared implementation path, must add or update a regression test, and must rerun acceptance commands.
- Parent accepts only after the Fixer gate and a fresh review of the repair.

**Success evidence:** the Reviewer catches the hidden defect, the Fixer changes only authorized files, the regression test passes, and the final acceptance record links the defect, repair, and verification.

## When to stop or change course

Stop after any fixture if the grader cannot distinguish good from bad work, the worker repeatedly violates scope, the evidence is not reproducible, or the next model call would not answer a useful question. Run cheap fake-CLI or OpenCode pilots before spending Luna calls on a new fixture. Keep Luna and DeepSeek results in separate provider series.
