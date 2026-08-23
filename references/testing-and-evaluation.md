# Testing and evaluation record

This document records what LunarMarch has actually tested, what each test establishes, what failed during development, and what the current evidence does and does not support.

## Contents

- [Evidence summary](#evidence-summary)
- [Offline automated suite](#offline-automated-suite)
- [Live orchestration evaluation](#live-orchestration-evaluation)
- [Live context-efficiency evaluation](#live-context-efficiency-evaluation)
- [Evaluator defects found and corrected](#evaluator-defects-found-and-corrected)
- [Interpretation and limitations](#interpretation-and-limitations)
- [Reproduction](#reproduction)
- [Plan and estimate for additional fixtures](#plan-and-estimate-for-additional-fixtures)

## Evidence summary

As of 2026-08-22:

- 35 offline automated tests pass.
- Python compilation passes for the evaluator and orchestration scripts.
- The Codex skill validator passes.
- The user-wide installation is a valid symlink to this repository.
- The first live Task-mode Builder/Reviewer workflow completed and was accepted.
- The clean context experiment completed all 12 expected Luna trials with no infrastructure failures and complete usage telemetry.
- All 12 context trials passed hidden behavior, public tests, and compilation.
- Compact context used 17.9% fewer mean total tokens and 30.0% fewer mean uncached input tokens than the materially equivalent padded context.
- One compact worker created an undeclared `report.md`, giving compact a mean overall score of 98.33 against padded's 100.

The evidence supports compact resolved contracts as the current efficiency default for LunarMarch. It does not prove that compact context always preserves quality, that padding always hurts, or that the result transfers unchanged to native subagents, other models, repositories, or task classes.

### Token reporting policy

Token counts are the primary efficiency metric. Direct Codex workers now request JSONL events and persist the final terminal usage record in `terminal.json` and `worker.log`. The record includes input, cached input, uncached input, output, reasoning, and total tokens. OpenCode workers may not expose equivalent counts through their default output, so their fields remain `not reported` until a provider-specific usage event is available. No count is inferred from text length.

## Offline automated suite

Run with:

```bash
python3 -m unittest discover -s tests -v
```

CI runs the suite on Python 3.11, 3.12, and 3.13. CI also compiles `scripts/` and `tests/`, exercises the command interface, and validates that the context-evaluation suite can be planned.

### Orchestration, transport, and integrity tests: 23

| Test | What it verifies |
|---|---|
| `test_builder_reviewer_acceptance_flow` | A mutating Builder can pass its gate, but final task acceptance requires a fresh independent Reviewer. |
| `test_gate_rejects_out_of_scope_change` | A successful worker cannot pass when it changes a path outside the contract's declared ownership. |
| `test_git_snapshot_ignores_python_cache_artifacts` | Git-backed source snapshots ignore generated `__pycache__`, `.pyc`, and `.pyo` files consistently. |
| `test_gate_rejects_read_only_mutation` | Scouts and other read-only roles fail their gate if they modify the project. |
| `test_gate_requires_exact_acceptance_results` | Missing declared command results cannot be treated as verified evidence. |
| `test_contract_is_immutable_after_registration` | A registered task contract cannot be edited before a later attempt. |
| `test_unknown_attempt_blocks_duplicate_writer` | A worker with an unknown/running lifecycle prevents a second overlapping writer. |
| `test_failed_command_is_gate_failure` | A nonzero acceptance command prevents a clear gate. |
| `test_report_tampering_after_terminal_is_rejected` | Worker evidence is hash-bound; changing a report after completion invalidates it. |
| `test_tampered_reservation_cannot_finish` | A worker cannot expand or rewrite its reserved authority and still finish normally. |
| `test_acceptance_rejects_project_movement_after_review` | Parent acceptance fails if the project changes after the accepted review evidence was produced. |
| `test_external_launcher_pins_luna_and_completes_attempt` | The external writer launcher requests `gpt-5.6-luna`, binds effort, uses the intended approval mode, and records completion. |
| `test_read_only_launcher_uses_explicit_sandbox_without_auto_approval` | Reviewers receive an explicit read-only sandbox and never automatic write approval. |
| `test_opencode_launcher_captures_report_and_binds_transport` | An OpenCode/DeepSeek-style worker is bound to its transport, model, and variant; stdout becomes immutable report evidence and the logged command redacts the prompt. |
| `test_opencode_readonly_policy_denies_mutation_and_delegation` | OpenCode read-only workers deny edits, shell, nested tasks, and external-directory access and never receive auto approval. |
| `test_opencode_transport_sanitizes_environment_and_rejects_bad_sandbox` | Third-party workers do not inherit API-key environment variables, and unknown sandbox modes fail closed. |
| `test_worker_timeout_is_bounded_and_terminal` | A timed-out worker is terminated promptly and recorded with exit code 124 instead of leaving the attempt active. |
| `test_cli_forwards_worker_timeout` | The public launch command forwards its configured worker timeout to the launcher. |
| `test_march_phase_requires_freeze_and_auditor` | March-mode phase acceptance requires frozen source evidence and a distinct Auditor. |
| `test_user_style_symlink_install_is_idempotent` | Reinstalling the same user-wide symlink is safe and idempotent. |
| `test_repo_style_copy_install_has_matching_fingerprint` | A repository-local copied skill matches the source bundle fingerprint. |
| `test_installer_refuses_silent_overwrite` | Installation refuses to replace an unrelated destination silently. |
| `test_installer_replace_preserves_backup` | Explicit replacement preserves the displaced installation as a recoverable backup. |

### Context-evaluator tests: 12

| Test | What it verifies |
|---|---|
| `test_suite_and_counterbalanced_plan` | The full five-condition schedule covers every condition and position, and trial IDs do not reveal condition names. |
| `test_padded_contract_preserves_contract_prefix` | Compact and padded packets contain the same material contract, while padding is substantially larger. |
| `test_plan_rejects_position_imbalanced_repetitions` | A two-condition plan with five repetitions is rejected; a six-pair plan balances first/second position exactly. |
| `test_usage_parser_uses_only_terminal_completed_record` | Usage comes only from the authoritative top-level terminal `turn.completed` event, not unrelated nested data. |
| `test_current_codex_usage_shape_and_event_counts` | Current CLI token fields and command/file/message event counts are parsed correctly. |
| `test_unittest_parser_scores_partial_failure` | Multiple reported test failures and errors produce the correct partial deterministic score. |
| `test_unittest_parser_rejects_malformed_nonzero_result` | A crashing or malformed nonzero grader cannot accidentally receive full credit. |
| `test_decision_requires_five_quality_preserving_token_pairs` | Endorsement requires complete quality and token pairs; partial rosters and missing telemetry are ineligible. |
| `test_fake_live_run_scores_and_summarizes` | A disposable fake CLI exercises copying, worker execution, grading, usage collection, integrity checks, and summary generation end to end. |
| `test_trial_copy_excludes_source_repository_metadata` | Source `.git` metadata and its potentially revealing contents are not copied into worker projects. |
| `test_checkpointed_run_resumes_same_manifest` | A partial balanced run remains ineligible, then resumes the same immutable manifest without repeating completed trials and becomes complete. |
| `test_checkpoint_resume_rejects_tampered_completed_trial` | Each finished trial is sealed into the manifest; editing a result before resume is rejected. |

These are regression tests for observable invariants. They do not merely assert that documentation contains particular wording.

## Live orchestration evaluation

The first model-backed Task evaluation used `gpt-5.6-luna` at high effort on a disposable `clamp_count` implementation fixture. It exercised the actual external launcher, durable attempts, objective gates, a fresh read-only Reviewer, and parent acceptance.

The attempt sequence mattered:

1. The first Builder launch failed because two Codex CLI options were mutually exclusive. LunarMarch retained the failed attempt instead of erasing it.
2. The next launch reached Codex but the containing application sandbox denied access to nested Codex state. The disposable run was retried with narrow authorization.
3. A Builder implemented the function and passed five functional checks, but the gate exposed inconsistent filtering of generated Python cache artifacts.
4. After fixing snapshot filtering, a fresh Builder passed all five checks and received a clear gate.
5. A fresh read-only Reviewer reran the declared checks, added equal-bound and negative-value probes, made no project changes, and received a clear gate.
6. The parent inspected the bounded evidence and explicitly accepted the task.

This evaluation directly produced launcher-policy and cache-filtering regression tests. The full attempt record is in [live-test-results-2026-08-22.md](live-test-results-2026-08-22.md).

## Live context-efficiency evaluation

### Question

When all required facts are already represented in a resolved contract, does adding irrelevant conversational history change Luna's usage or measured quality?

### Conditions

- `contract`: a compact 588-byte resolved contract containing every required fact.
- `contract-padded`: the identical material contract plus neutral irrelevant history, totaling 14,076 bytes.

The comparison deliberately did not use an under-specified prompt. That would conflate context volume with missing requirements. Thin and incomplete-context conditions remain useful negative controls for future experiments, but the cleanest first test held required information constant.

### Controls

- Requested model and effort were fixed at `gpt-5.6-luna`, high.
- Every trial started from the same immutable fixture and task.
- Trial directory names were opaque hashes and did not contain the condition.
- Six matched repetitions were used so each condition occupied the first and second position exactly three times.
- Each worker ran in a fresh committed project copy.
- Workers could see public tests but hidden graders were copied only after worker exit.
- Allowed paths and source hashes measured scope discipline independently of test success.
- Usage was taken from the last top-level terminal `turn.completed` event.
- Missing, duplicate, or unexpected trials invalidated the run.
- Missing token telemetry invalidated the paired decision.
- The suite repository had to be clean; its commit and complete referenced-content fingerprint were recorded.
- Failures and timeouts remained in intent-to-treat totals.

The clean run used repository commit `4e8332c381ac51d9e453c38d94d25e4d6068bffc` and suite fingerprint `042478bf825dc0fe9f2dab059d0daaa7748516ee7efa6432d871c27c75d412de`.

### Quality scoring

Each trial could earn 100 points:

- 70 points: hidden behavioral tests;
- 15 points: public tests;
- 5 points: compilation;
- 10 points: no modifications outside the declared path boundary.

The exploratory decision rule required at least five complete matched quality and token pairs. Compact could trail padded by no more than two mean quality points, and padded had to consume more mean total tokens. Passing this rule supports a default for further use; it is not a statistical proof of equivalence.

### Results

| Metric | Compact | Padded | Difference for compact |
|---|---:|---:|---:|
| Trials | 6 | 6 | n/a |
| Fully successful | 5/6 | 6/6 | one fewer |
| Mean overall quality | 98.33 | 100.0 | 1.67 points lower |
| Hidden behavior passed | 6/6 | 6/6 | equal |
| Public tests passed | 6/6 | 6/6 | equal |
| Compilation passed | 6/6 | 6/6 | equal |
| Scope clean | 5/6 | 6/6 | one fewer |
| Mean input tokens | 117,808.8 | 144,005.5 | 18.2% fewer |
| Mean uncached input tokens | 12,038.2 | 17,200.2 | 30.0% fewer |
| Mean output tokens | 2,003.2 | 1,936.5 | 3.4% more |
| Mean total tokens | 119,812 | 145,942 | 17.9% fewer |
| Median total tokens | 112,805 | 152,046 | 25.8% fewer |
| Mean worker time | 52.12 seconds | 54.32 seconds | 4.0% faster |
| Median worker time | 51.34 seconds | 57.22 seconds | 10.3% faster |
| Mean command calls | 4.50 | 5.17 | 12.9% fewer |
| Infrastructure failures | 0 | 0 | equal |

All six token pairs and quality pairs were observed. The run roster was complete. The compact-minus-padded mean total-token difference was −26,130 tokens. Padded-minus-compact mean quality was 1.6667 points, so compact remained inside the predeclared two-point tolerance.

The sole non-perfect compact run correctly implemented the requested behavior but created an undeclared `report.md` in addition to `handles.py`. It therefore lost the ten scope-discipline points. This is an execution-quality difference even though the produced code passed every behavioral check; it should not be hidden or reclassified after seeing the outcome.

The 95% Wilson interval for compact's 5/6 full-success rate is 43.65%-96.99%. For padded's 6/6 it is 60.97%-100%. The broad, overlapping intervals show how uncertain a six-pair single-fixture result remains.

The aggregate, per-trial table, and exact reproduction command are in [the dated result](../evals/context-efficiency/results/2026-08-22-contract-v-padding.md). The exact generated aggregate is preserved as [JSON](../evals/context-efficiency/results/2026-08-22-contract-v-padding-summary.json).

## Evaluator defects found and corrected

The evaluation process itself was tested and reviewed. An early diagnostic produced attractive results but was invalidated because condition names appeared in worker-visible filesystem paths. Those numbers were removed from the claim.

An independent Luna reviewer, started without inherited conversation, audited the evaluator and identified the following problems before the published result:

1. Condition labels leaked through trial and report paths. Trial identities are now opaque hashes.
2. Five quality pairs could satisfy eligibility even if fewer token pairs had telemetry. Eligibility now requires complete and equal quality/token pair counts.
3. Partial, duplicate, or unexpected trial rosters could look complete. Summaries now compare observed IDs against the immutable expected manifest.
4. Malformed nonzero unit-test output could receive full credit. Nonzero graders require explicit, valid success evidence.
5. Timeouts did not terminate the entire worker process group. The evaluator now kills and reaps the group.
6. Source repository metadata could be copied into a trial. `.git`, `.hg`, `.svn`, and generated Python caches are excluded.
7. Only the suite descriptor was hashed. Every referenced task, context, project, public test, and hidden grader is now included in the suite fingerprint, and dirty suites are rejected by default.
8. Usage parsing could select an unrelated nested usage object. Only the authoritative terminal event is accepted.
9. A two-condition, five-repetition schedule placed one condition first three times and the other twice. Repetitions must now be divisible by the selected condition count; the published run used six balanced pairs.

Each issue is covered by code or a regression test. The published run occurred only after the suite was clean and the independent reviewer confirmed the original eight defects were fixed; the ninth balance issue was then corrected before restarting the run.

## Interpretation and limitations

### Supported conclusions

- Compact resolved context can materially reduce Luna token usage when it contains all required facts.
- In this fixture, the additional neutral history did not improve implementation correctness: every implementation passed every behavioral test.
- Compact context met the predeclared exploratory efficiency rule despite one scope-discipline failure.
- “No inherited conversation” should mean “use a complete resolved contract,” not “give the worker almost no context.”

### Unsupported conclusions

- Compact context is not proven universally better or equivalent in quality.
- The experiment does not estimate behavior with genuinely missing facts; that needs `thin` and `recent` negative-control trials.
- One small Python function does not represent research, multi-file implementation, debugging, or long-running recovery.
- External `codex exec` workers and native Codex subagents have different system instructions and transports; their measurements must not be merged.
- Requested model identity was recorded from launch configuration. The CLI event stream did not independently expose the effective remote model identity.
- Local post-run grader copying is useful blinding but not a hostile-security boundary. Stronger public claims should use isolated containers or a grading service unavailable to workers.
- Token counts are cumulative CLI usage, not a direct dollar-cost calculation.

## Reproduction

Run all offline tests:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/context_eval.py scripts/lm_core.py scripts/lunarmarch.py
```

Validate the skill:

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py /path/to/LunarMarch
python3 scripts/install_skill.py --check --scope user
```

Inspect a balanced plan without using model tokens:

```bash
python3 scripts/context_eval.py plan \
  --suite evals/context-efficiency/suite.json \
  --conditions contract contract-padded \
  --repetitions 6 --seed 20260822
```

Run the live comparison in a new disposable output directory:

```bash
python3 scripts/context_eval.py run \
  --suite evals/context-efficiency/suite.json \
  --output /tmp/lunarmarch-context-eval \
  --conditions contract contract-padded \
  --repetitions 6 --seed 20260822 \
  --model gpt-5.6-luna --effort high \
  --quality-tolerance 2
```

Live execution consumes model usage and requires an installed authenticated Codex CLI. Do not publish a run that used `--allow-dirty-suite`.

Run only two new trials at a time:

```bash
python3 scripts/context_eval.py run \
  --suite evals/context-efficiency/suite.json \
  --output /tmp/lunarmarch-context-eval \
  --conditions contract contract-padded \
  --repetitions 6 --seed 20260822 \
  --model gpt-5.6-luna --effort high \
  --quality-tolerance 2 \
  --max-new-trials 2
```

Repeat the exact command with `--resume` on another day. The partial result is retained but cannot pass the decision rule until the complete balanced roster exists.

## Plan and estimate for additional fixtures

The next benchmark should add three to five fixtures with different failure surfaces:

1. **Research synthesis:** reconcile conflicting local sources into a structured answer with deterministic fact, citation, contradiction, and non-invention checks.
2. **Multi-file implementation:** change an API across several modules while preserving compatibility, tests, type checks, and ownership boundaries.
3. **Diagnosis from incomplete evidence:** identify a root cause from code, tests, and logs without implementing an unauthorized fix; grade diagnosis evidence and non-mutation.
4. **Resumable multi-phase work:** interrupt and resume a March run, then verify phase barriers, durable state, integration, and recovery behavior.
5. **Reviewer/Fixer recovery:** seed a plausible implementation defect, require independent review, bounded correction, regression checks, and final acceptance evidence.

The estimates below assume six compact-versus-padded pairs, or 12 live workers, per fixture. They describe total engineering time, not one required continuous session.

| Work | Three additional fixtures | Five additional fixtures |
|---|---:|---:|
| Fixture and packet design | 1.5-2.5 hours | 2.5-4 hours |
| Deterministic public/hidden graders | 1.5-2.5 hours | 2.5-4 hours |
| Leakage review and dry runs | 0.5-1 hour | 1-1.5 hours |
| Sequential live Luna execution | 30-45 minutes | 50-75 minutes |
| Audit, analysis, and documentation | 1-1.5 hours | 1.5-2.5 hours |
| **Expected elapsed total** | **5-7 hours** | **8-12 hours** |

Three additional fixtures are realistic in one focused working day. Five are more realistically one long day or two normal sessions. Research and resumability fixtures may require small evaluator extensions, so they carry more schedule risk than ordinary coding fixtures.

Running trials concurrently could reduce wall-clock time, but it risks adding load, cache, and contention effects to a context experiment. Sequential execution is the safer default unless concurrency is itself an explicit controlled factor.

### Bite-sized execution plan

Each fixture is an independent evidence unit and can be spread across days:

1. **Design checkpoint, 30-60 minutes and no model usage:** write the task, compact packet, padded packet, public tests, hidden grader, and declared paths.
2. **Offline checkpoint, 5-15 minutes and no model usage:** validate the suite, run the fake CLI end to end, and inspect leakage boundaries.
3. **Pilot checkpoint, one matched order block:** run two trials. Treat the output only as plumbing and failure-surface evidence.
4. **Completion checkpoints:** run two new trials at a time using `--resume`. Six two-trial checkpoints complete one 12-trial fixture.
5. **Audit checkpoint, 15-30 minutes and no model usage:** inspect every trial, publish the aggregate, and decide whether the next fixture is worth funding.

Nothing requires completing three or five fixtures before learning something. Finish and publish one fixture at a time. Stop after any fixture if the result is already unstable, the grader is not discriminating, or the next experiment is not worth its usage.

For minimum-cost development, validate new fixtures first with fake CLIs and then with inexpensive OpenCode/DeepSeek workers. Keep those results in a separate provider series because OpenCode and Codex telemetry and tool policies differ. Reserve Luna cross-checks for fixtures that survive the cheap pilot and answer a decision worth testing.
