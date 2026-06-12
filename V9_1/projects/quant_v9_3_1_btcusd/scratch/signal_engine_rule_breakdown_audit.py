#!/usr/bin/env python3
import json, pathlib, collections, math

AUDIT_PATH = pathlib.Path(r"c:/Quant Trade/v9/V9_1/projects/quant_v9_3_1_btcusd/logs/live_pipeline_audit.ndjson")
REPORT_PATH = pathlib.Path(r"c:/Quant Trade/v9/V9_1/projects/quant_v9_3_1_btcusd/reports/signal_engine_rule_breakdown_audit.md")

# Load rows
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

# Helper to extract session state and signal result
def get_session(r):
    # Prefer explicit field added by pipeline_live
    if "session_state" in r:
        return r["session_state"]
    # fallback to details.indicators.session_flag or top-level
    details = r.get("details", {})
    if isinstance(details, dict):
        sess = details.get("session_flag")
        if sess:
            return sess
        inds = details.get("indicators", {})
        if isinstance(inds, dict):
            sess = inds.get("session_flag")
            if sess:
                return sess
    return r.get("session_flag", "unknown")

def get_signal_result(r):
    if "signal_result" in r:
        return r["signal_result"]
    details = r.get("details", {})
    if isinstance(details, dict):
        dr = details.get("direction") or details.get("signal_result")
        if dr:
            return dr
    return r.get("direction", "unknown")

# Filter rows: valid sessions and flat signal
valid_sessions = {"london", "new_york"}
flat_rows = []
for r in recent:
    sess = str(get_session(r)).lower()
    if sess not in valid_sessions:
        continue
    if str(get_signal_result(r)).lower() == "flat":
        flat_rows.append(r)

# Classification counters
category_counts = collections.Counter()
# For averages
rsi_vals = []
adx_vals = []
atr_vals = []
sig_scores = []
ml_scores = []

for r in flat_rows:
    details = r.get('details', {})
    blocked = details.get('blocked_reasons', []) if isinstance(details, dict) else []
    # gather numeric fields if present
    # indicators may hold the values
    inds = details.get('indicators', {}) if isinstance(details, dict) else {}
    val = inds.get('rsi14_m15')
    if isinstance(val, (int, float)):
        rsi_vals.append(float(val))
    val = inds.get('adx14_h1')
    if isinstance(val, (int, float)):
        adx_vals.append(float(val))
    val = inds.get('atr14_m1')
    if isinstance(val, (int, float)):
        atr_vals.append(float(val))
    # signal_score and ml_score are top‑level fields in row (written by pipeline)
    ss = r.get('signal_score')
    if isinstance(ss, (int, float)):
        sig_scores.append(float(ss))
    ms = r.get('ml_score')
    if isinstance(ms, (int, float)):
        ml_scores.append(float(ms))

    # Determine category
    assigned = False
    for br in blocked:
        br_low = br.lower()
        if any(k in br_low for k in ["rsi", "missing_rsi", "rsi_out_of", "rsi_not_in", "rsi_unsafe"]):
            category_counts['RSI condition fail'] += 1
            assigned = True
            break
        if any(k in br_low for k in ["adx", "missing_adx", "trend_adx_too_low", "sideway_adx_too_high"]):
            category_counts['ADX/trend strength fail'] += 1
            assigned = True
            break
        if any(k in br_low for k in ["atr", "missing_atr", "atr_ratio_exceeds_limit"]):
            category_counts['ATR/volatility fail'] += 1
            assigned = True
            break
        if any(k in br_low for k in ["off_session_regime_no_trade", "shock_regime_no_trade", "transition_regime_disabled", "no_trade_in_regime", "off_session"]):
            category_counts['Regime mismatch'] += 1
            assigned = True
            break
        if "score_below_threshold" in br_low:
            category_counts['Score below threshold'] += 1
            assigned = True
            break
        if any(k in br_low for k in ["bias", "biases_mismatch", "trend_biases_mismatch"]):
            category_counts['Long/short conflict'] += 1
            assigned = True
            break
        if "missing_signal_score" in br_low:
            category_counts['Missing signal_score'] += 1
            assigned = True
            break
    if not assigned:
        if not blocked:
            # no blocked reasons but still flat – could be insufficient confirmation
            category_counts['Insufficient confirmation'] += 1
        else:
            category_counts['Unknown'] += 1

# Helper for percentages
total_flat = len(flat_rows)

def pct(cnt):
    return (cnt/total_flat*100) if total_flat else 0

# Build report
lines = []
lines.append("# Signal Engine Rule Breakdown Audit (last 1000 rows)\n\n")
lines.append(f"Total rows examined (last 1000): {len(recent)}\n")
lines.append(f"Flat rows in valid sessions (london/new_york): {total_flat}\n\n")
lines.append("## Failure Rule Distribution\n")
for cat, cnt in category_counts.most_common():
    lines.append(f"- {cat}: {cnt} ({pct(cnt):.2f}%)\n")
lines.append("\n## Averages of Key Fields (non‑null)\n")
if rsi_vals:
    lines.append(f"- rsi14_m15: avg={sum(rsi_vals)/len(rsi_vals):.2f}, min={min(rsi_vals):.2f}, max={max(rsi_vals):.2f}\n")
if adx_vals:
    lines.append(f"- adx14_h1: avg={sum(adx_vals)/len(adx_vals):.2f}, min={min(adx_vals):.2f}, max={max(adx_vals):.2f}\n")
if atr_vals:
    lines.append(f"- atr14_m1: avg={sum(atr_vals)/len(atr_vals):.2f}, min={min(atr_vals):.2f}, max={max(atr_vals):.2f}\n")
if sig_scores:
    lines.append(f"- signal_score: avg={sum(sig_scores)/len(sig_scores):.2f}, min={min(sig_scores):.2f}, max={max(sig_scores):.2f}\n")
if ml_scores:
    lines.append(f"- ml_score: avg={sum(ml_scores)/len(ml_scores):.2f}, min={min(ml_scores):.2f}, max={max(ml_scores):.2f}\n")

# Decision heuristic
# If majority of flats are due to score below threshold -> C
# If majority are regime mismatch/off_session -> B
# If majority are RSI/ADX/ATR failures -> A
# else D
most_common_rule, most_cnt = category_counts.most_common(1)[0] if category_counts else (None, 0)
if most_common_rule == 'Score below threshold':
    decision = 'C'
elif most_common_rule in ('Regime mismatch', 'Off session'):
    decision = 'B'
elif most_common_rule in ('RSI condition fail', 'ADX/trend strength fail', 'ATR/volatility fail'):
    decision = 'A'
else:
    decision = 'D'
lines.append("\n**Final decision:** " + decision + "\n")

REPORT_PATH.write_text(''.join(lines), encoding='utf-8')
print('Report written to', REPORT_PATH)
