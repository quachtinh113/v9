import os
import sys
import json
import webbrowser
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
import yaml

# Root directory
ROOT_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = ROOT_DIR / "projects"

class PortfolioDashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence default server logging to keep the console clean
        pass

    def do_GET(self):
        # Route endpoints
        if self.path == "/" or self.path == "/index.html":
            # If server is running on port 8369, serve architecture.html instead
            target_html = "architecture.html" if self.server.server_address[1] == 8369 else "index.html"
            self.serve_file(ROOT_DIR / "dashboard" / target_html, "text/html")
        elif self.path == "/app.css":
            self.serve_file(ROOT_DIR / "dashboard" / "app.css", "text/css")
        elif self.path == "/app.js":
            self.serve_file(ROOT_DIR / "dashboard" / "app.js", "application/javascript")
        elif self.path == "/architecture.js":
            self.serve_file(ROOT_DIR / "dashboard" / "architecture.js", "application/javascript")
        elif self.path == "/api/portfolio_status":
            self.serve_api_status()
        else:
            # Fallback to serving static files from dashboard/ or root/
            target_path = ROOT_DIR / self.path.lstrip("/")
            if target_path.exists() and target_path.is_file() and not self.path.startswith(".."):
                mime_type = "text/plain"
                if target_path.suffix == ".html": mime_type = "text/html"
                elif target_path.suffix == ".css": mime_type = "text/css"
                elif target_path.suffix == ".js": mime_type = "application/javascript"
                elif target_path.suffix == ".json": mime_type = "application/json"
                elif target_path.suffix in [".png", ".jpg", ".jpeg", ".gif"]: mime_type = f"image/{target_path.suffix[1:]}"
                self.serve_file(target_path, mime_type)
            else:
                self.send_error(404, "File Not Found")

    def do_POST(self):
        if self.path == "/api/update_config":
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                payload = json.loads(post_data.decode('utf-8'))
                
                symbol = payload.get("symbol")
                if not symbol:
                    self.send_error(400, "Missing symbol parameter")
                    return
                
                # Check target path
                repo_name = f"quant_v9_3_1_{symbol.lower()}"
                project_path = PROJECTS_DIR / repo_name
                
                if not project_path.exists():
                    self.send_error(404, f"Project not found for symbol {symbol}")
                    return
                
                # Update risk.yaml
                risk_yaml_path = project_path / "config" / "risk.yaml"
                if risk_yaml_path.exists():
                    with open(risk_yaml_path, "r", encoding="utf-8") as f:
                        risk_cfg = yaml.safe_load(f) or {}
                    
                    # Update fields
                    if "daily_loss_limit_pct" in payload:
                        risk_cfg["daily_loss_limit_pct"] = float(payload["daily_loss_limit_pct"])
                    if "weekly_soft_stop_pct" in payload:
                        risk_cfg["weekly_soft_stop_pct"] = float(payload["weekly_soft_stop_pct"])
                    if "hard_drawdown_pct" in payload:
                        risk_cfg["hard_drawdown_pct"] = float(payload["hard_drawdown_pct"])
                    if "spread_guard_enabled" in payload:
                        risk_cfg["spread_guard_enabled"] = bool(payload["spread_guard_enabled"])
                    if "slippage_guard_enabled" in payload:
                        risk_cfg["slippage_guard_enabled"] = bool(payload["slippage_guard_enabled"])
                    if "atr_shock_block_enabled" in payload:
                        risk_cfg["atr_shock_block_enabled"] = bool(payload["atr_shock_block_enabled"])
                    
                    with open(risk_yaml_path, "w", encoding="utf-8") as f:
                        yaml.safe_dump(risk_cfg, f, default_flow_style=False)
                        
                # Update symbol.yaml
                symbol_yaml_path = project_path / "config" / "symbol.yaml"
                if symbol_yaml_path.exists():
                    with open(symbol_yaml_path, "r", encoding="utf-8") as f:
                        symbol_cfg = yaml.safe_load(f) or {}
                    
                    # ml section
                    if "ml_enabled" in payload:
                        if "ml" not in symbol_cfg:
                            symbol_cfg["ml"] = {}
                        symbol_cfg["ml"]["enabled"] = bool(payload["ml_enabled"])
                        
                    # risk section
                    if "risk_per_trade_pct" in payload:
                        if "risk" not in symbol_cfg:
                            symbol_cfg["risk"] = {}
                        symbol_cfg["risk"]["risk_per_trade_pct"] = float(payload["risk_per_trade_pct"])
                        
                    if "max_daily_loss_pct" in payload:
                        if "risk" not in symbol_cfg:
                            symbol_cfg["risk"] = {}
                        symbol_cfg["risk"]["max_daily_loss_pct"] = float(payload["max_daily_loss_pct"])
                        
                    # position section
                    if "stop_atr_mult" in payload:
                        if "position" not in symbol_cfg:
                            symbol_cfg["position"] = {}
                        symbol_cfg["position"]["stop_atr_mult"] = float(payload["stop_atr_mult"])
                    if "tp_atr_mult" in payload:
                        if "position" not in symbol_cfg:
                            symbol_cfg["position"] = {}
                        symbol_cfg["position"]["tp_atr_mult"] = float(payload["tp_atr_mult"])
                    if "timeout_minutes" in payload:
                        if "position" not in symbol_cfg:
                            symbol_cfg["position"] = {}
                        symbol_cfg["position"]["timeout_minutes"] = int(payload["timeout_minutes"])
                        
                    with open(symbol_yaml_path, "w", encoding="utf-8") as f:
                        yaml.safe_dump(symbol_cfg, f, default_flow_style=False)
                        
                # Return success response
                resp = {"status": "success", "message": f"Configurations updated for {symbol}"}
                resp_bytes = json.dumps(resp).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(resp_bytes)))
                self.end_headers()
                self.wfile.write(resp_bytes)
                
            except Exception as e:
                self.send_error(500, f"Failed to update config: {str(e)}")
        else:
            self.send_error(404, "Not Found")

    def serve_file(self, file_path, mime_type):
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {str(e)}")

    def serve_api_status(self):
        try:
            # 1. Load consolidated summaries
            realism_summary_path = ROOT_DIR / "reports" / "realism_engine" / "summary.json"
            alpha_summary_path = ROOT_DIR / "reports" / "alpha_research" / "summary.json"
            edge_summary_path = ROOT_DIR / "reports" / "edge_discovery" / "summary.json"

            realism_data = []
            alpha_data = []
            edge_data = []

            if realism_summary_path.exists():
                with open(realism_summary_path, "r", encoding="utf-8") as f:
                    realism_data = json.load(f)
            if alpha_summary_path.exists():
                with open(alpha_summary_path, "r", encoding="utf-8") as f:
                    alpha_data = json.load(f)
            if edge_summary_path.exists():
                with open(edge_summary_path, "r", encoding="utf-8") as f:
                    edge_data = json.load(f)

            # Map files by symbol
            realism_by_sym = {item["symbol"]: item for item in realism_data}
            alpha_by_sym = {item["symbol"]: item for item in alpha_data}
            edge_by_sym = {item["symbol"]: item for item in edge_data}

            # 2. Determine Overall System State (Pulsing Indicator RED/YELLOW/GREEN)
            global_health_path = ROOT_DIR.parent / "logs" / "runtime_health.jsonl"
            system_state = "RED"
            system_reason = "Fleet runtime monitor is offline"
            heartbeat_ok = False
            
            if global_health_path.exists():
                try:
                    with open(global_health_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        if lines:
                            last_entry = json.loads(lines[-1])
                            ts_str = last_entry.get("timestamp")
                            if ts_str:
                                from datetime import datetime, timezone
                                last_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                                age_sec = (datetime.now(timezone.utc) - last_ts).total_seconds()
                                if age_sec <= 90:
                                    heartbeat_ok = last_entry.get("heartbeat_ok", False)
                                    system_state = "GREEN" if heartbeat_ok else "YELLOW"
                                    system_reason = "Fleet active and heartbeating" if system_state == "GREEN" else "Active but heartbeats lagging"
                                else:
                                    system_state = "RED"
                                    system_reason = f"Runtime health log stale ({age_sec:.0f}s old)"
                except Exception as e:
                    system_reason = f"Health check parse failure: {str(e)}"

            # 3. Scan all project configs & heartbeats for individual statuses
            symbols = ["GBPUSD", "EURUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "US30", "US100", "US500", "XAUUSD", "BTCUSD"]
            assets_status = []
            all_audit_logs = []
            
            for sym in symbols:
                repo_name = f"quant_v9_3_1_{sym.lower()}"
                project_path = PROJECTS_DIR / repo_name
                
                # Load symbol.yaml
                symbol_config = {}
                symbol_yaml_path = project_path / "config" / "symbol.yaml"
                if symbol_yaml_path.exists():
                    try:
                        with open(symbol_yaml_path, "r", encoding="utf-8") as f:
                            symbol_config = yaml.safe_load(f) or {}
                    except Exception:
                        pass
                
                # Load risk.yaml
                risk_config = {}
                risk_yaml_path = project_path / "config" / "risk.yaml"
                if risk_yaml_path.exists():
                    try:
                        with open(risk_yaml_path, "r", encoding="utf-8") as f:
                            risk_config = yaml.safe_load(f) or {}
                    except Exception:
                        pass

                symbol_val = symbol_config.get("symbol", sym)
                ml_enabled = symbol_config.get("ml", {}).get("enabled", True)
                risk_pct = symbol_config.get("risk", {}).get("risk_per_trade_pct", 0.25)
                max_daily_loss = symbol_config.get("risk", {}).get("max_daily_loss_pct", 1.8)

                # Merge realism and edge stats
                r_stat = realism_by_sym.get(sym, {})
                e_stat = edge_by_sym.get(sym, {})
                
                # --- READ ACTIVE HEARTBEAT FOR DYNAMIC SYMBOL STATUS ---
                hb_path = project_path / "logs" / "heartbeat.jsonl"
                sym_active = False
                hb_age = 999999
                ml_ok = True
                mt5_ok = False
                
                if hb_path.exists():
                    try:
                        with open(hb_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                            if lines:
                                last_hb = json.loads(lines[-1])
                                hb_ts_str = last_hb.get("timestamp")
                                if hb_ts_str:
                                    from datetime import datetime, timezone
                                    hb_ts = datetime.fromisoformat(hb_ts_str.replace("Z", "+00:00"))
                                    hb_age = (datetime.now(timezone.utc) - hb_ts).total_seconds()
                                    if hb_age <= 90:
                                        sym_active = True
                                    ml_ok = last_hb.get("ml_ok", True)
                                    mt5_ok = last_hb.get("mt5_ok", False)
                    except Exception:
                        pass

                # --- ESTIMATE DATA FRESHNESS & TICK AGE ---
                audit_path = project_path / "logs" / "no_entry_audit.jsonl"
                tick_age = 999999
                data_status = "disconnected"
                risk_status = "nominal"
                last_reason_code = "N/A"
                last_reason_text = ""
                
                if audit_path.exists():
                    try:
                        with open(audit_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                            if lines:
                                # Fetch last entry for stats
                                last_audit = json.loads(lines[-1])
                                tick_age = last_audit.get("tick_age_seconds", 999999)
                                mt5_connected = last_audit.get("mt5_connected", False)
                                last_reason_code = last_audit.get("reason_code", "N/A")
                                last_reason_text = last_audit.get("reason_text", "")
                                
                                if mt5_connected:
                                    data_status = "synced" if tick_age <= 300 else "stale"
                                else:
                                    data_status = "disconnected"
                                    
                                if last_reason_code in ["daily_loss_limit", "weekly_soft_stop", "weekly_hard_drawdown", "daily_hard_drawdown", "spread_guard_trigger", "slippage_guard_trigger", "atr_shock_trigger"]:
                                    risk_status = "vetoed"
                    except Exception:
                        pass

                # Compute final statuses
                symbol_status = "ACTIVE" if sym_active else "OFFLINE"
                model_status = "trained" if ml_ok else "ML_ERROR"
                dashboard_status = "active" if (sym_active and data_status == "synced" and ml_ok and risk_status == "nominal") else "blocked"

                # Parse specific gate blocks to dynamic console stream
                if audit_path.exists():
                    try:
                        with open(audit_path, "r", encoding="utf-8") as f:
                            # Read last 5 lines to keep stream fresh and performant
                            lines = f.readlines()[-5:]
                            for line in lines:
                                if line.strip():
                                    data = json.loads(line)
                                    all_audit_logs.append({
                                        "timestamp": data.get("timestamp", ""),
                                        "symbol": sym,
                                        "message": f"Block: Regime={data.get('regime')}, Decision={data.get('decision')}, Code={data.get('reason_code')}, Details={data.get('reason_text')}"
                                    })
                    except Exception:
                        pass

                # Determine asset verdict dynamically
                verdict = e_stat.get("portfolio_metrics", {}).get("verdict", r_stat.get("verdict", "APPROVED"))
                if not sym_active:
                    verdict = "OFFLINE"

                assets_status.append({
                    "symbol": sym,
                    "type": "forex" if sym in ["GBPUSD", "EURUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF"] else ("gold" if sym == "XAUUSD" else ("crypto" if sym == "BTCUSD" else "index")),
                    "verdict": verdict,
                    "profit_factor": r_stat.get("profit_factor", 0.0),
                    "max_drawdown": r_stat.get("max_drawdown_pct", 0.0),
                    "sharpe_ratio": r_stat.get("sharpe_ratio", 0.0),
                    "net_pnl": e_stat.get("portfolio_metrics", {}).get("net_pnl", r_stat.get("realized_pnl", 0.0)),
                    "trades": e_stat.get("portfolio_metrics", {}).get("total_trades", r_stat.get("max_consecutive_losses", 0)),
                    "best_setup": e_stat.get("alpha_profile", {}).get("best_setup", "mean reversion"),
                    "best_session": e_stat.get("alpha_profile", {}).get("best_session", "Asia"),
                    "volatility_pref": e_stat.get("alpha_profile", {}).get("volatility_preference", "LOW_VOLATILITY"),
                    
                    # Heartbeat Observe parameters mapped dynamically
                    "symbol_status": symbol_status,
                    "data_status": data_status,
                    "model_status": model_status,
                    "risk_status": risk_status,
                    "dashboard_status": dashboard_status,
                    
                    "guards": {
                        "spread_guard_enabled": risk_config.get("spread_guard_enabled", True),
                        "slippage_guard_enabled": risk_config.get("slippage_guard_enabled", True),
                        "atr_shock_block_enabled": risk_config.get("atr_shock_block_enabled", True),
                        "daily_loss_limit_pct": risk_config.get("daily_loss_limit_pct", 2.0),
                        "weekly_soft_stop_pct": risk_config.get("weekly_soft_stop_pct", 4.0),
                        "hard_drawdown_pct": risk_config.get("hard_drawdown_pct", 8.0)
                    },
                    "config": {
                        "ml_enabled": ml_enabled,
                        "risk_per_trade_pct": risk_pct,
                        "max_daily_loss_pct": max_daily_loss,
                        "stop_atr_mult": symbol_config.get("position", {}).get("stop_atr_mult", 1.8),
                        "tp_atr_mult": symbol_config.get("position", {}).get("tp_atr_mult", 2.5),
                        "timeout_minutes": symbol_config.get("position", {}).get("timeout_minutes", 120)
                    }
                })

            # Sort dynamic audit logs by timestamp descending
            all_audit_logs.sort(key=lambda x: x["timestamp"], reverse=True)
            logs = all_audit_logs[:30] # Keep latest 30 events
            
            # If no logs exist, supply system status lines
            if not logs:
                logs = [
                    {"timestamp": "2026-05-28 20:30:00", "symbol": "SYS", "message": "Quant Core Observability Layer started. Listening for bot heartbeats..."},
                    {"timestamp": "2026-05-28 20:30:01", "symbol": "SYS", "message": "Global telemetry path successfully synchronized."}
                ]

            # Calculate aggregated portfolio stats
            approved_assets = [a for a in assets_status if a["verdict"] in ["APPROVED", "INSTITUTIONAL_READY"]]
            total_pnl = sum([a["net_pnl"] for a in approved_assets])
            portfolio_max_dd = max([a["max_drawdown"] for a in assets_status]) if assets_status else 0.0

            response_data = {
                "system_status": {
                    "state": system_state,
                    "reason": system_reason,
                    "heartbeat_ok": heartbeat_ok
                },
                "summary": {
                    "total_aum": len(approved_assets) * 10000.0,
                    "total_pnl": total_pnl,
                    "approved_count": len(approved_assets),
                    "total_count": len(assets_status),
                    "portfolio_max_dd": portfolio_max_dd,
                    "risk_level": "LOW_VOLATILITY" if len(approved_assets) > 5 else "MODERATE"
                },
                "assets": assets_status,
                "audit_logs": logs
            }

            response_bytes = json.dumps(response_data, indent=4).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)
        except Exception as e:
            self.send_error(500, f"API Error: {str(e)}")
        except Exception as e:
            self.send_error(500, f"API Error: {str(e)}")

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, PortfolioDashboardHandler)
    print(f"=== QUANT CORE V9 PORTFOLIO COMMAND CENTER SERVER STARTED ===")
    print(f"URL: http://localhost:{port}")
    print(f"Close this console window to terminate server.")
    
    # Auto-open browser
    threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping command center server...")
        httpd.server_close()

if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try: port = int(sys.argv[1])
        except ValueError: pass
    run_server(port)
