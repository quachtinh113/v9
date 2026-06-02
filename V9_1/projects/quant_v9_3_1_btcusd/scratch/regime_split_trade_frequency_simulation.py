#!/usr/bin/env python3
import json, pathlib, collections, datetime, statistics
from dateutil import parser as dateparser

AUDIT_PATH = pathlib.Path(r"c:/Quant Trade/v9/V9_1/projects/quant_v9_3_1_btcusd/logs/live_pipeline_audit.ndjson")
REPORT_PATH = pathlib.Path(r"c:/Quant Trade/v9/V9_1/projects/quant_v9_3_1_btcusd/reports/regime_split_trade_frequency_simulation.md")

now = datetime.datetime.utcnow()
start_date = now - datetime.timedelta(days=30)

rows = []
with AUDIT_PATH.open() as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts_str = obj.get('timestamp')
        if not ts_str:
            continue
        try:
            ts = dateparser.isoparse(ts_str)
        except Exception:
            continue
        if ts < start_date:
            continue
        rows.append(obj)

# Counters
trend_cand = 0
range_cand = 0
transition_block = 0
off_session_block = 0

# Weekly grouping for trade estimate
weeks = collections.Counter()

allowed_sessions = {"london", "new_york"}

for r in rows:
    # session state – try explicit field first
    sess = None
    if "session_state" in r:
        sess = str(r["session_state"]).lower()
    else:
        details = r.get('details', {}) or {}
        sess = str(details.get('session_flag') or details.get('session_state') or r.get('session_flag') or "unknown").lower()
    # ADX
    details = r.get('details', {}) or {}
    inds = details.get('indicators', {}) or {}
    adx = inds.get('adx14_h1')
    rsi = inds.get('rsi14_m15')
    regime = details.get('regime') or r.get('regime')
    # Off‑session block
    if sess not in allowed_sessions:
        off_session_block += 1
        continue
    # Transition block (20 <= ADX <= 25)
    if isinstance(adx, (int, float)) and 20 <= adx <= 25:
        transition_block += 1
        continue
    # Trend candidate
    if isinstance(adx, (int, float)) and adx > 25 and regime == 'trend' and isinstance(rsi, (int, float)):
        if 40 <= rsi <= 75 or 25 <= rsi <= 60:
            trend_cand += 1
            # record week for trade estimate
            ts = dateparser.isoparse(r.get('timestamp'))
            weeks[ts.isocalendar()[:2]] += 1
            continue
    # Range candidate (sideway or range)
    if isinstance(adx, (int, float)) and adx < 20 and regime in ('sideway', 'range') and isinstance(rsi, (int, float)):
        if rsi <= 35 or rsi >= 65:
            range_cand += 1
            ts = dateparser.isoparse(r.get('timestamp'))
            weeks[ts.isocalendar()[:2]] += 1
            continue
    # Anything else is ignored for this simulation

total_weeks = len(weeks) if weeks else 1
estimated_trades_per_week = (trend_cand + range_cand) / total_weeks

# Determine which sub‑strategy contributes more
if trend_cand > range_cand:
    dominant = "Trend"
elif range_cand > trend_cand:
    dominant = "Range"
else:
    dominant = "Equal"

# Baseline from previous audit (0.8 trades/week) – hard‑coded for comparison
baseline = 0.8
increase = "increase" if estimated_trades_per_week > baseline else "decrease"

# Build report
lines = []
lines.append("# Regime‑Split Trade Frequency Simulation (last 30 days)\n\n")
lines.append(f"Total rows examined: {len(rows)}\n\n")
lines.append(f"1. Trend candidate count: {trend_cand}\n")
lines.append(f"2. Range candidate count: {range_cand}\n")
lines.append(f"3. Transition blocked count (20 ≤ ADX ≤ 25): {transition_block}\n")
lines.append(f"4. Off‑session blocked count: {off_session_block}\n\n")
lines.append(f"5. Estimated trades per week (assuming each candidate becomes a trade): {estimated_trades_per_week:.2f}\n\n")
lines.append(f"6. Sub‑strategy contributing more trades: {dominant}\n\n")
lines.append(f"7. Compared to baseline (0.8 trades/week) this represents a **{increase}** in trade frequency.\n")

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(''.join(lines), encoding='utf-8')
print('Report written to', REPORT_PATH)
