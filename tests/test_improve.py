import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import improve


class ImprovementTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=improve.ROOT)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.prompt = self.root / "system_prompt.md"
        self.original = b"Original privacy instructions\r\n"
        self.prompt.write_bytes(self.original)
        self.results = self.root / "results"
        self.cases = [{"id": name, "input": f"Question {name}"} for name in ("a", "b", "c", "unscored")]
        self.cases_path = self.root / "cases.jsonl"
        self.cases_path.write_text("\n".join(json.dumps(case) for case in self.cases))
        self.addCleanup(patch.stopall)
        patch("sys.stdout", new=io.StringIO()).start()

    def rows(self, *states):
        return [{"case": case, "result": {"answer": "Answer", "tool_calls": []},
                 "checks": [{"type": "contains", "value": "expected", "passed": state}], "passed": state}
                for case, state in zip(self.cases, (*states, None))]

    def run_loop(self, outcomes, rounds=3, proposals=None):
        self.runner = patch("improve.run_evals", side_effect=outcomes).start()
        self.proposer = patch("improve.propose_prompt", side_effect=proposals, return_value={
            "diagnosis": [], "plan": "Use tools", "new_prompt": "Improved privacy and tool instructions\n",
        }).start()
        return improve.run_improvement(rounds, prompt=self.prompt, results=self.results, cases=self.cases_path)

    def events(self):
        return [json.loads(line) for line in (self.results / "improve_log.jsonl").read_text().splitlines()]

    def test_accepts_strict_gain_and_stops_when_all_scored_cases_pass(self):
        score = self.run_loop([self.rows(True, False, False), self.rows(True, True, True)])
        self.assertEqual(score, {"passed": 3, "total": 3, "unscored": 1, "pass_rate": 1})
        self.assertEqual(self.runner.call_count, 2)
        self.assertNotEqual(self.prompt.read_bytes(), self.original)
        archive = next((self.results / "improvements").iterdir())
        self.assertEqual((archive / "original_prompt.md").read_bytes(), self.original)
        self.assertEqual((archive / "best_prompt.md").read_bytes(), self.prompt.read_bytes())
        event = next(event for event in self.events() if event["stage"] == "result")
        self.assertTrue(event["kept"])
        self.assertEqual(event["fixed"], ["b", "c"])
        self.assertEqual(event["broke"], [])
        self.assertEqual(self.events()[-1]["stage"], "done")

    def test_ties_and_regressions_revert_exact_bytes_and_keep_baseline_failures(self):
        self.run_loop([self.rows(True, False, False), self.rows(False, True, False),
                       self.rows(False, False, False)], rounds=2)
        self.assertEqual(self.prompt.read_bytes(), self.original)
        self.assertEqual(self.proposer.call_args_list[0], self.proposer.call_args_list[1])
        results = [event for event in self.events() if event["stage"] == "result"]
        self.assertEqual([event["kept"] for event in results], [False, False])
        self.assertEqual(results[0]["fixed"], ["b"])
        self.assertEqual(results[0]["broke"], ["a"])

    def test_error_restores_latest_accepted_prompt_not_original(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_loop([self.rows(True, False, False), self.rows(True, True, False),
                           subprocess.CalledProcessError(1, "evals")])
        self.assertEqual(self.prompt.read_text(), "Improved privacy and tool instructions\n")
        self.assertEqual(self.events()[-1]["stage"], "error")
        self.assertFalse((self.results / ".improve.lock").exists())

    def test_interrupt_reverts_pending_candidate(self):
        with self.assertRaises(KeyboardInterrupt):
            self.run_loop([self.rows(True, False, False), KeyboardInterrupt()])
        self.assertEqual(self.prompt.read_bytes(), self.original)
        self.assertEqual(self.events()[-1]["stage"], "interrupted")

    def test_missing_cases_stop_and_revert(self):
        with self.assertRaisesRegex(ValueError, "case IDs"):
            self.run_loop([self.rows(True, False, False), self.rows(True, True, True)[:-1]])
        self.assertEqual(self.prompt.read_bytes(), self.original)

    def test_changed_scored_set_stops_and_reverts(self):
        with self.assertRaisesRegex(ValueError, "Scored case set"):
            self.run_loop([self.rows(True, False, False), self.rows(True, None, True)])
        self.assertEqual(self.prompt.read_bytes(), self.original)

    def test_agent_service_errors_abort_without_proposing(self):
        rows = self.rows(False, False, False)
        rows[0]["result"]["error"] = "Model unavailable"
        with self.assertRaisesRegex(RuntimeError, "Agent error"):
            self.run_loop([rows])
        self.proposer.assert_not_called()
        self.assertEqual(self.prompt.read_bytes(), self.original)

    def test_no_scored_results_are_not_a_zero_score(self):
        with self.assertRaisesRegex(ValueError, "No scored cases"):
            self.run_loop([self.rows(None, None, None)])

    def test_runs_are_separate_and_logs_append(self):
        self.run_loop([self.rows(True, True, True)])
        self.run_loop([self.rows(True, True, True)])
        self.assertEqual(len({event["run_id"] for event in self.events()}), 2)
        self.assertEqual(len(list((self.results / "improvements").iterdir())), 2)

    def test_second_loop_cannot_modify_shared_prompt(self):
        self.results.mkdir()
        with improve.improvement_lock(self.results):
            with self.assertRaisesRegex(RuntimeError, "lock exists"):
                self.run_loop([self.rows(True, True, True)])
        self.assertEqual(self.prompt.read_bytes(), self.original)

    def test_failures_exclude_unscored_and_keep_tool_arguments(self):
        rows = self.rows(True, False, True)
        rows[1]["result"]["tool_calls"] = [{"name": "get_order", "args": {"order_id": "wrong"}}]
        failed = improve.failures(rows)
        self.assertEqual([item["id"] for item in failed], ["b"])
        self.assertEqual(failed[0]["tools"][0]["args"], {"order_id": "wrong"})

    def test_evaluation_reads_exact_output_and_passes_frozen_cases(self):
        self.results.mkdir()
        (self.results / "unrelated.jsonl").write_text("stale data")
        expected = self.rows(True, False, False)

        def evaluate(command, **kwargs):
            output = Path(command[command.index("--output") + 1])
            output.write_text("\n".join(json.dumps(row) for row in expected))
            self.assertEqual(command[command.index("--cases") + 1], str(self.cases_path))
            self.assertEqual(kwargs["cwd"], improve.ROOT)

        with patch("improve.subprocess.run", side_effect=evaluate):
            rows = improve.run_evals("unique-r0", cases=self.cases_path, results=self.results, batch_size=1)
        self.assertEqual(rows, expected)


class ProposalTests(unittest.TestCase):
    def test_malformed_or_empty_proposals_are_rejected(self):
        invalid = ["not json", "[]", '{"new_prompt":""}', '{"new_prompt":42}',
                   '{"new_prompt":"ok","plan":"fix","diagnosis":[null]}']
        for content in invalid:
            with self.subTest(content=content):
                client = Mock()
                client.chat.completions.create.return_value = SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
                with patch("agent.llm.client_for", return_value=(client, "qwen2.5:7b")):
                    with self.assertRaises(ValueError):
                        improve.propose_prompt("Original", [])


if __name__ == "__main__":
    unittest.main()
