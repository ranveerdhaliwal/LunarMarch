#!/usr/bin/env python3
"""Reproducible context-policy evaluation for LunarMarch workers."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import math
import os
import platform
import random
import re
import signal
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


class EvalError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvalError(f"missing JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvalError(f"invalid JSON file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvalError(f"expected a JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def validate_suite(suite_path: Path) -> tuple[Path, dict[str, Any]]:
    suite_path = suite_path.expanduser().resolve()
    suite = read_object(suite_path)
    if suite.get("format") != "lunarmarch-context-suite-v1":
        raise EvalError("unsupported context suite format")
    conditions = suite.get("conditions")
    cases = suite.get("cases")
    if not isinstance(conditions, list) or not conditions or len(set(conditions)) != len(conditions):
        raise EvalError("suite conditions must be a unique non-empty array")
    if any(not isinstance(item, str) or not item for item in conditions):
        raise EvalError("suite condition names must be non-empty strings")
    if not isinstance(cases, list) or not cases:
        raise EvalError("suite cases must be a non-empty array")
    case_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str):
            raise EvalError("each case needs an id")
        if case["id"] in case_ids:
            raise EvalError(f"duplicate case id: {case['id']}")
        case_ids.add(case["id"])
        if set(case.get("contexts", {})) != set(conditions):
            raise EvalError(f"case {case['id']} must define every condition exactly once")
        for field in ("project", "task", "grader_tests"):
            path = (suite_path.parent / case.get(field, "")).resolve()
            if not path.exists():
                raise EvalError(f"case {case['id']} missing {field}: {path}")
        if not isinstance(case.get("allowed_paths"), list):
            raise EvalError(f"case {case['id']} allowed_paths must be an array")
        graders = case.get("graders")
        if not isinstance(graders, list) or not graders:
            raise EvalError(f"case {case['id']} needs graders")
        current_weight = sum(float(item.get("weight", 0)) for item in graders if isinstance(item, dict))
        if not math.isclose(current_weight + float(suite.get("scope_weight", 0)), 100.0):
            raise EvalError(f"case {case['id']} grader plus scope weights must total 100")
    return suite_path, suite


def load_context(suite_dir: Path, parts: Any) -> str:
    if not isinstance(parts, list) or not parts:
        raise EvalError("context definition must be a non-empty array")
    output: list[str] = []
    for part in parts:
        if not isinstance(part, dict) or not isinstance(part.get("path"), str):
            raise EvalError("context part needs a path")
        repeat = part.get("repeat", 1)
        if not isinstance(repeat, int) or repeat < 1 or repeat > 1000:
            raise EvalError("context repeat must be an integer from 1 to 1000")
        path = (suite_dir / part["path"]).resolve()
        try:
            path.relative_to(suite_dir.resolve())
        except ValueError as exc:
            raise EvalError(f"context path escapes suite: {path}") from exc
        text = path.read_text(encoding="utf-8").rstrip() + "\n"
        output.extend(text for _ in range(repeat))
    return "\n".join(output).strip() + "\n"


def plan_trials(suite: dict[str, Any], repetitions: int, seed: int, selected: Iterable[str] | None = None) -> list[dict[str, Any]]:
    if repetitions < 1:
        raise EvalError("repetitions must be positive")
    conditions = list(suite["conditions"])
    if selected:
        requested = list(dict.fromkeys(selected))
        unknown = sorted(set(requested) - set(conditions))
        if unknown:
            raise EvalError(f"unknown conditions: {', '.join(unknown)}")
        conditions = [item for item in conditions if item in requested]
    rng = random.Random(seed)
    base = conditions[:]
    rng.shuffle(base)
    trials: list[dict[str, Any]] = []
    sequence = 0
    for case in suite["cases"]:
        for repetition in range(1, repetitions + 1):
            offset = (repetition - 1) % len(base)
            block = base[offset:] + base[:offset]
            for position, condition in enumerate(block, start=1):
                sequence += 1
                opaque = hashlib.sha256(
                    f"{seed}:{case['id']}:{repetition}:{condition}".encode("utf-8")
                ).hexdigest()[:12]
                trials.append(
                    {
                        "sequence": sequence,
                        "case_id": case["id"],
                        "repetition": repetition,
                        "position": position,
                        "condition": condition,
                        "trial_id": f"trial-{sequence:04d}-{opaque}",
                    }
                )
    return trials


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def snapshot(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part in {".git", "__pycache__"} for part in relative.parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        result[relative.as_posix()] = _sha256(path)
    return result


def changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    keys = set(before) | set(after)
    return sorted(path for path in keys if before.get(path) != after.get(path))


def path_allowed(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/").strip("/")
    for raw in patterns:
        pattern = raw.replace("\\", "/").strip("/")
        if any(token in pattern for token in "*?["):
            if fnmatch.fnmatchcase(normalized, pattern):
                return True
        elif normalized == pattern or normalized.startswith(pattern + "/"):
            return True
    return False


def extract_usage_jsonl(text: str) -> dict[str, int | None]:
    candidates: list[dict[str, Any]] = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(event, dict)
            and event.get("type") == "turn.completed"
            and isinstance(event.get("usage"), dict)
        ):
            candidates.append(event["usage"])
    if not candidates:
        return {
            "input_tokens": None,
            "cached_input_tokens": None,
            "uncached_input_tokens": None,
            "output_tokens": None,
            "reasoning_tokens": None,
            "total_tokens": None,
        }
    # `codex exec --json` emits one authoritative cumulative usage object on the
    # terminal turn.completed event. If a future CLI emits several turns, the
    # final completed turn is the cumulative record for this single exec run.
    usage = candidates[-1]
    input_tokens = _optional_int(usage.get("input_tokens"))
    output_tokens = _optional_int(usage.get("output_tokens"))
    total_tokens = _optional_int(usage.get("total_tokens"))
    details = usage.get("input_tokens_details") if isinstance(usage.get("input_tokens_details"), dict) else {}
    output_details = usage.get("output_tokens_details") if isinstance(usage.get("output_tokens_details"), dict) else {}
    cached = _optional_int(details.get("cached_tokens", usage.get("cached_input_tokens")))
    reasoning = _optional_int(
        output_details.get(
            "reasoning_tokens",
            usage.get("reasoning_output_tokens", usage.get("reasoning_tokens")),
        )
    )
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached,
        "uncached_input_tokens": input_tokens - cached if input_tokens is not None and cached is not None else None,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning,
        "total_tokens": total_tokens,
    }


def extract_event_metrics(text: str) -> dict[str, int | str | None]:
    command_ids: set[str] = set()
    file_change_ids: set[str] = set()
    agent_messages = 0
    thread_id: str | None = None
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
            thread_id = event["thread_id"]
        if event.get("type") != "item.completed" or not isinstance(event.get("item"), dict):
            continue
        item = event["item"]
        item_id = str(item.get("id", ""))
        if item.get("type") == "command_execution":
            command_ids.add(item_id)
        elif item.get("type") == "file_change":
            file_change_ids.add(item_id)
        elif item.get("type") == "agent_message":
            agent_messages += 1
    return {
        "thread_id": thread_id,
        "command_calls": len(command_ids),
        "file_change_calls": len(file_change_ids),
        "agent_messages": agent_messages,
    }


def _optional_int(value: Any) -> int | None:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def parse_unittest(text: str, returncode: int) -> tuple[int | None, int | None, float]:
    matches = re.findall(r"Ran (\d+) tests?", text)
    if not matches:
        return None, None, 1.0 if returncode == 0 else 0.0
    total = int(matches[-1])
    failure_counts = re.findall(r"(?:failures|errors)=(\d+)", text)
    if returncode != 0 and not failure_counts:
        return 0, total, 0.0
    failures = sum(int(value) for value in failure_counts)
    passed = max(0, total - failures) if returncode != 0 else total
    return passed, total, passed / total if total else (1.0 if returncode == 0 else 0.0)


def command_result(
    command: list[str],
    cwd: Path,
    timeout: int,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    output_limit: int | None = 12000,
) -> dict[str, Any]:
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=cwd,
        text=True,
        stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        start_new_session=os.name == "posix",
    )
    try:
        stdout, stderr = process.communicate(input=input_text, timeout=timeout)
        returncode = process.returncode
        timed_out = False
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        stdout, stderr = process.communicate()
        returncode = 124
        timed_out = True
    if output_limit is not None:
        stdout = stdout[-output_limit:]
        stderr = stderr[-output_limit:]
    return {
        "command": command,
        "returncode": returncode,
        "timed_out": timed_out,
        "wall_seconds": round(time.monotonic() - started, 6),
        "stdout": stdout,
        "stderr": stderr,
    }


def render_prompt(task: str, context: str, report_path: Path, public_command: list[str]) -> str:
    verification = " ".join(public_command)
    return f"""# Isolated implementation trial

