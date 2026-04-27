from src.core.models import PositionPlan, SignalDecision
from src.core.signal_engine import evaluate_signal

def generate_trade_plan(features, config=None):
    decision = evaluate_signal(features, config)
    if decision.direction == "flat": return None, decision
    plan = PositionPlan(features["close_m1"], features["close_m1"]*0.99, features["close_m1"]*1.02, 0.25, 120)
    return plan, decision
