import pytest
from src.position.dca_engine import DCAEngine
from src.core.models import RiskDecision

@pytest.fixture
def base_config():
    return {
        "dca": {
            "enabled": True,
            "mode": "atr_based",
            "max_layers": 3,
            "spacing_atr_multiplier": 0.8,
            "lot_multiplier": {
                "layer_1": 1.0,
                "layer_2": 1.0,
                "layer_3": 1.0
            },
            "require_regime_still_valid": True
        }
    }

def test_dca_permission_blocked_by_risk(base_config):
    engine = DCAEngine(base_config)
    risk = RiskDecision("BLOCK", ["daily_loss_limit"])
    assert not engine.validate_dca_permission("US30", "trend", "trend", risk, 1)

def test_dca_permission_regime_flip(base_config):
    engine = DCAEngine(base_config)
    risk = RiskDecision("ALLOW", [])
    assert not engine.validate_dca_permission("US30", "range", "trend", risk, 1)

def test_dca_permission_max_layers(base_config):
    engine = DCAEngine(base_config)
    risk = RiskDecision("ALLOW", [])
    assert not engine.validate_dca_permission("US30", "trend", "trend", risk, 3)

def test_dca_permission_allowed(base_config):
    engine = DCAEngine(base_config)
    risk = RiskDecision("ALLOW", [])
    assert engine.validate_dca_permission("US30", "trend", "trend", risk, 2)

def test_dca_plan_generation(base_config):
    engine = DCAEngine(base_config)
    layers = engine.build_dca_plan("US30", 35000.0, "long", 100.0, 0.1)
    assert len(layers) == 3
    assert layers[0].entry == 35000.0 - (100.0 * 0.8)
    assert layers[0].size == 0.1 # No martingale
    assert layers[1].entry == 35000.0 - (100.0 * 0.8 * 2)

def test_dca_no_martingale():
    # Even if config tries to be aggressive, engine should clamp to 1.0
    cfg = {"dca": {"enabled": True, "lot_multiplier": {"layer_1": 2.0}}}
    engine = DCAEngine(cfg)
    assert engine.calculate_dca_lot(0.1, 1) == 0.1
