# Compact contract versus padded contract , 2026-08-22

## Conclusion

The compact-contract default passed the predeclared exploratory decision rule for this fixture: it used 17.9% fewer cumulative tokens while mean overall quality trailed by 1.67 points, within the two-point tolerance.

All behavioral, public-test, and compilation graders passed in both conditions. One compact worker created an undeclared `report.md`, so compact had five fully successful trials out of six and mean quality 98.33; padded had six of six and mean quality 100. This evidence favors compact context for efficiency, but it does not prove equal or better code quality.

This is a twelve-trial, single-fixture case study. It is not a general quality or cost claim for Luna, native subagents, other repositories, or other task classes.

## Controlled comparison

- Requested model: `gpt-5.6-luna`
- Effort: `high`
- Codex CLI: `0.149.0-alpha.4.1`
- Repository commit: `4e8332c381ac51d9e453c38d94d25e4d6068bffc` (clean)
- Suite fingerprint: `042478bf825dc0fe9f2dab059d0daaa7748516ee7efa6432d871c27c75d412de`
- Seed: `20260822`
- Repetitions: six matched pairs; each condition occupied each order position three times
- Compact context: 588 bytes
- Padded context: 14,076 bytes
- Material facts: identical; padding contained neutral irrelevant history
- Primary quality: hidden behavior (70), public tests (15), compilation (5), declared-path discipline (10)
- Predeclared tolerance: compact mean quality could trail by at most two points

Trial names and project paths were opaque. The evaluator launched each trial in a fresh committed repository, copied hidden graders only after worker exit, retained failures in intent-to-treat totals, and used the final top-level `turn.completed` usage event. The expected roster, all twelve trials, and all six token pairs were present.

## Aggregate result

| Metric | Compact contract | Padded contract | Compact difference |
|---|---:|---:|---:|
| Fully successful trials | 5/6 | 6/6 | one fewer |
| Mean overall quality | 98.33 | 100.0 | 1.67 points lower |
| Behavioral/public/compile passes | 6/6 | 6/6 | equal |
| Scope-clean trials | 5/6 | 6/6 | one fewer |
| Mean input tokens | 117,808.8 | 144,005.5 | 18.2% fewer |
| Mean uncached input tokens | 12,038.2 | 17,200.2 | 30.0% fewer |
| Mean output tokens | 2,003.2 | 1,936.5 | 3.4% more |
| Mean cumulative total tokens | 119,812 | 145,942 | 17.9% fewer |
| Median cumulative total tokens | 112,805 | 152,046 | 25.8% fewer |
| Mean worker time | 52.12 s | 54.32 s | 4.0% faster |
| Median worker time | 51.34 s | 57.22 s | 10.3% faster |
| Mean command calls | 4.50 | 5.17 | 12.9% fewer |
| Infrastructure failures | 0 | 0 | equal |

The 95% Wilson intervals are 43.65%-96.99% for compact's 5/6 full-success rate and 60.97%-100% for padded's 6/6. They overlap substantially, underscoring the uncertainty. The one compact failure was scope discipline, not incorrect implementation: it changed `handles.py` correctly but also created `report.md`.

## Per-trial audit

| Repetition | Position | Condition | Quality | Total tokens | Worker seconds | Commands | Scope clean |
|---:|---:|---|---:|---:|---:|---:|---|
| 1 | 1 | padded | 100 | 142,550 | 56.26 | 5 | yes |
| 1 | 2 | compact | 100 | 108,300 | 43.09 | 4 | yes |
| 2 | 1 | compact | 90 | 112,792 | 48.31 | 4 | no (`report.md`) |
| 2 | 2 | padded | 100 | 161,987 | 60.38 | 6 | yes |
| 3 | 1 | padded | 100 | 161,358 | 61.13 | 6 | yes |
| 3 | 2 | compact | 100 | 111,852 | 50.13 | 4 | yes |
| 4 | 1 | compact | 100 | 112,818 | 52.56 | 4 | yes |
| 4 | 2 | padded | 100 | 105,174 | 40.68 | 3 | yes |
| 5 | 1 | padded | 100 | 161,849 | 58.18 | 6 | yes |
| 5 | 2 | compact | 100 | 142,137 | 56.50 | 6 | yes |
| 6 | 1 | compact | 100 | 130,973 | 62.15 | 5 | yes |
| 6 | 2 | padded | 100 | 142,734 | 49.28 | 5 | yes |

Requested model identity is recorded from launch configuration; the CLI stream did not independently expose an effective remote model identifier.

## Reproduce

```bash
python3 scripts/context_eval.py run \
  --suite evals/context-efficiency/suite.json \
  --output /tmp/lunarmarch-context-eval \
  --conditions contract contract-padded \
  --repetitions 6 --seed 20260822 \
  --model gpt-5.6-luna --effort high \
  --quality-tolerance 2
```

Before making a broader claim, add at least three to five heterogeneous fixtures, justify sample size against a minimum meaningful effect, rerun on another day or pinned snapshot, and use stronger grader isolation.
