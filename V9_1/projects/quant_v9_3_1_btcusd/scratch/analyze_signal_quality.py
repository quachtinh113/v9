import json
import os
from collections import Counter, defaultdict
import math

LOG_PATH = r"c:/Quant Trade/v9/V9_1/projects/quant_v9_3_1_btcusd/logs/live_pipeline_audit.ndjson"

def is_nan(val):
    return isinstance(val, float) and math.isnan(val)

def load_last_n_lines(path, n):
    # Efficiently read last n lines
    with open(path, 'rb') as f:
        f.seek(0, os.SEEK_END)
        end = f.tell()
        block_size = 1024
        lines = []
        while len(lines) < n and end > 0:
            delta = min(block_size, end)
            f.seek(end - delta)
            block = f.read(delta)
            lines_in_block = block.split(b'\n')
            # prepend to lines, ignoring possible incomplete first line
            if lines:
                # the first element of block may be continuation of previous line
                lines_in_block[-1] += lines[0]
                lines = lines_in_block[:-1] + lines[1:]
            else:
                lines = lines_in_block
            end -= delta
        # Decode and filter empty
        decoded = [l.decode('utf-8') for l in lines if l]
        return decoded[-n:]

def parse_entries(lines):
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries

def main():
    lines = load_last_n_lines(LOG_PATH, 5000)
    entries = parse_entries(lines)
    # Counters
    regime_counter = Counter()
    signal_counter = Counter()
    session_counter = Counter()
    ml_mode_counter = Counter()
    ml_score_vals = []
    risk_decision_counter = Counter()
    execution_mode_counter = Counter()
    order_sent_counter = Counter()
    blocked_reason_counter = Counter()
    feature_missing = defaultdict(int)
    feature_zero = defaultdict(int)
    feature_nan = defaultdict(int)

    for e in entries:
        stage = e.get('stage')
        if stage == 'LOOP_AUDIT':
            regime_counter[e.get('regime_result')] += 1
            signal_counter[e.get('signal_result')] += 1
            # session distribution not explicit; infer from flag? use risk_decision N/A vs ALLOW etc.
            # Assume session based on presence of 'session' field else unknown
            session = e.get('session', 'unknown')
            session_counter[session] += 1
            ml_mode_counter[e.get('ml_mode')] += 1
            ml_score = e.get('ml_score')
            if isinstance(ml_score, (int, float)):
                ml_score_vals.append(ml_score)
            risk_decision_counter[e.get('risk_decision')] += 1
            execution_mode_counter[e.get('execution_mode')] += 1
            order_sent_counter[str(e.get('order_send_called'))] += 1
            # blocked reasons from details
            details = e.get('details', {})
            blocked = details.get('blocked_reasons', [])
            for br in blocked:
                blocked_reason_counter[br] += 1
            # feature quality from indicators if present
            indicators = details.get('indicators', {})
            for feat in ['rsi14_m15', 'adx14_h1', 'atr14_m1', 'spread', 'regime']:
                val = indicators.get(feat)
                if val is None:
                    feature_missing[feat] += 1
                else:
                    if isinstance(val, (int, float)):
                        if val == 0:
                            feature_zero[feat] += 1
                        if is_nan(val):
                            feature_nan[feat] += 1
        elif stage == 'SIGNAL':
            # reason_code categorization
            reason = e.get('reason_code')
            # treat as blocked reason for analysis
            blocked_reason_counter[reason] += 1
        # else ignore
    # Summary stats
    total = len(entries)
    ml_min = min(ml_score_vals) if ml_score_vals else None
    ml_max = max(ml_score_vals) if ml_score_vals else None
    ml_mean = sum(ml_score_vals)/len(ml_score_vals) if ml_score_vals else None
    ml_median = sorted(ml_score_vals)[len(ml_score_vals)//2] if ml_score_vals else None
    # Output report
    report_lines = []
    report_lines.append("# Signal Quality Root Cause Audit (last 5000 rows)")
    report_lines.append(f"Total rows analyzed: {total}\n")
    report_lines.append("## Regime Distribution")
    for k, v in regime_counter.most_common():
        report_lines.append(f"- {k}: {v} ({v/total:.2%})")
    report_lines.append("\n## Signal Distribution")
    for k, v in signal_counter.most_common():
        report_lines.append(f"- {k}: {v} ({v/total:.2%})")
    report_lines.append("\n## Session Distribution (raw field)")
    for k, v in session_counter.most_common():
        report_lines.append(f"- {k}: {v} ({v/total:.2%})")
    report_lines.append("\n## ML Mode Distribution")
    for k, v in ml_mode_counter.items():
        report_lines.append(f"- {k}: {v}")
    report_lines.append("\n## ML Score Statistics")
    report_lines.append(f"- min: {ml_min:.4f}" if ml_min is not None else "- min: N/A")
    report_lines.append(f"- max: {ml_max:.4f}" if ml_max is not None else "- max: N/A")
    report_lines.append(f"- mean: {ml_mean:.4f}" if ml_mean is not None else "- mean: N/A")
    report_lines.append(f"- median: {ml_median:.4f}" if ml_median is not None else "- median: N/A")
    report_lines.append("\n## Risk Decisions")
    for k, v in risk_decision_counter.items():
        report_lines.append(f"- {k}: {v}")
    report_lines.append("\n## Execution Modes")
    for k, v in execution_mode_counter.items():
        report_lines.append(f"- {k}: {v}")
    report_lines.append("\n## Order Send Called")
    for k, v in order_sent_counter.items():
        report_lines.append(f"- {k}: {v}")
    report_lines.append("\n## Top Blocked Reasons")
    for k, v in blocked_reason_counter.most_common(10):
        pct = v/total
        report_lines.append(f"- {k}: {v} ({pct:.2%})")
    report_lines.append("\n## Feature Quality Issues")
    for feat in ['rsi14_m15', 'adx14_h1', 'atr14_m1', 'spread', 'regime']:
        missing = feature_missing[feat]
        zero = feature_zero[feat]
        nan = feature_nan[feat]
        report_lines.append(f"- {feat}: missing={missing}, zero={zero}, nan={nan}")
    # Determine root cause heuristic
    # Simple rule: if many blocked reasons are 'trend_biases_mismatch' -> Signal Engine too strict
    # if many 'ML_GATEKEEPER_BLOCK' -> ML gatekeeper block
    # else if regime mostly 'off_session' -> Session filter strict
    # else if risk decisions have many VETO -> Risk Engine veto
    # Count specific keywords
    trend_mismatch = sum(v for k, v in blocked_reason_counter.items() if 'trend_biases_mismatch' in k.lower())
    ml_block = sum(v for k, v in blocked_reason_counter.items() if 'ml_gatekeeper_block' in k.lower() or 'ml_score' in k.lower())
    # Determine dominant
    root_cause = []
    if trend_mismatch/total > 0.2:
        root_cause.append('A')
    if ml_block/total > 0.2:
        root_cause.append('F')
    # regime off_session proportion
    off_session = regime_counter.get('off_session',0)/total
    if off_session > 0.3:
        root_cause.append('B')
    # risk veto proportion
    veto = risk_decision_counter.get('VETO',0)/total
    if veto > 0.1:
        root_cause.append('E')
    # feature missing/zero high proportion
    poor_feature = any((feature_missing[feat]+feature_zero[feat]+feature_nan[feat])/total > 0.3 for feat in ['rsi14_m15','adx14_h1','atr14_m1','spread'])
    if poor_feature:
        root_cause.append('D')
    # Default to market condition if none
    if not root_cause:
        root_cause.append('C')
    report_lines.append("\n## Inferred Root Cause Categories (A-F)\n" + ", ".join(root_cause))
    # Write to report file
    report_path = r"c:/Quant Trade/v9/V9_1/projects/quant_v9_3_1_btcusd/reports/signal_quality_root_cause_audit.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
    print(f"Report written to {report_path}")

if __name__ == "__main__":
    main()
