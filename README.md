# Judge the Agent 🟡

> **Parcel Pigeon's** AI support bot goes live next week.
> Your job: prove whether it's ready, with evidence instead of vibes.

## 🎯 What you'll build

- A **test set** of customer questions
- **Automatic checks** that score answers against explicit rules
- A **before/after scorecard** showing that your fix worked

## ⚙️ Setup (10 min)

You need: [Docker](https://docs.docker.com/get-docker/) and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
cp .env.example .env
docker compose up -d                                   # starts local LLMs
docker compose exec ollama ollama pull llama3.2:3b     # the agent (2 GB)
uv run python -m agent.agent "How much is Next Day delivery?"
```

✅ You should see an answer mentioning **£6.50**.

💡 Using a hosted model (OpenAI, Gemini, Mistral…) instead? See [docs/providers.md](docs/providers.md).

## 🪜 The challenge

| Level | Goal | Time |
|---|---|---|
| 1 | Meet the agent | 15 min |
| 2 | Write the tests | 45 min |
| 3 | Review the checks | 30 min |
| 4 | Fix it and prove it | 30 min |
| ⭐ | Bonus | Any time left |

### Level 1: Meet the agent

1. Skim [agent/data/policies.md](agent/data/policies.md). This is what the bot should know.
2. Ask it a few questions with `uv run python -m agent.agent "..."`
3. Run the starter tests:
   ```bash
   uv run python -m evals.run --label baseline
   ```

   Cases run in parallel batches of **5**, including their checks. Each batch finishes before the next starts. Use `--batch-size 1` for sequential runs, or set another batch size with `--batch-size <number>`.

✅ **Done when:** you see a scorecard. (➖ means "not scored yet". You'll fix that next.)

### Level 2: Write the tests

1. ✅ Implemented `tool_called` in [evals/checks.py](evals/checks.py).
2. Add **at least one check of your own** (ideas in the file).
3. Add **15+ cases** to [evals/cases.jsonl](evals/cases.jsonl) → [how to write good cases](docs/writing-cases.md)

✅ **Done when:** 20+ cases, and no ➖ in the Checks column.

### Level 3: Review the checks

1. Run the full suite again.
2. Read answers for 3–4 passing and failing cases in `results/` and compare them with each case's `expected` behaviour.
3. Improve checks that miss incorrect answers or reject correct ones. Cases without implemented checks remain unscored (➖); `expected` text is for manual review only.
4. Is one score enough? A customer, a support manager and a lawyer would each assess the same answer differently. Pick the perspectives that matter to you (readability is one) and decide how to measure each with checks or metrics.

✅ **Done when:** every case has an implemented check, and you've reviewed what those checks can miss.

### Level 4: Fix it and prove it

1. Pick a failure. Change **one thing**: the [system prompt](agent/system_prompt.md), a [tool](agent/tools.py), or the model.
2. Re-run and compare:
   ```bash
   uv run python -m evals.run --label fix-1
   uv run python -m evals.compare results/<baseline>.jsonl results/<fix-1>.jsonl
   ```

💡 Watch for fixes that break something else. And not every fix belongs in the prompt.

✅ **Done when:** the comparison shows at least one 🟢 fixed and no 🔴 broke.

### ⭐ Bonus

Tracing, check accuracy, model shoot-outs, red-teaming → [docs/stretch.md](docs/stretch.md)

## 🎤 Demo (3 min)

- Your scorecard **before and after**
- One **interesting failure**, and why it happened
- **Do you trust your checks?** Why or why not?
- **Which metrics did you choose**, and what did each one reveal?

## 🗂️ Project map

```
agent/                  the bot you're testing
├── agent.py            agent loop (no need to edit)
├── system_prompt.md    its instructions ← edit in Level 4
├── tools.py            get_order, search_policies
└── data/               policies + orders (the "truth")
evals/                  your work happens here
├── cases.jsonl         test cases ← Level 2
├── checks.py           deterministic checks ← Level 2
├── run.py              runs everything → results/
└── compare.py          before vs after
docs/                   short guides
results/                saved runs (one file per run)
```

## 🆘 Stuck?

| Problem | Try |
|---|---|
| Connection error | `docker compose ps` (is Ollama running?) and check `.env` |
| Too slow | `--only <case-id>`, increase `--batch-size`, or use a hosted model |
| Model ignores tools | Normal for small models! That's a finding: put it in a test. |
| Anything else | Grab an organiser 🙋 |
