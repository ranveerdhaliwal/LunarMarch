# Context-efficiency evaluation

Use this protocol before claiming that more or less inherited context improves Luna work.

## Hypothesis

The default LunarMarch policy is a compact resolved contract with no inherited conversation. It should reduce input usage without lowering quality relative to full raw history. A deliberately thin packet tests the opposite boundary: context can be too small.

## Controlled conditions

- `thin`: task shell with deliberately insufficient product context. Negative control.
- `recent`: only the latest conversational slice. Tests loss of older decisions.
- `contract`: all material facts reconciled into a compact contract. Candidate default.
- `contract-padded`: the identical resolved contract plus neutral irrelevant history. Paired with `contract`, this is the cleanest bundled test of additional context volume/noise while holding required facts fixed.
- `full`: the same material facts embedded in raw, noisy, partly superseded history.

Do not label the condition inside the model-visible prompt. Hold task, fixture, model, effort, tools, sandbox, checks, and output request constant. Counterbalance condition position within each case. Use at least five repetitions per case and condition, rounded up so the repetition count is divisible by the number of selected conditions; for a two-condition comparison, use at least six. Treat the bundled single fixture as an exploratory case study. For a publishable claim, predeclare a practically important effect, use several heterogeneous cases, justify sample size, report confidence intervals, and rerun on another day or model snapshot.

## Measurements

Primary quality must be deterministic and blind to condition:

- hidden behavioral or property-test pass rate;
- public test and compilation results;
- undeclared-path mutations;
- task-specific safety and robustness checks.

Track actual `input_tokens`, cached input, uncached input, output tokens, reasoning tokens when exposed, total tokens, worker latency, grader latency, worker exit, changed paths, and report presence. Record missing telemetry as missing; never replace it with character-count estimates. Also retain context bytes and words as payload-size descriptors. Treat a model-based maintainability review as secondary evidence: randomize artifact labels, require identical reviewer coverage and configuration, use at least two raters or an adjudication rule, and keep it separate from deterministic correctness.

Report every attempted trial, including launch failures and timeouts. Compare condition means, medians, dispersion, success rates, and paired deltas against `contract`. Separate infrastructure failure from task failure, but keep both in intent-to-treat totals. Lower usage counts as improvement only when quality remains within a predeclared tolerance. Recommended exploratory tolerance: no more than two quality points or two percentage points of task success, whichever is stricter.

The bundled grader is copied into each trial only after the worker exits, but a local workspace sandbox is not a secrecy boundary against a worker that deliberately searches the wider machine. For publishable hidden-test claims, generate graders after execution in an isolated container or use a separate grading service inaccessible to workers.

## Native delegation boundary

When the native host exposes a context-fork control, use no inherited turns for the `contract` condition, a fixed recent-turn count for `recent`, and full inheritance for `full`. Native workers share the workspace, so keep the same immutable fixture and packet artifacts across conditions. If the host does not expose authoritative per-worker usage, report native quality separately and use the external runner only for controlled token accounting. Do not merge native and external trials into one estimate: their system instructions, tools, and transport may differ.

## Run the bundled benchmark

Plan without spending model usage:

```bash
python3 <skill>/scripts/context_eval.py plan \
  --suite <skill>/evals/context-efficiency/suite.json \
  --repetitions 10 --seed 20260822
```

Run live trials in a disposable output directory:

```bash
python3 <skill>/scripts/context_eval.py run \
  --suite <skill>/evals/context-efficiency/suite.json \
  --output /tmp/lunarmarch-context-eval \
  --repetitions 10 --seed 20260822 \
  --model gpt-5.6-luna --effort high
```

The runner uses `codex exec --json`, fresh project copies, randomized trial order, hidden post-run graders, source snapshots, and a machine-readable result per trial. It writes `summary.json` and `report.md`. Running it consumes model usage and may require permission for nested Codex access to authenticated local state.

### Run it in small checkpoints

Predeclare the complete balanced run but execute only one or two new trials:

```bash
python3 <skill>/scripts/context_eval.py run \
  --suite <skill>/evals/context-efficiency/suite.json \
  --output /tmp/lunarmarch-context-eval \
  --conditions contract contract-padded \
  --repetitions 6 --seed 20260822 \
  --model gpt-5.6-luna --effort high \
  --max-new-trials 2
```

Continue the same immutable run later by repeating the exact arguments and adding `--resume`. The evaluator verifies the expected trial plan, model, effort, CLI version, suite-content fingerprint, and evaluator hash before continuing. It skips completed trials and runs at most the requested number of pending trials.

Every checkpoint writes a summary with `checkpoint.remaining_trials`. Partial runs remain `run_integrity.complete: false` and decision-ineligible. Each completed trial is also sealed: a hash inventory of its prompt, events, report, copied project, graders, and result is written inside the trial, and that seal is immediately bound into the run manifest. Resume and summarize reject changed or unsealed completed artifacts. This makes spending interruptible without turning a small, imbalanced or edited sample into a claim. If a process is interrupted inside a trial, the incomplete directory is retained for diagnosis and the evaluator refuses automatic reuse of that run root.

These hashes provide consistency and accidental-tamper detection, not hostile-storage security. A person who can rewrite the entire run root can also rewrite its local seals. For adversarial provenance, publish the manifest and seal hashes to an independently controlled signed release, transparency log, or other trusted store.

Use `--conditions contract full --repetitions 2` only as a position-balanced plumbing smoke test. It is not enough evidence for a quality claim.

Only publish a result produced from a clean suite commit with `dirty_suite_override` set to `false`, a complete expected-trial roster, and telemetry for every paired trial. An earlier diagnostic run exposed condition labels in filesystem paths and was intentionally invalidated rather than cited as evidence.

The first clean, opaque, position-balanced six-pair case study is recorded in [../evals/context-efficiency/results/2026-08-22-contract-v-padding.md](../evals/context-efficiency/results/2026-08-22-contract-v-padding.md).
