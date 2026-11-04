# ⭐ Bonus challenges

Pick any. They're independent.

## 🔭 Trace every step

See exactly what the agent did: every model call, tool call and token.

```bash
uv sync --group tracing
docker compose --profile tracing up -d     # wait ~10 s for it to start
```

Add to the top of `evals/run.py`:

```python
from phoenix.otel import register
register(project_name="parcel-pigeon", auto_instrument=True)
```

Run the evals, then open <http://localhost:6006>. Click into a failure.

## ⚖️ Can you trust the checks?

1. Hand-label 10 answers yourselves (pass/fail).
2. Compare with the automatic checks. What % do you agree on?
3. Improve `checks.py` or the cases' check definitions and see if agreement goes up.

## 🎲 Is it flaky?

Run each case 3 times. Which ones flip between pass and fail? Add a `--repeat` option to `run.py`.

## 🏁 Model shoot-out

Run the same suite on 2–3 agent models. Make a table: **pass rate · avg latency · tokens**. Which would you ship?

## 🕵️ Red team

Write 5 sneaky cases to make the bot leak data, promise refunds or go off-topic. Then defend against them.
