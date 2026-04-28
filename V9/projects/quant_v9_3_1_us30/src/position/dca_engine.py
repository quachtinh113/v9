from typing import Dict, Any, List, Optional
from src.core.models import PositionLayer, SignalDecision, RiskDecision

class DCAEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("dca", {})
        self.enabled = self.config.get("enabled", False)
        self.max_layers = self.config.get("max_layers", 3)
        self.spacing_atr_multiplier = self.config.get("spacing_atr_multiplier", 0.8)
        self.require_regime_still_valid = self.config.get("require_regime_still_valid", True)
        self.lot_multipliers = self.config.get("lot_multiplier", {"layer_1": 1.0, "layer_2": 1.0, "layer_3": 1.0})

    def validate_dca_permission(self, symbol: str, current_regime: str, original_regime: str, risk_decision: RiskDecision, current_layers: int) -> bool:
        if not self.enabled:
            return False
        if current_layers >= self.max_layers:
            return False
        if risk_decision.action == "BLOCK":
            return False
        if self.require_regime_still_valid and current_regime != original_regime:
            return False
        return True

    def calculate_dca_spacing(self, atr: float, symbol: str) -> float:
        spacing = atr * self.spacing_atr_multiplier
        # Optional: check min_spacing_points if pip value conversion exists
        return spacing

    def calculate_dca_lot(self, base_lot: float, layer_index: int) -> float:
        # Prevent martingale by taking min of multiplier and 1.0 (strict rule: no > 1x multiplier)
        multiplier_str = f"layer_{layer_index}"
        mult = float(self.lot_multipliers.get(multiplier_str, 1.0))
        mult = min(mult, 1.0) # Enforce non-martingale rule
        return base_lot * mult

    def build_dca_plan(self, symbol: str, base_entry: float, direction: str, atr: float, base_lot: float) -> List[PositionLayer]:
        layers = []
        spacing = self.calculate_dca_spacing(atr, symbol)
        
        for i in range(1, self.max_layers + 1):
            if direction == "long":
                entry_price = base_entry - (spacing * i)
            else:
                entry_price = base_entry + (spacing * i)
                
            lot_size = self.calculate_dca_lot(base_lot, i)
            layers.append(PositionLayer(layer_id=i, entry=entry_price, size=lot_size, note=f"DCA Layer {i}"))
            
        return layers
