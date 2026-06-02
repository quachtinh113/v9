import os
import sys
import copy
from pathlib import Path

import os
os.environ["RISK_STATE_DB_PATH"] = str(Path("c:/Quant Trade/v9/V9_1/logs/test_risk_state.db").resolve())

def clear_src_modules():
    to_delete = [m for m in sys.modules if m.startswith('src.') or m == 'src']
    for m in to_delete:
        del sys.modules[m]

def run_dry_run_proof(symbol):
    print(f"\n{'='*75}")
    print(f"  DRY-RUN PROOF OF SIGNAL PIPELINE: {symbol} (WITH EXPANDED LIVE TELEMETRY)")
    print(f"{'='*75}")
    
    repo_name = f"quant_v9_3_1_{symbol.lower()}"
    root = Path(f"C:/Quant Trade/v9/V9_1/projects/{repo_name}")
    clear_src_modules()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
        
    original_cwd = os.getcwd()
    os.chdir(str(root))
    
    try:
        from src.utils.config import load_yaml
        from src.core.signal_engine import evaluate_signal
        from src.core.risk_engine import RiskGateway
        
        config = load_yaml(root / "config" / "symbol.yaml")
        
        # Load risk config safely
        risk_config = {}
        risk_yaml_path = root / "config" / "risk.yaml"
        if risk_yaml_path.exists():
            risk_config.update(load_yaml(risk_yaml_path) or {})
        risk_config.update(config.get("risk", {}))
        
        base_features = {
            "rsi14_m15": 50.0,
            "bb_width_m15": 0.01,
            "macd_hist_m15": 0.0,
            "adx14_h1": 25.0,
            "adx14_h4": 20.0,
            "atr14_m1": 0.001,
            "atr14_h1": 0.0008,
            "atr14_h4": 0.0007,
            "atr_ratio": 1.25,
            "bias": "flat",
            "bias_h1": "flat",
            "bias_h4": "flat",
            "session_flag": "london",
            "hour": 9,
            "minute": 30,
            "hour_sin": 0.5,
            "hour_cos": 0.86,
            "close": 1.1000,
            "close_m1": 1.1000,
            "close_m5": 1.1000,
            "timestamp": "2026-05-28 09:30:00"
        }
        
        scenarios = [
            {
                "name": "Scenario 1: Live Model Trend BUY Setup (Actual ML score is evaluated natively)",
                "features": {
                    "adx14_h1": 32.0,
                    "adx14_h4": 24.0,
                    "bias": "long",
                    "bias_h1": "long",
                    "bias_h4": "long",
                    "rsi14_m15": 58.0,
                    "atr_ratio": 1.1,
                    "session_flag": "london"
                },
                "cfg_overrides": {
                    "ml": {"enabled": True, "block_threshold": 0.50},
                    "risk": {"transition_trade_enabled": False}
                },
                "mock_ml": None
            },
            {
                "name": "Scenario 2: Boundary Proof - Score = 0.53 under OLD Threshold (0.55) -> BLOCKED!",
                "features": {
                    "adx14_h1": 32.0,
                    "adx14_h4": 24.0,
                    "bias": "long",
                    "bias_h1": "long",
                    "bias_h4": "long",
                    "rsi14_m15": 58.0,
                    "atr_ratio": 1.1,
                    "session_flag": "london"
                },
                "cfg_overrides": {
                    "ml": {"enabled": True, "block_threshold": 0.55},
                    "risk": {"transition_trade_enabled": False}
                },
                "mock_ml": 0.53
            },
            {
                "name": "Scenario 3: Boundary Proof - Score = 0.53 under NEW Threshold (0.50) -> PASSES & EXECUTION_READY!",
                "features": {
                    "adx14_h1": 32.0,
                    "adx14_h4": 24.0,
                    "bias": "long",
                    "bias_h1": "long",
                    "bias_h4": "long",
                    "rsi14_m15": 58.0,
                    "atr_ratio": 1.1,
                    "session_flag": "london"
                },
                "cfg_overrides": {
                    "ml": {"enabled": True, "block_threshold": 0.50},
                    "risk": {"transition_trade_enabled": False}
                },
                "mock_ml": 0.53
            }
        ]
        
        for sc in scenarios:
            print(f"\n--- Running: {sc['name']} ---")
            
            # Prepare config and features
            test_cfg = copy.deepcopy(config)
            for k, val in sc["cfg_overrides"].items():
                if k in test_cfg:
                    test_cfg[k].update(val)
                else:
                    test_cfg[k] = val
            
            test_features = copy.deepcopy(base_features)
            test_features.update(sc["features"])
            
            # Mock the ML predict if needed
            if sc["mock_ml"] is not None:
                from src.ml.xgb_filter import _FILTER_CACHE
                model_path = test_cfg.get("ml", {}).get("model_path", "models/xgb_trade_filter.json")
                
                class MockXGBFilter:
                    def __init__(self):
                        self.enabled = True
                        self.load_failed = False
                    def predict_quality(self, features, score):
                        return float(sc["mock_ml"])
                        
                _FILTER_CACHE[model_path] = MockXGBFilter()
            else:
                from src.ml.xgb_filter import _FILTER_CACHE
                _FILTER_CACHE.clear()
            
            # 1. Strategy Signal Evaluation
            dec = evaluate_signal(test_features, test_cfg)
            
            # 2. Strategy Sizing and Position Plan
            strategy_name = symbol.lower() + "_strategy"
            strategy = __import__(f"src.strategies.{strategy_name}", fromlist=["generate_trade_plan"])
            plan, dec_final = strategy.generate_trade_plan(test_features, test_cfg)
            
            # 3. Risk Gateway
            risk_gateway = RiskGateway(test_cfg.get("risk", {}))
            
            account_data = {
                "daily_dd_pct": 0.0,
                "weekly_dd_pct": 0.0,
                "loss_streak": 0,
                "open_positions": 0,
                "daily_trades_count": 0
            }
            atr_ratio = float(test_features.get("atr_ratio", 1.0))
            effective_spread = float(test_cfg.get("backtest", {}).get("spread_bps", 2.0)) * max(1.0, atr_ratio)
            effective_slippage = float(test_cfg.get("backtest", {}).get("slippage_bps", 1.0)) * max(1.0, atr_ratio)
            
            market_data = {
                "session_flag": test_features.get("session_flag", "london"),
                "spread_bps": effective_spread,
                "slippage_bps": effective_slippage,
                "atr_ratio": atr_ratio
            }
            
            risk_dec = risk_gateway.full_gate(account_data, market_data)
            
            # 4. Standardized Output variables
            ts_val = test_features.get("timestamp", "N/A")
            raw_sig = getattr(dec, "raw_signal", dec.direction)
            ml_thresh = test_cfg.get("ml", {}).get("block_threshold", 0.50)
            
            risk_act = risk_dec.action
            risk_reasons = risk_dec.reasons
            
            # If dec was blocked by ML, add that block reason
            all_blocks = []
            if dec.ml_decision == "BLOCK":
                all_blocks.append("ML_gatekeeper_block")
            all_blocks += dec.blocked_reasons + risk_reasons
            all_blocks = list(dict.fromkeys(all_blocks))
            
            final_act = "EXECUTION_READY" if (risk_act == "ALLOW" and dec_final.position_plan_valid and dec.entry_allowed) else "FLATTENED"
            
            # Extract indicators safely
            rsi_m15 = test_features.get("rsi14_m15", 0.0)
            adx_val = test_features.get("adx14_h1", 0.0)
            atr_val = test_features.get("atr14_m1", 0.001)
            
            # Print requested debug output
            print(f"[DIAGNOSTIC] symbol={symbol} | timestamp={ts_val} | regime={dec.regime} | rsi_m15={rsi_m15:.2f} | rsi_h1=N/A | rsi_h4=N/A | adx={adx_val:.2f} | atr={atr_val:.6f} | raw_signal={raw_sig} | signal_score={dec.score:.0f} | ml_score={dec.ml_score:.4f} | ml_threshold={ml_thresh:.2f} | ml_decision={dec.ml_decision} | risk_decision={risk_act} | final_action={final_act} | block_reason={all_blocks}")
            
            if final_act == "EXECUTION_READY" and plan:
                print(f"  >>> Sizing: Approved Order to Send {dec.direction.upper()} size {plan.size:.2f} lots at {plan.entry:.5f}")
            else:
                print(f"  >>> Signal Starvation Status: BLOCKED. Reasons: {all_blocks}")
                
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        os.chdir(original_cwd)
        if str(root) in sys.path:
            sys.path.remove(str(root))

if __name__ == "__main__":
    run_dry_run_proof("EURUSD")
