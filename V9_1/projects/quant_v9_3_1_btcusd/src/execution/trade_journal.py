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

    def write_loop_audit(self, symbol, tick_ok, broker_symbol, data_stale, regime_result, signal_result, ml_mode, ml_score, risk_decision, execution_mode, order_send_called, ml_gate_mode=None, ml_block_applied=None, ml_reason=None, model_provenance_valid=None, model_id=None, model_status=None, allowed_to_block=None, details=None):
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
            "ml_gate_mode": ml_gate_mode,
            "ml_block_applied": ml_block_applied,
            "ml_reason": ml_reason,
            "model_provenance_valid": model_provenance_valid,
            "model_id": model_id,
            "model_status": model_status,
            "allowed_to_block": allowed_to_block,
            "details": details or {}
        }
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
            "ml_gate_mode": ml_gate_mode,
            "ml_block_applied": ml_block_applied,
            "ml_reason": ml_reason,
            "model_provenance_valid": model_provenance_valid,
            "details": details or {}
        }
        try:
            with open(self.p, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except:
            pass

