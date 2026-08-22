"""Deterministic run state and integrity helpers for LunarMarch.

This module deliberately proves only objective facts. It does not infer whether a
worker's prose or implementation semantically satisfies a task.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
TASK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
ROLES = {
    "scout",
    "builder",
    "reviewer",
    "fixer",
    "verifier",
    "sentinel",
    "recovery",
    "auditor",
    "clerk",
}
WRITE_ROLES = {"builder", "fixer"}
READ_ONLY_ROLES = ROLES - WRITE_ROLES
RISKS = {"trivial", "routine", "medium", "high"}
MODES = {"quick", "research", "task", "march"}

ROLE_GUIDANCE = {
    "scout": "Investigate the bounded question read-only. Cite exact evidence and separate fact, inference, and unknown.",
    "builder": "Implement exactly the bounded objective inside allowed paths. Run relevant checks and never self-approve.",
    "reviewer": "Independently and adversarially review the supplied task and current implementation. Stay project-read-only; do not repair findings.",
    "fixer": "Repair only supplied task-relevant findings inside the existing write scope. Do not widen the task.",
    "verifier": "Establish exactly one assigned technical predicate. Stay read-only and report procedure, evidence, and limitations.",
    "sentinel": "Monitor only the named long-running process. Report material change, completion, or blocker; unchanged state is expected.",
    "recovery": "Forensically classify interrupted or suspect work without modifying the project. Recommend a disposition; do not perform it.",
    "auditor": "Audit the frozen phase and cross-task integration read-only. Surface remediation-ready findings; do not approve the phase.",
    "clerk": "Compress and reconcile existing evidence read-only. Never invent proof, rerun verification, waive failures, or accept work.",
}


class LunarMarchError(RuntimeError):
    """Expected user-facing LunarMarch failure."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def atomic_write_bytes(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_bytes(path, canonical_json_bytes(value))


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LunarMarchError(f"missing JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LunarMarchError(f"invalid JSON file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LunarMarchError(f"expected JSON object: {path}")
    return value


def resolve_existing_directory(path: str | Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise LunarMarchError(f"directory does not exist: {resolved}")
    return resolved


def resolve_within(root: Path, raw: str | Path) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise LunarMarchError(f"path escapes run root: {path}") from exc
    return path


def validate_contract(contract: dict[str, Any]) -> None:
    required = {
        "task_id",
        "phase",
        "objective",
        "role_hint",
        "risk",
        "allowed_paths",
        "acceptance_commands",
        "requirements",
        "inputs",
        "non_goals",
        "depends_on",
    }
    missing = sorted(required - contract.keys())
    extra = sorted(contract.keys() - required)
    if missing:
        raise LunarMarchError(f"contract missing fields: {', '.join(missing)}")
    if extra:
        raise LunarMarchError(f"contract has unknown fields: {', '.join(extra)}")
    for field in ("task_id", "phase"):
        value = contract[field]
        if not isinstance(value, str) or not TASK_ID_RE.fullmatch(value):
            raise LunarMarchError(f"invalid {field}: {value!r}")
    if not isinstance(contract["objective"], str) or not contract["objective"].strip():
        raise LunarMarchError("objective must be a non-empty string")
    if contract["role_hint"] not in ROLES:
        raise LunarMarchError(f"unknown role_hint: {contract['role_hint']!r}")
    if contract["risk"] not in RISKS:
        raise LunarMarchError(f"unknown risk: {contract['risk']!r}")
    for field in ("allowed_paths", "acceptance_commands", "requirements", "inputs", "non_goals", "depends_on"):
        value = contract[field]
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise LunarMarchError(f"{field} must be an array of non-empty strings")
    if not contract["requirements"]:
        raise LunarMarchError("requirements must contain at least one criterion")
    for raw in contract["allowed_paths"]:
        normalized = raw.replace("\\", "/").strip("/")
        if normalized in {"", ".", ".."} or normalized.startswith("../") or "/../" in normalized:
            raise LunarMarchError(f"unsafe allowed path: {raw!r}")
    for dependency in contract["depends_on"]:
        if not TASK_ID_RE.fullmatch(dependency):
            raise LunarMarchError(f"invalid depends_on task id: {dependency!r}")


def init_run(project_root: Path, run_root: Path, goal: str, mode: str) -> dict[str, Any]:
    project_root = resolve_existing_directory(project_root)
    run_root = Path(run_root).expanduser().resolve()
    if mode not in MODES:
        raise LunarMarchError(f"mode must be one of: {', '.join(sorted(MODES))}")
    if not goal.strip():
        raise LunarMarchError("goal must not be empty")
    if run_root.exists() and any(run_root.iterdir()):
        raise LunarMarchError(f"run root is not empty: {run_root}")
    run_root.mkdir(parents=True, exist_ok=True)
    for name in ("contracts", "attempts", "artifacts"):
        (run_root / name).mkdir(mode=0o700, exist_ok=True)
    created = utc_now()
    state = {
        "format": "lunarmarch-run-v1",
        "schema_version": SCHEMA_VERSION,
        "run_id": run_root.name,
        "project_root": str(project_root),
        "run_root": str(run_root),
        "goal": goal.strip(),
        "mode": mode,
        "status": "active",
        "created_at": created,
        "updated_at": created,
        "next_action": "register the first task contract",
        "phases": {},
        "tasks": {},
    }
    atomic_write_json(run_root / "state.json", state)
    return state


def load_state(run_root: Path) -> dict[str, Any]:
    run_root = resolve_existing_directory(run_root)
    state = read_json(run_root / "state.json")
    if state.get("format") != "lunarmarch-run-v1":
        raise LunarMarchError(f"unsupported run state format: {state.get('format')!r}")
    if Path(state.get("run_root", "")).resolve() != run_root:
        raise LunarMarchError("state run_root binding does not match requested run")
    return state


def save_state(run_root: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = utc_now()
    atomic_write_json(run_root / "state.json", state)


def add_task(run_root: Path, spec_path: Path) -> dict[str, Any]:
    run_root = resolve_existing_directory(run_root)
    state = load_state(run_root)
    contract = read_json(Path(spec_path).expanduser().resolve())
    validate_contract(contract)
    task_id = contract["task_id"]
    if task_id in state["tasks"]:
        raise LunarMarchError(f"task already exists: {task_id}")
    unknown_dependencies = [item for item in contract["depends_on"] if item not in state["tasks"]]
    if unknown_dependencies:
        raise LunarMarchError(f"dependencies must be registered first: {', '.join(unknown_dependencies)}")
    existing_phase = state.get("phases", {}).get(contract["phase"])
    if isinstance(existing_phase, dict) and existing_phase.get("status") != "active":
        raise LunarMarchError(f"cannot add task to non-active phase: {contract['phase']}")
    target = run_root / "contracts" / f"{task_id}.json"
    atomic_write_json(target, contract)
    binding = {
        "task_id": task_id,
        "phase": contract["phase"],
        "status": "pending",
        "contract": str(target.relative_to(run_root)),
        "contract_sha256": sha256_file(target),
        "attempts": [],
        "accepted_attempt": None,
    }
    state["tasks"][task_id] = binding
    phase = state["phases"].setdefault(
        contract["phase"],
        {"status": "active", "task_ids": [], "freeze": None, "audit_attempt": None},
    )
    phase["task_ids"].append(task_id)
    state["next_action"] = f"dispatch or reserve task {task_id}"
    save_state(run_root, state)
    return binding


def contract_for_task(run_root: Path, state: dict[str, Any], task_id: str) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    task = state.get("tasks", {}).get(task_id)
    if not isinstance(task, dict):
        raise LunarMarchError(f"unknown task: {task_id}")
    contract_path = resolve_within(run_root, task["contract"])
    if sha256_file(contract_path) != task["contract_sha256"]:
        raise LunarMarchError(f"immutable contract changed: {contract_path}")
    contract = read_json(contract_path)
    validate_contract(contract)
    return task, contract_path, contract


def _git_paths(project_root: Path) -> list[str] | None:
    probe = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "--is-inside-work-tree"],
        text=True,
        capture_output=True,
        check=False,
    )
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        return None
    result = subprocess.run(
        ["git", "-C", str(project_root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise LunarMarchError(f"git file census failed: {result.stderr.decode('utf-8', 'replace')[:1000]}")
    return [item.decode("utf-8", "surrogateescape") for item in result.stdout.split(b"\0") if item]


def _walk_paths(project_root: Path) -> list[str]:
    paths: list[str] = []
    for directory, names, files in os.walk(project_root, followlinks=False):
        current = Path(directory)
        names[:] = sorted(name for name in names if name not in {".git", ".lunarmarch", "__pycache__"})
        for name in sorted(files):
            paths.append((current / name).relative_to(project_root).as_posix())
    return paths


def _excluded_prefix(project_root: Path, run_root: Path | None) -> str | None:
    if run_root is None:
        return None
    try:
        relative = run_root.resolve().relative_to(project_root.resolve()).as_posix().strip("/")
    except ValueError:
        return None
    return relative or None


def capture_snapshot(project_root: Path, run_root: Path | None = None) -> dict[str, Any]:
    project_root = resolve_existing_directory(project_root)
    paths = _git_paths(project_root)
    source = "git" if paths is not None else "walk"
    if paths is None:
        paths = _walk_paths(project_root)
    excluded = _excluded_prefix(project_root, run_root)
    files: dict[str, dict[str, Any]] = {}
    for relative in sorted(set(paths)):
        normalized = relative.replace("\\", "/").lstrip("./")
        if not normalized or normalized == ".git" or normalized.startswith(".git/"):
            continue
        if normalized == ".lunarmarch" or normalized.startswith(".lunarmarch/"):
            continue
        if excluded and (normalized == excluded or normalized.startswith(excluded + "/")):
            continue
        path = project_root / normalized
        if path.is_symlink():
            files[normalized] = {"kind": "symlink", "target": os.readlink(path)}
        elif path.is_file():
            files[normalized] = {"kind": "file", "sha256": sha256_file(path), "size": path.stat().st_size}
    return {
        "format": "lunarmarch-snapshot-v1",
        "project_root": str(project_root),
        "source": source,
        "files": files,
    }


def compare_snapshots(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    before = baseline.get("files", {})
    after = current.get("files", {})
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise LunarMarchError("invalid snapshot files mapping")
    added = sorted(set(after) - set(before))
    deleted = sorted(set(before) - set(after))
    modified = sorted(path for path in set(before) & set(after) if before[path] != after[path])
    return {
        "format": "lunarmarch-scope-v1",
        "added": added,
        "modified": modified,
        "deleted": deleted,
        "changed": sorted(added + modified + deleted),
    }


def render_prompt(role: str, contract: dict[str, Any], report_path: Path) -> str:
    return f"""# LunarMarch worker packet

Role: {role}

{ROLE_GUIDANCE[role]}

Universal boundaries:
- Work only in the current project and this task contract.
- Never spawn or delegate to another worker.
- Preserve unrelated existing changes.
- Never weaken checks or invent evidence.
- Do not perform destructive, external, paid, deploy, release, commit, or push operations unless the contract and parent separately authorize them.
- Write the final report to the exact path below through the Codex final response mechanism.

Report path: {report_path}

Task contract:
```json
{json.dumps(contract, indent=2, sort_keys=True, ensure_ascii=False)}
```

Lead with a concise conclusion. Then state work or findings, verification actually performed, decisive evidence, changed paths, defects or uncertainty, and the smallest next action. Natural language is evidence, not a magic wire format.
"""


def reservation_errors(
    run_root: Path,
    attempt_dir: Path,
    reservation: dict[str, Any],
    state: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if reservation.get("format") != "lunarmarch-reservation-v1":
        errors.append("unsupported reservation format")
    task_id = reservation.get("task_id")
    role = reservation.get("role")
    if not isinstance(task_id, str) or task_id not in state.get("tasks", {}):
        errors.append("reservation task is not registered in run state")
        return errors
    task = state["tasks"][task_id]
    try:
        registered_attempts = {resolve_within(run_root, item) for item in task.get("attempts", [])}
    except (LunarMarchError, TypeError):
        registered_attempts = set()
        errors.append("task has invalid attempt bindings")
    if attempt_dir not in registered_attempts:
        errors.append("attempt is not registered to the reserved task")
    if role not in ROLES:
        errors.append("reservation has unknown role")
    expected_sandbox = "workspace-write" if role in WRITE_ROLES else "read-only"
    if reservation.get("sandbox") != expected_sandbox:
        errors.append("reservation sandbox does not match role authority")
    expected_paths = {
        "contract": run_root / task["contract"],
        "baseline": attempt_dir / "baseline.json",
        "prompt": attempt_dir / "prompt.md",
        "report": attempt_dir / "report.md",
    }
    for field, expected in expected_paths.items():
        raw = reservation.get(field)
        if not isinstance(raw, str) or Path(raw).resolve() != expected.resolve():
            errors.append(f"reservation {field} path mismatch")
    return errors


def _next_attempt_number(run_root: Path, task_id: str, role: str) -> int:
    root = run_root / "attempts" / task_id
    maximum = 0
    if root.is_dir():
        pattern = re.compile(rf"^{re.escape(role)}-(\d+)$")
        for child in root.iterdir():
            match = pattern.fullmatch(child.name)
            if match:
                maximum = max(maximum, int(match.group(1)))
    return maximum + 1


def reserve_attempt(
    run_root: Path,
    task_id: str,
    role: str,
    model: str = "gpt-5.6-luna",
    effort: str | None = None,
) -> Path:
    run_root = resolve_existing_directory(run_root)
    state = load_state(run_root)
    task, contract_path, contract = contract_for_task(run_root, state, task_id)
    if role not in ROLES:
        raise LunarMarchError(f"unknown role: {role}")
    for dependency in contract["depends_on"]:
        if state["tasks"][dependency]["status"] != "accepted":
            raise LunarMarchError(f"dependency is not accepted: {dependency}")
    active = []
    for attempt_raw in task["attempts"]:
        candidate = resolve_within(run_root, attempt_raw)
        if not (candidate / "terminal.json").is_file():
            active.append(candidate.name)
    if active:
        raise LunarMarchError(f"task has running_or_unknown attempt(s): {', '.join(active)}")
    if effort is None:
        effort = "medium" if role in {"scout", "sentinel", "clerk", "recovery"} else "high"
    if effort not in {"low", "medium", "high", "xhigh", "max"}:
        raise LunarMarchError(f"unsupported reasoning effort: {effort}")
    attempt_number = _next_attempt_number(run_root, task_id, role)
    attempt_dir = run_root / "attempts" / task_id / f"{role}-{attempt_number}"
    attempt_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    baseline_path = attempt_dir / "baseline.json"
    prompt_path = attempt_dir / "prompt.md"
    report_path = attempt_dir / "report.md"
    project_root = resolve_existing_directory(state["project_root"])
    atomic_write_json(baseline_path, capture_snapshot(project_root, run_root))
    atomic_write_bytes(prompt_path, render_prompt(role, contract, report_path).encode("utf-8"))
    sandbox = "workspace-write" if role in WRITE_ROLES else "read-only"
    reservation = {
        "format": "lunarmarch-reservation-v1",
        "task_id": task_id,
        "role": role,
        "model": model,
        "effort": effort,
        "sandbox": sandbox,
        "created_at": utc_now(),
        "contract": str(contract_path),
        "contract_sha256": sha256_file(contract_path),
        "baseline": str(baseline_path),
        "baseline_sha256": sha256_file(baseline_path),
        "prompt": str(prompt_path),
        "prompt_sha256": sha256_file(prompt_path),
        "report": str(report_path),
    }
    atomic_write_json(attempt_dir / "reservation.json", reservation)
    task["attempts"].append(str(attempt_dir.relative_to(run_root)))
    task["status"] = "active"
    state["next_action"] = f"wait for or launch {task_id}/{attempt_dir.name}"
    save_state(run_root, state)
    return attempt_dir


def _path_allowed(path: str, patterns: Iterable[str]) -> bool:
    normalized = path.replace("\\", "/").strip("/")
    for raw in patterns:
        pattern = raw.replace("\\", "/").strip("/")
        if any(token in pattern for token in "*?["):
            if fnmatch.fnmatchcase(normalized, pattern):
                return True
        elif normalized == pattern or normalized.startswith(pattern + "/"):
            return True
    return False


def run_checks(project_root: Path, commands: list[str], timeout_seconds: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command in commands:
        started = utc_now()
        try:
            result = subprocess.run(
                command,
                cwd=project_root,
                shell=True,
                text=True,
                capture_output=True,
                check=False,
                timeout=timeout_seconds,
            )
            results.append(
                {
                    "command": command,
                    "returncode": result.returncode,
                    "started_at": started,
                    "finished_at": utc_now(),
                    "stdout": result.stdout[-4000:],
                    "stderr": result.stderr[-4000:],
                }
            )
        except subprocess.TimeoutExpired as exc:
            results.append(
                {
                    "command": command,
                    "returncode": 124,
                    "started_at": started,
                    "finished_at": utc_now(),
                    "stdout": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
                    "stderr": "acceptance command timed out",
                }
            )
    return results


def finish_attempt(
    run_root: Path,
    attempt_dir: Path,
    exit_code: int,
    check_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    run_root = resolve_existing_directory(run_root)
    attempt_dir = resolve_within(run_root, attempt_dir)
    terminal_path = attempt_dir / "terminal.json"
    if terminal_path.exists():
        raise LunarMarchError(f"terminal event already exists: {terminal_path}")
    reservation_path = attempt_dir / "reservation.json"
    reservation = read_json(reservation_path)
    state = load_state(run_root)
    authority_errors = reservation_errors(run_root, attempt_dir, reservation, state)
    if authority_errors:
        raise LunarMarchError("invalid reservation authority: " + "; ".join(authority_errors))
    baseline_path = Path(reservation["baseline"]).resolve()
    if sha256_file(baseline_path) != reservation["baseline_sha256"]:
        raise LunarMarchError("baseline changed before terminal capture")
    project_root = resolve_existing_directory(state["project_root"])
    project_snapshot = capture_snapshot(project_root, run_root)
    scope = compare_snapshots(read_json(baseline_path), project_snapshot)
    scope_path = attempt_dir / "terminal-scope.json"
    project_snapshot_path = attempt_dir / "terminal-project.json"
    atomic_write_json(scope_path, scope)
    atomic_write_json(project_snapshot_path, project_snapshot)
    report_path = Path(reservation["report"]).resolve()
    terminal = {
        "format": "lunarmarch-terminal-v1",
        "finished_at": utc_now(),
        "exit_code": int(exit_code),
        "reservation": str(reservation_path),
        "reservation_sha256": sha256_file(reservation_path),
        "scope": str(scope_path),
        "scope_sha256": sha256_file(scope_path),
        "project_snapshot": str(project_snapshot_path),
        "project_snapshot_sha256": sha256_file(project_snapshot_path),
        "report": str(report_path),
        "report_sha256": sha256_file(report_path) if report_path.is_file() else None,
        "checks": check_results or [],
    }
    atomic_write_json(terminal_path, terminal)
    state = load_state(run_root)
    task = state["tasks"][reservation["task_id"]]
    task["status"] = "review" if reservation["role"] in WRITE_ROLES else "active"
    state["next_action"] = f"gate {reservation['task_id']}/{attempt_dir.name}"
    save_state(run_root, state)
    return terminal


def gate_attempt(run_root: Path, attempt_dir: Path) -> dict[str, Any]:
    run_root = resolve_existing_directory(run_root)
    attempt_dir = resolve_within(run_root, attempt_dir)
    errors: list[str] = []
    warnings: list[str] = []
    reservation_path = attempt_dir / "reservation.json"
    terminal_path = attempt_dir / "terminal.json"
    reservation = read_json(reservation_path)
    terminal = read_json(terminal_path)
    state = load_state(run_root)
    errors.extend(reservation_errors(run_root, attempt_dir, reservation, state))
    if terminal.get("format") != "lunarmarch-terminal-v1":
        errors.append("unsupported terminal format")
    if terminal.get("reservation") != str(reservation_path):
        errors.append("terminal reservation path mismatch")
    if terminal.get("reservation_sha256") != sha256_file(reservation_path):
        errors.append("reservation changed after terminal binding")
    for field, hash_field in (("contract", "contract_sha256"), ("baseline", "baseline_sha256"), ("prompt", "prompt_sha256")):
        path = Path(reservation[field]).resolve()
        if not path.is_file():
            errors.append(f"reserved {field} is missing")
        elif sha256_file(path) != reservation[hash_field]:
            errors.append(f"reserved {field} changed after launch")
    scope_path = Path(terminal.get("scope", "")).resolve()
    if scope_path != (attempt_dir / "terminal-scope.json").resolve():
        errors.append("terminal scope path mismatch")
    if not scope_path.is_file():
        errors.append("terminal scope is missing")
        scope: dict[str, Any] = {"changed": []}
    else:
        if terminal.get("scope_sha256") != sha256_file(scope_path):
            errors.append("terminal scope changed after binding")
        scope = read_json(scope_path)
    project_snapshot_path = Path(terminal.get("project_snapshot", "")).resolve()
    if project_snapshot_path != (attempt_dir / "terminal-project.json").resolve():
        errors.append("terminal project snapshot path mismatch")
    if not project_snapshot_path.is_file():
        errors.append("terminal project snapshot is missing")
    elif terminal.get("project_snapshot_sha256") != sha256_file(project_snapshot_path):
        errors.append("terminal project snapshot changed after binding")
    report_path = Path(reservation["report"]).resolve()
    if not report_path.is_file() or report_path.stat().st_size == 0:
        errors.append("worker report is missing or empty")
    elif terminal.get("report_sha256") != sha256_file(report_path):
        errors.append("worker report changed after terminal binding")
    if terminal.get("exit_code") != 0:
        errors.append(f"worker exited with code {terminal.get('exit_code')!r}")
    _, _, contract = contract_for_task(run_root, state, reservation["task_id"])
    changed = scope.get("changed", [])
    if not isinstance(changed, list) or any(not isinstance(item, str) for item in changed):
        errors.append("terminal scope has invalid changed paths")
        changed = []
    if reservation["role"] in READ_ONLY_ROLES and changed:
        errors.append(f"read-only role changed project paths: {', '.join(changed[:20])}")
    if reservation["role"] in WRITE_ROLES:
        if not contract["allowed_paths"]:
            errors.append("write role has no allowed_paths")
        outside = [path for path in changed if not _path_allowed(path, contract["allowed_paths"])]
        if outside:
            errors.append(f"project changes outside allowed_paths: {', '.join(outside[:20])}")
        if not changed:
            warnings.append("write role produced no frozen project changes")
    expected_commands = contract["acceptance_commands"]
    checks = terminal.get("checks", [])
    if expected_commands:
        observed = [item.get("command") for item in checks if isinstance(item, dict)]
        if observed != expected_commands:
            errors.append("acceptance command results are missing, reordered, or mismatched")
        for item in checks:
            if isinstance(item, dict) and item.get("returncode") != 0:
                errors.append(f"acceptance command failed ({item.get('returncode')}): {item.get('command')}")
    gate = {
        "format": "lunarmarch-gate-v1",
        "checked_at": utc_now(),
        "attempt": str(attempt_dir),
        "task_id": reservation["task_id"],
        "role": reservation["role"],
        "clear": not errors,
        "errors": errors,
        "warnings": warnings,
        "changed_paths": changed,
        "meaning": "Objective integrity only; semantic acceptance remains with an independent reviewer and parent.",
    }
    atomic_write_json(attempt_dir / "gate.json", gate)
    state = load_state(run_root)
    task = state["tasks"][reservation["task_id"]]
    if gate["clear"]:
        task["status"] = "review" if reservation["role"] in WRITE_ROLES else task["status"]
        state["next_action"] = (
            f"dispatch independent reviewer for {reservation['task_id']}"
            if reservation["role"] in WRITE_ROLES
            else f"interpret bounded evidence for {reservation['task_id']}"
        )
    else:
        state["next_action"] = f"classify gate failure for {reservation['task_id']}/{attempt_dir.name}"
    save_state(run_root, state)
    return gate


def launch_worker(
    run_root: Path,
    task_id: str,
    role: str,
    model: str,
    effort: str | None,
    codex_bin: str,
    run_acceptance: bool,
    check_timeout: int,
) -> tuple[Path, dict[str, Any]]:
    executable = shutil.which(codex_bin) if not Path(codex_bin).is_absolute() else codex_bin
    if not executable or not Path(executable).is_file():
        raise LunarMarchError(f"Codex executable not found: {codex_bin}")
    attempt_dir = reserve_attempt(run_root, task_id, role, model, effort)
    reservation = read_json(attempt_dir / "reservation.json")
    state = load_state(Path(run_root).resolve())
    project_root = resolve_existing_directory(state["project_root"])
    command = [
        str(executable),
        "exec",
        "--ephemeral",
        "-C",
        str(project_root),
        "-m",
        reservation["model"],
        "-c",
        f'model_reasoning_effort="{reservation["effort"]}"',
        "-c",
        "agents.max_depth=0",
        "-s",
        reservation["sandbox"],
        "--output-last-message",
        reservation["report"],
        "-",
    ]
    if reservation["sandbox"] == "workspace-write":
        command.insert(-1, "--approve-for-me")
    prompt = Path(reservation["prompt"]).read_text(encoding="utf-8")
    result = subprocess.run(command, input=prompt, text=True, capture_output=True, check=False)
    atomic_write_bytes(
        attempt_dir / "worker.log",
        (f"command={json.dumps(command)}\nexit_code={result.returncode}\n\nSTDOUT\n{result.stdout}\n\nSTDERR\n{result.stderr}\n").encode("utf-8", "replace"),
    )
    _, _, contract = contract_for_task(Path(run_root).resolve(), load_state(Path(run_root).resolve()), task_id)
    checks: list[dict[str, Any]] = []
    if result.returncode == 0 and run_acceptance:
        checks = run_checks(project_root, contract["acceptance_commands"], check_timeout)
    terminal = finish_attempt(Path(run_root).resolve(), attempt_dir, result.returncode, checks)
    return attempt_dir, terminal


def accept_task(run_root: Path, task_id: str, attempt_dir: Path) -> dict[str, Any]:
    run_root = resolve_existing_directory(run_root)
    state = load_state(run_root)
    task, _, contract = contract_for_task(run_root, state, task_id)
    if contract["role_hint"] == "auditor" and state["mode"] == "march":
        raise LunarMarchError("march-mode auditor tasks are accepted through accept-phase")
    attempt_dir = resolve_within(run_root, attempt_dir)
    # Never trust a persisted PASS flag at an authority boundary. Recompute the
    # objective gate from its hash-bound artifacts immediately before acceptance.
    gate = gate_attempt(run_root, attempt_dir)
    if gate.get("task_id") != task_id or not gate.get("clear"):
        raise LunarMarchError("acceptance requires a clear gate for the same task")
    terminal = read_json(attempt_dir / "terminal.json")
    terminal_project = read_json(Path(terminal["project_snapshot"]).resolve())
    current_project = capture_snapshot(resolve_existing_directory(state["project_root"]), run_root)
    if compare_snapshots(terminal_project, current_project)["changed"]:
        raise LunarMarchError("project changed after accepted evidence was captured; review again")
    writer_attempts = []
    for raw in task["attempts"]:
        reservation = read_json(resolve_within(run_root, raw) / "reservation.json")
        if reservation["role"] in WRITE_ROLES:
            writer_attempts.append(raw)
    if writer_attempts and gate.get("role") not in {"reviewer", "auditor"}:
        raise LunarMarchError("mutated work requires a clear independent reviewer or auditor attempt before acceptance")
    task["status"] = "accepted"
    task["accepted_attempt"] = str(attempt_dir.relative_to(run_root))
    remaining = [
        key
        for key, value in state["tasks"].items()
        if value["status"] != "accepted" and read_json(resolve_within(run_root, value["contract"]))["role_hint"] != "auditor"
    ]
    if remaining:
        state["next_action"] = f"continue with task {remaining[0]}"
    elif state["mode"] == "march":
        active_phases = [key for key, value in state["phases"].items() if value["status"] == "active"]
        frozen_phases = [key for key, value in state["phases"].items() if value["status"] == "frozen"]
        if active_phases:
            state["next_action"] = f"freeze phase {active_phases[0]}"
        elif frozen_phases:
            state["next_action"] = f"audit frozen phase {frozen_phases[0]}"
        else:
            state["status"] = "complete"
            state["next_action"] = "report completed run"
    else:
        state["status"] = "complete"
        state["next_action"] = "report completed run"
    save_state(run_root, state)
    return task


def freeze_phase(run_root: Path, phase_id: str) -> dict[str, Any]:
    run_root = resolve_existing_directory(run_root)
    state = load_state(run_root)
    if state["mode"] != "march":
        raise LunarMarchError("phase barriers are available only in march mode")
    phase = state.get("phases", {}).get(phase_id)
    if not isinstance(phase, dict):
        raise LunarMarchError(f"unknown phase: {phase_id}")
    if phase["status"] != "active":
        raise LunarMarchError(f"phase is not active: {phase_id}")
    audit_tasks: list[str] = []
    incomplete: list[str] = []
    for task_id in phase["task_ids"]:
        task, _, contract = contract_for_task(run_root, state, task_id)
        if contract["role_hint"] == "auditor":
            audit_tasks.append(task_id)
        elif task["status"] != "accepted":
            incomplete.append(task_id)
        for raw in task["attempts"]:
            attempt_dir = resolve_within(run_root, raw)
            if not (attempt_dir / "terminal.json").is_file():
                raise LunarMarchError(f"phase has running_or_unknown attempt: {task_id}/{attempt_dir.name}")
    if incomplete:
        raise LunarMarchError(f"phase has unaccepted tasks: {', '.join(incomplete)}")
    if len(audit_tasks) != 1:
        raise LunarMarchError("phase must contain exactly one pending task with role_hint auditor")
    project_root = resolve_existing_directory(state["project_root"])
    freeze_root = run_root / "artifacts" / "phases" / phase_id
    freeze_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    snapshot_path = freeze_root / "freeze.json"
    if snapshot_path.exists():
        raise LunarMarchError(f"phase freeze already exists: {snapshot_path}")
    atomic_write_json(snapshot_path, capture_snapshot(project_root, run_root))
    phase["status"] = "frozen"
    phase["freeze"] = {
        "path": str(snapshot_path.relative_to(run_root)),
        "sha256": sha256_file(snapshot_path),
        "frozen_at": utc_now(),
    }
    state["next_action"] = f"run auditor task {audit_tasks[0]} for frozen phase {phase_id}"
    save_state(run_root, state)
    return phase


def accept_phase(run_root: Path, phase_id: str, attempt_dir: Path) -> dict[str, Any]:
    run_root = resolve_existing_directory(run_root)
    state = load_state(run_root)
    phase = state.get("phases", {}).get(phase_id)
    if not isinstance(phase, dict) or phase.get("status") != "frozen":
        raise LunarMarchError(f"phase is not frozen: {phase_id}")
    freeze = phase.get("freeze")
    if not isinstance(freeze, dict):
        raise LunarMarchError("phase freeze binding is missing")
    freeze_path = resolve_within(run_root, freeze["path"])
    if sha256_file(freeze_path) != freeze.get("sha256"):
        raise LunarMarchError("phase freeze artifact changed")
    attempt_dir = resolve_within(run_root, attempt_dir)
    reservation = read_json(attempt_dir / "reservation.json")
    if reservation.get("role") != "auditor":
        raise LunarMarchError("phase acceptance requires an auditor attempt")
    task, _, contract = contract_for_task(run_root, state, reservation["task_id"])
    if contract["phase"] != phase_id or contract["role_hint"] != "auditor":
        raise LunarMarchError("auditor attempt is not bound to this phase")
    gate = gate_attempt(run_root, attempt_dir)
    if not gate.get("clear"):
        raise LunarMarchError("phase acceptance requires a clear auditor gate")
    current = capture_snapshot(resolve_existing_directory(state["project_root"]), run_root)
    movement = compare_snapshots(read_json(freeze_path), current)
    if movement["changed"]:
        raise LunarMarchError("project changed after phase freeze; reopen and re-audit the phase")
    task["status"] = "accepted"
    task["accepted_attempt"] = str(attempt_dir.relative_to(run_root))
    phase["status"] = "accepted"
    phase["audit_attempt"] = str(attempt_dir.relative_to(run_root))
    remaining_phases = [key for key, value in state["phases"].items() if value["status"] != "accepted"]
    if remaining_phases:
        state["next_action"] = f"continue phase {remaining_phases[0]}"
    else:
        state["status"] = "complete"
        state["next_action"] = "report completed run"
    save_state(run_root, state)
    return phase


def status_summary(run_root: Path) -> dict[str, Any]:
    run_root = resolve_existing_directory(run_root)
    state = load_state(run_root)
    tasks: list[dict[str, Any]] = []
    for task_id, task in state["tasks"].items():
        attempts = []
        for raw in task["attempts"]:
            attempt_dir = resolve_within(run_root, raw)
            reservation = read_json(attempt_dir / "reservation.json")
            if (attempt_dir / "terminal.json").is_file():
                lifecycle = "gated" if (attempt_dir / "gate.json").is_file() else "terminal"
            else:
                lifecycle = "running_or_unknown"
            attempts.append({"name": attempt_dir.name, "role": reservation["role"], "lifecycle": lifecycle})
        tasks.append({"task_id": task_id, "phase": task["phase"], "status": task["status"], "attempts": attempts})
    return {
        "run_id": state["run_id"],
        "goal": state["goal"],
        "mode": state["mode"],
        "status": state["status"],
        "next_action": state["next_action"],
        "phases": state.get("phases", {}),
        "tasks": tasks,
    }
