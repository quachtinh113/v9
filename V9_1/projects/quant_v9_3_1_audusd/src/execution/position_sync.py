from __future__ import annotations
from typing import Any, Dict, List

class PositionSync:
    def __init__(self) -> None:
        self.positions: List[Dict[str, Any]] = []

    def update_from_execution(self, execution_result: Dict[str, Any]) -> None:
        if execution_result.get('status') in {'submitted', 'paper_only', 'paper_success'}:
            req = execution_result.get('request_dict') or {}
            self.positions.append({
                'symbol': req.get('symbol'),
                'direction': req.get('direction'),
                'volume': req.get('volume'),
                'stop_loss': req.get('stop_loss'),
                'take_profit': req.get('take_profit'),
                'status': execution_result.get('status'),
            })

    def snapshot(self) -> List[Dict[str, Any]]:
        return list(self.positions)
