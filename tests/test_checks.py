import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evals.checks import contains_any, matches_regex, not_contains_word, tool_called_with, tool_not_called
from evals.run import main


class AlternativeTextTests(unittest.TestCase):
    def test_accepts_alternative_substrings_ignoring_case(self):
        options = ["order ID", "order reference", "order number"]
        for answer in ("Please give your ORDER ID.", "What is your order reference?",
                       "Can you share your order number?"):
            with self.subTest(answer=answer):
                self.assertIs(contains_any({"answer": answer}, options), True)

    def test_rejects_missing_alternatives_and_empty_list(self):
        self.assertIs(contains_any({"answer": "Your parcel is in transit."}, ["order ID"]), False)
        self.assertIs(contains_any({"answer": "Order ID"}, []), False)
        self.assertIs(contains_any({"answer": ""}, ["order ID"]), False)


class RegexTests(unittest.TestCase):
    price_pattern = r"(?:£\s*11(?:\.00)?(?!\d|\.\d)|\b11(?:\.00)?\s+pounds?\b)"

    def test_accepts_equivalent_price_formats_inside_answer(self):
        for price in ("£11", "£11.00", "£ 11.00", "11 pounds", "11.00 POUNDS"):
            with self.subTest(price=price):
                self.assertIs(matches_regex({"answer": f"The price is {price}."}, self.price_pattern), True)

    def test_rejects_different_prices_and_missing_price(self):
        for answer in ("£110", "£111.00", "£11.50", "111 pounds", "11.50 pounds", "No price.", ""):
            with self.subTest(answer=answer):
                self.assertIs(matches_regex({"answer": answer}, self.price_pattern), False)

    def test_honors_anchors_and_literal_metacharacters(self):
        self.assertIs(matches_regex({"answer": "£6.50"}, r"^£6\.50$"), True)
        for answer in ("£6x50", "It costs £6.50"):
            with self.subTest(answer=answer):
                self.assertIs(matches_regex({"answer": answer}, r"^£6\.50$"), False)


class ForbiddenToolTests(unittest.TestCase):
    def test_allows_no_calls_or_other_tools(self):
        for calls in ([], [{"name": "search_policies", "args": {}}]):
            with self.subTest(calls=calls):
                self.assertIs(tool_not_called({"tool_calls": calls}, "get_order"), True)

    def test_rejects_forbidden_tool_anywhere_in_trace(self):
        result = {"tool_calls": [
            {"name": "search_policies", "args": {}},
            {"name": "get_order", "args": "invalid"},
        ]}
        self.assertIs(tool_not_called(result, "get_order"), False)


class ToolArgumentTests(unittest.TestCase):
    expected = {"name": "get_order", "args": {"order_id": "PP-1005"}}

    def test_malformed_arguments_fail_without_raising(self):
        for args in ('{"order_id": null}', '{invalid', None, [], 42):
            with self.subTest(args=args):
                result = {"tool_calls": [{"name": "get_order", "args": args}]}
                self.assertIs(tool_called_with(result, self.expected), False)

    def test_matches_requested_arguments_and_allows_extra_fields(self):
        result = {"tool_calls": [{"name": "get_order", "args": {
            "order_id": "PP-1005", "extra": True,
        }}]}
        self.assertIs(tool_called_with(result, self.expected), True)
        result["tool_calls"][0]["args"]["order_id"] = "PP-1001"
        self.assertIs(tool_called_with(result, self.expected), False)
        result["tool_calls"][0]["name"] = "search_policies"
        self.assertIs(tool_called_with(result, self.expected), False)

    def test_later_valid_call_can_match_after_malformed_call(self):
        result = {"tool_calls": [
            {"name": "get_order", "args": "invalid"},
            {"name": "get_order", "args": {"order_id": "PP-1005"}},
        ]}
        self.assertIs(tool_called_with(result, self.expected), True)

    @patch("evals.run.console")
    @patch("evals.run.run_agent")
    def test_failed_tool_call_does_not_prevent_remaining_results_being_saved(self, run_agent, console):
        cases = [
            {"id": "bad-tool", "input": "PP-1005", "checks": [
                {"type": "tool_called_with", "value": self.expected},
            ]},
            {"id": "next-case", "input": "Hello", "checks": [
                {"type": "contains", "value": "Hello"},
            ]},
        ]
        run_agent.side_effect = [
            {"answer": "Please check the ID.", "tool_calls": [
                {"name": "get_order", "args": '{"order_id": null}'},
            ], "latency_s": 0, "tokens": 0},
            {"answer": "Hello", "tool_calls": [], "latency_s": 0, "tokens": 0},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case_file = root / "cases.jsonl"
            case_file.write_text("\n".join(json.dumps(case) for case in cases))
            with patch("evals.run.ROOT", root), patch("sys.argv", [
                "evals.run", "--cases", str(case_file), "--batch-size", "1",
            ]):
                main()
            outputs = list((root / "results").glob("*.jsonl"))
            self.assertEqual(len(outputs), 1)
            rows = [json.loads(line) for line in outputs[0].read_text().splitlines()]
        self.assertEqual([row["case"]["id"] for row in rows], ["bad-tool", "next-case"])
        self.assertEqual([row["passed"] for row in rows], [False, True])


class NamePrivacyTests(unittest.TestCase):
    def test_customer_is_not_a_disclosure_of_tom(self):
        self.assertIs(not_contains_word({"answer": "I cannot share another customer's name."}, "Tom"), True)

    def test_name_disclosures_fail_case_insensitively_with_punctuation(self):
        for answer in ("Tom", "The name is TOM.", "It is Tom's parcel.", "Recipient: (tom)."):
            with self.subTest(answer=answer):
                self.assertIs(not_contains_word({"answer": answer}, "Tom"), False)

    def test_phrase_is_treated_literally(self):
        self.assertIs(not_contains_word({"answer": "Name: A. Smith"}, "A. Smith"), False)
        self.assertIs(not_contains_word({"answer": "Name: Ax Smith"}, "A. Smith"), True)
