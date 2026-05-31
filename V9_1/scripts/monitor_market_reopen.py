#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import json
import urllib.request
from datetime import datetime, timezone

def monitor_reopen():
    print("[*] Starting Monday Market Reopen Monitor...")
    report_path = "reports/monday_reopen_monitoring_report.md"
    log_path = "reports/monday_reopen_monitoring.ndjson"
    
    os.makedirs("reports", exist_ok=True)
    
    # Initialize markdown report if not exists
    if not os.path.exists(report_path):
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Monday Market Reopen Live Monitoring Report\n\n")
            f.write("This report dynamically tracks the transition of Quant V9 fleet symbols as the Forex, Gold, and Index markets reopen.\n\n")
            f.write("| Symbol | Transition Time (UTC) | Original Stage | New Stage | ML Score | Risk Action | Bottleneck | Status |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
            
    # Track previous stage per symbol to detect transitions
    prev_stages = {}
    
    while True:
        try:
            url = "http://localhost:8000/api/portfolio_status"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                
            pipeline_status = data.get("pipeline_status", [])
            timestamp_utc = datetime.now(timezone.utc).isoformat()
            
            for p in pipeline_status:
                symbol = p.get("symbol")
                stage = p.get("stage")
                ml_score = p.get("ml_score", 0.0)
                risk_action = p.get("risk_action", "N/A")
                block_reason = p.get("block_reason", "N/A")
                
                # Check for stage transition
                if symbol in prev_stages:
                    old_stage = prev_stages[symbol]
                    if old_stage != stage:
                        # Log the transition event
                        log_entry = {
                            "timestamp": timestamp_utc,
                            "symbol": symbol,
                            "old_stage": old_stage,
                            "new_stage": stage,
                            "ml_score": ml_score,
                            "risk_action": risk_action,
                            "block_reason": block_reason
                        }
                        
                        with open(log_path, "a", encoding="utf-8") as lf:
                            lf.write(json.dumps(log_entry) + "\n")
                            
                        # Update human-readable markdown table
                        status_emoji = "🟢 OPEN" if stage in ["SIGNAL_ENGINE", "ML_GATEKEEPER", "RISK_GATEWAY", "ORDER_ROUTER", "ORDER_SENT"] else "🟡 STALE"
                        if stage == "DATA_OFFLINE":
                            status_emoji = "🔴 OFFLINE"
                            
                        row = f"| **{symbol}** | {timestamp_utc[:19].replace('T', ' ')} | `{old_stage}` | `{stage}` | {ml_score:.4f} | `{risk_action}` | {block_reason} | {status_emoji} |\n"
                        with open(report_path, "a", encoding="utf-8") as f:
                            f.write(row)
                            
                        print(f"[TRANSITION] {symbol}: {old_stage} ➔ {stage} (Score={ml_score}, Reason={block_reason})")
                
                # Record current stage
                prev_stages[symbol] = stage
                
        except Exception as e:
            print(f"[WARNING] Monitoring poll failed: {e}")
            
        time.sleep(60)

if __name__ == "__main__":
    monitor_reopen()
