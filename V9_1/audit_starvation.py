import os
import json
import re
from pathlib import Path
import numpy as np

def parse_diagnostic_line(line):
    if "[DIAGNOSTIC]" not in line:
        return None
    try:
        parts = line.strip().split(" | ")
        parts[0] = parts[0].replace("[DIAGNOSTIC] ", "")
        data = {}
        for part in parts:
            if "=" in part:
                k, v = part.split("=", 1)
                data[k.strip()] = v.strip()
        return data
    except Exception:
        return None

def run_audit():
    print("=============================================================")
    print("  QUANT V9.1 PORTFOLIO SIGNAL STARVATION AUDIT")
    print("=============================================================\n")
    
    projects_dir = Path("c:/Quant Trade/v9/V9_1/projects")
    
    # Global aggregates
    global_rsi = []
    global_adx = []
    global_atr = []
    global_spread = []
    global_score = []
    global_regimes = {}
    global_actions = {}
    
    starvation_reasons = {}
    
    asset_metrics = {}
    
    for proj in sorted(projects_dir.iterdir()):
        if not proj.is_dir() or not proj.name.startswith("quant_v9_3_1_"):
            continue
            
        symbol = proj.name.split("_")[-1].upper()
        log_file = proj / "logs" / "console_out.log"
        no_entry_file = proj / "logs" / "no_entry_audit.jsonl"
        
        metrics = {
            "raw_signal_count": 0,
            "pass_signal_count": 0,
            "blocked_by_signal": 0,
            "blocked_by_regime": 0,
            "blocked_by_risk": 0,
            "blocked_by_data": 0,
            "off_session": 0,
            "final_trade_count": 0,
            "ticks_count": 0
        }
        
        # Parse spreads from no_entry_audit if present
        spreads = []
        if no_entry_file.exists():
            try:
                with open(no_entry_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        try:
                            row = json.loads(line.strip())
                            ind = row.get("indicator_values", {})
                            if "spread" in ind:
                                spreads.append(float(ind["spread"]))
                                global_spread.append(float(ind["spread"]))
                        except: pass
            except: pass
            
        # Parse console log
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        data = parse_diagnostic_line(line)
                        if not data:
                            continue
                            
                        metrics["ticks_count"] += 1
                        
                        # Extract indicator distributions
                        try:
                            rsi = float(data.get("rsi_m15", 0.0))
                            global_rsi.append(rsi)
                        except: pass
                        
                        try:
                            adx = float(data.get("adx", 0.0))
                            global_adx.append(adx)
                        except: pass
                        
                        try:
                            atr = float(data.get("atr", 0.0))
                            global_atr.append(atr)
                        except: pass
                        
                        try:
                            score = float(data.get("signal_score", 0.0))
                            global_score.append(score)
                        except: pass
                        
                        regime = data.get("regime", "unknown")
                        global_regimes[regime] = global_regimes.get(regime, 0) + 1
                        
                        final_act = data.get("final_action", "N/A")
                        global_actions[final_act] = global_actions.get(final_act, 0) + 1
                        
                        # Starvation metrics
                        raw_sig = data.get("raw_signal", "flat").lower()
                        ml_dec = data.get("ml_decision", "PASS").upper()
                        risk_dec = data.get("risk_decision", "N/A").upper()
                        
                        # 1. Raw signals
                        if raw_sig in ("long", "short"):
                            metrics["raw_signal_count"] += 1
                            if ml_dec in ("PASS", "REDUCE"):
                                metrics["pass_signal_count"] += 1
                        
                        # 2. Block categorizations
                        if final_act == "BLOCKED_BY_SIGNAL":
                            metrics["blocked_by_signal"] += 1
                        elif final_act == "BLOCKED_BY_RISK":
                            metrics["blocked_by_risk"] += 1
                        
                        block_reasons = data.get("block_reason", "[]")
                        if "stale_data" in block_reasons or "stale_data_veto" in block_reasons:
                            metrics["blocked_by_data"] += 1
                            
                        if regime in ("off_session", "invalid_session") or "off_session" in block_reasons:
                            metrics["off_session"] += 1
                            metrics["blocked_by_regime"] += 1
                            
                        if final_act == "ORDER_SENT" or final_act == "EXECUTION_READY":
                            metrics["final_trade_count"] += 1
                            
                        # Starvation reasons tracking
                        if block_reasons.startswith("[") and block_reasons.endswith("]"):
                            reasons = [r.strip().strip("'").strip('"') for r in block_reasons[1:-1].split(",") if r.strip()]
                            for r in reasons:
                                starvation_reasons[r] = starvation_reasons.get(r, 0) + 1
            except Exception as e:
                print(f"Error parsing log for {symbol}: {e}")
                
        asset_metrics[symbol] = metrics

    # Format distributions
    def print_dist_summary(name, values):
        if not values:
            print(f"  {name:<15}: N/A (no data)")
            return
        vals = np.array(values)
        print(f"  {name:<15}: Mean={vals.mean():.4f} | Min={vals.min():.4f} | Max={vals.max():.4f} | Median={np.median(vals):.4f}")

    print("-------------------------------------------------------------")
    print("  ASSET STARVATION METRICS MATRIX:")
    print("-------------------------------------------------------------")
    print(f"{'Asset':<8} | {'Raw':<5} | {'Pass':<5} | {'Blk_Sig':<7} | {'Blk_Reg':<7} | {'Blk_Rsk':<7} | {'Blk_Dat':<7} | {'Off_Ses':<7} | {'Trades':<6}")
    print("-" * 75)
    for sym, m in asset_metrics.items():
        print(f"{sym:<8} | {m['raw_signal_count']:<5} | {m['pass_signal_count']:<5} | {m['blocked_by_signal']:<7} | {m['blocked_by_regime']:<7} | {m['blocked_by_risk']:<7} | {m['blocked_by_data']:<7} | {m['off_session']:<7} | {m['final_trade_count']:<6}")

    print("\n-------------------------------------------------------------")
    print("  GLOBAL INDICATOR DISTRIBUTIONS:")
    print("-------------------------------------------------------------")
    print_dist_summary("RSI (M15)", global_rsi)
    print_dist_summary("ADX (H1)", global_adx)
    print_dist_summary("ATR (M1)", global_atr)
    print_dist_summary("Spread (BPS)", global_spread)
    print_dist_summary("Signal Score", global_score)
    
    print("\n  Regime Distribution:")
    for k, v in sorted(global_regimes.items(), key=lambda x: x[1], reverse=True):
        print(f"    - {k:<15}: {v} ticks ({v/sum(global_regimes.values())*100:.2f}%)")
        
    print("\n  Final Action Distribution:")
    for k, v in sorted(global_actions.items(), key=lambda x: x[1], reverse=True):
        print(f"    - {k:<25}: {v} ticks ({v/sum(global_actions.values())*100:.2f}%)")

    # Formulate top 3 root causes
    sorted_starve = sorted(starvation_reasons.items(), key=lambda x: x[1], reverse=True)
    print("\n-------------------------------------------------------------")
    print("  TOP SIGNAL STARVATION ROOT CAUSES:")
    print("-------------------------------------------------------------")
    
    rank = 1
    for r, count in sorted_starve[:5]:
        print(f"ROOT CAUSE #{rank}: {r} (blocked {count} evaluations)")
        rank += 1
        if rank > 3:
            break

if __name__ == "__main__":
    run_audit()
