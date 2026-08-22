from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lm_core import (  # noqa: E402
    LunarMarchError,
    accept_phase,
    accept_task,
    add_task,
    capture_snapshot,
    finish_attempt,
    freeze_phase,
    gate_attempt,
    init_run,
    launch_worker,
    reserve_attempt,
    status_summary,
)
from install_skill import InstallError, bundle_fingerprint, install, inspect_installation  # noqa: E402


class LunarMarchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.project = root / "project"
        self.run = root / "run"
        self.project.mkdir()
        (self.project / "src").mkdir()
        (self.project / "tests").mkdir()
        (self.project / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.project / "README.md").write_text("demo\n", encoding="utf-8")
        init_run(self.project, self.run, "Change the demo safely", "task")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def contract(self, **overrides: object) -> dict[str, object]:
        value: dict[str, object] = {
            "task_id": "demo-task",
            "phase": "main",
            "objective": "Update the demo value.",
            "role_hint": "builder",
            "risk": "routine",
            "allowed_paths": ["src", "tests"],
            "acceptance_commands": ["python3 -m unittest discover -s tests -v"],
            "requirements": ["The value is updated."],
            "inputs": [],
            "non_goals": ["Do not edit documentation."],
            "depends_on": [],
        }
        value.update(overrides)
        return value

    def add_contract(self, **overrides: object) -> None:
        spec = Path(self.temporary.name) / "contract.json"
        spec.write_text(json.dumps(self.contract(**overrides)), encoding="utf-8")
        add_task(self.run, spec)

    @staticmethod
    def passing_checks() -> list[dict[str, object]]:
        return [
            {
                "command": "python3 -m unittest discover -s tests -v",
                "returncode": 0,
                "stdout": "OK",
                "stderr": "",
            }
        ]

    def finish_with_report(self, attempt: Path, checks: list[dict[str, object]] | None = None) -> dict[str, object]:
        (attempt / "report.md").write_text("Completed with bounded evidence.\n", encoding="utf-8")
        return finish_attempt(self.run, attempt, 0, checks)

    def test_builder_reviewer_acceptance_flow(self) -> None:
        self.add_contract()
        builder = reserve_attempt(self.run, "demo-task", "builder")
        (self.project / "src" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
        self.finish_with_report(builder, self.passing_checks())
        builder_gate = gate_attempt(self.run, builder)
        self.assertTrue(builder_gate["clear"], builder_gate)
        self.assertEqual(builder_gate["changed_paths"], ["src/app.py"])

        with self.assertRaisesRegex(LunarMarchError, "independent reviewer"):
            accept_task(self.run, "demo-task", builder)

        reviewer = reserve_attempt(self.run, "demo-task", "reviewer")
        self.finish_with_report(reviewer, self.passing_checks())
        reviewer_gate = gate_attempt(self.run, reviewer)
        self.assertTrue(reviewer_gate["clear"], reviewer_gate)
        accepted = accept_task(self.run, "demo-task", reviewer)
        self.assertEqual(accepted["status"], "accepted")
        self.assertEqual(status_summary(self.run)["status"], "complete")

    def test_gate_rejects_out_of_scope_change(self) -> None:
        self.add_contract()
        attempt = reserve_attempt(self.run, "demo-task", "builder")
        (self.project / "README.md").write_text("changed\n", encoding="utf-8")
        self.finish_with_report(attempt, self.passing_checks())
        gate = gate_attempt(self.run, attempt)
        self.assertFalse(gate["clear"])
        self.assertTrue(any("outside allowed_paths" in error for error in gate["errors"]))

    def test_git_snapshot_ignores_python_cache_artifacts(self) -> None:
        subprocess.run(["git", "-C", str(self.project), "init", "-b", "main"], check=True, capture_output=True)
        cache = self.project / "__pycache__"
        cache.mkdir()
        (cache / "app.cpython-312.pyc").write_bytes(b"generated")
        (self.project / "src" / "standalone.pyc").write_bytes(b"generated")
        snapshot = capture_snapshot(self.project, self.run)
        self.assertEqual(snapshot["source"], "git")
        self.assertNotIn("__pycache__/app.cpython-312.pyc", snapshot["files"])
        self.assertNotIn("src/standalone.pyc", snapshot["files"])

    def test_gate_rejects_read_only_mutation(self) -> None:
        self.add_contract(role_hint="scout", acceptance_commands=[])
        attempt = reserve_attempt(self.run, "demo-task", "scout")
        (self.project / "src" / "app.py").write_text("VALUE = 9\n", encoding="utf-8")
        self.finish_with_report(attempt, [])
        gate = gate_attempt(self.run, attempt)
        self.assertFalse(gate["clear"])
        self.assertTrue(any("read-only role changed" in error for error in gate["errors"]))

    def test_gate_requires_exact_acceptance_results(self) -> None:
        self.add_contract()
        attempt = reserve_attempt(self.run, "demo-task", "builder")
        (self.project / "src" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
        self.finish_with_report(attempt, [])
        gate = gate_attempt(self.run, attempt)
        self.assertFalse(gate["clear"])
        self.assertTrue(any("acceptance command results" in error for error in gate["errors"]))

    def test_contract_is_immutable_after_registration(self) -> None:
        self.add_contract(acceptance_commands=[])
        contract_path = self.run / "contracts" / "demo-task.json"
        contract_path.write_text(contract_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
        with self.assertRaisesRegex(LunarMarchError, "immutable contract changed"):
            reserve_attempt(self.run, "demo-task", "builder")

    def test_unknown_attempt_blocks_duplicate_writer(self) -> None:
        self.add_contract(acceptance_commands=[])
        first = reserve_attempt(self.run, "demo-task", "builder")
        summary = status_summary(self.run)
        self.assertEqual(summary["tasks"][0]["attempts"][0]["lifecycle"], "running_or_unknown")
        with self.assertRaisesRegex(LunarMarchError, "running_or_unknown"):
            reserve_attempt(self.run, "demo-task", "builder")
        self.assertTrue(first.is_dir())

    def test_failed_command_is_gate_failure(self) -> None:
        self.add_contract()
        attempt = reserve_attempt(self.run, "demo-task", "builder")
        (self.project / "src" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
        checks = self.passing_checks()
        checks[0]["returncode"] = 1
        self.finish_with_report(attempt, checks)
        gate = gate_attempt(self.run, attempt)
        self.assertFalse(gate["clear"])
        self.assertTrue(any("acceptance command failed" in error for error in gate["errors"]))

    def test_report_tampering_after_terminal_is_rejected(self) -> None:
        self.add_contract(acceptance_commands=[])
        attempt = reserve_attempt(self.run, "demo-task", "scout")
        self.finish_with_report(attempt, [])
        (attempt / "report.md").write_text("rewritten evidence\n", encoding="utf-8")
        gate = gate_attempt(self.run, attempt)
        self.assertFalse(gate["clear"])
        self.assertTrue(any("report changed" in error for error in gate["errors"]))

    def test_tampered_reservation_cannot_finish(self) -> None:
        self.add_contract(acceptance_commands=[])
        attempt = reserve_attempt(self.run, "demo-task", "builder")
        reservation_path = attempt / "reservation.json"
        reservation = json.loads(reservation_path.read_text(encoding="utf-8"))
        reservation["sandbox"] = "read-only"
        reservation_path.write_text(json.dumps(reservation), encoding="utf-8")
        (attempt / "report.md").write_text("done\n", encoding="utf-8")
        with self.assertRaisesRegex(LunarMarchError, "invalid reservation authority"):
            finish_attempt(self.run, attempt, 0, [])

    def test_acceptance_rejects_project_movement_after_review(self) -> None:
        self.add_contract(acceptance_commands=[])
        reviewer = reserve_attempt(self.run, "demo-task", "reviewer")
        self.finish_with_report(reviewer, [])
        self.assertTrue(gate_attempt(self.run, reviewer)["clear"])
        (self.project / "src" / "app.py").write_text("VALUE = 7\n", encoding="utf-8")
        with self.assertRaisesRegex(LunarMarchError, "project changed after accepted evidence"):
            accept_task(self.run, "demo-task", reviewer)

    def test_external_launcher_pins_luna_and_completes_attempt(self) -> None:
        self.add_contract(acceptance_commands=[])
        fake = Path(self.temporary.name) / "fake-codex"
        fake.write_text(
            """#!/usr/bin/env python3
import pathlib
import sys
args = sys.argv[1:]
project = pathlib.Path(args[args.index('-C') + 1])
report = pathlib.Path(args[args.index('--output-last-message') + 1])
project.joinpath('src/app.py').write_text('VALUE = 3\\n', encoding='utf-8')
report.write_text('fake Luna completed\\n', encoding='utf-8')
sys.stdin.read()
""",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        attempt, terminal = launch_worker(
            self.run,
            "demo-task",
            "builder",
            "gpt-5.6-luna",
            "high",
            str(fake),
            True,
            30,
        )
        self.assertEqual(terminal["exit_code"], 0)
        reservation = json.loads((attempt / "reservation.json").read_text(encoding="utf-8"))
        self.assertEqual(reservation["model"], "gpt-5.6-luna")
        self.assertEqual(reservation["effort"], "high")
        command = json.loads((attempt / "worker.log").read_text(encoding="utf-8").splitlines()[0].removeprefix("command="))
        self.assertIn("--approve-for-me", command)
        self.assertNotIn("-s", command)
        self.assertTrue(gate_attempt(self.run, attempt)["clear"])

    def test_read_only_launcher_uses_explicit_sandbox_without_auto_approval(self) -> None:
        self.add_contract(role_hint="reviewer", acceptance_commands=[])
        fake = Path(self.temporary.name) / "fake-codex-read-only"
        fake.write_text(
            """#!/usr/bin/env python3
import pathlib
import sys
args = sys.argv[1:]
report = pathlib.Path(args[args.index('--output-last-message') + 1])
report.write_text('review complete\\n', encoding='utf-8')
sys.stdin.read()
""",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        attempt, terminal = launch_worker(
            self.run,
            "demo-task",
            "reviewer",
            "gpt-5.6-luna",
            "high",
            str(fake),
            True,
            30,
        )
        self.assertEqual(terminal["exit_code"], 0)
        command = json.loads((attempt / "worker.log").read_text(encoding="utf-8").splitlines()[0].removeprefix("command="))
        self.assertEqual(command[command.index("-s") + 1], "read-only")
        self.assertNotIn("--approve-for-me", command)
        self.assertTrue(gate_attempt(self.run, attempt)["clear"])

    def test_march_phase_requires_freeze_and_auditor(self) -> None:
        march_run = Path(self.temporary.name) / "march-run"
        init_run(self.project, march_run, "Complete a guarded phase", "march")
        task_spec = Path(self.temporary.name) / "march-task.json"
        task_spec.write_text(json.dumps(self.contract(acceptance_commands=[])), encoding="utf-8")
        add_task(march_run, task_spec)
        audit_spec = Path(self.temporary.name) / "audit-task.json"
        audit_spec.write_text(
            json.dumps(
                self.contract(
                    task_id="main-audit",
                    objective="Audit the frozen main phase.",
                    role_hint="auditor",
                    allowed_paths=[],
                    acceptance_commands=[],
                    requirements=["Cross-task integration is assessed against the frozen phase."],
                    depends_on=["demo-task"],
                )
            ),
            encoding="utf-8",
        )
        add_task(march_run, audit_spec)

        scout = reserve_attempt(march_run, "demo-task", "scout")
        (scout / "report.md").write_text("research complete\n", encoding="utf-8")
        finish_attempt(march_run, scout, 0, [])
        self.assertTrue(gate_attempt(march_run, scout)["clear"])
        accept_task(march_run, "demo-task", scout)
        phase = freeze_phase(march_run, "main")
        self.assertEqual(phase["status"], "frozen")

        auditor = reserve_attempt(march_run, "main-audit", "auditor")
        (auditor / "report.md").write_text("phase audit complete\n", encoding="utf-8")
        finish_attempt(march_run, auditor, 0, [])
        self.assertTrue(gate_attempt(march_run, auditor)["clear"])
        accepted = accept_phase(march_run, "main", auditor)
        self.assertEqual(accepted["status"], "accepted")
        self.assertEqual(status_summary(march_run)["status"], "complete")

    def test_user_style_symlink_install_is_idempotent(self) -> None:
        destination = Path(self.temporary.name) / "user-skills" / "lunar-march"
        first = install(destination, "link", source=ROOT)
        second = install(destination, "link", source=ROOT)
        self.assertEqual(first["status"], "installed")
        self.assertEqual(second["status"], "already-installed")
        self.assertTrue(destination.is_symlink())
        self.assertTrue(inspect_installation(destination)["valid"])

    def test_repo_style_copy_install_has_matching_fingerprint(self) -> None:
        destination = Path(self.temporary.name) / "repo" / ".agents" / "skills" / "lunar-march"
        result = install(destination, "copy", source=ROOT)
        self.assertEqual(result["status"], "installed")
        self.assertFalse(destination.is_symlink())
        self.assertEqual(bundle_fingerprint(destination), bundle_fingerprint(ROOT))

    def test_installer_refuses_silent_overwrite(self) -> None:
        destination = Path(self.temporary.name) / "occupied" / "lunar-march"
        destination.mkdir(parents=True)
        (destination / "unexpected.txt").write_text("mine\n", encoding="utf-8")
        with self.assertRaisesRegex(InstallError, "different content"):
            install(destination, "copy", source=ROOT)

    def test_installer_replace_preserves_backup(self) -> None:
        destination = Path(self.temporary.name) / "occupied" / "lunar-march"
        destination.mkdir(parents=True)
        original = destination / "unexpected.txt"
        original.write_text("mine\n", encoding="utf-8")
        result = install(destination, "copy", replace=True, source=ROOT)
        backup = Path(result["backup"])
        self.assertTrue((backup / "unexpected.txt").is_file())
        self.assertEqual((backup / "unexpected.txt").read_text(encoding="utf-8"), "mine\n")
        self.assertTrue(inspect_installation(destination)["valid"])


if __name__ == "__main__":
    unittest.main()
