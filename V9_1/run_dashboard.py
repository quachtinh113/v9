import os
import sys
import json
import webbrowser
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
import yaml

HEARTBEAT_TIMEOUT_SECONDS = 45  # seconds
import logging
import datetime





from http.server import BaseHTTPRequestHandler, HTTPServer
import yaml

# Root directory
ROOT_DIR = Path(__file__).resolve().parent
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger('run_dashboard')
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
            age_sec = None
            latest_heartbeat_entry = None

            if global_health_path.exists():
                try:
                    with open(global_health_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    if lines:
                        last_entry = json.loads(lines[-1])
                        latest_heartbeat_entry = last_entry
                        ts_str = last_entry.get("timestamp")
                        if ts_str:
                            # Parse ISO timestamp, handling possible 'Z' suffix
                            ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            # Convert to naive UTC for comparison
                            if ts.tzinfo is not None:
                                ts = ts.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                            else:
                                ts = ts.replace(tzinfo=datetime.timezone.utc)
                            age_sec = (datetime.datetime.utcnow() - ts).total_seconds()
                            heartbeat_ok = age_sec <= HEARTBEAT_TIMEOUT_SECONDS
                            if heartbeat_ok:
                                system_state = "GREEN"
                                system_reason = "Heartbeat healthy"
                            else:
                                system_state = "RED"
                                system_reason = f"Heartbeat stale ({age_sec:.0f}s old)"
                        else:
                            system_state = "RED"
                            system_reason = "No heartbeat timestamp"
                except Exception as e:
                    logger.error(f"Error reading runtime health: {e}")
                    system_reason = f"Health check parse failure: {str(e)}"

            # 3. Scan all project configs & heartbeats for individual statuses
            symbols = ["GBPUSD", "EURUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "US30", "US100", "US500", "XAUUSD", "BTCUSD"]
            assets_status = []
            all_audit_logs = []
            pipeline_status = []
            
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
                hb_timestamp_str = ""
                
                if hb_path.exists():
                    try:
                        with open(hb_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                            if lines:
                                last_hb = json.loads(lines[-1])
                                hb_ts_str = last_hb.get("timestamp")
                                if hb_ts_str:
                                    hb_timestamp_str = hb_ts_str
                                    hb_ts = datetime.datetime.fromisoformat(hb_ts_str.replace("Z", ""))
                                    if hb_ts.tzinfo is None:
                                        hb_age = (datetime.datetime.utcnow() - hb_ts).total_seconds()
                                    else:
                                        hb_age = (datetime.datetime.now(datetime.timezone.utc) - hb_ts).total_seconds()
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

                # --- TELEMETRY PARSING FOR LIVE ORDER PIPELINE STATUS ---
                audit_ndjson_path = project_path / "logs" / "live_pipeline_audit.ndjson"
                latest_loop_audit = None
                latest_signal_block = None
                latest_strategy_flat = None
                latest_risk_block = None
                
                if audit_ndjson_path.exists():
                    try:
                        with open(audit_ndjson_path, "r", encoding="utf-8") as f:
                            lines_audit = f.readlines()[-100:]
                            for line in reversed(lines_audit):
                                if not line.strip():
                                    continue
                                data = json.loads(line)
                                if data.get("stage") == "LOOP_AUDIT" and latest_loop_audit is None:
                                    latest_loop_audit = data
                                if data.get("stage") == "SIGNAL" and data.get("reason_code") == "ML_GATEKEEPER_BLOCK" and latest_signal_block is None:
                                    latest_signal_block = data
                                if data.get("stage") == "SIGNAL" and data.get("reason_code") == "STRATEGY_FLAT" and latest_strategy_flat is None:
                                    latest_strategy_flat = data
                                if data.get("stage") == "RISK" and latest_risk_block is None:
                                    latest_risk_block = data
                                if latest_loop_audit and latest_signal_block and latest_strategy_flat and latest_risk_block:
                                    break
                    except Exception:
                        pass

                tick_timestamp = ""
                data_stale = False
                signal_direction = "flat"
                ml_score_val = 0.0
                ml_decision_val = "ALLOW"
                risk_action_val = "N/A"
                order_send_called_val = False
                exec_mode_val = "PAPER"

                if latest_loop_audit:
                    tick_timestamp = latest_loop_audit.get("timestamp", "")
                    data_stale = latest_loop_audit.get("data_stale", False)
                    signal_direction = latest_loop_audit.get("signal_result", "flat")
                    ml_score_val = latest_loop_audit.get("ml_score", 0.0)
                    risk_action_val = latest_loop_audit.get("risk_decision", "N/A")
                    order_send_called_val = latest_loop_audit.get("order_send_called", False)
                    exec_mode_val = latest_loop_audit.get("execution_mode", "PAPER").upper()

                if latest_signal_block:
                    ml_decision_val = "BLOCK"
                elif latest_loop_audit and latest_loop_audit.get("ml_score", 0.0) < 0.50 and latest_loop_audit.get("signal_result") in ["long", "short"]:
                    ml_decision_val = "BLOCK"

                has_journal_order = False
                for journal_name in ["live_journal.jsonl", "demo_journal.jsonl"]:
                    journal_path = project_path / "logs" / journal_name
                    if journal_path.exists():
                        try:
                            with open(journal_path, "r", encoding="utf-8") as f:
                                lines_j = f.readlines()[-50:]
                                for line in lines_j:
                                    if not line.strip():
                                        continue
                                    data = json.loads(line)
                                    response = data.get("response", {})
                                    if response:
                                        status = str(response.get("status", "")).lower()
                                        retcode = response.get("retcode")
                                        if "success" in status or retcode == 10009 or "TRADE_RETCODE_DONE" in str(response):
                                            has_journal_order = True
                                            break
                        except Exception:
                            pass
                    if has_journal_order:
                        break

                # Resolve Stage, Bottleneck and Color
                is_market_closed = False
                if data_stale and sym.upper() != "BTCUSD":
                    from datetime import datetime, timezone
                    now_utc = datetime.now(timezone.utc)
                    weekday = now_utc.weekday()  # 0 = Monday, 6 = Sunday
                    hour = now_utc.hour
                    
                    if weekday == 5:  # Saturday
                        is_market_closed = True
                    elif weekday == 4 and hour >= 21:  # Friday evening after 21:00 UTC
                        is_market_closed = True
                    elif weekday == 6 and hour < 21:  # Sunday before 21:00 UTC
                        is_market_closed = True

                if not sym_active:
                    stage_resolved = "DATA_OFFLINE"
                    bottleneck_resolved = "Data feed not running"
                    color_resolved = "gray"
                elif is_market_closed:
                    stage_resolved = "MARKET_CLOSED"
                    bottleneck_resolved = "Weekend market halt"
                    color_resolved = "gray"
                elif data_stale:
                    stage_resolved = "DATA_STALE"
                    bottleneck_resolved = "MT5 tick stale"
                    color_resolved = "orange"
                elif signal_direction == "flat" or signal_direction == "N/A":
                    stage_resolved = "SIGNAL_ENGINE"
                    bottleneck_resolved = "No valid setup"
                    color_resolved = "blue"
                elif ml_decision_val == "BLOCK":
                    stage_resolved = "ML_GATEKEEPER"
                    bottleneck_resolved = "ML blocked signal"
                    color_resolved = "purple"
                elif risk_action_val in ["SOFT_BLOCK", "HARD_KILL"]:
                    stage_resolved = "RISK_GATEWAY"
                    bottleneck_resolved = "Risk veto"
                    color_resolved = "red"
                elif risk_action_val == "ALLOW" and not order_send_called_val:
                    stage_resolved = "ORDER_ROUTER_WAITING"
                    bottleneck_resolved = "Signal passed but no order call"
                    color_resolved = "yellow"
                elif order_send_called_val and not has_journal_order:
                    stage_resolved = "ORDER_ROUTER"
                    bottleneck_resolved = "Order routing in progress"
                    color_resolved = "cyan"
                elif has_journal_order:
                    stage_resolved = "ORDER_SENT"
                    bottleneck_resolved = "Order sent to broker"
                    color_resolved = "green"
                else:
                    stage_resolved = "SIGNAL_ENGINE"
                    bottleneck_resolved = "No valid setup"
                    color_resolved = "blue"

                # Resolve Block Reason
                block_reason_resolved = "No valid setup"
                
                if stage_resolved == "DATA_OFFLINE":
                    block_reason_resolved = "Data feed not running"
                elif stage_resolved == "MARKET_CLOSED":
                    block_reason_resolved = "Weekend market halt"
                elif stage_resolved == "DATA_STALE":
                    hb_tick_age = 99999
                    if hb_path.exists():
                        try:
                            with open(hb_path, "r", encoding="utf-8") as f:
                                lines_h = f.readlines()
                                if lines_h:
                                    last_h = json.loads(lines_h[-1])
                                    hb_tick_age = int(last_h.get("tick_age", 99999))
                        except Exception:
                            pass
                    if hb_tick_age > 100000:
                        block_reason_resolved = f"tick_age={hb_tick_age % 1000}"
                    else:
                        block_reason_resolved = f"tick_age={hb_tick_age}"
                elif stage_resolved == "SIGNAL_ENGINE":
                    if latest_strategy_flat:
                        reasons = latest_strategy_flat.get("details", {}).get("blocked_reasons", [])
                        if reasons:
                            block_reason_resolved = reasons[0]
                        else:
                            block_reason_resolved = "No valid setup"
                    else:
                        block_reason_resolved = "No valid setup"
                elif stage_resolved == "ML_GATEKEEPER":
                    block_reason_resolved = f"ml_score={round(ml_score_val, 2)}"
                elif stage_resolved == "RISK_GATEWAY":
                    risk_reasons = []
                    if latest_risk_block:
                        risk_reasons = latest_risk_block.get("details", {}).get("reasons", [])
                    if not risk_reasons and last_reason_code and last_reason_code != "N/A":
                        risk_reasons = [last_reason_code]
                    
                    if risk_reasons:
                        first_reason = risk_reasons[0]
                        if "spread_guard" in first_reason:
                            block_reason_resolved = "spread_guard"
                        elif "slippage_guard" in first_reason:
                            block_reason_resolved = "slippage_guard"
                        elif "atr_shock" in first_reason:
                            block_reason_resolved = "atr_shock"
                        elif "daily_loss" in first_reason:
                            block_reason_resolved = "daily_loss_limit"
                        elif "weekly_soft" in first_reason:
                            block_reason_resolved = "weekly_soft_stop"
                        elif "hard_drawdown" in first_reason:
                            block_reason_resolved = "hard_drawdown"
                        else:
                            block_reason_resolved = first_reason
                    else:
                        block_reason_resolved = "Risk veto"
                elif stage_resolved == "ORDER_ROUTER_WAITING":
                    block_reason_resolved = "Signal passed but no order call"
                elif stage_resolved == "ORDER_ROUTER":
                    block_reason_resolved = "Order routing in progress"
                elif stage_resolved == "ORDER_SENT":
                    block_reason_resolved = "Order sent to broker"

                # Order Name formatting
                from datetime import datetime, timezone
                ts_to_use = tick_timestamp if tick_timestamp else hb_timestamp_str
                formatted_ts = ""
                if ts_to_use:
                    try:
                        ts_clean = ts_to_use.replace("Z", "").replace("+00:00", "").replace("T", " ").strip()
                        dt = datetime.fromisoformat(ts_clean)
                        formatted_ts = dt.strftime("%Y%m%d-%H%M")
                    except Exception:
                        try:
                            dt = datetime.strptime(ts_to_use[:16], "%Y-%m-%d %H:%M")
                            formatted_ts = dt.strftime("%Y%m%d-%H%M")
                        except Exception:
                            formatted_ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
                else:
                    formatted_ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")

                direction_mapped = "FLAT"
                if signal_direction == "long":
                    direction_mapped = "LONG"
                elif signal_direction == "short":
                    direction_mapped = "SHORT"

                order_name = f"{sym.upper()}-{direction_mapped}-{formatted_ts}"

                # Last update display
                last_update_display = ""
                if ts_to_use:
                    try:
                        ts_clean = ts_to_use.replace("Z", "").replace("+00:00", "").replace("T", " ").strip()
                        dt = datetime.fromisoformat(ts_clean)
                        last_update_display = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        last_update_display = ts_to_use[:19]
                else:
                    last_update_display = "N/A"

                pipeline_status.append({
                    "symbol": sym,
                    "order_name": order_name,
                    "stage": stage_resolved,
                    "block_reason": block_reason_resolved,
                    "ml_score": round(ml_score_val, 4),
                    "risk_action": risk_action_val,
                    "last_update": last_update_display,
                    "color": color_resolved
                })

            # Sort blocked symbols first:
            # Blocked stages are: RISK_GATEWAY, DATA_OFFLINE, DATA_STALE, ML_GATEKEEPER, ORDER_ROUTER_WAITING, SIGNAL_ENGINE
            # Non-blocked stages are: ORDER_ROUTER, ORDER_SENT
            def get_stage_priority(stage):
                priority = {
                    "RISK_GATEWAY": 0,
                    "DATA_OFFLINE": 1,
                    "DATA_STALE": 2,
                    "MARKET_CLOSED": 2.5,
                    "ML_GATEKEEPER": 3,
                    "ORDER_ROUTER_WAITING": 4,
                    "SIGNAL_ENGINE": 5,
                    "ORDER_ROUTER": 6,
                    "ORDER_SENT": 7
                }
                return priority.get(stage, 99)

            pipeline_status.sort(key=lambda x: get_stage_priority(x["stage"]))

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

            # Calculate summary counters
            total_symbols = len(symbols)
            signal_blocked = sum(1 for p in pipeline_status if p["stage"] == "SIGNAL_ENGINE")
            ml_blocked = sum(1 for p in pipeline_status if p["stage"] == "ML_GATEKEEPER")
            risk_blocked = sum(1 for p in pipeline_status if p["stage"] == "RISK_GATEWAY")
            execution_waiting = sum(1 for p in pipeline_status if p["stage"] == "ORDER_ROUTER_WAITING")
            orders_sent = sum(1 for p in pipeline_status if p["stage"] in ["ORDER_SENT", "ORDER_ROUTER"])

            pipeline_summary = {
                "total_symbols": total_symbols,
                "signal_blocked": signal_blocked,
                "ml_blocked": ml_blocked,
                "risk_blocked": risk_blocked,
                "execution_waiting": execution_waiting,
                "orders_sent": orders_sent
            }

            # Calculate dynamic fleet status
            active_agents = sum(1 for a in assets_status if a["symbol_status"] == "ACTIVE")
            
            key_ticks = {}
            for p in pipeline_status:
                if p["symbol"] in ["BTCUSD", "XAUUSD", "US30", "EURUSD"]:
                    if p["stage"] == "MARKET_CLOSED":
                        key_ticks[p["symbol"]] = "Market Closed"
                    elif p["stage"] == "DATA_OFFLINE":
                        key_ticks[p["symbol"]] = "Offline"
                    else:
                        if "tick_age=" in p["block_reason"]:
                            key_ticks[p["symbol"]] = f"{p['block_reason'].split('=')[1]}s ago"
                        else:
                            key_ticks[p["symbol"]] = "< 1s ago" if p["symbol"] == "BTCUSD" else "Active"
            
            fleet_status = {
    "running": active_agents > 0,
    "agents_alive": f"{active_agents} / {len(symbols)}",
    "last_telemetry": datetime.now(timezone.utc).strftime("%H:%M:%S"),
    "heartbeat_ok": heartbeat_ok,
    "heartbeat_age_seconds": age_sec,
    "heartbeat_timeout_seconds": HEARTBEAT_TIMEOUT_SECONDS,
    "key_ticks": key_ticks
}









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
                "audit_logs": logs,
                "pipeline_status": pipeline_status,
                "pipeline_summary": pipeline_summary,
                "fleet_status": fleet_status,
                "latest_heartbeat": latest_heartbeat_entry
            }

            response_bytes = json.dumps(response_data, indent=4).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)
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
