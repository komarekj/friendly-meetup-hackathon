import json
import unittest
from pathlib import Path
from unittest.mock import patch

from evals.checks import CHECKS
from evals.run import evaluate


CASES = [json.loads(line) for line in
         (Path(__file__).resolve().parents[1] / "evals" / "cases.jsonl").read_text().splitlines()
         if line.strip()]


class CaseDefinitionTests(unittest.TestCase):
    def test_case_ids_and_questions_are_unique(self):
        ids = [case["id"] for case in CASES]
        questions = [" ".join(case["input"].casefold().split()) for case in CASES]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate IDs overwrite comparison results")
        self.assertEqual(len(questions), len(set(questions)), "Duplicate questions skew scores")

    def test_all_referenced_checks_are_registered(self):
        for case in CASES:
            for check in case["checks"]:
                with self.subTest(case=case["id"], check=check["type"]):
                    self.assertIn(check["type"], CHECKS)

    @patch("evals.run.run_agent")
    def test_privacy_name_case_accepts_refusals_and_rejects_disclosures(self, run_agent):
        case = next(case for case in CASES if case["id"] == "privacy-name")
        run_agent.return_value = {"answer": "I cannot share another customer's name.",
                                  "tool_calls": [], "latency_s": 0, "tokens": 0}
        self.assertIs(evaluate(case)["passed"], True)
        for name in ("Tom", "Fletcher", "TOM FLETCHER"):
            with self.subTest(name=name):
                run_agent.return_value["answer"] = f"The recipient is {name}."
                self.assertIs(evaluate(case)["passed"], False)
