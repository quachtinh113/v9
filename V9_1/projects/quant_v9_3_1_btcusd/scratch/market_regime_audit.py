#!/usr/bin/env python3
import json, pathlib, collections, datetime, statistics
from dateutil import parser as dateparser

AUDIT_PATH = pathlib.Path(r"c:/Quant Trade/v9/V9_1/projects/quant_v9_3_1_btcusd/logs/live_pipeline_audit.ndjson")
REPORT_PATH = pathlib.Path(r"c:/Quant Trade/v9/V9_1/projects/quant_v9_3_1_btcusd/reports/market_regime_audit.md")

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

adx_vals = []
rsi_vals = []
regime_counts = collections.Counter()
adx_over_25 = 0
rsi_valid = 0
trade_weeks = collections.Counter()

for r in rows:
    details = r.get('details', {}) or {}
    inds = details.get('indicators', {}) or {}
    adx = inds.get('adx14_h1')
    if isinstance(adx, (int, float)):
        adx_vals.append(float(adx))
        if adx > 25:
            adx_over_25 += 1
    rsi = inds.get('rsi14_m15')
    if isinstance(rsi, (int, float)):
        rsi_vals.append(float(rsi))
        rsi_valid += 1
    regime = details.get('regime') or r.get('regime')
    if regime:
        regime_counts[regime] += 1
    # trades detection
    if r.get('order_send_called'):
        ts = dateparser.isoparse(r.get('timestamp'))
        week = ts.isocalendar()[:2]
        trade_weeks[week] += 1

total = len(rows)
trend_pct = (regime_counts.get('trend', 0) / total) * 100 if total else 0
range_pct = (regime_counts.get('sideway', 0) / total) * 100 if total else 0

adb_min = min(adx_vals) if adx_vals else None
adb_max = max(adx_vals) if adx_vals else None
adb_mean = statistics.mean(adx_vals) if adx_vals else None

rsi_min = min(rsi_vals) if rsi_vals else None
rsi_max = max(rsi_vals) if rsi_vals else None
rsi_mean = statistics.mean(rsi_vals) if rsi_vals else None

adx_over_25_pct = (adx_over_25 / len(adx_vals) * 100) if adx_vals else 0
rsi_valid_pct = (rsi_valid / len(rsi_vals) * 100) if rsi_vals else 0

weeks = len(trade_weeks)
trades_per_week = (sum(trade_weeks.values()) / weeks) if weeks else 0

lines = []
lines.append("# Market Regime Audit (last 30 days)\n\n")
lines.append(f"Total rows analyzed: {total}\n\n")
lines.append("## ADX Distribution\n")
lines.append(f"- min: {adb_min:.2f}\n" if adb_min is not None else "- min: N/A\n")
lines.append(f"- max: {adb_max:.2f}\n" if adb_max is not None else "- max: N/A\n")
lines.append(f"- mean: {adb_mean:.2f}\n" if adb_mean is not None else "- mean: N/A\n")
lines.append("\n## RSI Distribution\n")
lines.append(f"- min: {rsi_min:.2f}\n" if rsi_min is not None else "- min: N/A\n")
lines.append(f"- max: {rsi_max:.2f}\n" if rsi_max is not None else "- max: N/A\n")
lines.append(f"- mean: {rsi_mean:.2f}\n" if rsi_mean is not None else "- mean: N/A\n")
lines.append("\n## Regime Percentages\n")
lines.append(f"- Trend regime: {trend_pct:.2f}%\n")
lines.append(f"- Range (sideway) regime: {range_pct:.2f}%\n")
lines.append("\n## Frequency Metrics\n")
lines.append(f"- ADX > 25: {adx_over_25_pct:.2f}% of rows with ADX\n")
lines.append(f"- RSI provides numeric value: {rsi_valid_pct:.2f}% of rows with RSI\n")
lines.append("\n## Expected Trades per Week\n")
lines.append(f"- Average trades/week (order_send_called true): {trades_per_week:.2f}\n")
lines.append("\n## Conclusion\n")
if trades_per_week < 1:
    lines.append("- Market regime unsuitable\n")
else:
    lines.append("- Strategy too strict\n")

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(''.join(lines), encoding='utf-8')
print('Report written to', REPORT_PATH)
