"""The two tools the support agent can call."""

import json
import re
from pathlib import Path

DATA = Path(__file__).parent / "data"
ORDERS = {o["order_id"]: o for o in json.loads((DATA / "orders.json").read_text())}
POLICY_SECTIONS = ["## " + s for s in (DATA / "policies.md").read_text().split("\n## ")[1:]]
STOPWORDS = {"a", "an", "the", "is", "are", "my", "i", "do", "does", "can", "to", "of", "for", "how", "what", "it", "on", "in", "and", "you"}


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower())) - STOPWORDS


def get_order(order_id: str) -> str:
    order = ORDERS.get(order_id.strip().upper())
    return json.dumps(order) if order else f"No order found with ID {order_id}."


def search_policies(query: str) -> str:
    """Naive keyword search: returns the 2 policy sections sharing the most words with the query."""
    query_words = _words(query)
    ranked = sorted(POLICY_SECTIONS, key=lambda s: len(query_words & _words(s)), reverse=True)
    return "\n\n".join(ranked[:2])


TOOLS = {"get_order": get_order, "search_policies": search_policies}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Look up a customer's order by its ID, e.g. PP-1001.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_policies",
            "description": "Search Parcel Pigeon's policies: prices, delivery times, refunds, lost parcels, prohibited items, etc.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]
