# Live Luna smoke test

Run this only when model-backed testing is desired. It consumes model usage and launches a workspace-write agent inside a disposable fixture copy.

## Prepare

Confirm `codex debug models` includes `gpt-5.6-luna`. Then create a disposable project:

```bash
mkdir -p /tmp/lunarmarch-live
cp -R <skill>/examples/smoke-project /tmp/lunarmarch-live/project
git -C /tmp/lunarmarch-live/project init
```

Initialize and register the task:

```bash
python3 <skill>/scripts/lunarmarch.py init \
  --project-root /tmp/lunarmarch-live/project \
  --run-root /tmp/lunarmarch-live/run \
  --goal "Implement and independently review clamp_count" \
  --mode task

python3 <skill>/scripts/lunarmarch.py add-task \
  --run-root /tmp/lunarmarch-live/run \
  --spec <skill>/examples/smoke-contract.json
```

## Builder and gate

```bash
python3 <skill>/scripts/lunarmarch.py launch \
  --run-root /tmp/lunarmarch-live/run \
  --task-id clamp-count --role builder --effort high --run-checks

python3 <skill>/scripts/lunarmarch.py gate \
  --run-root /tmp/lunarmarch-live/run \
  --attempt /tmp/lunarmarch-live/run/attempts/clamp-count/builder-1
```

A clear gate is objective integrity, not semantic PASS. Inspect its bounded diff and report before review.

## Independent review and acceptance

```bash
python3 <skill>/scripts/lunarmarch.py launch \
  --run-root /tmp/lunarmarch-live/run \
  --task-id clamp-count --role reviewer --effort high --run-checks

python3 <skill>/scripts/lunarmarch.py gate \
  --run-root /tmp/lunarmarch-live/run \
  --attempt /tmp/lunarmarch-live/run/attempts/clamp-count/reviewer-1

python3 <skill>/scripts/lunarmarch.py accept \
  --run-root /tmp/lunarmarch-live/run \
  --task-id clamp-count \
  --attempt /tmp/lunarmarch-live/run/attempts/clamp-count/reviewer-1
```

Record wall time, changed paths, test results, findings, retries, and parent inspection cost. Keep the disposable directory until the results are captured.
