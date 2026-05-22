from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

from src.data.loaders import resolve_csv_source, load_ohlcv_csv
from src.data.mtf_builder import build_feature_table
from src.execution.mt5_adapter import MT5Adapter
from src.execution.order_router import OrderRouter
from src.execution.position_sync import PositionSync
from src.execution.trade_journal import TradeJournal
from src.risk.kill_switch import should_kill
from src.risk.session_guard import is_session_allowed
from src.utils.config import load_yaml


def latest_signal(root: Path) -> Dict[str, Any]:
    symbol_cfg = load_yaml(root / 'config' / 'symbol.yaml')
    strategy_name = str(symbol_cfg['symbol']).lower() + '_strategy'
    strategy_module = __import__(f'src.strategies.{strategy_name}', fromlist=['generate_trade_plan'])
    csv_path = resolve_csv_source(root, str(symbol_cfg['symbol']))
    df = load_ohlcv_csv(str(csv_path))
    features = build_feature_table(df)
    row = features.iloc[-1].to_dict()
    plan, decision = strategy_module.generate_trade_plan(row, symbol_cfg)
    return {
        'symbol': symbol_cfg['symbol'],
        'timestamp': str(row['timestamp']),
        'hhmm': str(row['timestamp'])[11:16],
        'direction': decision.direction,
        'score': decision.score,
        'reason': getattr(decision, 'reason', ''),
        'price': float(row['close_m5']),
        'stop_loss': None if plan is None else float(plan.stop_loss),
        'take_profit': None if plan is None else float(plan.take_profit),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['paper', 'mt5'], default='paper')
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    symbol_cfg = load_yaml(root / 'config' / 'symbol.yaml')
    risk_cfg = symbol_cfg.get('risk', {})
    demo_cfg_path = root / 'config' / 'mt5_demo.yaml'
    demo_cfg = load_yaml(demo_cfg_path) if demo_cfg_path.exists() else load_yaml(root / 'config' / 'mt5_demo.yaml.example')
    journal = TradeJournal(root / 'logs' / 'demo_journal.jsonl')

    # Fetch latest plan and decision
    csv_path = resolve_csv_source(root, str(symbol_cfg['symbol']))
    df = load_ohlcv_csv(str(csv_path))
    features = build_feature_table(df)
    row = features.iloc[-1].to_dict()
    strategy_name = str(symbol_cfg['symbol']).lower() + '_strategy'
    strategy_module = __import__(f'src.strategies.{strategy_name}', fromlist=['generate_trade_plan'])
    plan, decision = strategy_module.generate_trade_plan(row, symbol_cfg)
    
    if plan is None or decision.direction == 'flat':
        print(f"{symbol_cfg['symbol']} no actionable signal.")
        return
        
    # Evaluate risk gateway
    from src.core.risk_engine import RiskGateway
    gateway = RiskGateway(risk_cfg)
    account_data = {"daily_dd_pct": 0.0, "weekly_dd_pct": 0.0, "loss_streak": 0}
    market_data = {
        "session_flag": row.get("session_flag", "london"),
        "spread_bps": float(symbol_cfg.get("backtest", {}).get("spread_bps", 1.0)),
        "slippage_bps": float(symbol_cfg.get("backtest", {}).get("slippage_bps", 0.5)),
        "atr_ratio": float(row.get("atr_ratio", 1.0))
    }
    risk_decision = gateway.full_gate(account_data, market_data)

    enabled = bool(demo_cfg.get('mt5', {}).get('enabled', False)) and args.mode == 'mt5'
    mt5_settings = demo_cfg.get('mt5', {})
    adapter = MT5Adapter(
        login=mt5_settings.get('login'),
        password=mt5_settings.get('password'),
        server=mt5_settings.get('server'),
        path=mt5_settings.get('path'),
        enabled=enabled
    )
    adapter.connect()
    
    router = OrderRouter(adapter, demo_cfg.get('execution', {}), journal)
    result = router.route_order(plan, decision, risk_decision, bar_ts=str(row['timestamp']))
    
    print(
        f"{symbol_cfg['symbol']} demo={args.mode} status={result.get('status')} "
        f"direction={decision.direction} score={decision.score}"
    )


if __name__ == '__main__':
    main()
