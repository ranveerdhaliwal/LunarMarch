# Installation and use from other chats

LunarMarch is a standalone skill bundle. Install it in one of two scopes.

## User-wide

Use this when LunarMarch should appear in every local Codex or OpenCode chat for the current user:

```bash
python3 /absolute/path/to/LunarMarch/scripts/install_skill.py --scope user
```

The default creates a symlink at `$HOME/.agents/skills/lunar-march`, so edits in the LunarMarch repository are immediately visible to newly loaded chats. Both Codex and OpenCode discover the agent-compatible location.

## Repository-scoped

Use this when a project should carry its own reviewed copy:

```bash
python3 /absolute/path/to/LunarMarch/scripts/install_skill.py \
  --scope repo --repo-root /absolute/project
```

This copies the runtime bundle to `<project>/.agents/skills/lunar-march`. It can be committed so every Codex chat opened within that repository can discover the same version.

The installer refuses differing existing content. `--replace` moves the prior installation to a timestamped sibling backup before installing; it does not delete it. Use `--check` for a read-only inspection.

## Invoke it

Start a new chat, then use an explicit request such as:

```text
$lunar-march research this subsystem using three independent read-only angles, then synthesize the evidence.
```

```text
$lunar-march execute the plan at plans/migration.md as a resumable march. Keep Luna as the default worker and stop only for a real authorization boundary.
```

Codex or OpenCode may also invoke LunarMarch implicitly when a request matches its description. Explicit `$lunar-march` invocation is best for deliberate orchestration and makes delegation intent unambiguous.

Skill edits are normally detected automatically. Restart Codex if a newly installed or updated skill is not visible.

## Wider distribution

Keep LunarMarch as a standalone skill while developing and evaluating it. If it later needs one-click installation for other people or bundling with connectors, package the same skill as a Codex plugin without changing the orchestration core.
