"""Deterministic checks: fast, free and repeatable.

Each check gets the agent's `result` and the `value` from the test case, and returns:
  True = pass, False = fail, None = not implemented yet (skipped)

`result` looks like:
  {"answer": "...", "tool_calls": [{"name": "get_order", "args": {"order_id": "PP-1001"}}],
   "latency_s": 3.2, "tokens": 812}
"""

import re


def contains(result: dict, value: str) -> bool:
    return value.lower() in result["answer"].lower()


def not_contains(result: dict, value: str) -> bool:
    return value.lower() not in result["answer"].lower()


def not_contains_word(result: dict, value: str) -> bool:
    """Reject a whole word or phrase, so 'Tom' does not match 'customer'."""
    return re.search(r"\b" + re.escape(value) + r"\b", result["answer"], re.IGNORECASE) is None


def tool_called(result: dict, value: str) -> bool:
    return any(call["name"] == value for call in result["tool_calls"])


def tool_called_with(result: dict, value: dict) -> bool:
    """Match a tool and its arguments, skipping malformed calls recorded as strings."""
    return any(
        call["name"] == value["name"]
        and isinstance(call["args"], dict)
        and all(call["args"].get(k) == v for k, v in value.get("args", {}).items())
        for call in result["tool_calls"]
    )


# TODO (Level 2): add your own checks here, then register them below. Ideas:
#   max_seconds       answer arrived in time
#   max_words         answer is concise
#   no_tools          agent didn't call any tool (e.g. for off-topic questions)
#   matches_regex     e.g. any price in the form £0.00


CHECKS = {
    "contains": contains,
    "not_contains": not_contains,
    "not_contains_word": not_contains_word,
    "tool_called": tool_called,
    "tool_called_with": tool_called_with,
}
