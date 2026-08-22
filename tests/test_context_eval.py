from __future__ import annotations

import json
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from context_eval import (  # noqa: E402
    extract_event_metrics,
    extract_usage_jsonl,
    load_context,
    main,
    parse_unittest,
    plan_trials,
    run_trial,
    summarize,
    validate_suite,
)


SUITE = ROOT / "evals" / "context-efficiency" / "suite.json"


class ContextEvalTests(unittest.TestCase):
    def test_suite_and_counterbalanced_plan(self) -> None:
        _, suite = validate_suite(SUITE)
        trials = plan_trials(suite, repetitions=5, seed=7)
        conditions = suite["conditions"]
        self.assertEqual(len(trials), len(conditions) * 5 * len(suite["cases"]))
        for condition in conditions:
            positions = sorted(item["position"] for item in trials if item["condition"] == condition)
            self.assertEqual(positions, list(range(1, len(conditions) + 1)))
        for trial in trials:
            self.assertNotIn(trial["condition"], trial["trial_id"])

    def test_padded_contract_preserves_contract_prefix(self) -> None:
        suite_path, suite = validate_suite(SUITE)
        case = suite["cases"][0]
        contract = load_context(suite_path.parent, case["contexts"]["contract"])
        padded = load_context(suite_path.parent, case["contexts"]["contract-padded"])
        self.assertTrue(padded.startswith(contract.strip()))
        self.assertGreater(len(padded), len(contract) * 10)

    def test_usage_parser_uses_only_terminal_completed_record(self) -> None:
        events = "\n".join(
            [
                json.dumps({"type": "progress", "usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12}}),
                json.dumps({"type": "noise", "nested": {"usage": {"input_tokens": 999999}}}),
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 120,
                            "input_tokens_details": {"cached_tokens": 40},
                            "output_tokens": 30,
                            "output_tokens_details": {"reasoning_tokens": 12},
                            "total_tokens": 150,
                        },
                    }
                ),
            ]
        )
        usage = extract_usage_jsonl(events)
        self.assertEqual(usage["input_tokens"], 120)
        self.assertEqual(usage["cached_input_tokens"], 40)
        self.assertEqual(usage["uncached_input_tokens"], 80)
        self.assertEqual(usage["reasoning_tokens"], 12)
        self.assertEqual(usage["total_tokens"], 150)

    def test_current_codex_usage_shape_and_event_counts(self) -> None:
        events = "\n".join(
            [
                json.dumps({"type": "thread.started", "thread_id": "thread-1"}),
                json.dumps({"type": "item.completed", "item": {"id": "a", "type": "command_execution"}}),
                json.dumps({"type": "item.completed", "item": {"id": "b", "type": "file_change"}}),
                json.dumps({"type": "item.completed", "item": {"id": "c", "type": "agent_message"}}),
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 100,
                            "cached_input_tokens": 60,
                            "output_tokens": 25,
                            "reasoning_output_tokens": 7,
                        },
                    }
                ),
            ]
        )
        usage = extract_usage_jsonl(events)
        self.assertEqual(usage["total_tokens"], 125)
        self.assertEqual(usage["reasoning_tokens"], 7)
        metrics = extract_event_metrics(events)
        self.assertEqual(metrics["thread_id"], "thread-1")
        self.assertEqual(metrics["command_calls"], 1)
        self.assertEqual(metrics["file_change_calls"], 1)
        self.assertEqual(metrics["agent_messages"], 1)

    def test_unittest_parser_scores_partial_failure(self) -> None:
        passed, total, score = parse_unittest("Ran 10 tests\nFAILED (failures=2, errors=1)", 1)
        self.assertEqual((passed, total), (7, 10))
        self.assertAlmostEqual(score, 0.7)

    def test_unittest_parser_rejects_malformed_nonzero_result(self) -> None:
        passed, total, score = parse_unittest("Ran 10 tests\nrunner crashed", 1)
        self.assertEqual((passed, total, score), (0, 10, 0.0))

    def test_decision_requires_five_quality_preserving_token_pairs(self) -> None:
        results = []
        for repetition in range(1, 6):
            for condition, tokens in (("contract", 100), ("contract-padded", 150)):
                results.append(
                    {
                        "case_id": "case",
                        "repetition": repetition,
                        "condition": condition,
                        "quality_score": 100.0,
                        "task_success": True,
                        "infrastructure_failure": False,
                        "context_bytes": 100 if condition == "contract" else 1000,
                        "worker": {"wall_seconds": 1.0},
                        "events": {"command_calls": 1},
                        "usage": {
                            "input_tokens": tokens - 10,
                            "cached_input_tokens": 0,
                            "uncached_input_tokens": tokens - 10,
                            "output_tokens": 10,
                            "reasoning_tokens": 5,
                            "total_tokens": tokens,
                        },
                    }
                )
        for sequence, result in enumerate(results, start=1):
            result["trial_id"] = f"trial-{sequence}"
        expected = [item["trial_id"] for item in results]
        summary = summarize(
            results,
            ["contract", "contract-padded"],
            quality_tolerance=2.0,
            expected_trial_ids=expected,
        )
        self.assertTrue(summary["decision"]["eligible"])
        self.assertTrue(summary["decision"]["compact_contract_default_supported"])
        self.assertEqual(
            summary["paired_vs_contract"]["contract-padded"]["mean_total_token_delta_vs_contract"],
            50.0,
        )

        incomplete = summarize(
            results[:-1],
            ["contract", "contract-padded"],
            quality_tolerance=2.0,
            expected_trial_ids=expected,
        )
        self.assertFalse(incomplete["run_integrity"]["complete"])
        self.assertFalse(incomplete["decision"]["eligible"])

        results[-1]["usage"]["total_tokens"] = None
        missing_telemetry = summarize(
            results,
            ["contract", "contract-padded"],
            quality_tolerance=2.0,
            expected_trial_ids=expected,
        )
        self.assertEqual(missing_telemetry["paired_vs_contract"]["contract-padded"]["token_pairs"], 4)
        self.assertFalse(missing_telemetry["decision"]["eligible"])

    def test_fake_live_run_scores_and_summarizes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = root / "fake-codex"
            fake.write_text(
                """#!/usr/bin/env python3
import json
import pathlib
import sys

if '--version' in sys.argv:
    print('fake-codex 1.0')
    raise SystemExit(0)

args = sys.argv[1:]
project = pathlib.Path(args[args.index('-C') + 1])
report = pathlib.Path(args[args.index('--output-last-message') + 1])
project.joinpath('handles.py').write_text('''import re
import unicodedata


def canonical_handle(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("value must be a string")
    candidate = unicodedata.normalize("NFKC", value.strip())
    if candidate.startswith("@"):
        candidate = candidate[1:]
    candidate = candidate.casefold()
    if not 3 <= len(candidate) <= 20 or re.fullmatch(r"[a-z0-9_]+", candidate) is None:
        raise ValueError("invalid handle")
    return "@" + candidate
''', encoding='utf-8')
report.write_text('implemented and tested\\n', encoding='utf-8')
sys.stdin.read()
print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 100, 'input_tokens_details': {'cached_tokens': 20}, 'output_tokens': 25, 'output_tokens_details': {'reasoning_tokens': 5}, 'total_tokens': 125}}))
""",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            output = root / "run"
            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "run",
                        "--suite",
                        str(SUITE),
                        "--output",
                        str(output),
                        "--conditions",
                        "contract",
                        "--repetitions",
                        "1",
                        "--codex-bin",
                        str(fake),
                        "--allow-dirty-suite",
                    ]
                )
            self.assertEqual(exit_code, 0)
            result_path = next((output / "trials").glob("*/result.json"))
            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["quality_score"], 100.0)
            self.assertTrue(result["task_success"])
            self.assertEqual(result["usage"]["uncached_input_tokens"], 80)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["conditions"]["contract"]["task_success_rate"], 1.0)
            self.assertTrue(summary["run_integrity"]["complete"])
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["runtime"]["dirty_suite_override"])

    def test_trial_copy_excludes_source_repository_metadata(self) -> None:
        suite_path, suite = validate_suite(SUITE)
        case = dict(suite["cases"][0])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            source.joinpath("handles.py").write_text("def canonical_handle(value):\n    return value\n", encoding="utf-8")
            source.joinpath(".git").mkdir()
            source.joinpath(".git", "secret").write_text("must not copy", encoding="utf-8")
            task = root / "task.md"
            task.write_text("Implement the function.\n", encoding="utf-8")
            graders = root / "graders"
            graders.mkdir()
            graders.joinpath("test_ok.py").write_text("import unittest\n", encoding="utf-8")
            context = root / "context.md"
            context.write_text("Return the input.\n", encoding="utf-8")
            local_suite = root / "suite.json"
            case.update(
                {
                    "id": "copy-check",
                    "project": "source",
                    "task": "task.md",
                    "grader_tests": "graders",
                    "allowed_paths": ["handles.py"],
                    "contexts": {name: [{"path": "context.md"}] for name in suite["conditions"]},
                }
            )
            local = dict(suite)
            local["cases"] = [case]
            local_suite.write_text(json.dumps(local), encoding="utf-8")
            fake = root / "fake-codex"
            fake.write_text(
                "#!/usr/bin/env python3\nimport json, pathlib, sys\n"
                "report = pathlib.Path(sys.argv[sys.argv.index('--output-last-message') + 1])\n"
                "report.write_text('done')\nsys.stdin.read()\n"
                "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':1,'output_tokens':1}}))\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            trial = plan_trials(local, 1, 3, ["contract"])[0]
            run_trial(local_suite, local, case, trial, root / "out", "gpt-5.6-luna", "high", str(fake), 30)
            copied = root / "out" / "trials" / trial["trial_id"] / "project"
            self.assertFalse(copied.joinpath(".git", "secret").exists())


if __name__ == "__main__":
    unittest.main()
