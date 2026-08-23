# Studio Core improvement and benchmark plan: 2026-08-23

This plan turns the real [Studio Core durability march](live-test-results-2026-08-23-studio-core.md) into LunarMarch improvements and a controlled benchmark. The source run is evidence about that application, not a general performance claim for Luna, Sol, Codex, or OpenCode.

## Outcome and usage

- Status: two phases and nine tasks accepted
- Verification: Ruff passed and 101 tests passed
- Excluded work: H3, Music 3, CUDA, and GPU workloads
- Run root: `/tmp/studio-core-lunarmarch-20260823`
- Attempts: 28
- Model-reaching attempts: 22, all completed
- Pre-model infrastructure failures: 6
- Productive worker wall time: 3,558 seconds
- End-to-end time: about 87 minutes

| Metric | Value |
|---|---:|
| Total tokens | 11,206,626 |
| Cached input tokens | 9,962,496 |
| Uncached input tokens | 1,095,610 |
| Output tokens | 148,520 |
| Uncached input plus output | 1,244,130 |
| Input cache rate | 90.1% |
| Reviewer and Auditor total-token share | 48.5% |
| Reviewer and Auditor uncached-input-plus-output share | 62.5% |

Total tokens remain useful for capacity planning. For workflow efficiency, the primary comparison metric is uncached input plus output: cache reuse made 88.8% of this run's total-token count cached input.

## Evidence that the workflow helped

Independent reviews found four real defects: error values were not JSON stored, SQL insert values were swapped, conditional state transitions raced, and empty exception messages incorrectly marked jobs complete. A phase Auditor also found an inherited API issue where an invalid source ID returned HTTP 500. Frozen phase snapshots and path gates prevented out-of-scope changes. Parent adjudication correctly rejected findings that contradicted the actual contract.

## Prioritized improvement plan

### P0: reduce preventable infrastructure and review waste

1. Give every OpenCode worker a writable attempt-local temporary, cache, data, state, and runtime directory. This is implemented.
2. Put the OpenCode `--file` attachment last, after the positional worker instruction, so the instruction is not parsed as another file. This is implemented.
3. Tell read-only Reviewers that launcher-run checks are authoritative. A local test that cannot create a cache is a sandbox limitation, not evidence that the check was unverified. This is implemented.
4. Use one same-task Fixer followed by one fresh Reviewer of the latest snapshot. Do not create a separate task for each small finding unless ownership or rollback needs isolation. This is now the documented default.

### P1: preserve behavior inside allowed files

1. Put known security and compatibility properties in `protected_invariants` on the task contract.
2. Put focused, deterministic probes in `invariant_commands`. LunarMarch records them before the attempt and reruns them after launcher checks. A passing baseline followed by a failure is a gate error even if the changed path was allowed. This is implemented.
3. Give normal change tasks `max_reviewer_attempts: 2`: one review of the Builder, then one review after a Fixer. More review attempts require parent escalation. This is implemented as an optional contract budget.
4. Keep task `inputs` narrow and specific. The worker packet now directs workers to begin with those paths and widen their inspection only for an explicit requirement or protected invariant.

### P2: retain boundaries that code cannot prove alone

1. Codex local state needs narrow write access from the containing application while the project sandbox remains read-only. LunarMarch can preserve the project read-only policy, but it cannot grant the outer application permission itself.
2. Requested model identity is launch configuration evidence, not proof of the provider's remote runtime identity. Report it that way until the host exposes authoritative session metadata.
3. OpenCode needs network access and is a provider trust boundary. Its LunarMarch policy denies web tools, nested tasks, external directories, and inherited API-key environment variables, but this is not an operating-system sandbox.

## Regression coverage

| Finding | Coverage |
|---|---|
| OpenCode consumed the worker instruction as a second file | `test_opencode_launcher_captures_report_and_binds_transport` asserts the `--file` pair is last. |
| OpenCode could not create temporary or XDG directories | The same test launches a fake worker that writes probes to the attempt-local temporary, cache, data, state, and runtime directories. |
| Read-only Reviewer reported checks unverified because cache writes failed | `test_reviewer_packet_defers_authoritative_checks_to_launcher` verifies the packet distinguishes local checks from launcher authority. |
| Codex project read-only policy drift | `test_read_only_launcher_uses_explicit_sandbox_without_auto_approval` verifies explicit read-only policy and no automatic write approval. The outer Codex-state permission remains an environment integration requirement. |
| OpenCode trust or credential leakage | `test_opencode_readonly_policy_denies_mutation_and_delegation` and `test_opencode_transport_sanitizes_environment_and_rejects_bad_sandbox` deny web, external access, nested work, and API-key inheritance. |
| Allowed-file change regressed an existing property | `test_protected_invariant_detects_regression_inside_allowed_path` records a passing baseline then rejects a failed post-work invariant. |
| Review fan-out continued after enough attempts | `test_reviewer_attempt_budget_requires_parent_escalation` rejects a Reviewer beyond the contract budget. |

## Lean default workflow

```text
compact contract and exact inputs
        |
Builder
        |
launcher checks plus protected invariants
        |
fresh Reviewer, latest snapshot only
        |
clear: parent acceptance
finding: same-task Fixer, then one fresh Reviewer
        |
review budget reached or material disagreement: parent escalation
```

For routine change tasks, start with a Builder, one fresh Reviewer, and `max_reviewer_attempts: 2`. Reserve an Auditor for a meaningful frozen phase, not every small repair. Record total tokens and uncached input plus output for every attempt. Treat a large cache rate as a reason to inspect marginal usage and elapsed time, not as a reason to ignore total-token capacity.

## Controlled benchmark: LunarMarch versus Sol-only

Question: on the same frozen fixture, does the LunarMarch workflow improve deterministic quality enough to justify its marginal usage relative to one Sol-only implementation?

### Arms

- **LunarMarch arm:** fixed Sol parent instructions, Luna Builder, one fresh Luna Reviewer, same-task Fixer only for a concrete finding, `max_reviewer_attempts: 2`.
- **Sol-only arm:** one Sol implementation worker with the same task contract, exact inputs, sandbox, time limit, and no delegated review loop.

This evaluates whole workflows, not a pure model-quality comparison. The review cost is part of the LunarMarch arm by design.

### Controls

1. Use one committed disposable fixture with hidden deterministic tests, one focused invariant command, and a fixed task packet.
2. Use opaque trial identifiers and six matched repetitions per arm. Counterbalance arm order three times in each position.
3. Pin model names, efforts, CLI versions, sandbox policy, timeout, tool availability, and fixture commit for the complete benchmark.
4. Run both arms from fresh project copies. Do not expose hidden graders until the worker exits.
5. Grade both arms with the same hidden tests, invariant commands, path-scope checks, and a blinded parent review of only the final evidence.

### Metrics and decision rule

- Primary quality: hidden behavior, invariant preservation, declared-path discipline, and public checks.
- Primary efficiency: mean uncached input plus output tokens per completed fixture.
- Secondary efficiency: total tokens, cache rate, wall time, attempt count, and reviewer finding rate.
- Require all matched trials and usage telemetry. Do not replace failures or timeouts.
- Adopt a leaner default only if quality is not worse by more than a predeclared tolerance and the marginal usage saving is large enough to matter for the intended workload.

Publish aggregate and per-trial results with [the metrics report template](metrics-report-template.md). Keep Luna, Sol, and OpenCode provider series distinct outside this controlled fixture.
