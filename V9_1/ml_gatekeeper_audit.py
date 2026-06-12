import json
import pathlib
import statistics

FILE = pathlib.Path(r"c:/Quant Trade/v9/V9_1/projects/quant_v9_3_1_btcusd/logs/live_pipeline_audit.ndjson")

lines = FILE.read_text().splitlines()
# take last 1000 lines
records = [json.loads(line) for line in lines[-1000:]]

# Collect ml_scores and signal results where present
ml_scores = []
signal_counts = {"BUY": 0, "SELL": 0, "FLAT": 0}
ml_pass_block = {"PASS": 0, "BLOCK": 0}

for rec in records:
    # signal result
    sig = rec.get('signal_result')
    if sig:
        signal_counts[sig.upper()] = signal_counts.get(sig.upper(), 0) + 1
    # ml_score exists
    ml = rec.get('ml_score')
    if ml is not None:
        ml_scores.append(ml)
        # Determine block based on reason_code if present
        reason = rec.get('reason_code', '')
        if reason == 'ML_GATEKEEPER_BLOCK':
            ml_pass_block['BLOCK'] += 1
        else:
            ml_pass_block['PASS'] += 1

# Stats on ml_scores
if ml_scores:
    ml_min = min(ml_scores)
    ml_max = max(ml_scores)
    ml_mean = sum(ml_scores) / len(ml_scores)
    ml_median = statistics.median(ml_scores)
    # Use quantiles to approximate percentiles
    ml_p75 = statistics.quantiles(ml_scores, n=100)[74]
    ml_p90 = statistics.quantiles(ml_scores, n=100)[89]
    ml_p95 = statistics.quantiles(ml_scores, n=100)[94]
else:
    ml_min = ml_max = ml_mean = ml_median = ml_p75 = ml_p90 = ml_p95 = 0

thresholds = [0.30, 0.35, 0.40, 0.45, 0.50]
threshold_stats = []
for th in thresholds:
    pass_cnt = sum(1 for s in ml_scores if s >= th)
    block_cnt = len(ml_scores) - pass_cnt
    rate = (pass_cnt / len(ml_scores) * 100) if ml_scores else 0
    threshold_stats.append((th, pass_cnt, block_cnt, rate))

# Print report
print("ML Gatekeeper Calibration Audit Report")
print("---")
print(f"Total records considered (with ml_score): {len(ml_scores)}")
print(f"Signal distribution: BUY={signal_counts.get('BUY',0)}, SELL={signal_counts.get('SELL',0)}, FLAT={signal_counts.get('FLAT',0)}")
print(f"ML Pass/Block count (based on reason_code): PASS={ml_pass_block['PASS']}, BLOCK={ml_pass_block['BLOCK']}")
print("ML Score Statistics:")
print(f"  min: {ml_min:.6f}")
print(f"  max: {ml_max:.6f}")
print(f"  mean: {ml_mean:.6f}")
print(f"  median: {ml_median:.6f}")
print(f"  75th percentile: {ml_p75:.6f}")
print(f"  90th percentile: {ml_p90:.6f}")
print(f"  95th percentile: {ml_p95:.6f}")
print("\nThreshold analysis:")
for th, pc, bc, rate in threshold_stats:
    print(f"  Threshold {th:.2f}: PASS={pc}, BLOCK={bc}, PASS_RATE={rate:.2f}%")

# Recommendation: choose highest threshold with pass rate >= 20%
eligible = [th for th, pc, bc, rate in threshold_stats if rate >= 20]
recommended = max(eligible) if eligible else min(thresholds)
print("\nRecommended paper threshold (PASS_RATE >=20%):", recommended)
