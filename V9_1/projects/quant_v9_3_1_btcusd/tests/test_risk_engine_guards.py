import pytest
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.risk_engine import RiskGateway

@pytest.fixture
def risk_gateway():
    config = {
        "max_trades_per_symbol_per_hour": 3,
        "min_seconds_between_same_symbol_trades": 300,
        "stop_symbol_after_n_consecutive_losses": 3,
        "fleet_loss_streak_brake": 8,
        "cooldown_after_loss_minutes": 30,
        "max_open_trades_per_symbol": 1
    }
    return RiskGateway(config)

def test_max_trades_per_symbol_per_hour(risk_gateway):
    account = {"daily_dd_pct": 0, "weekly_dd_pct": 0, "loss_streak": 0, "trades_last_hour": 3}
    market = {"spread_bps": 1, "slippage_bps": 1, "atr_ratio": 1, "session_flag": "london"}
    decision = risk_gateway.full_gate(account, market)
    assert decision.action == "HARD_KILL"
    assert "max_trades_per_hour_exceeded" in decision.reasons

def test_min_seconds_between_same_symbol_trades(risk_gateway):
    account = {"daily_dd_pct": 0, "weekly_dd_pct": 0, "loss_streak": 0, "seconds_since_last_trade": 150}
    market = {"spread_bps": 1, "slippage_bps": 1, "atr_ratio": 1, "session_flag": "london"}
    decision = risk_gateway.full_gate(account, market)
    assert decision.action == "HARD_KILL"
    assert "too_soon_since_last_trade" in decision.reasons

def test_max_open_trades_per_symbol(risk_gateway):
    account = {"daily_dd_pct": 0, "weekly_dd_pct": 0, "loss_streak": 0, "open_positions": 1}
    market = {"spread_bps": 1, "slippage_bps": 1, "atr_ratio": 1, "session_flag": "london"}
    decision = risk_gateway.full_gate(account, market)
    assert decision.action == "HARD_KILL"
    assert "max_open_trades_per_symbol_exceeded" in decision.reasons

def test_prevent_duplicate_direction(risk_gateway):
    account = {"daily_dd_pct": 0, "weekly_dd_pct": 0, "loss_streak": 0, "open_directions": ["long"]}
    market = {"spread_bps": 1, "slippage_bps": 1, "atr_ratio": 1, "session_flag": "london", "pending_direction": "long"}
    decision = risk_gateway.full_gate(account, market)
    assert decision.action == "HARD_KILL"
    assert "duplicate_direction_open" in decision.reasons

def test_stop_symbol_after_n_consecutive_losses(risk_gateway):
    account = {"daily_dd_pct": 0, "weekly_dd_pct": 0, "loss_streak": 0, "consecutive_losses_symbol": 3}
    market = {"spread_bps": 1, "slippage_bps": 1, "atr_ratio": 1, "session_flag": "london"}
    decision = risk_gateway.full_gate(account, market)
    assert decision.action == "HARD_KILL"
    assert "symbol_consecutive_loss_limit" in decision.reasons

def test_fleet_loss_streak_brake(risk_gateway):
    account = {"daily_dd_pct": 0, "weekly_dd_pct": 0, "loss_streak": 0, "fleet_loss_streak": 8}
    market = {"spread_bps": 1, "slippage_bps": 1, "atr_ratio": 1, "session_flag": "london"}
    decision = risk_gateway.full_gate(account, market)
    assert decision.action == "HARD_KILL"
    assert "fleet_loss_streak_limit" in decision.reasons

def test_cooldown_after_loss_minutes(risk_gateway):
    account = {"daily_dd_pct": 0, "weekly_dd_pct": 0, "loss_streak": 0, "seconds_since_last_loss": 600} # 10 minutes, threshold is 30 mins (1800)
    market = {"spread_bps": 1, "slippage_bps": 1, "atr_ratio": 1, "session_flag": "london"}
    decision = risk_gateway.full_gate(account, market)
    assert decision.action == "HARD_KILL"
    assert "loss_cooldown_active" in decision.reasons

def test_allow_when_safe(risk_gateway):
    account = {
        "daily_dd_pct": 0, "weekly_dd_pct": 0, "loss_streak": 0, 
        "trades_last_hour": 1, "seconds_since_last_trade": 400, 
        "open_positions": 0, "open_directions": [], 
        "consecutive_losses_symbol": 0, "fleet_loss_streak": 0, 
        "seconds_since_last_loss": 2000
    }
    market = {"spread_bps": 1, "slippage_bps": 1, "atr_ratio": 1, "session_flag": "london", "pending_direction": "long"}
    decision = risk_gateway.full_gate(account, market)
    assert decision.action == "ALLOW"
