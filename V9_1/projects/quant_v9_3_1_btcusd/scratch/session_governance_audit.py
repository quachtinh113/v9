#!/usr/bin/env python3
import json, pathlib, collections

AUDIT_PATH = pathlib.Path(r"c:/Quant Trade/v9/V9_1/projects/quant_v9_3_1_btcusd/logs/live_pipeline_audit.ndjson")
REPORT_PATH = pathlib.Path(r"c:/Quant Trade/v9/V9_1/projects/quant_v9_3_1_btcusd/reports/session_governance_audit.md")

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

recent = rows[-1000:]

# Helper to get session state from details.indicators or top-level
def get_session(r):
    # Prefer details.indicators.session_flag if present
    details = r.get('details', {})
    if isinstance(details, dict):
        sess = details.get('session_flag')
        if sess:
            return sess
        # sometimes under 'indicators'
        inds = details.get('indicators', {})
        if isinstance(inds, dict):
            sess = inds.get('session_flag')
            if sess:
                return sess
    # fallback
    return r.get('session_state') or r.get('session_flag') or 'unknown'

# Distribution of session_state
session_dist = collections.Counter()
for r in recent:
    session_dist[get_session(r)] += 1

# Identify flat / STRATEGY_FLAT rows
flat_rows = []
for r in recent:
    if r.get('reason_code') == 'STRATEGY_FLAT':
        flat_rows.append(r)
        continue
    details = r.get('details', {})
    if isinstance(details, dict):
        if details.get('direction') == 'flat' or any('STRATEGY_FLAT' in br for br in details.get('blocked_reasons', [])):
            flat_rows.append(r)
            continue
    # also check top-level direction
    if r.get('direction') == 'flat':
        flat_rows.append(r)

# Trades count: where order_send_called true in loop audit rows (they are in recent rows)
trades = 0
for r in recent:
    details = r.get('details', {})
    if isinstance(details, dict) and details.get('order_send_called'):
        trades += 1
    # also top-level field
    if r.get('order_send_called'):
        trades += 1

# STRATEGY_FLAT count by session
flat_by_session = collections.Counter()
for r in flat_rows:
    flat_by_session[get_session(r)] += 1

# Build report
def pct(cnt, total):
    return (cnt/total*100) if total else 0

lines = []
lines.append("# Session Governance Audit (last 1000 rows)\n\n")
lines.append(f"Total rows examined: {len(recent)}\n\n")
lines.append("## Session State Distribution\n")
for sess, cnt in session_dist.most_common():
    lines.append(f"- {sess}: {cnt} ({pct(cnt, len(recent)):.2f}%)\n")
lines.append("\n## Trades by Session State (order_send_called)\n")
# compute trade counts per session
trade_by_session = collections.Counter()
for r in recent:
    if (r.get('order_send_called') or (r.get('details',{}) or {}).get('order_send_called')):
        trade_by_session[get_session(r)] += 1
for sess, cnt in trade_by_session.most_common():
    lines.append(f"- {sess}: {cnt} ({pct(cnt, trades):.2f}% of trades)\n")
lines.append("\n## STRATEGY_FLAT occurrences by Session State\n")
for sess, cnt in flat_by_session.most_common():
    lines.append(f"- {sess}: {cnt} ({pct(cnt, len(flat_rows)):.2f}% of flat rows)\n")
lines.append("\n## Answers to Queries\n")
lines.append(f"1. Session state is calculated from the `session_flag` feature, derived in `mtf_builder` based on UTC hour.\n")
lines.append(f"2. Observed session values: {', '.join(session_dist.keys())}.\n")
lines.append(f"3. Allowed to trade sessions (configured in `detect_regime`): `london` and `new_york`.\n")
lines.append(f"4. Session state distribution counts are listed above.\n")
lines.append(f"5. Trades by session state counts are listed above.\n")
lines.append(f"6. STRATEGY_FLAT by session state counts are listed above.\n")
lines.append(f"7. Unknown session is treated as off‑session by `detect_regime` (falls into the `off_session` branch).\n")
lines.append(f"8. BTCUSD is intended to trade only during London and New York windows (24/5 not enabled).\n")

# Decision logic – simple heuristic
if flat_by_session.get('off_session',0) > trades*0.5:
    decision = 'B'  # too restrictive
else:
    decision = 'A'
lines.append(f"\n**Final decision:** {decision} (Session config {'correct' if decision=='A' else 'too restrictive'})\n")

REPORT_PATH.write_text(''.join(lines), encoding='utf-8')
print('Report written to', REPORT_PATH)
