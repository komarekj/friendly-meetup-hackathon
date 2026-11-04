# Team Awesome Checkers: Judge the Agent 🐦

**Is Parcel Pigeon's support bot ready to ship?** We built an evaluation harness to answer that with evidence: customer scenarios, tool-use checks, privacy tests, and before/after comparisons.

**Demo verdict: not ready to ship yet.** Our hackathon exposed privacy leaks, skipped order lookups, incorrect price maths, and off-topic answers. We fixed the tool's disclosure of customer names and addresses, then examined where both the bot and its evaluators still fell short.

→ **[Walk through our changes and demo](docs/walkthrough.md)**

## What we built

- **42 consolidated cases** covering policy, dates, multi-step requests, missing information, unknown orders, privacy, injection, and overpromising. The original presentation used 22 cases.
- **Deterministic checks**, including `tool_called_with` for the right tool **and** order ID, whole-word privacy checks, forbidden tool calls, alternative wording, and price patterns.
- **A tool-level privacy fix:** `get_order` removes `customer_name` and `address` before data reaches the model.
- **Parallel evaluations** in batches of five, saved JSONL results, category breakdowns, latency/token reporting, and before/after comparisons.
- **An LLM-judge experiment** using a 1–5 rubric and retrieved evidence. It is part of the demo history; the current runner is checks-only.
- **A Streamlit dashboard** for scorecards, comparisons, and case inspection, delivered in [UI PR #3](https://github.com/komarekj/friendly-meetup-hackathon/pull/3). See the [dashboard walkthrough](docs/walkthrough.md#6-open-the-dashboard) for its separate setup.

## Quick start

Use Python 3.11+, [uv](https://docs.astral.sh/uv/getting-started/installation/), and Docker for the local model. Run commands from the repository root.

```bash
cp .env.example .env
docker compose up -d ollama
docker compose exec ollama ollama pull llama3.2:3b
uv sync
uv run python -m agent.agent "How much is Next Day delivery?"
uv run python -m evals.run --label current
```

The policy price is **£6.50** for Next Day delivery up to 2 kg; the model's answer is what we are testing, not a guaranteed result. For hosted models, configure `AGENT_*` in `.env` using [the provider guide](docs/providers.md).

Useful evaluation commands:

```bash
uv run python -m evals.run --only privacy-address --label privacy
uv run python -m evals.run --only standard-weekend-delay --label refund-dates
uv run python -m evals.run --batch-size 1 --label sequential
```

Each run prints a scorecard and saves `results/<timestamp>-<label>.jsonl`. The current CLI has **no `--judge` or `--no-judge` option** and needs no judge model.

## Read the results

| Signal | Meaning |
|---|---|
| ✅ | Every implemented check on the case passed |
| ❌ | A check failed, or the agent raised an error |
| ➖ | No implemented checks scored the case |
| By-tag pass rates | Results grouped by policy, privacy, safety, and other categories |
| Latency and tokens | Per-case agent latency/token usage; average latency and total tokens in the summary |

`expected` describes the desired behaviour for human review; it does **not** affect the current score. Four of the 42 cases currently have no checks. A green result proves only the checks that ran, not overall answer quality.

For a controlled comparison, save a run, change one thing, and re-run with the same model, cases, and scoring rules. Then compare the two saved files:

```bash
uv run python -m evals.compare "results/<before>.jsonl" "results/<after>.jsonl"
```

Replace the quoted paths with real filenames printed by the runner. See the [full comparison walkthrough](docs/walkthrough.md#5-make-a-controlled-beforeafter-comparison).

## What the presentation reported

The supplied **Team Awesome Checkers: Judge the Agent** PDF describes a historical 22-case experiment with `llama3.2:3b` as the bot and `qwen2.5:7b` as judge.

| Reported result | PDF source |
|---|---|
| Baseline: **10/22** passing | Page 4 |
| Later `fix-1-v2` run: **13/22** passing | Page 6 |
| Later run: **3.8/5** average judge score, **4.1 s** average latency | Page 6 |

These are slide-reported results, not fresh measurements of this checkout. The later run also used an improved judge, and its slide leaves the matched “Before” value as **TBC**; the figures do not establish a controlled three-case gain caused solely by the privacy fix. The original run files are not committed. Read the [demo findings and limitations](docs/walkthrough.md#7-present-the-original-demo-honestly).

## Explore the repo

| Location | Purpose |
|---|---|
| [agent/agent.py](agent/agent.py) | Model/tool loop and run telemetry |
| [agent/tools.py](agent/tools.py) | Redacted order lookup and policy search |
| [agent/data/](agent/data/) | Order fixtures and policy source used by the tools |
| [agent/system_prompt.md](agent/system_prompt.md) | Assistant instructions |
| [evals/cases.jsonl](evals/cases.jsonl) | Evaluation scenarios |
| [evals/checks.py](evals/checks.py) | Deterministic check implementations |
| [evals/run.py](evals/run.py) / [evals/compare.py](evals/compare.py) | Run and compare evaluations |
| [tests/](tests/) | Unit coverage for checks, cases, batching, and privacy filtering |
| [docs/walkthrough.md](docs/walkthrough.md) | Our changes, runnable tour, and demo narrative |

Add cases with [Writing good test cases](docs/writing-cases.md), change models with [Choosing your models](docs/providers.md), or explore [bonus challenges](docs/stretch.md).

## Next steps

Improve required tool use and refund-date reasoning, check off-topic handling and price maths, add scoring for unscored cases, and measure flakiness with repeated runs. If revisiting the judge, compare its decisions with human labels. None of these are certified fixed by the historical scorecard.
