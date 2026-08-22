# Contributing to LunarMarch

LunarMarch welcomes small, independently reviewable contributions. You do not need an API key or a large model budget to help.

## Good bite-sized contributions

- Add one deterministic fixture without running paid trials.
- Improve public or hidden graders for an existing fixture.
- Audit a fixture for condition, path, test, or answer leakage.
- Add fake-CLI coverage for a worker transport.
- Reproduce an existing result on another day and publish the complete run metadata.
- Improve recovery, timeout, or permission handling without changing task semantics.
- Document a provider from its official current documentation without committing credentials.

## Fixture contribution contract

A fixture should include:

- a bounded task with a declared write or read-only boundary;
- a compact packet containing every required fact;
- a materially equivalent padded packet when testing context volume;
- an intentionally incomplete packet only when it is clearly labeled as a negative control;
- a minimal starting project or evidence corpus;
- public checks that help the worker self-correct;
- deterministic hidden checks that grade correctness, non-invention, robustness, and scope as appropriate;
- no condition labels or answers in worker-visible paths;
- no secrets, personal data, network dependency, or destructive behavior.

Start with fake-CLI and offline tests. A pull request can be valuable without paid model results. If live results are included, preserve every attempted trial and follow [references/context-evaluation.md](references/context-evaluation.md).

## Provider contributions

Prefer the existing OpenCode transport when OpenCode already supports the provider. Add a new transport only for a genuinely different executable or lifecycle, following [references/providers.md](references/providers.md#adding-another-provider-later).

Never commit API keys or place them in contracts, prompts, run roots, examples, test fixtures, logs, or screenshots. Use the provider's credential store or documented environment substitution.

## Local verification

```bash
python3 -m compileall -q scripts tests
python3 -m unittest discover -s tests -v
python3 scripts/lunarmarch.py --help
python3 scripts/context_eval.py plan \
  --suite evals/context-efficiency/suite.json \
  --conditions contract --repetitions 1
```

Also run the Codex skill validator when it is available. Keep changes narrowly scoped, explain the invariant being added or corrected, and include a regression test for behavioral changes.

## Evidence language

Separate these claims:

- “The offline invariant passes.”
- “The requested model was configured.”
- “The runtime independently proved the effective model.”
- “This fixture supports a bounded conclusion.”
- “This result generalizes.”

The first four may be supportable with the right artifacts. The fifth normally requires several heterogeneous fixtures, justified sample size, and independent reproduction.
