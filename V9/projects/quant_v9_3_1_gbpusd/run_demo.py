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
        'price': float(row['close_m1']),
        'stop_loss': None if plan is None else float(plan.stop_loss),
        'take_profit': None if plan is None else float(plan.take_profit),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['paper', 'mt5'], default='paper')
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    risk_cfg = load_yaml(root / 'config' / 'risk.yaml')
    session_cfg = load_yaml(root / 'config' / 'sessions.yaml')
    demo_cfg_path = root / 'config' / 'mt5_demo.yaml'
    demo_cfg = load_yaml(demo_cfg_path) if demo_cfg_path.exists() else load_yaml(root / 'config' / 'mt5_demo.yaml.example')
    journal = TradeJournal(root / 'logs' / 'demo_journal.jsonl')

    signal = latest_signal(root)
    journal.write('signal_generated', signal)

    if signal['direction'] == 'none' or signal['stop_loss'] is None:
        print(f"{signal['symbol']} no actionable signal. score={signal['score']}")
        journal.write('signal_blocked', {'reason': 'no_signal', 'signal': signal})
        return

    windows = session_cfg.get('entry_windows_vn', []) or session_cfg.get('entry_windows', {}).get('new_york', [])
    if windows and not is_session_allowed(signal['hhmm'], windows):
        print(f"{signal['symbol']} signal blocked by session guard at {signal['hhmm']}")
        journal.write('signal_blocked', {'reason': 'session_guard', 'signal': signal})
        return

    hard = float(risk_cfg.get('hard_drawdown_pct', 8.0))
    if should_kill(daily_dd_pct=0.0, hard_limit_pct=hard):
        print(f"{signal['symbol']} blocked by kill switch")
        journal.write('signal_blocked', {'reason': 'kill_switch', 'signal': signal})
        return

    enabled = bool(demo_cfg.get('mt5', {}).get('enabled', False)) and args.mode == 'mt5'
    adapter = MT5Adapter(mt5_config=demo_cfg.get('mt5', {}), execution_config=demo_cfg.get('execution', {}), enabled=enabled)
    router = OrderRouter(adapter, demo_cfg.get('execution', {}))
    sync = PositionSync()

    result = router.route(signal)
    sync.update_from_execution(result)
    journal.write('order_routed', {'signal': signal, 'result': result, 'positions': sync.snapshot()})

    print(
        f"{signal['symbol']} demo={args.mode} status={result['status']} "
        f"direction={signal['direction']} score={signal['score']} positions={len(sync.snapshot())}"
    )


if __name__ == '__main__':
    main()
