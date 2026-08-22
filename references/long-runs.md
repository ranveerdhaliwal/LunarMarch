# Long runs, barriers, and recovery

## Durable truth

Treat `state.json` and immutable attempt artifacts as the run’s durable control plane. Conversation history, worker prose, and process listings are supporting evidence, not authority. On resume, read `status` first and execute its bounded `next_action`; do not reconstruct the run from memory.

## Lifecycle

Tasks move through `pending`, `active`, `review`, `accepted`, `blocked`, or `rejected`. Attempts move through `reserved`, `terminal`, and `gated`. A reserved attempt without a terminal event is `running_or_unknown`, never automatically failed.

Never retry an unknown writer in the same checkout. First establish that no writer can continue and reconcile the exact source movement. Prefer a separate worktree if uncertainty remains.

## Phase barrier

For each phase:

1. Finish all writers.
2. Ensure every task mutation has independent review.
3. Freeze the phase source/evidence identity.
4. Run required post-barrier verification.
5. Run a fresh Auditor.
6. Let the parent accept or reopen the phase.

Any later mutation reopens the phase and invalidates stale audit evidence.

## Checkpoints

Checkpoint only at safe boundaries: before dispatch, after terminal capture, after gate, after semantic acceptance, and after phase decisions. Keep `next_action` singular and mechanical where possible.

## Retry discipline

Default to two attempts per task/role and one premium escalation. Retry transport failures only when classified as transient. Do not retry policy denial, invalid configuration, deterministic gate failure, or completed-low-quality output without changing the task route or evidence.
