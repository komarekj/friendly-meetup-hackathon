import json
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

st.set_page_config(page_title="Parcel Pigeon Evals", layout="wide")
st.title("🐦 Team Awesome Checkers: Judge the Agent")
st_autorefresh(interval=2000, key="live")


def load(path):
    """A writer may not have finished its last JSONL record yet."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    rows = []
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def icon(passed):
    return "➖" if passed is None else "✅" if passed else "❌"


def counts(rows):
    scored = [row for row in rows if row.get("passed") is not None]
    return sum(row["passed"] is True for row in scored), len(scored)


def table(rows):
    return pd.DataFrame([{
        "case": row["case"]["id"],
        "tags": ", ".join(row["case"].get("tags", [])),
        "pass": icon(row.get("passed")),
        "checks": " ".join(icon(check.get("passed")) for check in row.get("checks", [])),
        "judge": (row.get("judge") or {}).get("score"),
        "tools": ", ".join(tool["name"] for tool in row["result"].get("tool_calls", [])),
        "secs": row["result"].get("latency_s"),
    } for row in rows])


# Improvement events are not evaluation rows. Keep them out of all three run pickers.
runs = {}
for path in sorted(RESULTS.glob("*.jsonl"), reverse=True):
    if path.name == "improve_log.jsonl":
        continue
    rows = load(path)
    if rows and all(isinstance(row.get("case"), dict) and "id" in row["case"]
                    and isinstance(row.get("result"), dict) for row in rows):
        runs[path] = rows
files = list(runs)

tab1, tab2, tab3, tab4 = st.tabs(["Scorecard", "Before vs after", "Inspect a case", "🔁 Self-improvement"])

with tab1:
    if not files:
        st.info("No evaluation runs yet.")
    else:
        run = st.selectbox("Run", files, format_func=lambda path: path.stem, key="scorecard_run")
        rows = runs[run]
        df = table(rows)
        passed, total = counts(rows)
        c1, c2, c3 = st.columns(3)
        c1.metric("Pass rate", f"{passed}/{total}" if total else "Not scored")
        c2.metric("Avg latency", f"{df['secs'].mean():.1f}s")
        judge_scores = df["judge"].dropna()
        if not judge_scores.empty:
            c3.metric("Avg judge score", f"{judge_scores.mean():.1f}/5")
        else:
            c3.metric("Unscored", len(rows) - total)
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab2:
    if not files:
        st.info("No evaluation runs yet.")
    else:
        a, b = st.columns(2)
        before = a.selectbox("Before", files, index=min(1, len(files) - 1), format_func=lambda p: p.stem)
        after = b.selectbox("After", files, index=0, format_func=lambda p: p.stem)
        old = {row["case"]["id"]: row.get("passed") for row in runs[before]}
        new = {row["case"]["id"]: row.get("passed") for row in runs[after]}
        comparison = pd.DataFrame([{
            "case": cid,
            "before": icon(old[cid]) if cid in old else "—",
            "after": icon(new[cid]) if cid in new else "—",
            "change": "Added" if cid not in old else "Removed" if cid not in new
                      else "🟢 fixed" if old[cid] is False and new[cid] is True
                      else "🔴 broke" if old[cid] is True and new[cid] is False else "",
        } for cid in sorted(set(old) | set(new))])
        passed, total = counts(runs[after])
        st.metric("After pass rate", f"{passed}/{total}" if total else "Not scored")
        st.dataframe(comparison, use_container_width=True, hide_index=True)

with tab3:
    if not files:
        st.info("No evaluation runs yet.")
    else:
        run = st.selectbox("Run", files, format_func=lambda p: p.stem, key="inspect_run")
        rows_by_id = {row["case"]["id"]: row for row in runs[run]}
        row = rows_by_id[st.selectbox("Case", list(rows_by_id))]
        st.markdown(f"**Customer:** {row['case']['input']}")
        st.markdown(f"**Expected:** {row['case'].get('expected', '-')}")
        st.info(row["result"]["answer"])
        judge = row.get("judge")
        if judge:
            st.markdown(f"**Judge:** {judge.get('score', '-')}/5, {judge.get('reason', '')}")
        st.json({"tool_calls": row["result"].get("tool_calls"), "checks": row.get("checks")})

with tab4:
    events = [event for event in load(RESULTS / "improve_log.jsonl")
              if all(key in event for key in ("run_id", "round", "stage"))]
    if not events:
        st.info("Start it with: uv run python improve.py 3")
    else:
        run_ids = list(dict.fromkeys(event["run_id"] for event in events))
        # Follow a new run even if the dashboard was already open.
        selected = st.selectbox("Improvement run", ["Latest", *reversed(run_ids)], key="improvement_run")
        run_id = run_ids[-1] if selected == "Latest" else selected
        events = [event for event in events if event["run_id"] == run_id]
        scores = []
        retained = None
        for event in events:
            if event["stage"] in ("baseline", "result"):
                candidate = 100 * event["passed"] / event["total"]
                if event["stage"] == "baseline" or event["kept"]:
                    retained = candidate
                scores.append({"Round": event["round"], "Candidate %": candidate, "Retained %": retained})
        if scores:
            st.line_chart(pd.DataFrame(scores).set_index("Round"))
        last = events[-1]
        st.caption(f"Round {last['round']} · {last['stage']}")
        if last["stage"] in ("error", "interrupted"):
            st.error(last.get("error") or "Run interrupted; pending candidate reverted.")
        elif last["stage"] == "done":
            st.success(f"Best: {last['best']}/{last['total']} ({last['pass_rate']:.1%})")
        for event in reversed(events):
            rnd = event["round"]
            stage = event["stage"]
            if stage == "baseline":
                with st.expander(f"Round 0 · baseline {event['passed']}/{event['total']}"):
                    if event.get("unscored"):
                        st.caption(f"{event['unscored']} unscored cases excluded")
                    for failure in event["failures"]:
                        st.markdown(f"❌ **{failure['id']}**: {failure['input']}")
                        st.caption(f"Bot said: {failure['answer'][:300]}")
                        st.json({"failed_checks": failure["failed_checks"], "tools": failure["tools"]})
            elif stage == "plan":
                with st.expander(f"Round {rnd} · proposed changes", expanded=rnd == last["round"]):
                    for diagnosis in event.get("diagnosis", []):
                        st.markdown(f"- **{diagnosis['case']}**: {diagnosis['why_it_failed']}")
                    st.info(event["plan"])
                    a, b = st.columns(2)
                    a.text_area("Old prompt", event["old_prompt"], height=200,
                                key=f"old-{run_id}-{rnd}", disabled=True)
                    b.text_area("New prompt", event["new_prompt"], height=200,
                                key=f"new-{run_id}-{rnd}", disabled=True)
            elif stage == "result":
                decision = "✅ kept" if event["kept"] else "↩️ reverted"
                st.markdown(f"**Round {rnd}: {event['previous']}/{event['total']} → "
                            f"{event['passed']}/{event['total']} ({decision})**")
                st.caption(f"Fixed: {', '.join(event['fixed']) or '—'} · Broke: {', '.join(event['broke']) or '—'}")
