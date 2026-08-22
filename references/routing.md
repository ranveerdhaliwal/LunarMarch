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

## Context inheritance

Native subagents have separate context windows. Depending on the host, they may receive all parent turns, a bounded recent window, or no surrounding turns. They share workspace files but do not continuously share the parent's later conversation.

Use the smallest sufficient context:

- Default to no inherited turns plus a compact resolved contract, exact paths, and required evidence.
- Use a small recent-turn window only when recent intent has not yet been captured in durable artifacts.
- Use full-history inheritance only for conversation-dependent interpretation where compression would remove material ambiguity.
- Send new facts explicitly after launch; never assume a worker learned them from the parent automatically.
- Keep worker reports bounded because returned prose also consumes parent synthesis context.

Do not confuse `no inherited turns` with `no context`. The contract and referenced workspace artifacts must still contain every fact needed to perform and verify the task. Missing context and excess context are separate failure modes.

## Escalate when

- two bounded Luna attempts fail the same criterion;
- implementation and review disagree on a material claim;
- evidence remains ambiguous after targeted verification;
- the task crosses architecture, security, data migration, payments, or release boundaries;
- the parent must make a product or authority decision.

Escalation changes the consumer or decision-maker; it does not retroactively validate missing evidence.

## Transport

Prefer native tasks when the host proves the requested model and sandbox were applied. Use external `codex exec` for Luna or `opencode run` for an explicitly selected provider model. Record requested identity as a fact about launch configuration, not proof of remote runtime identity unless session records establish it.

The external launcher starts a fresh conversation and sends only the generated worker packet. This approximates native no-history delegation and makes prompt size inspectable. Native and external results are not interchangeable evidence when their system instructions or tools differ; compare context policies within one transport before comparing transports.

The durable contract, source snapshot, terminal record, gate, and independent-review rule are transport-neutral. The OpenCode adapter supplies a conservative child-agent policy: nested tasks, external directories, web access, and skills are denied; read-only roles also deny edits and shell. OpenCode permissions are not an operating-system sandbox, so use Codex sandboxing or another isolated runtime for hostile or high-risk work. Read [providers.md](providers.md) before selecting or adding a transport.
