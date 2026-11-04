# BASELINE — original Parcel Pigeon agent

Recorded on **4 November 2026**, before automatic improvements, using the original two-line prompt and unfiltered order tools from starter commit `60ce214`.

**31/42 cases passed (73.8%); 11 failed; zero unscored.** All 89 checks ran; 62 passed. No agent errors.

- [Full scorecard and failures](scorecard.md)
- [Raw per-case answers, tool traces, and check results](results.jsonl)
- [Machine-readable summary](summary.json)
- [Source hashes and run metadata](manifest.json)
- [Frozen original agent and evaluation harness](source/)
- [Runner output](run.log)

The frozen source is the code actually evaluated. The repository's main agent tools already contain a privacy improvement, so rerun from this snapshot to reproduce the original baseline. The GPT-6 Luna provider compatibility setting is retained. API credentials are not included.

Use this run as the baseline for future before/after comparisons, keeping the case and check hashes fixed. This supersedes the earlier partially scored baseline. Changes in the percentage from that earlier run are not evidence of an agent improvement.
