from dataclasses import dataclass, field, asdict
from typing import List, Optional

@dataclass
class RegimeState:
    regime: str
    confidence: float
    adx_h1: float = 0.0
    adx_h4: float = 0.0
    atr_ratio: float = 1.0
    bb_width: float = 0.0
    session_flag: str = "off"

@dataclass
class SignalDecision:
    symbol: str
    direction: str
    score: float
    reason: str
    regime: str = "unknown"
    ml_score: float = 1.0
    ml_decision: str = "OFF"
    ml_reason: str = "N/A"
    size_multiplier: float = 1.0
    entry_allowed: bool = False
    gate_status: str = "REJECTED"
    blocked_reasons: List[str] = field(default_factory=list)
    rsi_mtf_pass: bool = False
    adx_pass: bool = False
    atr_pass: bool = False
    session_pass: bool = False
    direction_alignment_pass: bool = False
    risk_action: str = "N/A"
    position_plan_valid: bool = False

@dataclass
class RiskDecision:
    action: str
    reasons: List[str] = field(default_factory=list)
    daily_dd_pct: float = 0.0
    weekly_dd_pct: float = 0.0
    loss_streak: int = 0
    open_positions: int = 0

@dataclass
class PositionLayer:
    layer_id: int
    entry: float
    size: float
    note: str = ""

@dataclass
class PositionPlan:
    entry: float
    stop_loss: float
    take_profit: float
    size: float
    timeout_minutes: int
    note: Optional[str] = None
    layers: List[PositionLayer] = field(default_factory=list)

@dataclass
class Trade:
    symbol: str
    direction: str
    entry_time: str
    exit_time: str
    entry: float
    exit: float
    stop_loss: float
    take_profit: float
    pnl: float
    bars_held: int
    exit_reason: str
    def to_dict(self) -> dict: return asdict(self)

class DataIncompleteError(Exception):
    """Raised when data feed is missing, stale, or symbol cannot be resolved."""
    pass

