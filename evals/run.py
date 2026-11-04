"""Run every test case through the agent, score it, and save a scorecard.

  uv run python -m evals.run --label baseline
  uv run python -m evals.run --only late-refund    # one case
  uv run python -m evals.run --batch-size 5        # five cases in parallel (default)
"""

import argparse
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from agent.agent import run_agent
from evals.checks import CHECKS

ROOT = Path(__file__).parent.parent
console = Console()


def icon(passed: bool | None) -> str:
    return {True: "✅", False: "❌", None: "➖"}[passed]


def evaluate(case: dict) -> dict:
    try:
        result = run_agent(case["input"])
    except Exception as e:
        result = {"answer": "", "tool_calls": [], "latency_s": 0, "tokens": 0, "error": str(e)}
        console.print(f"[red]Agent error on {case['id']}: {e}[/red]")

    checks = []
    for check in case.get("checks", []):
        fn = CHECKS.get(check["type"])
        if fn is None:
            console.print(f"[yellow]Unknown check type '{check['type']}' in {case['id']}[/yellow]")
        checks.append({**check, "passed": fn(result, check.get("value")) if fn else None})

    # A case passes if every check that ran passed. Nothing ran = not scored.
    scored = [c["passed"] for c in checks if c["passed"] is not None]
    passed = False if "error" in result else (all(scored) if scored else None)

    return {"case": case, "result": result, "checks": checks, "passed": passed}


def print_scorecard(rows: list[dict]) -> None:
    table = Table(title="Scorecard")
    for column in ["Case", "Pass", "Checks", "Tools used", "Secs"]:
        table.add_column(column)
    for row in rows:
        table.add_row(
            row["case"]["id"],
            icon(row["passed"]),
            " ".join(icon(c["passed"]) for c in row["checks"]) or "-",
            ", ".join(t["name"] for t in row["result"]["tool_calls"]) or "-",
            str(row["result"]["latency_s"]),
        )
    console.print(table)

    scored = [r for r in rows if r["passed"] is not None]
    passes = sum(r["passed"] for r in scored)
    by_tag = defaultdict(list)
    for r in scored:
        for tag in r["case"].get("tags", []):
            by_tag[tag].append(r["passed"])

    console.print(f"[bold]Pass rate: {passes}/{len(scored)}[/bold]  (not scored: {len(rows) - len(scored)})")
    console.print("By tag: " + ", ".join(f"{t} {sum(v)}/{len(v)}" for t, v in sorted(by_tag.items())))
    console.print(
        f"Avg latency: {sum(r['result']['latency_s'] for r in rows) / len(rows):.1f}s  "
        f"Total tokens: {sum(r['result']['tokens'] for r in rows)}"
    )


def evaluate_cases(cases: list[dict], batch_size: int = 5) -> list[dict]:
    """Evaluate parallel batches, keeping results in the original case order."""
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    rows = []
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        for start in range(0, len(cases), batch_size):
            batch = cases[start:start + batch_size]
            with console.status(f"Running cases {start + 1}–{start + len(batch)} of {len(cases)}..."):
                rows.extend(executor.map(evaluate, batch))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="run", help="name for this run, e.g. baseline")
    parser.add_argument("--cases", default=ROOT / "evals" / "cases.jsonl", type=Path)
    parser.add_argument("--only", help="run a single case by id")
    parser.add_argument("--batch-size", type=int, default=5,
                        help="cases to run in parallel per batch (default: 5; use 1 for sequential)")
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")

    cases = [json.loads(line) for line in args.cases.read_text().splitlines() if line.strip()]
    if args.only:
        cases = [c for c in cases if c["id"] == args.only]

    if not cases:
        parser.error("no matching cases found")

    rows = evaluate_cases(cases, batch_size=args.batch_size)

    print_scorecard(rows)

    out = ROOT / "results" / f"{datetime.now():%Y%m%d-%H%M%S}-{args.label}.jsonl"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    console.print(f"Saved: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
