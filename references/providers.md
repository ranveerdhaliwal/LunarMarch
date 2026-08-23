# Worker providers and transports

LunarMarch has a provider-neutral evidence core and two launch transports:

| Transport | Default model | Best fit |
|---|---|---|
| `codex` | `gpt-5.6-luna` | Native Codex-family workflow with an enforced workspace sandbox. |
| `opencode` | `deepseek/deepseek-v4-flash` | Low-cost external workers and future providers supported by OpenCode. |

Transport adapters only start workers and capture their final output. Contracts, role boundaries, source snapshots, acceptance checks, immutable terminal records, gates, and independent review do not depend on the provider.

## DeepSeek through OpenCode

Current DeepSeek documentation lists `deepseek-v4-flash` and `deepseek-v4-pro` through an OpenAI-compatible endpoint. OpenCode has a built-in DeepSeek provider and identifies models as `provider/model`. The current worker ID is therefore `deepseek/deepseek-v4-flash`. Check the current model list before relying on an ID because provider catalogs change.

1. Install OpenCode using its official instructions.
2. In OpenCode, run `/connect`, choose DeepSeek, and enter the API key. Alternatively use `opencode auth login`. OpenCode saves `/connect` credentials in its local credential store. LunarMarch intentionally strips API-key environment variables from OpenCode child processes, so this saved credential is the required setup for LunarMarch workers.
3. Run `opencode models deepseek` and confirm the exact model ID.
4. Never add the key to a task contract, prompt, shell argument, committed `.env`, or LunarMarch run root.
5. Launch a bounded worker:

```bash
python3 scripts/lunarmarch.py launch \
  --run-root /absolute/project-run \
  --task-id bounded-task \
  --role builder \
  --transport opencode \
  --model deepseek/deepseek-v4-flash \
  --run-checks
```

The adapter runs `opencode --pure run`, attaches a fresh prompt from a file rather than placing it in the process argument list, disables automatic sharing and updates, sanitizes the inherited environment, closes standard input, enforces a timeout, and injects a temporary agent policy. Nested tasks, external-directory access, web tools, and skills are denied. Read-only LunarMarch roles additionally deny editing and shell execution. Writer roles use OpenCode auto approval only for operations not explicitly denied.

Worker stdout and stderr are retained in the run root as review evidence, and OpenCode stdout becomes the worker report. Treat run roots as potentially sensitive task artifacts even though credentials are excluded by design; do not ask workers to print secrets.

OpenCode's permission system is a tool policy, not an operating-system security boundary. A writer with shell access may still be inappropriate for hostile code, secrets, production credentials, or consequential systems. Use an isolated container or the Codex workspace sandbox for stronger containment.

## DeepSeek directly through Codex

DeepSeek also publishes an official Codex setup script. It configures the Codex model catalog and provider in `~/.codex/models.json` and `~/.codex/config.toml`, backs up the prior Codex configuration under `~/.codex/backup-deepseek`, and points Codex at DeepSeek's Responses-compatible endpoint. Review the script and its changes before running it; it is a remote shell script and it stores the credential in the local Codex provider configuration. It does not create a LunarMarch repository file or environment file.

For WSL/Linux, the documented entry point is:

```bash
bash <(curl -fsSL https://cdn.deepseek.com/api-docs/codex-deepseek-setup.sh)
```

Choose the model in the interactive menu, enter the key when prompted, then restart Codex. The script provides a restore option and keeps the original configuration in its backup directory.

After that setup, LunarMarch can use the direct Codex transport with the DeepSeek model slug:

```bash
python3 scripts/lunarmarch.py launch \
  --run-root /absolute/project-run \
  --task-id bounded-task \
  --role builder \
  --transport codex \
  --model deepseek-v4-flash \
  --run-checks
```

This route is native and useful for a standalone Codex smoke test. The tradeoff is that the Codex configuration is global for that local Codex installation: switching the default provider to DeepSeek can affect subsequent Codex sessions until the backed-up configuration is restored or the provider is changed again. Keep GPT-5.6 Luna as the normal LunarMarch default unless a deliberate DeepSeek Codex run is being tested.

Official references:

- [DeepSeek API compatibility and supported agent tools](https://api-docs.deepseek.com/guides/function_calling)
- [DeepSeek model catalog and pricing](https://api-docs.deepseek.com/quick_start/pricing/)
- [OpenCode DeepSeek provider setup](https://opencode.ai/docs/providers/)
- [OpenCode CLI model, agent, directory, variant, and non-interactive flags](https://dev.opencode.ai/docs/cli/)
- [OpenCode permissions](https://opencode.ai/docs/permissions/)
- [DeepSeek Codex integration](https://api-docs.deepseek.com/quick_start/agent_integrations/codex)

## Sol orchestrator with DeepSeek workers

There are two distinct cost arrangements:

1. **Codex-hosted parent:** select GPT-5.6 Sol in Codex and have LunarMarch launch DeepSeek workers through OpenCode. DeepSeek worker calls do not use Codex model quota, but the parent task still uses Codex according to the user's plan.
2. **API-hosted parent in OpenCode:** configure OpenCode's primary model as `openai/gpt-5.6-sol`, load LunarMarch from the user-wide `.agents/skills/lunar-march` installation, and launch DeepSeek children through the LunarMarch OpenCode transport. This avoids relying on a Codex subscription, but Sol calls are billed to the configured OpenAI API account and DeepSeek calls to the DeepSeek account.

The second shape can start from [../examples/opencode-hybrid.json](../examples/opencode-hybrid.json). Copy it to the target project's `opencode.json`, authenticate OpenAI and DeepSeek through OpenCode, then start OpenCode in that project. The example denies OpenCode's untracked native Task delegation for the primary Build agent so delegated work goes through LunarMarch's durable launcher.

Official OpenAI documentation describes GPT-5.6 Sol as the frontier member for complex professional work and Luna as the efficient high-volume member. Use Sol for decomposition, consequential judgment, disagreement resolution, and final synthesis; send repetitive bounded work to Luna or DeepSeek only when objective gates can verify it.

- [OpenAI GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/latest-model)
- [GPT-5.6 Sol model page](https://developers.openai.com/api/docs/models/gpt-5.6-sol)
- [OpenCode model configuration](https://opencode.ai/docs/models)
- [OpenCode skill discovery, including `.agents/skills`](https://opencode.ai/docs/skills)

## Adding another provider later

If OpenCode already supports the provider, first try it without changing LunarMarch:

```bash
python3 scripts/lunarmarch.py launch \
  --transport opencode \
  --model provider/model-id \
  --run-root /absolute/run \
  --task-id bounded-task \
  --role builder
```

Add a new LunarMarch transport only when a provider needs a different executable or lifecycle. A transport must:

- accept one fresh resolved worker packet;
- bind and record the requested model identity without overstating the effective runtime identity;
- prevent nested delegation;
- distinguish read-only and writer authority;
- capture a nonempty final report;
- never persist secrets;
- return an exit code while leaving checks and semantic acceptance to the core;
- have fake-CLI regression tests before any paid live test.

Provider quality and cost comparisons must use separate controlled runs. Do not merge Codex and OpenCode results because their system prompts, tools, permission enforcement, telemetry, and caching differ.
