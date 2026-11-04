import threading
import unittest
from unittest.mock import call, patch

from evals.run import evaluate, evaluate_cases


class BatchTests(unittest.TestCase):
    @patch("evals.run.console")
    def test_parallel_batches_preserve_order_and_wait_for_previous_batch(self, console):
        cases = [{"id": i} for i in range(12)]
        barriers = [threading.Barrier(5), threading.Barrier(5), threading.Barrier(2)]
        completed = set()
        lock = threading.Lock()

        def evaluate(case):
            index = case["id"]
            with lock:
                self.assertTrue(set(range(index // 5 * 5)).issubset(completed))
            # All cases in the batch must start concurrently to clear the barrier.
            barriers[index // 5].wait(timeout=5)
            with lock:
                completed.add(index)
            return case

        with patch("evals.run.evaluate", side_effect=evaluate):
            self.assertEqual(evaluate_cases(cases), cases)
        self.assertEqual(completed, set(range(12)))

    @patch("evals.run.console")
    def test_sequential_mode(self, console):
        cases = [{"id": i} for i in range(3)]
        with patch("evals.run.evaluate", side_effect=lambda case: case) as evaluate:
            self.assertEqual(evaluate_cases(cases, batch_size=1), cases)
        self.assertEqual(evaluate.call_args_list, [call(case) for case in cases])

    def test_rejects_nonpositive_batch_size(self):
        for size in (0, -1):
            with self.assertRaises(ValueError):
                evaluate_cases([], batch_size=size)


class EvaluateTests(unittest.TestCase):
    @patch("evals.run.run_agent")
    def test_checks_determine_pass_status(self, run_agent):
        run_agent.return_value = {"answer": "Delivery is £6.50", "tool_calls": [],
                                  "latency_s": 0, "tokens": 0}
        case = {"id": "price", "input": "How much?", "checks": [
            {"type": "contains", "value": "6.50"},
            {"type": "not_contains", "value": "free"},
        ]}
        self.assertIs(evaluate(case)["passed"], True)
        run_agent.return_value["answer"] = "Delivery is free"
        self.assertIs(evaluate(case)["passed"], False)

    @patch("evals.run.run_agent")
    def test_expectation_without_checks_is_unscored(self, run_agent):
        run_agent.return_value = {"answer": "Hello", "tool_calls": [],
                                  "latency_s": 0, "tokens": 0}
        row = evaluate({"id": "no-checks", "input": "Hello", "expected": "Say hello"})
        self.assertEqual(row["checks"], [])
        self.assertIsNone(row["passed"])

    @patch("evals.run.console")
    @patch("evals.run.run_agent", side_effect=RuntimeError("Unavailable"))
    def test_agent_error_fails_even_without_checks(self, run_agent, console):
        row = evaluate({"id": "error", "input": "Hello"})
        self.assertIs(row["passed"], False)
        self.assertEqual(row["result"]["error"], "Unavailable")


if __name__ == "__main__":
    unittest.main()
