#!/usr/bin/env python3
import json, pathlib, collections

AUDIT_PATH = pathlib.Path(r"c:/Quant Trade/v9/V9_1/projects/quant_v9_3_1_btcusd/logs/live_pipeline_audit.ndjson")
REPORT_PATH = pathlib.Path(r"c:/Quant Trade/v9/V9_1/projects/quant_v9_3_1_btcusd/reports/strategy_flat_decision_audit.md")

# Load audit rows
rows = []
with AUDIT_PATH.open() as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue

# Latest 1000 rows
recent = rows[-1000:]

# Identify flat or STRATEGY_FLAT rows
flat_rows = []
for r in recent:
    if r.get('reason_code') == 'STRATEGY_FLAT':
        flat_rows.append(r)
        continue
    details = r.get('details', {})
    if details.get('direction') == 'flat':
        flat_rows.append(r)
        continue
    if any('STRATEGY_FLAT' in br for br in details.get('blocked_reasons', [])):
        flat_rows.append(r)
        continue

total_flat = len(flat_rows)

# Aggregations
blocked_counts = collections.Counter()
category_counts = collections.Counter()

for r in flat_rows:
    details = r.get('details', {})
    blocked = details.get('blocked_reasons', [])
    for br in blocked:
        blocked_counts[br] += 1
        # high level categories
        if 'off_session' in br:
            category_counts['off_session_regime'] += 1
        elif 'shock' in br:
            category_counts['shock_regime'] += 1
        elif 'invalid_session' in br:
            category_counts['invalid_session'] += 1
        elif 'rsi' in br:
            category_counts['rsi'] += 1
        elif 'adx' in br:
            category_counts['adx'] += 1
        elif 'atr' in br:
            category_counts['atr'] += 1
        elif 'spread' in br:
            category_counts['spread'] += 1
        elif 'score_below_threshold' in br:
            category_counts['score_below'] += 1
        else:
            category_counts['other'] += 1

# Field statistics (non-null values)
field_stats = {
    'rsi14_m15': [],
    'adx14_h1': [],
    'atr14_m1': [],
    'spread_bps': [],
    'effective_spread': [],
    'regime': [],
    'regime_result': [],
    'session_state': [],
    'signal_score': [],
    'ml_score': [],
}

for r in flat_rows:
    details = r.get('details', {})
    inds = details.get('indicators', {})
    for key in field_stats:
        if key in inds:
            field_stats[key].append(inds[key])
        elif key in r:
            field_stats[key].append(r[key])
        # else missing

def compute_stats(vals):
    if not vals:
        return None, None, None, 0
    mn = min(vals)
    mx = max(vals)
    avg = sum(vals) / len(vals)
    return mn, avg, mx, len(vals)

lines = []
lines.append("# Strategy Flat Decision Audit (last 1000 rows)\n\n")
lines.append(f"Total rows examined (last 1000): {len(recent)}\n")
lines.append(f"Rows with flat direction or STRATEGY_FLAT reason: {total_flat}\n\n")
lines.append("## Top Blocked Reasons (by count)\n")
for br, cnt in blocked_counts.most_common(10):
    pct = (cnt / total_flat) * 100 if total_flat else 0
    lines.append(f"- {br}: {cnt} ({pct:.2f}%)\n")
lines.append("\n## High-Level Failure Categories\n")
for cat, cnt in category_counts.most_common():
    pct = (cnt / total_flat) * 100 if total_flat else 0
    lines.append(f"- {cat}: {cnt} ({pct:.2f}%)\n")
lines.append("\n## Field Statistics (non-null values)\n")
for key, vals in field_stats.items():
    mn, avg, mx, cnt = compute_stats(vals)
    if cnt == 0:
        continue
    lines.append(f"- {key}: count={cnt}, min={mn:.2f}, mean={avg:.2f}, max={mx:.2f}\n")

# Answers to requested checks
lines.append("\n## Answers to Requested Checks\n")
if blocked_counts:
    top_reason = blocked_counts.most_common(1)[0][0]
else:
    top_reason = "N/A"
lines.append(f"1. Exact rule causing STRATEGY_FLAT: **{top_reason}**\n")
lines.append(f"2. RSI condition failing? {'Yes' if category_counts.get('rsi',0) else 'No'} (count={category_counts.get('rsi',0)})\n")
lines.append(f"3. ADX condition failing? {'Yes' if category_counts.get('adx',0) else 'No'} (count={category_counts.get('adx',0)})\n")
lines.append(f"4. ATR/volatility condition failing? {'Yes' if category_counts.get('atr',0) else 'No'} (count={category_counts.get('atr',0)})\n")
lines.append(f"5. Spread guard failing? {'Yes' if category_counts.get('spread',0) else 'No'} (count={category_counts.get('spread',0)})\n")
regime_fail = (
    category_counts.get('off_session_regime',0) +
    category_counts.get('shock_regime',0) +
    category_counts.get('invalid_session',0)
)
lines.append(f"6. Regime/session condition failing? {'Yes' if regime_fail else 'No'} (count={regime_fail})\n")
lines.append(f"7. Signal score below threshold? {'Yes' if category_counts.get('score_below',0) else 'No'} (count={category_counts.get('score_below',0)})\n")

REPORT_PATH.write_text(''.join(lines), encoding='utf-8')
print('Report written to', REPORT_PATH)
