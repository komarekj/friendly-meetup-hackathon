"""LLM-as-judge: a second model grades each answer against rubric.md."""

import json
from pathlib import Path

from agent.llm import client_for
from agent.tools import TOOLS

RUBRIC = (Path(__file__).parent / "rubric.md").read_text()


# def judge(case: dict, result: dict) -> dict | None:
#     """Return {"score": 1-5, "passed": bool, "reason": "..."}, or None to skip."""
#     if not case.get("expected"):
#         return None

#     # TODO (Level 3):
#     # 1. Build a prompt from RUBRIC, case["input"], case["expected"] and result["answer"].
#     # 2. Call the judge model:  client, model = client_for("JUDGE")
#     # 3. Ask for JSON back and parse it.  Hint: response_format={"type": "json_object"}
#     # 4. Decide which scores count as a pass.
#     return None

def _evidence(result: dict) -> str:
    """Re-run the agent's tool calls so the judge sees the same source data."""
    parts = []
    for call in result.get("tool_calls", []):
        fn = TOOLS.get(call["name"])
        if not fn:
            continue
        try:
            output = fn(**call["args"])
        except Exception as e:
            output = f"(tool error: {e})"
        parts.append(f"{call['name']}({json.dumps(call['args'])}) returned:\n{output}")
    return "\n\n".join(parts) or "(The assistant called no tools.)"



def judge(case: dict, result: dict) -> dict | None:
    """Return {"score": 1-5, "passed": bool, "reason": "..."}, or None to skip."""
    if not case.get("expected"):
        return None
    client, model = client_for("JUDGE")
    prompt = (
        f"{RUBRIC}\n\n"
        "Extra details in the answer are fine if the source data below supports them. "
        "Penalise anything the source data contradicts or doesn't support, "
        "including invented promises or made-up facts.\n\n"
        f"Customer question:\n{case['input']}\n\n"
        f"Expected behaviour:\n{case['expected']}\n\n"
        f"Source data the assistant retrieved:\n{_evidence(result)}\n\n"
        f"Assistant's answer:\n{result['answer']}"
    )
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    try:
        data = json.loads(response.choices[0].message.content)
        score = int(data["score"])
        reason = str(data.get("reason", ""))
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return {"score": None, "passed": False, "reason": "Judge returned invalid JSON"}
    return {"score": score, "passed": score >= 4, "reason": reason}
