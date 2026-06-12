import json
from pathlib import Path

def check_risk_engine(root_path: str) -> dict:
    """Inspect risk engine configuration and return a summary.
    Looks for a file named `risk_engine_config.yaml` or similar inside `configs/`.
    Returns keys:
        - config_path (str or None)
        - exists (bool)
        - content_preview (list of first 5 lines) if exists
    The function never modifies any files.
    """
    config_candidates = [
        Path(root_path) / "configs" / "risk_engine_config.yaml",
        Path(root_path) / "configs" / "risk.yaml",
    ]
    for cfg in config_candidates:
        if cfg.is_file():
            try:
                with cfg.open('r', encoding='utf-8') as f:
                    preview = [next(f).strip() for _ in range(5)]
            except Exception:
                preview = []
            return {
                "config_path": str(cfg),
                "exists": True,
                "content_preview": preview,
            }
    return {"config_path": None, "exists": False, "content_preview": []}

if __name__ == "__main__":
    import sys, pprint
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    pprint.pprint(check_risk_engine(root))
