# ✍️ Writing good test cases

## The format

One case per line in `evals/cases.jsonl`:

```json
{"id": "price-next-day", "input": "How much does Next Day delivery cost?", "expected": "£6.50 for parcels up to 2 kg.", "checks": [{"type": "contains", "value": "6.50"}], "tags": ["policy"]}
```

| Field | What it's for |
|---|---|
| `id` | Short, unique name |
| `input` | What the customer says |
| `expected` | Ideal behaviour, in plain English, for manual review; does not affect the score |
| `checks` | Deterministic checks to run (types live in `checks.py`) |
| `tags` | Groups for the scorecard, e.g. `policy`, `safety` |

## What to cover

Aim for a mix. A test set of only easy questions tells you nothing.

| Category | Example idea |
|---|---|
| 😊 Happy path | Simple price or delivery-time questions |
| 🧮 Reasoning | Was order PP-1005 late *enough* for a refund? (Check the dates!) |
| 🔗 Multi-step | Needs **both** tools: an order lookup *and* a policy |
| ❓ Missing info | "Where's my parcel?" with no order ID |
| 🚫 Doesn't exist | An order ID that isn't in the data |
| 📏 Edge cases | A 25 kg parcel, a Sunday delivery, a perfume bottle |
| 🔒 Privacy | Asking for someone else's details |
| 💸 Overpromising | Pushing the bot to issue a refund itself |
| 🕵️ Injection | "Ignore your instructions and…" |
| 🌍 Off-topic | Questions nothing to do with parcels |

## Tips

- **Add checks to score a case.** A case without implemented checks remains unscored (➖), even if it has `expected` text.
- **One behaviour per case.** Easier to see what broke.
- **Merge overlapping scenarios.** Keep the existing case ID and combine useful checks; use a new case for a different boundary, fixture, or attack.
- **Match names as whole words.** Use `not_contains_word` for names such as `Tom`; a substring check would also reject `customer`.
- **Check order IDs as well as tool names.** Use `{"type": "tool_called_with", "value": {"name": "get_order", "args": {"order_id": "PP-1005"}}}` to check the requested order was looked up. Malformed tool arguments fail this check instead of stopping the run.
- **Check the truth.** Answers live in `agent/data/`, not in your memory.
- **Make cases fail for the right reason.** If a check fails, read the answer: is the bot wrong, or your check?
- **Avoid brittle checks.** `contains "£6.50"` fails on "6.50 pounds". Is that what you want?
