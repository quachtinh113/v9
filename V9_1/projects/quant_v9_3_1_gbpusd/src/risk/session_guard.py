from __future__ import annotations

def is_session_allowed(current_hhmm: str, allowed_windows: list[str]) -> bool:
    return current_hhmm in allowed_windows
