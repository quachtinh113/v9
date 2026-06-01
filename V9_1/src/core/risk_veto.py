import datetime
import sys
import os

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.core.account_registry import AccountRegistry

class RiskVetoLayer:
    """
    Centralized risk vetting that intercepts order execution if account risk limits are breached.
    """
    
    @staticmethod
    def vet_order(account_id: str, order_type: str, lots: float, current_floating_pnl: float, current_balance: float):
        """
        Returns (bool, str): (is_allowed, block_reason)
        """
        account = AccountRegistry.get_account(account_id)
        if not account:
            return False, f"VETO: Unknown account_id {account_id}"

        # 1. Execution Mode Check
        if not account.get("risk_profile", {}).get("live_execution_enabled", False):
            # If paper trading, we might still allow "paper" orders but we block MT5 live sends.
            # In this context, if live_execution_enabled is False, real orders are vetoed.
            return False, f"VETO: Live execution is DISABLED for account {account_id}"

        # 2. Risk Checks
        risk_profile = account.get("risk_profile", {})
        max_dd_pct = risk_profile.get("max_drawdown_pct", 10.0)
        max_daily_loss_pct = risk_profile.get("max_daily_loss_pct", 2.0)

        # Drawdown calculation
        # Simplified: If floating PnL is extremely negative relative to balance
        if current_balance > 0:
            drawdown_pct = (abs(current_floating_pnl) / current_balance) * 100 if current_floating_pnl < 0 else 0
            
            if drawdown_pct >= max_dd_pct:
                return False, f"VETO: Hard drawdown breached ({drawdown_pct:.2f}% >= {max_dd_pct}%)"
                
            if drawdown_pct >= max_daily_loss_pct:
                return False, f"VETO: Daily loss limit breached ({drawdown_pct:.2f}% >= {max_daily_loss_pct}%)"
        
        return True, "ALLOWED"
