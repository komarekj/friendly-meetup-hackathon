import json, sys, time
from pathlib import Path

from tqdm import tqdm

from agent.llm import client_for
from evals.run import evaluate

PROMPT = Path("agent/system_prompt.md")
LOG = Path("results/improve_log.jsonl")
CASES = [json.loads(l) for l in Path("evals/cases.jsonl").open() if l.strip()]
ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
Path("results").mkdir(exist_ok=True)


def log(round_, stage, **data):
    tqdm.write(f"[round {round_}] {stage}")
    with LOG.open("a") as f:
        f.write(json.dumps({"t": time.time(), "round": round_, "stage": stage, **data}) + "\n")


def run_evals(label):
    rows = [evaluate(case, use_judge=True) for case in tqdm(CASES, desc=label, unit="case")]
    out = Path("results") / f"{time.strftime('%Y%m%d-%H%M%S')}-{label}.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return rows


def failures(rows):
    return [{
        "id": r["case"]["id"], "input": r["case"]["input"],
        "expected": r["case"].get("expected"), "answer": r["result"]["answer"],
        "tools": [t["name"] for t in r["result"]["tool_calls"]],
        "failed_checks": [c for c in r.get("checks", []) if c.get("passed") is False],
        "judge": r.get("judge"),
    } for r in rows if not r.get("passed")]


client, model = client_for("JUDGE")
log(0, "starting")
rows = run_evals("improve-r0")
best = sum(bool(r.get("passed")) for r in rows)
log(0, "baseline", passed=best, total=len(rows), failures=failures(rows))

for rnd in tqdm(range(1, ROUNDS + 1), desc="rounds", unit="round"):
    fails = failures(rows)
    log(rnd, "thinking", n_failures=len(fails))
    current = PROMPT.read_text()
    resp = client.chat.completions.create(
        model=model, temperature=0.7, response_format={"type": "json_object"},
        messages=[{"role": "user", "content":
            "You improve the system prompt of a customer support bot.\n\n"
            f"Current system prompt:\n{current}\n\nFailing test cases:\n{json.dumps(fails, indent=1)}\n\n"
            'Reply with JSON: {"diagnosis": [{"case": id, "why_it_failed": "..."}], '
            '"plan": "step-by-step reasoning about what to change and why", '
            '"new_prompt": "the full improved system prompt"}'}])
    proposal = json.loads(resp.choices[0].message.content)
    log(rnd, "plan", diagnosis=proposal.get("diagnosis"), plan=proposal.get("plan"),
        old_prompt=current, new_prompt=proposal["new_prompt"])

    PROMPT.write_text(proposal["new_prompt"])
    log(rnd, "testing")
    new_rows = run_evals(f"improve-r{rnd}")
    score = sum(bool(r.get("passed")) for r in new_rows)
    old_pass = {r["case"]["id"] for r in rows if r.get("passed")}
    new_pass = {r["case"]["id"] for r in new_rows if r.get("passed")}
    kept = score > best
    log(rnd, "result", passed=score, previous=best, kept=kept,
        fixed=sorted(new_pass - old_pass), broke=sorted(old_pass - new_pass))
    if kept:
        best, rows = score, new_rows
    else:
        PROMPT.write_text(current)

log(ROUNDS, "done", best=best)