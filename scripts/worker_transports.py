"""External worker transport adapters for LunarMarch.

Adapters only launch a bounded worker. Durable contracts, snapshots, checks, and
acceptance remain transport-independent in ``lm_core``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_TRANSPORTS = {"codex", "opencode"}
DEFAULT_MODELS = {
    "codex": "gpt-5.6-luna",
    "opencode": "deepseek/deepseek-v4-flash",
}


@dataclass(frozen=True)
class WorkerInvocation:
    command: list[str]
    env: dict[str, str]
    stdin: str | None
    capture_stdout_as_report: bool
    logged_command: list[str]


def _sanitized_environment() -> dict[str, str]:
    safe_names = {
        "APPDATA",
        "COMSPEC",
        "HOME",
        "LANG",
        "LOCALAPPDATA",
        "LOGNAME",
        "PATH",
        "PATHEXT",
        "SHELL",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "USER",
        "USERPROFILE",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
    }
    return {key: value for key, value in os.environ.items() if key in safe_names or key.startswith("LC_")}


def default_model_for_transport(transport: str) -> str:
    try:
        return DEFAULT_MODELS[transport]
    except KeyError as exc:
        raise ValueError(f"unsupported worker transport: {transport}") from exc


def _opencode_agent(sandbox: str) -> tuple[str, dict[str, object]]:
    common: dict[str, object] = {
        "task": "deny",
        "external_directory": "deny",
        "webfetch": "deny",
        "websearch": "deny",
        "skill": "deny",
    }
    if sandbox == "read-only":
        name = "lunarmarch-readonly"
        common.update({"edit": "deny", "bash": "deny"})
        description = "Read-only LunarMarch evidence worker"
        steps = 20
    else:
        name = "lunarmarch-writer"
        description = "Bounded LunarMarch implementation worker"
        steps = 40
    return name, {
        "description": description,
        "mode": "primary",
        "steps": steps,
        "permission": common,
    }


def build_worker_invocation(
    transport: str,
    executable: str,
    project_root: Path,
    model: str,
    effort: str | None,
    variant: str | None,
    sandbox: str,
    report_path: Path,
    prompt_path: Path,
    prompt: str,
) -> WorkerInvocation:
    if sandbox not in {"read-only", "workspace-write"}:
        raise ValueError(f"unsupported worker sandbox: {sandbox}")
    if transport == "codex":
        if effort is None:
            raise ValueError("Codex transport requires reasoning effort")
        command = [
            executable,
            "exec",
            "--ephemeral",
            "-C",
            str(project_root),
            "-m",
            model,
            "-c",
            f'model_reasoning_effort="{effort}"',
            "-c",
            "agents.max_depth=0",
            "--json",
            "--output-last-message",
            str(report_path),
            "-",
        ]
        if sandbox == "workspace-write":
            command.insert(-1, "--approve-for-me")
        else:
            command[-1:-1] = ["-s", sandbox]
        # Codex authentication and desktop integration may rely on environment
        # variables in addition to HOME-backed state. Preserve its established
        # launch behavior; the third-party OpenCode boundary is sanitized below.
        return WorkerInvocation(command, os.environ.copy(), prompt, False, command[:])

    if transport == "opencode":
        if "/" not in model:
            raise ValueError("OpenCode model must use provider/model format")
        agent_name, agent = _opencode_agent(sandbox)
        inline_config = {
            "$schema": "https://opencode.ai/config.json",
            "agent": {agent_name: agent},
        }
        env = _sanitized_environment()
        env.update(
            {
                "OPENCODE_CONFIG_CONTENT": json.dumps(inline_config, separators=(",", ":")),
                "OPENCODE_AUTO_SHARE": "false",
                "OPENCODE_DISABLE_AUTOUPDATE": "true",
            }
        )
        command = [
            executable,
            "--pure",
            "run",
            "--dir",
            str(project_root),
            "--model",
            model,
            "--agent",
            agent_name,
            "--format",
            "default",
            "--file",
            str(prompt_path),
        ]
        if variant:
            command.extend(["--variant", variant])
        if sandbox == "workspace-write":
            command.append("--auto")
        command.append("Execute the attached LunarMarch worker packet and return its requested report.")
        return WorkerInvocation(command, env, None, True, command[:])

    raise ValueError(f"unsupported worker transport: {transport}")
