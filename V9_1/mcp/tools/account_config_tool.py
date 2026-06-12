import yaml
from pathlib import Path

def load_account_config(root_path: str) -> dict:
    """Load account configuration from `configs/account_config.yaml` if it exists.
    Returns a dictionary with the parsed YAML content, or an empty dict if the file is missing.
    This tool is read‑only and does not modify any state.
    """
    config_path = Path(root_path) / "configs" / "account_config.yaml"
    if not config_path.is_file():
        return {}
    try:
        with config_path.open('r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

if __name__ == "__main__":
    import sys, pprint
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    pprint.pprint(load_account_config(root))
