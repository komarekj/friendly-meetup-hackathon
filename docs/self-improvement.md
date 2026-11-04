# Live self-improvement demo

The loop in [improve.py](../improve.py) evaluates Parcel Pigeon, asks `qwen2.5:7b`
for a diagnosis and replacement system prompt, and evaluates the candidate on
the same cases. It keeps the prompt **only when the scored pass rate increases**;
a tie or regression restores the last accepted prompt. This changes only
`agent/system_prompt.md`, not tools, checks, or test expectations.

## Set up

Use the existing [agent setup](../README.md). Add these entries to your `.env`
if it predates this feature (do not overwrite your existing agent configuration):

```dotenv
JUDGE_BASE_URL=http://localhost:11434/v1
JUDGE_API_KEY=
JUDGE_MODEL=qwen2.5:7b
```

The `JUDGE_*` name reuses the model-role configuration; this model now **proposes
prompt changes**, not evaluation grades. Scoring remains deterministic and
checks-only. Pull the optimizer once if using the local Ollama setup:

```bash
docker compose exec ollama ollama pull qwen2.5:7b
```

## Run side by side

From the **same checkout**, open two terminals. Start the dashboard in the first:

```bash
uv run --group ui streamlit run ui/ui.py
```

Or use the transient dependencies from the demo sketch:

```bash
uv run --with streamlit --with pandas --with streamlit-autorefresh streamlit run ui/ui.py
```

Start the loop in the second:

```bash
uv run python improve.py 3
```

Open **🔁 Self-improvement**. It refreshes every two seconds, including before
the first result exists. Each round shows the diagnosis, a concise rationale,
old/new prompts, fixed/broken cases, and the keep/revert decision. The chart plots
percentages: **Candidate %** can fall; **Retained %** tracks the best accepted
prompt. The first three tabs still inspect saved evaluation runs.

Three rounds means one baseline plus up to three full candidate evaluations.
The loop stops early if all scored cases pass. Speed depends on model and
hardware; use `--batch-size 1` for sequential evaluation if needed.

## What is saved and what counts

- `results/improve_log.jsonl` is append-only, with a unique `run_id` on every
  event. You do **not** need to delete it between demos. The run picker follows
  **Latest** by default and can inspect older runs.
- `results/improvements/<run_id>/original_prompt.md` is the exact starting
  prompt; `best_prompt.md` holds the latest accepted version. Backups are automatic.
- The same directory contains a frozen `cases.jsonl`; every candidate must
  return the same case definitions and scored case IDs as the baseline.
- `results/improve-<run_id>-r<round>.jsonl` records each evaluation. The loop reads
  that exact output, not the newest file from a previous run.
- Cases with `passed: null` are **unscored**, not failures. They are excluded
  from optimization and the denominator. With the current 42-case suite, four
  cases normally remain unscored. Review their answers separately.
- Model-service/agent errors, malformed proposals, missing/duplicate cases,
  empty results, or a changed scored set stop the run. They are not improvements.
- An aggregate gain may still break individual cases. The log and live page
  expose both fixed and broken cases; this is not a no-regressions gate.

Generated logs, results, backups, and the lock file are gitignored. The accepted
system prompt stays modified in your worktree for review; the loop does not
commit, push, or publish it.

## Stop and recover

Ctrl-C or SIGTERM during candidate evaluation restores the previous accepted
prompt. A rejected candidate is also restored byte-for-byte. Do not edit the
prompt or run independent evaluations in this checkout while a candidate is
being tested; they share the same prompt file. A lock blocks a second improvement
loop in this checkout.

A forced kill or power loss cannot run cleanup. If that happens:

1. Confirm the optimizer and its evaluation subprocess are no longer running.
2. Copy `results/improvements/<run_id>/best_prompt.md` back to
   `agent/system_prompt.md` (or use `original_prompt.md` to reset the whole demo).
3. Remove the stale `results/.improve.lock` only after confirming there is no
   live loop. Then start a new run; its history will be separate.

## Avoid mistaking training gains for readiness

The proposer sees the failing inputs, expected answers, and checks, so this is
optimization on a **training set**, not independent evidence of generalization.
Instructions discourage memorized order IDs and phrases, but cannot guarantee
that the model won't overfit. Review the generated prompt for shortcuts.

Keep separate, meaningful training and held-out JSONL files. Run the loop only
on the training file, then evaluate the held-out suite without feeding its
failures back into the loop:

```bash
uv run python improve.py 3 --cases path/to/training.jsonl
uv run python -m evals.run --cases path/to/held-out.jsonl --label held-out
```

These paths are placeholders for your own files; this feature does not supply
or claim a validated split. Repeat runs to measure flakiness. A higher score on
the optimization cases alone does not mean the bot is ready to ship.
