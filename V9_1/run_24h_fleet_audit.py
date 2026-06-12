import sqlite3
import json
import os
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

def get_report(db_path, projects_dir):
    report = {
        "total_trades": 0,
        "trades_per_symbol": {},
        "net_pnl_per_symbol": {},
        "max_trades_per_symbol_per_hour": 0,
        "max_consecutive_losses_fleet": 0,
        "max_consecutive_losses_per_symbol": {},
        "number_of_risk_vetoes": 0,
        "veto_reasons_distribution": {},
        "database_error_count": 0,
        "duplicate_entry_count": 0,
        "conclusion": "SAFE_DEMO"
    }

    if db_path.exists():
        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT symbol, COUNT(*), SUM(pnl) FROM trades WHERE status='CLOSED' GROUP BY symbol")
                for row in cursor.fetchall():
                    symbol, count, pnl = row
                    report["total_trades"] += count
                    report["trades_per_symbol"][symbol] = count
                    report["net_pnl_per_symbol"][symbol] = round(pnl if pnl else 0, 2)

                cursor.execute("SELECT symbol, entry_time FROM trades WHERE entry_time IS NOT NULL ORDER BY entry_time")
                trades_time = cursor.fetchall()
                symbol_times = {}
                for sym, t_str in trades_time:
                    if not t_str: continue
                    import dateutil.parser
                    t = dateutil.parser.isoparse(t_str)
                    symbol_times.setdefault(sym, []).append(t)
                
                max_hourly = 0
                for sym, times in symbol_times.items():
                    for i in range(len(times)):
                        count = 0
                        for j in range(i, len(times)):
                            if (times[j] - times[i]).total_seconds() <= 3600:
                                count += 1
                            else:
                                break
                        max_hourly = max(max_hourly, count)
                report["max_trades_per_symbol_per_hour"] = max_hourly

                cursor.execute("SELECT symbol, pnl FROM trades WHERE status='CLOSED' ORDER BY exit_time")
                all_closed = cursor.fetchall()
                
                current_fleet_loss = 0
                symbol_loss_streaks = {}
                max_symbol_loss_streaks = {}
                
                for sym, pnl in all_closed:
                    pnl = pnl or 0
                    if pnl < 0:
                        current_fleet_loss += 1
                        symbol_loss_streaks[sym] = symbol_loss_streaks.get(sym, 0) + 1
                    else:
                        current_fleet_loss = 0
                        symbol_loss_streaks[sym] = 0
                        
                    report["max_consecutive_losses_fleet"] = max(report["max_consecutive_losses_fleet"], current_fleet_loss)
                    max_symbol_loss_streaks[sym] = max(max_symbol_loss_streaks.get(sym, 0), symbol_loss_streaks[sym])
                
                report["max_consecutive_losses_per_symbol"] = max_symbol_loss_streaks
                
                # duplicate entries check
                cursor.execute("SELECT symbol, direction, COUNT(*) FROM trades WHERE status='OPEN' GROUP BY symbol, direction HAVING COUNT(*) > 1")
                dupes = cursor.fetchall()
                for row in dupes:
                    report["duplicate_entry_count"] += (row[2] - 1)
                    
        except sqlite3.Error as e:
            report["database_error_count"] += 1

    for proj in os.listdir(projects_dir):
        audit_log_path = projects_dir / proj / "logs" / "live_pipeline_audit.ndjson"
        if audit_log_path.exists():
            with open(audit_log_path, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("stage") == "RISK" and entry.get("reason_code") == "HARD_KILL":
                            report["number_of_risk_vetoes"] += 1
                            details = entry.get("details", {})
                            reasons = details.get("reasons", [])
                            for r in reasons:
                                report["veto_reasons_distribution"][r] = report["veto_reasons_distribution"].get(r, 0) + 1
                    except:
                        pass

    # Stop Conditions Evaluator
    block_reasons = []
    if report["max_consecutive_losses_fleet"] >= 8:
        block_reasons.append("Fleet loss streak >= 8")
    if report["database_error_count"] > 0:
        block_reasons.append("Database locked errors > 0")
    if report["max_trades_per_symbol_per_hour"] > 3:
        block_reasons.append("Symbol trades > 3/hour")
    if report["duplicate_entry_count"] > 0:
        block_reasons.append("Duplicate same-direction entries detected")
        
    if block_reasons:
        report["conclusion"] = f"BLOCKED_DEMO ({', '.join(block_reasons)})"
    else:
        report["conclusion"] = "SAFE_DEMO"
        
    return report

def write_final_reports(report, root_dir):
    reports_dir = root_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = reports_dir / "24h_safe_demo_final_report.json"
    with open(json_path, 'w') as f:
        json.dump(report, f, indent=4)
        
    md_path = reports_dir / "24h_safe_demo_final_report.md"
    with open(md_path, 'w') as f:
        f.write("# 24H SAFE DEMO FINAL REPORT\n\n")
        f.write(f"- **Final Status:** {report['conclusion']}\n")
        f.write(f"- **Total Trades:** {report['total_trades']}\n")
        f.write(f"- **Max Trades/Symbol/Hour:** {report['max_trades_per_symbol_per_hour']}\n")
        f.write(f"- **Max Consecutive Losses Fleet:** {report['max_consecutive_losses_fleet']}\n")
        f.write(f"- **Database Error Count:** {report['database_error_count']}\n")
        f.write(f"- **Duplicate Entry Count:** {report['duplicate_entry_count']}\n")
        f.write(f"- **Risk Vetoes:** {report['number_of_risk_vetoes']}\n\n")
        f.write("## Trades per Symbol\n")
        for sym, count in report['trades_per_symbol'].items():
            f.write(f"- {sym}: {count}\n")
        f.write("\n## PnL per Symbol\n")
        for sym, pnl in report['net_pnl_per_symbol'].items():
            f.write(f"- {sym}: ${pnl}\n")
        f.write("\n## Veto Reasons Distribution\n")
        for r, c in report['veto_reasons_distribution'].items():
            f.write(f"- {r}: {c}\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-hours", type=float, required=True)
    parser.add_argument("--snapshot-minutes", type=float, required=True)
    args = parser.parse_args()

    root_dir = Path("c:/Quant Trade/v9/V9_1")
    db_path = root_dir / "logs" / "risk_state.db"
    projects_dir = root_dir / "projects"
    
    snapshots_dir = root_dir / "logs" / "24h_audit_snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    
    # Resume support
    state_file = snapshots_dir / "audit_state.json"
    start_time = datetime.now(timezone.utc)
    
    if state_file.exists():
        with open(state_file, 'r') as f:
            state = json.load(f)
            start_time = datetime.fromisoformat(state['start_time'])
            print(f"Resuming audit started at {start_time}")
    else:
        with open(state_file, 'w') as f:
            json.dump({"start_time": start_time.isoformat()}, f)
            print(f"Starting new audit at {start_time}")

    duration_seconds = args.duration_hours * 3600
    snapshot_seconds = args.snapshot_minutes * 60

    while True:
        now = datetime.now(timezone.utc)
        elapsed = (now - start_time).total_seconds()
        
        report = get_report(db_path, projects_dir)
        
        # Write snapshot
        snap_name = f"snapshot_{now.strftime('%Y%m%d_%H%M')}.json"
        with open(snapshots_dir / snap_name, 'w') as f:
            json.dump(report, f, indent=4)
        print(f"[{now.isoformat()}] Wrote snapshot {snap_name}. Elapsed: {elapsed/3600:.2f}/{args.duration_hours:.2f} hours. Status: {report['conclusion']}")

        if elapsed >= duration_seconds:
            print("Audit duration reached.")
            write_final_reports(report, root_dir)
            break
            
        if "BLOCKED_DEMO" in report["conclusion"]:
            print(f"Stop condition met: {report['conclusion']}")
            write_final_reports(report, root_dir)
            break
            
        time.sleep(min(snapshot_seconds, duration_seconds - elapsed))

if __name__ == "__main__":
    main()
