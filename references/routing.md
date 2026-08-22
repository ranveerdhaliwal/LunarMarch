# Routing and escalation

## Default ladder

| Work | Model | Effort | Sandbox |
|---|---|---:|---|
| Monitoring, clerical synthesis | Luna | medium | read-only |
| Repository/web research | Luna | medium or high | read-only |
| Bounded implementation | Luna | high | workspace-write |
| Independent review | fresh Luna | high | read-only |
| Difficult adjudication | Luna | xhigh | read-only |
| Consequential unresolved decision | Terra or Sol | high | read-only unless separately authorized |

Use measured evidence to change these defaults. `max` is not a ceremonial quality switch.

## Risk ladder

- **Trivial:** one worker and parent verification.
- **Routine:** Builder, targeted checks, proportionate independent Luna review.
- **Medium:** Scout when scope is unclear, Builder, Luna High review, Luna XHigh only for material disagreement.
- **High:** research and decomposition first, isolated writer, independent review, premium review for unresolved high-impact risk. Keep destructive/live actions behind explicit user authorization.

## Concurrency

Read-only Scouts may fan out when their questions are distinct. Start with at most four and expand only when the evidence map justifies it. Start with one writer; allow two only in separate worktrees with non-overlapping ownership. Never permit overlapping writers in one checkout.

## Escalate when

- two bounded Luna attempts fail the same criterion;
- implementation and review disagree on a material claim;
- evidence remains ambiguous after targeted verification;
- the task crosses architecture, security, data migration, payments, or release boundaries;
- the parent must make a product or authority decision.

Escalation changes the consumer or decision-maker; it does not retroactively validate missing evidence.

## Transport

Prefer native tasks when the host proves the requested model and sandbox were applied. Use external `codex exec` when native routing cannot bind Luna or when larger fan-out needs an independent process pool. Record requested identity as a fact about launch configuration, not proof of remote runtime identity unless session records establish it.
