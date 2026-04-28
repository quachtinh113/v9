from typing import List, Dict

def check_alerts(data: dict, risk_config: dict, dashboard_config: dict) -> List[Dict[str, str]]:
    alerts = []
    
    # Check Risk Engine config
    if not risk_config.get("risk_engine", {}).get("enabled", False):
        alerts.append({"level": "CRITICAL", "msg": "Risk Engine is DISABLED in risk_config.yaml!"})
        
    # Check Audit Logger
    # For now we assume if audit df is empty and state says running, it might be disabled
    
    # Check Daily Loss
    max_daily = risk_config.get("risk_engine", {}).get("max_daily_loss_pct", 2.0)
    warning_daily = dashboard_config.get("alerts", {}).get("max_daily_loss_warning_pct", 1.5)
    
    states = data.get("state", {})
    positions = data.get("positions", {})
    
    buy_assets = 0
    sell_assets = 0
    
    for symbol, state in states.items():
        if state.get("daily_loss_pct", 0) >= warning_daily:
            level = "CRITICAL" if state.get("daily_loss_pct", 0) >= max_daily else "WARNING"
            alerts.append({"level": level, "msg": f"[{symbol}] Daily loss at {state.get('daily_loss_pct', 0)}%"})
            
    for symbol, pos in positions.items():
        # fixed lot check
        if pos.get("lot_size", 0) == 0.25 and risk_config.get("position_sizing", {}).get("disable_fixed_lot_multi_asset", True):
            alerts.append({"level": "CRITICAL", "msg": f"[{symbol}] Fixed lot 0.25 detected!"})
            
        # layer check
        if pos.get("layers", 0) > 3:
            alerts.append({"level": "CRITICAL", "msg": f"[{symbol}] DCA layers exceeded 3!"})
            
        # pending orders
        if pos.get("pending_orders", 0) > dashboard_config.get("alerts", {}).get("max_pending_orders_warning", 3):
            alerts.append({"level": "WARNING", "msg": f"[{symbol}] High pending orders: {pos.get('pending_orders')}"})
            
        # correlation check
        if pos.get("direction") == "long" and symbol in risk_config.get("correlation_guard", {}).get("risk_assets", []):
            buy_assets += 1
        elif pos.get("direction") == "short" and symbol in risk_config.get("correlation_guard", {}).get("risk_assets", []):
            sell_assets += 1
            
        if not pos.get("sl") or not pos.get("tp"):
            if pos.get("active", False):
                alerts.append({"level": "CRITICAL", "msg": f"[{symbol}] Position missing SL/TP!"})
            
    if buy_assets >= 3 or sell_assets >= 3:
        alerts.append({"level": "CRITICAL", "msg": f"Multiple simultaneous Risk Assets in same direction!"})
        
    return alerts
