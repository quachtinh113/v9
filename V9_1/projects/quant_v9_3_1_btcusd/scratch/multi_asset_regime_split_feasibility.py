#!/usr/bin/env python3
"""Multi‑Asset Regime‑Split Feasibility Audit

For each listed asset the script reads the last 30 days of
`logs/live_pipeline_audit.ndjson` and computes:
  * ADX and RSI distribution (min/mean/max)
  * Trend % and Range %
  * Current trades per week (order_send_called==True)
  * Simulated trades per week using the regime‑split rules
  * Improvement factor (simulated / current)

The results are written to
`reports/multi_asset_regime_split_feasibility.md`.
"""
import json, pathlib, collections, datetime, statistics
from dateutil import parser as dateparser

# ---------------------------------------------------------------------
ASSETS = [
    "btcusd",
    "xauusd",
    "us30",
    "us100",
    "eurusd",
    "gbpusd",
    "usdjpy",
    "usdchf",
    "audusd",
    "nzdusd",
]
# Mapping from asset symbol to project folder name (lowercase asset suffix)
PROJECT_ROOT = pathlib.Path(r"c:/Quant Trade/v9/V9_1/projects")
REPORT_PATH = pathlib.Path(r"c:/Quant Trade/v9/V9_1/reports/multi_asset_regime_split_feasibility.md")

now = datetime.datetime.utcnow()
start_date = now - datetime.timedelta(days=30)

def load_rows(audit_path: pathlib.Path):
    rows = []
    if not audit_path.is_file():
        return rows
    with audit_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts_str = obj.get("timestamp")
            if not ts_str:
                continue
            try:
                ts = dateparser.isoparse(ts_str)
            except Exception:
                continue
            if ts < start_date:
                continue
            rows.append(obj)
    return rows

# ---------------------------------------------------------------------
report_lines = []
report_lines.append("# Multi‑Asset Regime‑Split Feasibility Audit (30 days)\n\n")
report_lines.append("| Asset | Current trades / wk | Regime‑Split trades / wk | Improvement factor | Tier |
|------|-------------------|--------------------------|--------------------|------|\n")

for asset in ASSETS:
    proj_dir = PROJECT_ROOT / f"quant_v9_3_1_{asset}"
    audit_path = proj_dir / "logs" / "live_pipeline_audit.ndjson"
    rows = load_rows(audit_path)
    if not rows:
        # asset missing or no data – skip with placeholder
        report_lines.append(f"| {asset.upper()} | N/A | N/A | N/A | C |
")
        continue
    # ------------------- basic stats -------------------
    adx_vals = []
    rsi_vals = []
    regime_counts = collections.Counter()
    current_weeks = collections.Counter()
    simulated_weeks = collections.Counter()
    trend_cand = 0
    range_cand = 0
    allowed_sessions = {"london", "new_york"}
    for r in rows:
        details = r.get('details', {}) or {}
        inds = details.get('indicators', {}) or {}
        adx = inds.get('adx14_h1')
        rsi = inds.get('rsi14_m15')
        if isinstance(adx, (int, float)):
            adx_vals.append(float(adx))
        if isinstance(rsi, (int, float)):
            rsi_vals.append(float(rsi))
        regime = details.get('regime') or r.get('regime')
        if regime:
            regime_counts[regime] += 1
        # current trades per week (order_send_called true)
        if r.get('order_send_called'):
            ts = dateparser.isoparse(r.get('timestamp'))
            week = ts.isocalendar()[:2]
            current_weeks[week] += 1
        # simulation – only when session is london or new_york
        sess = None
        if "session_state" in r:
            sess = str(r["session_state"]).lower()
        else:
            sess = str(details.get('session_flag') or details.get('session_state') or r.get('session_flag') or "unknown").lower()
        if sess not in allowed_sessions:
            continue
        # transition block – ignore
        if isinstance(adx, (int, float)) and 20 <= adx <= 25:
            continue
        # trend candidate
        if isinstance(adx, (int, float)) and adx > 25 and regime == 'trend' and isinstance(rsi, (int, float)):
            if 40 <= rsi <= 75 or 25 <= rsi <= 60:
                trend_cand += 1
                ts = dateparser.isoparse(r.get('timestamp'))
                week = ts.isocalendar()[:2]
                simulated_weeks[week] += 1
                continue
        # range candidate (sideway or range)
        if isinstance(adx, (int, float)) and adx < 20 and regime in ('sideway', 'range') and isinstance(rsi, (int, float)):
            if rsi <= 35 or rsi >= 65:
                range_cand += 1
                ts = dateparser.isoparse(r.get('timestamp'))
                week = ts.isocalendar()[:2]
                simulated_weeks[week] += 1
                continue
    # ------------------- calculations -------------------
    total = len(rows)
    trend_pct = (regime_counts.get('trend', 0) / total) * 100 if total else 0
    range_pct = (regime_counts.get('sideway', 0) + regime_counts.get('range', 0)) / total * 100 if total else 0

    # current trades per week
    weeks_curr = len(current_weeks) if current_weeks else 1
    cur_trades_wk = sum(current_weeks.values()) / weeks_curr

    # simulated trades per week
    weeks_sim = len(simulated_weeks) if simulated_weeks else 1
    sim_trades_wk = (trend_cand + range_cand) / weeks_sim

    # improvement factor
    improvement = sim_trades_wk / cur_trades_wk if cur_trades_wk else float('inf')
    # tier decision (arbitrary thresholds)
    if improvement >= 1.5:
        tier = "A"
    elif improvement >= 1.0:
        tier = "B"
    else:
        tier = "C"

    # add a row to the markdown table
    report_lines.append(
        f"| {asset.upper()} | {cur_trades_wk:.2f} | {sim_trades_wk:.2f} | {improvement:.2f} | {tier} |\n"
    )

# ---------------------------------------------------------------------
report_lines.append("\n## Recommendations\n\n")
report_lines.append("**Tier A** – Strong candidate for regime‑split architecture (≥ 1.5× improvement).\n\n")
report_lines.append("**Tier B** – Optional; modest benefit (≈ 1.0–1.5×).\n\n")
report_lines.append("**Tier C** – Keep existing strategy; little or no gain.\n\n")

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(''.join(report_lines), encoding='utf-8')
print('Report written to', REPORT_PATH)
