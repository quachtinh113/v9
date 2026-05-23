from __future__ import annotations

def should_kill(daily_dd_pct: float, hard_limit_pct: float) -> bool:
    return daily_dd_pct >= hard_limit_pct
