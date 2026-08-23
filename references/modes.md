# Operating modes

Choose the smallest mode that materially improves the work.

## Quick

Use for one self-contained, low-risk request whose output the parent can verify cheaply. One Scout or Builder is enough. Do not create durable run state unless interruption or evidence retention matters.

## Research

Use for broad questions that split into independent angles. Create one shared evidence packet and distinct Scout contracts. Keep Scouts read-only, avoid duplicated questions, and synthesize only after required lanes finish. Missing lanes are missing evidence, not implicit agreement.

Good lane boundaries include subsystems, competing hypotheses, source classes, time periods, or verification dimensions. Parallelize independent work; sequence lanes when later questions depend on earlier findings.

## Task

Use for one bounded mutation or technical deliverable:

```text
optional Scout → Builder → objective gate → independent Reviewer
                                      finding → same-task Fixer → fresh Reviewer of latest snapshot
                                      clear → parent acceptance
```

A Fixer may consume supplied findings. It does not inherit permission to redesign unrelated code. The implementer never reviews itself.

For routine work, use one Reviewer after the Builder and one after a same-task Fixer. Put `max_reviewer_attempts: 2` in the contract. Do not split a small repair into another task solely to create another review cycle. Use a separate task only when ownership, dependencies, rollout, or rollback genuinely needs isolation.

## March

Use when work has multiple reviewable units, dependencies, long waits, or a meaningful chance of interruption. Decompose into phases and tasks. Complete writers before freezing a phase; then run post-barrier verification and a fresh Auditor. Any later phase mutation invalidates the frozen evidence.

Use a Sentinel for CI, jobs, downloads, or other long waits. Sentinel updates only on material change, completion, or blocker; unchanged state is expected.
