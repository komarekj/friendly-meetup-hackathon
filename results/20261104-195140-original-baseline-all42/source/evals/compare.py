"""Compare two runs side by side.

  uv run python -m evals.compare results/<before>.jsonl results/<after>.jsonl
"""

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from evals.run import icon


def load(path: str) -> dict:
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    return {r["case"]["id"]: r for r in rows}


def main() -> None:
    before, after = load(sys.argv[1]), load(sys.argv[2])
    table = Table(title="Before → After")
    for column in ["Case", "Before", "After", "Change"]:
        table.add_column(column)

    for case_id in sorted(before.keys() | after.keys()):
        b = before.get(case_id, {}).get("passed")
        a = after.get(case_id, {}).get("passed")
        change = "🟢 fixed" if (b is False and a) else "🔴 broke" if (b and a is False) else ""
        table.add_row(case_id, icon(b), icon(a), change)

    Console().print(table)
    for name, run in [("Before", before), ("After", after)]:
        scored = [r["passed"] for r in run.values() if r["passed"] is not None]
        print(f"{name}: {sum(scored)}/{len(scored)} passed")


if __name__ == "__main__":
    main()
