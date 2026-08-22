#!/usr/bin/env python3
"""Command-line interface for LunarMarch durable orchestration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lm_core import (
    LunarMarchError,
    accept_phase,
    accept_task,
    add_task,
    finish_attempt,
    freeze_phase,
    gate_attempt,
    init_run,
    launch_worker,
    reserve_attempt,
    status_summary,
)
from worker_transports import default_model_for_transport


def emit(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LunarMarch durable provider-aware orchestration")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="initialize a durable run")
    init.add_argument("--project-root", required=True, type=Path)
    init.add_argument("--run-root", required=True, type=Path)
    init.add_argument("--goal", required=True)
    init.add_argument("--mode", choices=["quick", "research", "task", "march"], default="task")

    add = commands.add_parser("add-task", help="register an immutable task contract")
    add.add_argument("--run-root", required=True, type=Path)
    add.add_argument("--spec", required=True, type=Path)

    reserve = commands.add_parser("reserve", help="create an immutable attempt without launching")
    reserve.add_argument("--run-root", required=True, type=Path)
    reserve.add_argument("--task-id", required=True)
    reserve.add_argument("--role", required=True)
    reserve.add_argument("--model", help="model ID; defaults by transport")
    reserve.add_argument("--effort")
    reserve.add_argument("--transport", choices=["codex", "opencode"], default="codex")
    reserve.add_argument("--variant")

    finish = commands.add_parser("finish", help="capture a terminal event for a manually executed attempt")
    finish.add_argument("--run-root", required=True, type=Path)
    finish.add_argument("--attempt", required=True, type=Path)
    finish.add_argument("--exit-code", required=True, type=int)
    finish.add_argument("--check-results", type=Path, help="optional JSON array of command results")

    gate = commands.add_parser("gate", help="verify an attempt's objective integrity envelope")
    gate.add_argument("--run-root", required=True, type=Path)
    gate.add_argument("--attempt", required=True, type=Path)

    launch = commands.add_parser("launch", help="reserve and run an external worker")
    launch.add_argument("--run-root", required=True, type=Path)
    launch.add_argument("--task-id", required=True)
    launch.add_argument("--role", required=True)
    launch.add_argument("--model", help="model ID; defaults by transport")
    launch.add_argument("--effort")
    launch.add_argument("--transport", choices=["codex", "opencode"], default="codex")
    launch.add_argument("--variant", help="provider-specific OpenCode model variant")
    launch.add_argument("--worker-bin", help="worker CLI executable; defaults to the selected transport")
    launch.add_argument("--codex-bin", help=argparse.SUPPRESS)
    launch.add_argument("--run-checks", action="store_true")
    launch.add_argument("--check-timeout", type=int, default=1200)
    launch.add_argument("--worker-timeout", type=int, default=1800)

    accept = commands.add_parser("accept", help="record the parent's semantic acceptance")
    accept.add_argument("--run-root", required=True, type=Path)
    accept.add_argument("--task-id", required=True)
    accept.add_argument("--attempt", required=True, type=Path)

    freeze = commands.add_parser("freeze-phase", help="freeze an accepted march phase before audit")
    freeze.add_argument("--run-root", required=True, type=Path)
    freeze.add_argument("--phase", required=True)

    accept_phase_parser = commands.add_parser("accept-phase", help="accept a frozen phase after a clear auditor gate")
    accept_phase_parser.add_argument("--run-root", required=True, type=Path)
    accept_phase_parser.add_argument("--phase", required=True)
    accept_phase_parser.add_argument("--attempt", required=True, type=Path)

    status = commands.add_parser("status", help="print compact durable run status")
    status.add_argument("--run-root", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            emit(init_run(args.project_root, args.run_root, args.goal, args.mode))
        elif args.command == "add-task":
            emit(add_task(args.run_root, args.spec))
        elif args.command == "reserve":
            model = args.model or default_model_for_transport(args.transport)
            attempt = reserve_attempt(
                args.run_root,
                args.task_id,
                args.role,
                model,
                args.effort,
                args.transport,
                args.variant,
            )
            emit({"status": "reserved", "attempt": str(attempt)})
        elif args.command == "finish":
            checks = None
            if args.check_results:
                checks = json.loads(args.check_results.read_text(encoding="utf-8"))
                if not isinstance(checks, list):
                    raise LunarMarchError("check-results must contain a JSON array")
            emit(finish_attempt(args.run_root, args.attempt, args.exit_code, checks))
        elif args.command == "gate":
            gate = gate_attempt(args.run_root, args.attempt)
            emit(gate)
            return 0 if gate["clear"] else 1
        elif args.command == "launch":
            if args.worker_bin and args.codex_bin:
                raise LunarMarchError("use only one of --worker-bin or legacy --codex-bin")
            worker_bin = args.worker_bin or args.codex_bin or args.transport
            model = args.model or default_model_for_transport(args.transport)
            attempt, terminal = launch_worker(
                args.run_root,
                args.task_id,
                args.role,
                model,
                args.effort,
                worker_bin,
                args.run_checks,
                args.check_timeout,
                args.transport,
                args.variant,
                args.worker_timeout,
            )
            emit({"status": "terminal", "attempt": str(attempt), "terminal": terminal})
        elif args.command == "accept":
            emit(accept_task(args.run_root, args.task_id, args.attempt))
        elif args.command == "freeze-phase":
            emit(freeze_phase(args.run_root, args.phase))
        elif args.command == "accept-phase":
            emit(accept_phase(args.run_root, args.phase, args.attempt))
        elif args.command == "status":
            emit(status_summary(args.run_root))
        return 0
    except (LunarMarchError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"lunarmarch: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
