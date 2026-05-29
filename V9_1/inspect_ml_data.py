import os
import json
import glob
from pathlib import Path
import numpy as np

def analyze_backtest_audit(file_path):
    print(f"\nAnalyzing {file_path.name}...")
    
    raw_signals = 0
    ml_decisions = {"PASS": 0, "BLOCK": 0, "REDUCE": 0, "OFF": 0}
    scores = []
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line.strip())
                # Check if it contains signal evaluations
                # In backtest_audit, signal_direction is the strategy's raw direction
                direction = row.get("signal_direction", "flat")
                if direction in ("long", "short"):
                    raw_signals += 1
                    dec = row.get("ml_decision", "N/A")
                    ml_decisions[dec] = ml_decisions.get(dec, 0) + 1
                    
                    score = row.get("ml_score")
                    if score is not None and score != 1.0: # 1.0 is often the default/bypassed score
                        scores.append(float(score))
            except Exception as e:
                pass
                
    print(f"  Raw signals evaluated: {raw_signals}")
    print(f"  ML Decisions: {ml_decisions}")
    if scores:
        print(f"  ML Scores collected (excluding defaults): {len(scores)}")
        print(f"    Min Score   : {min(scores):.4f}")
        print(f"    Max Score   : {max(scores):.4f}")
        print(f"    Mean Score  : {np.mean(scores):.4f}")
        print(f"    Median Score: {np.median(scores):.4f}")
    else:
        print("  No non-default ML scores found.")

def analyze_demo_journals():
    projects_dir = Path("c:/Quant Trade/v9/V9_1/projects")
    print("\nScanning demo_journal.jsonl across all projects...")
    
    all_events = {}
    trade_outcomes = []
    scores = []
    decisions = {}
    raw_signal_count = 0
    
    for proj in projects_dir.iterdir():
        if proj.is_dir() and proj.name.startswith("quant_v9_3_1_"):
            demo_j = proj / "logs" / "demo_journal.jsonl"
            if demo_j.exists():
                with open(demo_j, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            ev_type = event.get("event_type")
                            all_events[ev_type] = all_events.get(ev_type, 0) + 1
                            
                            # Parse signal_generated events
                            if ev_type == "signal_generated":
                                payload = event.get("payload", {})
                                direction = payload.get("direction", "flat")
                                if direction in ("long", "short"):
                                    raw_signal_count += 1
                                    ml_dec = payload.get("ml_decision", "OFF")
                                    decisions[ml_dec] = decisions.get(ml_dec, 0) + 1
                                    
                                    ml_sc = payload.get("ml_score")
                                    if ml_sc is not None:
                                        scores.append(float(ml_sc))
                                        
                            # Parse trade_closed events
                            elif ev_type == "trade_closed":
                                payload = event.get("payload", {})
                                pnl = payload.get("pnl", 0.0)
                                ticket = payload.get("ticket")
                                symbol = payload.get("symbol")
                                direction = payload.get("direction")
                                
                                # Find corresponding signal to see what the ML score was
                                ml_sc = payload.get("ml_score", 1.0)
                                trade_outcomes.append({
                                    "symbol": symbol,
                                    "direction": direction,
                                    "pnl": float(pnl),
                                    "ml_score": float(ml_sc)
                                })
                        except Exception as e:
                            pass
                            
    print(f"Event types across journals: {all_events}")
    print(f"Total raw signals in journals: {raw_signal_count}")
    print(f"ML Decisions: {decisions}")
    if scores:
        print(f"ML Scores collected: {len(scores)}")
        print(f"  Min Score   : {min(scores):.4f}")
        print(f"  Max Score   : {max(scores):.4f}")
        print(f"  Mean Score  : {np.mean(scores):.4f}")
        print(f"  Median Score: {np.median(scores):.4f}")
        
    print(f"Trade outcomes collected: {len(trade_outcomes)}")
    if trade_outcomes:
        profitable = sum(1 for t in trade_outcomes if t["pnl"] > 0)
        unprofitable = sum(1 for t in trade_outcomes if t["pnl"] <= 0)
        win_rate = profitable / len(trade_outcomes) * 100
        total_pnl = sum(t["pnl"] for t in trade_outcomes)
        print(f"  Profitable trades: {profitable}")
        print(f"  Unprofitable trades: {unprofitable}")
        print(f"  Win Rate: {win_rate:.2f}%")
        print(f"  Total PnL: {total_pnl:.2f}")
        
        # Print trades with their ML scores
        print("\nDetail of closed trades:")
        for idx, t in enumerate(trade_outcomes):
            print(f"  Trade {idx+1}: Sym: {t['symbol']} | Dir: {t['direction']} | PnL: {t['pnl']:.2f} | ML Score: {t['ml_score']:.4f}")

if __name__ == "__main__":
    # Check GBPUSD backtest
    backtest_file = Path("c:/Quant Trade/v9/V9_1/projects/quant_v9_3_1_gbpusd/logs/backtest_audit.ndjson")
    if backtest_file.exists():
        analyze_backtest_audit(backtest_file)
    analyze_demo_journals()