Complete the task using only the supplied context packet and files in the current project. Do not search outside the project, inspect sibling trials or evaluation files, delegate, commit, or modify tests. Keep changes within the task's declared file boundary. Run the public tests. Write a concise final report to the configured output path.

Public verification command: `{verification}`

## Task

{task.strip()}

## Context packet

{context.strip()}

## Report

The final response is captured at: {report_path}
"""


def runtime_metadata(codex_bin: str, suite_path: Path, model: str, effort: str, seed: int) -> dict[str, Any]:
    version = subprocess.run([codex_bin, "--version"], text=True, capture_output=True, check=False)
    commit = subprocess.run(
        ["git", "-C", str(suite_path.parent), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    dirty = subprocess.run(
        ["git", "-C", str(suite_path.parent), "status", "--porcelain"],
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "created_at": utc_now(),
        "requested_model": model,
        "requested_effort": effort,
        "codex_version": (version.stdout or version.stderr).strip(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "suite": str(suite_path),
        "suite_sha256": _sha256(suite_path),
        "repository_commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "repository_dirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else None,
        "seed": seed,
        "effective_remote_model": None,
        "note": "Requested model is launch configuration; effective runtime identity is recorded only if telemetry proves it.",
    }


def suite_content_manifest(suite_path: Path, suite: dict[str, Any]) -> dict[str, str]:
    suite_dir = suite_path.parent
    paths: set[Path] = {suite_path}
    for case in suite["cases"]:
        for field in ("task",):
            paths.add((suite_dir / case[field]).resolve())
        for field in ("project", "grader_tests"):
            root = (suite_dir / case[field]).resolve()
            paths.update(
                path
                for path in root.rglob("*")
                if path.is_file()
                and ".git" not in path.parts
                and "__pycache__" not in path.parts
                and path.suffix not in {".pyc", ".pyo"}
            )
        for parts in case["contexts"].values():
            for part in parts:
                paths.add((suite_dir / part["path"]).resolve())
    manifest = {path.relative_to(suite_dir).as_posix(): _sha256(path) for path in sorted(paths)}
    return manifest


def manifest_fingerprint(manifest: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for path, value in sorted(manifest.items()):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(value.encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def run_trial(
    suite_path: Path,
    suite: dict[str, Any],
    case: dict[str, Any],
    trial: dict[str, Any],
    output: Path,
    model: str,
    effort: str,
    codex_bin: str,
    timeout: int,
) -> dict[str, Any]:
    suite_dir = suite_path.parent
    trial_root = output / "trials" / trial["trial_id"]
    project = trial_root / "project"
    trial_root.mkdir(parents=True, exist_ok=False)
    shutil.copytree(
        suite_dir / case["project"],
        project,
        ignore=shutil.ignore_patterns(".git", ".hg", ".svn", "__pycache__", "*.pyc", "*.pyo"),
    )
    git_commands = [
        ["git", "init", "-b", "main"],
        ["git", "add", "."],
        [
            "git",
            "-c",
            "user.name=LunarMarch Eval",
            "-c",
            "user.email=lunarmarch-eval@invalid",
            "commit",
            "-m",
            "evaluation baseline",
        ],
    ]
    for git_command in git_commands:
        initialized = subprocess.run(git_command, cwd=project, text=True, capture_output=True, check=False)
        if initialized.returncode != 0:
            raise EvalError(f"failed to initialize trial repository: {initialized.stderr.strip()}")
    baseline = snapshot(project)
    context = load_context(suite_dir, case["contexts"][trial["condition"]])
    task = (suite_dir / case["task"]).read_text(encoding="utf-8")
    report_path = trial_root / "report.md"
    public_grader = next((item for item in case["graders"] if item.get("name") == "public-tests"), None)
    if not isinstance(public_grader, dict):
        raise EvalError(f"case {case['id']} needs a public-tests grader")
    prompt = render_prompt(task, context, report_path, public_grader["command"])
    (trial_root / "prompt.md").write_text(prompt, encoding="utf-8")
    command = [
        codex_bin,
        "exec",
        "--ephemeral",
        "-C",
        str(project),
        "-m",
        model,
        "-c",
        f'model_reasoning_effort="{effort}"',
        "-c",
        "agents.max_depth=0",
        "--approve-for-me",
        "--json",
        "--output-last-message",
        str(report_path),
        "-",
    ]
    worker = command_result(command, project, timeout, input_text=prompt, output_limit=None)
    (trial_root / "events.jsonl").write_text(worker["stdout"], encoding="utf-8")
    (trial_root / "worker.stderr.log").write_text(worker["stderr"], encoding="utf-8")
    current = snapshot(project)
    changed = changed_paths(baseline, current)
    outside = [item for item in changed if not path_allowed(item, case["allowed_paths"])]

    grader_tests = trial_root / "grader-tests"
    shutil.copytree(suite_dir / case["grader_tests"], grader_tests)
    grader_env = os.environ.copy()
    grader_env["PYTHONPATH"] = str(project)
    grader_results: list[dict[str, Any]] = []
    grader_started = time.monotonic()
    quality = 0.0
    for grader in case["graders"]:
        command_tokens = [str(grader_tests) if token == "{grader_tests}" else token for token in grader["command"]]
        result = command_result(command_tokens, project, timeout, grader_env)
        combined = result["stdout"] + "\n" + result["stderr"]
        if grader["kind"] == "unittest":
            passed, total, score = parse_unittest(combined, result["returncode"])
        else:
            passed, total, score = None, None, 1.0 if result["returncode"] == 0 else 0.0
        result.update(
            {
                "name": grader["name"],
                "kind": grader["kind"],
                "weight": grader["weight"],
                "passed_tests": passed,
                "total_tests": total,
                "score": score,
            }
        )
        quality += float(grader["weight"]) * score
        grader_results.append(result)
    scope_pass = not outside
    quality += float(suite["scope_weight"]) * (1.0 if scope_pass else 0.0)
    usage = extract_usage_jsonl(worker["stdout"])
    events = extract_event_metrics(worker["stdout"])
    graders_clear = all(
        item["returncode"] == 0 and not item["timed_out"] and math.isclose(float(item["score"]), 1.0)
        for item in grader_results
    )
    result = {
        "format": "lunarmarch-context-trial-v1",
        **trial,
        "requested_model": model,
        "requested_effort": effort,
        "context_bytes": len(context.encode("utf-8")),
        "context_words": len(context.split()),
        "prompt_bytes": len(prompt.encode("utf-8")),
        "worker": {key: value for key, value in worker.items() if key not in {"stdout", "stderr"}},
        "usage": usage,
        "events": events,
        "changed_paths": changed,
        "outside_allowed_paths": outside,
        "scope_pass": scope_pass,
        "report_present": report_path.is_file() and report_path.stat().st_size > 0,
        "graders": grader_results,
        "grader_wall_seconds": round(time.monotonic() - grader_started, 6),
        "quality_score": round(quality, 4),
        "task_success": quality >= 100.0 and worker["returncode"] == 0 and not worker["timed_out"] and graders_clear,
        "infrastructure_failure": worker["returncode"] != 0 and not changed,
    }
    write_json(trial_root / "result.json", result)
    return result


def _mean(values: list[float | int]) -> float | None:
    return round(statistics.mean(values), 4) if values else None


def _median(values: list[float | int]) -> float | None:
    return round(statistics.median(values), 4) if values else None


def _stdev(values: list[float | int]) -> float | None:
    return round(statistics.stdev(values), 4) if len(values) > 1 else 0.0 if values else None


def _p95(values: list[float | int]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(float(ordered[index]), 4)


def _wilson(successes: int, total: int) -> list[float] | None:
    if total == 0:
        return None
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / denominator
    return [round(max(0.0, center - margin), 4), round(min(1.0, center + margin), 4)]


def summarize(
    results: list[dict[str, Any]],
    conditions: list[str],
    quality_tolerance: float = 2.0,
    expected_trial_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    actual_ids = [str(item.get("trial_id")) for item in results]
    duplicate_ids = sorted({item for item in actual_ids if actual_ids.count(item) > 1})
    expected = set(expected_trial_ids) if expected_trial_ids is not None else set(actual_ids)
    actual = set(actual_ids)
    missing_trials = sorted(expected - actual)
    unexpected_trials = sorted(actual - expected)
    run_complete = not duplicate_ids and not missing_trials and not unexpected_trials and len(actual_ids) == len(expected)
    aggregates: dict[str, Any] = {}
    for condition in conditions:
        rows = [item for item in results if item["condition"] == condition]
        quality = [float(item["quality_score"]) for item in rows]
        latency = [float(item["worker"]["wall_seconds"]) for item in rows]
        usage_summary: dict[str, Any] = {}
        for field in ("input_tokens", "cached_input_tokens", "uncached_input_tokens", "output_tokens", "reasoning_tokens", "total_tokens"):
            values = [int(item["usage"][field]) for item in rows if item["usage"].get(field) is not None]
            usage_summary[field] = {"mean": _mean(values), "median": _median(values), "observed": len(values)}
        successes = sum(bool(item["task_success"]) for item in rows)
        aggregates[condition] = {
            "trials": len(rows),
            "task_success_rate": round(successes / len(rows), 4) if rows else None,
            "task_success_wilson_95": _wilson(successes, len(rows)),
            "infrastructure_failures": sum(bool(item["infrastructure_failure"]) for item in rows),
            "quality": {"mean": _mean(quality), "median": _median(quality), "stdev": _stdev(quality)},
            "worker_wall_seconds": {
                "mean": _mean(latency),
                "median": _median(latency),
                "p95": _p95(latency),
                "stdev": _stdev(latency),
            },
            "context_bytes": {"mean": _mean([item["context_bytes"] for item in rows])},
            "command_calls": {
                "mean": _mean([item.get("events", {}).get("command_calls", 0) for item in rows]),
                "median": _median([item.get("events", {}).get("command_calls", 0) for item in rows]),
            },
            "usage": usage_summary,
        }
    paired: dict[str, Any] = {}
    contract_rows = {(item["case_id"], item["repetition"]): item for item in results if item["condition"] == "contract"}
    for condition in conditions:
        if condition == "contract":
            continue
        differences_quality: list[float] = []
        differences_tokens: list[float] = []
        for item in results:
            key = (item["case_id"], item["repetition"])
            if item["condition"] != condition or key not in contract_rows:
                continue
            control = contract_rows[key]
            differences_quality.append(float(item["quality_score"]) - float(control["quality_score"]))
            left = item["usage"].get("total_tokens")
            right = control["usage"].get("total_tokens")
            if left is not None and right is not None:
                differences_tokens.append(float(left) - float(right))
        paired[condition] = {
            "quality_pairs": len(differences_quality),
            "token_pairs": len(differences_tokens),
            "mean_quality_delta_vs_contract": _mean(differences_quality),
            "mean_total_token_delta_vs_contract": _mean(differences_tokens),
        }
    padded = paired.get("contract-padded", {})
    quality_pairs = int(padded.get("quality_pairs") or 0)
    token_pairs = int(padded.get("token_pairs") or 0)
    eligible = run_complete and quality_pairs >= 5 and token_pairs >= 5 and quality_pairs == token_pairs
    quality_delta = padded.get("mean_quality_delta_vs_contract")
    token_delta = padded.get("mean_total_token_delta_vs_contract")
    default_supported = bool(
        eligible
        and quality_delta is not None
        and token_delta is not None
        and quality_delta <= quality_tolerance
        and token_delta > 0
    )
    return {
        "format": "lunarmarch-context-summary-v1",
        "generated_at": utc_now(),
        "total_trials": len(results),
        "run_integrity": {
            "complete": run_complete,
            "expected_trials": len(expected),
            "observed_trials": len(actual_ids),
            "missing_trial_ids": missing_trials,
            "unexpected_trial_ids": unexpected_trials,
            "duplicate_trial_ids": duplicate_ids,
        },
        "conditions": aggregates,
        "paired_vs_contract": paired,
        "decision": {
            "quality_tolerance_points": quality_tolerance,
            "minimum_pairs": 5,
            "eligible": eligible,
            "compact_contract_default_supported": default_supported,
            "rule": "contract-padded minus contract quality <= tolerance and total-token delta > 0",
        },
        "interpretation_boundary": "Exploratory evidence for these cases and runtime only; not a general model-quality claim.",
    }


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# LunarMarch context evaluation",
        "",
        summary["interpretation_boundary"],
        "",
        "| Condition | Trials | Success | Quality mean | Input tokens mean | Total tokens mean | Worker seconds mean |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition, value in summary["conditions"].items():
        usage = value["usage"]
        lines.append(
            f"| {condition} | {value['trials']} | {value['task_success_rate']} | {value['quality']['mean']} | "
            f"{usage['input_tokens']['mean']} | {usage['total_tokens']['mean']} | {value['worker_wall_seconds']['mean']} |"
        )
    lines.extend(["", "## Paired differences from compact contract", ""])
    for condition, value in summary["paired_vs_contract"].items():
        lines.append(
            f"- `{condition}`: quality {value['mean_quality_delta_vs_contract']}, total tokens "
            f"{value['mean_total_token_delta_vs_contract']} across {value['quality_pairs']} quality pair(s) "
            f"and {value['token_pairs']} token pair(s)."
        )
    lines.extend(
        [
            "",
            f"Decision eligible: `{summary['decision']['eligible']}`. Compact-contract default supported by the predeclared exploratory rule: `{summary['decision']['compact_contract_default_supported']}`.",
            "",
            "Lower usage is an improvement only if quality remains within the predeclared tolerance. Inspect every trial result and artifact before publishing a claim.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Measure Luna quality and usage under controlled context policies")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "run"):
        command = commands.add_parser(name)
        command.add_argument("--suite", required=True, type=Path)
        command.add_argument("--repetitions", type=int, default=5)
        command.add_argument("--seed", type=int, default=20260822)
        command.add_argument("--conditions", nargs="+")
        if name == "run":
            command.add_argument("--output", required=True, type=Path)
            command.add_argument("--model", default="gpt-5.6-luna")
            command.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"], default="high")
            command.add_argument("--codex-bin", default="codex")
            command.add_argument("--timeout", type=int, default=1800)
            command.add_argument("--quality-tolerance", type=float, default=2.0)
            command.add_argument("--allow-dirty-suite", action="store_true")
    summary = commands.add_parser("summarize")
    summary.add_argument("--run-root", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "summarize":
            run_root = args.run_root.expanduser().resolve()
            manifest = read_object(run_root / "manifest.json")
            result_paths = sorted((run_root / "trials").glob("*/result.json"))
            results = [read_object(path) for path in result_paths]
            for result_path, result in zip(result_paths, results, strict=True):
                events_path = result_path.parent / "events.jsonl"
                if events_path.is_file():
                    events_text = events_path.read_text(encoding="utf-8")
                    result["usage"] = extract_usage_jsonl(events_text)
                    result["events"] = extract_event_metrics(events_text)
                    write_json(result_path, result)
            expected_ids = [item["trial_id"] for item in manifest.get("trials", [])]
            summary = summarize(
                results,
                manifest["conditions"],
                float(manifest.get("quality_tolerance", 2.0)),
                expected_ids,
            )
            write_json(run_root / "summary.json", summary)
            (run_root / "report.md").write_text(render_report(summary), encoding="utf-8")
            print(json.dumps(summary, indent=2, sort_keys=True))
            return 0
        suite_path, suite = validate_suite(args.suite)
        trials = plan_trials(suite, args.repetitions, args.seed, args.conditions)
        if args.command == "plan":
            context_sizes: dict[str, Any] = {}
            for case in suite["cases"]:
                context_sizes[case["id"]] = {
                    condition: {
                        "bytes": len(load_context(suite_path.parent, case["contexts"][condition]).encode("utf-8")),
                        "words": len(load_context(suite_path.parent, case["contexts"][condition]).split()),
                    }
                    for condition in suite["conditions"]
                    if not args.conditions or condition in args.conditions
                }
            print(json.dumps({"trials": trials, "context_sizes": context_sizes}, indent=2, sort_keys=True))
            return 0
        output = args.output.expanduser().resolve()
        if output.exists() and any(output.iterdir()):
            raise EvalError(f"output directory is not empty: {output}")
        output.mkdir(parents=True, exist_ok=True)
        selected_conditions = [item for item in suite["conditions"] if not args.conditions or item in args.conditions]
        metadata = runtime_metadata(args.codex_bin, suite_path, args.model, args.effort, args.seed)
        if metadata["repository_dirty"] and not args.allow_dirty_suite:
            raise EvalError("suite repository has uncommitted changes; commit them or pass --allow-dirty-suite for a non-publishable run")
        content_manifest = suite_content_manifest(suite_path, suite)
        metadata["suite_content_manifest"] = content_manifest
        metadata["suite_content_fingerprint"] = manifest_fingerprint(content_manifest)
        metadata["dirty_suite_override"] = bool(args.allow_dirty_suite)
        manifest = {
            "format": "lunarmarch-context-run-v1",
            "conditions": selected_conditions,
            "trials": trials,
            "runtime": metadata,
            "quality_tolerance": args.quality_tolerance,
        }
        write_json(output / "manifest.json", manifest)
        cases = {case["id"]: case for case in suite["cases"]}
        results = []
        for trial in trials:
            print(f"[{trial['sequence']}/{len(trials)}] {trial['trial_id']}", flush=True)
            results.append(
                run_trial(
                    suite_path,
                    suite,
                    cases[trial["case_id"]],
                    trial,
                    output,
                    args.model,
                    args.effort,
                    args.codex_bin,
                    args.timeout,
                )
            )
        summary_value = summarize(
            results,
            selected_conditions,
            args.quality_tolerance,
            [item["trial_id"] for item in trials],
        )
        write_json(output / "summary.json", summary_value)
        (output / "report.md").write_text(render_report(summary_value), encoding="utf-8")
        print(json.dumps(summary_value, indent=2, sort_keys=True))
        return 0
    except (EvalError, OSError, ValueError) as exc:
        print(f"context-eval: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
