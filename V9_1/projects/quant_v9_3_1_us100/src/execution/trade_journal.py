import json
class TradeJournal:
    def __init__(self, p): self.p = p
    def write(self, et, pl): pass
class PipelineAuditLog:
    def __init__(self, p): self.p = p
    def write_tick(self, **kwargs): pass
    def write_blocked(self, reason, symbol, stage="DATA", details=None):
        import json
        from datetime import datetime, timezone
        if details is None:
            details = {"message": f"Block reason: {reason}"}
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "symbol": symbol,
            "stage": stage,
            "reason_code": reason,
            "details": details
        }
        try:
            with open(self.p, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except:
            pass

    def write_loop_audit(self, symbol, tick_ok, broker_symbol, data_stale, regime_result, signal_result, ml_mode, ml_score, risk_decision, execution_mode, order_send_called, details=None):
        import json
        from datetime import datetime, timezone
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "symbol": symbol,
            "stage": "LOOP_AUDIT",
            "tick_ok": tick_ok,
            "broker_symbol": broker_symbol,
            "data_stale": data_stale,
            "regime_result": regime_result,
            "signal_result": signal_result,
            "ml_mode": ml_mode,
            "ml_score": ml_score,
            "risk_decision": risk_decision,
            "execution_mode": execution_mode,
            "order_send_called": order_send_called,
            
            "trades_last_hour": trades_last_hour,
            "consecutive_losses_symbol": consecutive_losses_symbol,
            "consecutive_losses_fleet": consecutive_losses_fleet,
            "cooldown_status": cooldown_status,
            "veto_reason": veto_reason,
            "adx": adx14_h1,
            "rsi": rsi14_m15,
            "direction": signal_result,
"details": details or {}
        }
        try:
            with open(self.p, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except:
            pass

