import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Parcel Pigeon Evals", layout="wide")
st.title("🐦 Team Awesome Checkers: Judge the Agent")

files = sorted(Path("results").glob("*.jsonl"), reverse=True)
if not files:
    st.warning("No runs in results/ yet.")
    st.stop()


def load(path):
    return [json.loads(line) for line in path.open() if line.strip()]


def table(rows):
    return pd.DataFrame([{
        "case": r["case"]["id"],
        "tags": ", ".join(r["case"].get("tags", [])),
        "pass": "✅" if r.get("passed") else "❌",
        "checks": " ".join("✅" if c.get("passed") else "➖" if c.get("passed") is None else "❌"
                           for c in r.get("checks", [])),
        "judge": (r.get("judge") or {}).get("score"),
        "tools": ", ".join(t["name"] for t in r["result"].get("tool_calls", [])),
        "secs": r["result"].get("latency_s"),
    } for r in rows])


tab1, tab2, tab3 = st.tabs(["Scorecard", "Before vs after", "Inspect a case"])

with tab1:
    run = st.selectbox("Run", files, format_func=lambda p: p.stem)
    rows = load(run)
    df = table(rows)
    passed = sum(1 for r in rows if r.get("passed"))
    c1, c2, c3 = st.columns(3)
    c1.metric("Pass rate", f"{passed}/{len(rows)}")
    c2.metric("Avg latency", f"{df['secs'].mean():.1f}s")
    c3.metric("Avg judge score", f"{df['judge'].dropna().mean():.1f}/5")
    st.dataframe(df, use_container_width=True, hide_index=True)

with tab2:
    a, b = st.columns(2)
    before = a.selectbox("Before", files, index=min(1, len(files) - 1), format_func=lambda p: p.stem)
    after = b.selectbox("After", files, index=0, format_func=lambda p: p.stem)
    old = {r["case"]["id"]: r.get("passed") for r in load(before)}
    new = {r["case"]["id"]: r.get("passed") for r in load(after)}
    cmp = pd.DataFrame([{
        "case": cid,
        "before": "✅" if old.get(cid) else "❌",
        "after": "✅" if new.get(cid) else "❌",
        "change": "🟢 fixed" if new.get(cid) and not old.get(cid)
                  else "🔴 broke" if old.get(cid) and not new.get(cid) else "",
    } for cid in sorted(set(old) | set(new))])
    st.metric("Pass rate", f"{sum(map(bool, new.values()))}/{len(new)}",
              delta=sum(map(bool, new.values())) - sum(map(bool, old.values())))
    st.dataframe(cmp, use_container_width=True, hide_index=True)

with tab3:
    run = st.selectbox("Run ", files, format_func=lambda p: p.stem)
    rows = {r["case"]["id"]: r for r in load(run)}
    r = rows[st.selectbox("Case", list(rows))]
    st.markdown(f"**Customer:** {r['case']['input']}")
    st.markdown(f"**Expected:** {r['case'].get('expected', '-')}")
    st.info(r["result"]["answer"])
    judge = r.get("judge") or {}
    st.markdown(f"**Judge:** {judge.get('score', '-')}/5, {judge.get('reason', '')}")
    st.json({"tool_calls": r["result"].get("tool_calls"), "checks": r.get("checks")})