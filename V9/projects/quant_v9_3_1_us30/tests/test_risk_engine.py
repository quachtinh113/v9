import pytest
from src.core.risk_engine import RiskGateway

@pytest.fixture
def risk_config():
    return {
        "risk_engine": {
            "enabled": True,
            "max_daily_loss_pct": 2.0,
            "max_basket_risk_pct": 0.75,
            "max_total_open_risk_pct": 1.5,
            "max_open_positions_total": 10,
            "max_open_positions_per_symbol": 2,
            "max_pending_orders_per_symbol": 3,
            "max_same_direction_assets": 3,
            "block_trade_if_spread_high": True
        }
    }

def test_risk_allow(risk_config):
    gw = RiskGateway(risk_config)
    dec = gw.full_gate({}, {})
    assert dec.action == "ALLOW"

def test_risk_daily_loss(risk_config):
    gw = RiskGateway(risk_config)
    dec = gw.full_gate({"daily_dd_pct": 2.5}, {})
    assert dec.action == "BLOCK"
    assert "daily_loss_limit" in dec.reasons

def test_risk_basket_limit(risk_config):
    gw = RiskGateway(risk_config)
    dec = gw.full_gate({}, {}, {"basket_risk_pct": 1.0})
    assert dec.action == "BLOCK"
    assert "basket_risk_limit" in dec.reasons

def test_risk_max_pending(risk_config):
    gw = RiskGateway(risk_config)
    dec = gw.full_gate({}, {}, {"pending_orders": 3})
    assert dec.action == "BLOCK"
    assert "max_pending_orders_symbol" in dec.reasons

def test_risk_max_same_direction(risk_config):
    gw = RiskGateway(risk_config)
    dec = gw.full_gate({"same_direction_count": 4}, {})
    assert dec.action == "BLOCK"
    assert "max_same_direction_assets" in dec.reasons

def test_risk_spread_high(risk_config):
    gw = RiskGateway(risk_config)
    dec = gw.full_gate({}, {"spread_high": True})
    assert dec.action == "BLOCK"
    assert "spread_high" in dec.reasons
