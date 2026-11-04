import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class DashboardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "ui").mkdir()
        self.script = self.root / "ui/ui.py"
        shutil.copyfile(ROOT / "ui/ui.py", self.script)
        self.results = self.root / "results"
        self.results.mkdir()

    def run_app(self):
        with patch("streamlit_autorefresh.st_autorefresh"):
            app = AppTest.from_file(str(self.script)).run(timeout=15)
        self.assertFalse(app.exception)
        return app

    def write_log(self, events, suffix=""):
        (self.results / "improve_log.jsonl").write_text(
            "\n".join(json.dumps(event) for event in events) + "\n" + suffix)

    def test_empty_results_still_show_fourth_tab(self):
        app = self.run_app()
        self.assertEqual(len(app.tabs), 4)
        self.assertIn("Self-improvement", app.tabs[3].label)
        self.assertIn("uv run python improve.py 3", app.info[-1].value)

    def test_log_only_and_partial_line_do_not_enter_run_picker(self):
        self.write_log([{"run_id": "first", "round": 0, "stage": "start"}], '{"run_id":')
        app = self.run_app()
        self.assertEqual([widget.label for widget in app.selectbox], ["Improvement run"])
        self.assertEqual(app.caption[-1].value, "Round 0 · start")

    def test_distinct_runs_with_same_round_have_no_widget_collisions(self):
        events = []
        for run_id in ("first", "second"):
            events.extend([
                {"run_id": run_id, "round": 0, "stage": "baseline", "passed": 1, "total": 2,
                 "failures": [], "unscored": 1},
                {"run_id": run_id, "round": 1, "stage": "plan", "diagnosis": [], "plan": "Use tools",
                 "old_prompt": "Old", "new_prompt": "New"},
                {"run_id": run_id, "round": 1, "stage": "result", "passed": 0, "total": 2,
                 "previous": 1, "kept": False, "fixed": [], "broke": ["a"]},
            ])
        self.write_log(events)
        app = self.run_app()
        self.assertEqual(app.selectbox[0].options, ["Latest", "second", "first"])
        self.assertEqual(len(app.text_area), 2)
        self.assertTrue(all("second" in widget.key for widget in app.text_area))
        self.assertTrue(any("reverted" in item.value for item in app.markdown))

    def test_checks_only_score_excludes_unscored_and_hides_missing_judge(self):
        rows = [{"case": {"id": str(index), "input": "Question"}, "checks": [], "passed": state,
                 "result": {"answer": "Answer", "tool_calls": [], "latency_s": 1}}
                for index, state in enumerate((True, False, None))]
        (self.results / "example.jsonl").write_text("\n".join(json.dumps(row) for row in rows))
        self.write_log([{"run_id": "first", "round": 0, "stage": "start"}])
        app = self.run_app()
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Pass rate"], "1/2")
        self.assertEqual(metrics["Unscored"], "1")
        self.assertNotIn("Avg judge score", metrics)
        self.assertEqual(app.selectbox[0].options, ["example"])


if __name__ == "__main__":
    unittest.main()
