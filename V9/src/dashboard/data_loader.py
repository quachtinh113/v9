import json
import pandas as pd
from pathlib import Path
import yaml
import os

ROOT_DIR = Path(os.path.dirname(__file__)).resolve().parents[2] # D:\V9

def load_yaml(filepath: Path) -> dict:
    if not filepath.exists():
        return {}
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)

def load_ndjson(filepath: Path) -> pd.DataFrame:
    if not filepath.exists():
        return pd.DataFrame()
    records = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except:
                    pass
    return pd.DataFrame(records)

def load_csv(filepath: Path) -> pd.DataFrame:
    if not filepath.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(filepath)
    except:
        return pd.DataFrame()

def load_json(filepath: Path) -> dict:
    if not filepath.exists():
        return {}
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except:
        return {}

def get_all_projects_data(dashboard_config: dict) -> dict:
    paths = dashboard_config.get("paths", {})
    projects_dir = ROOT_DIR / paths.get("projects_root", "projects")
    
    aggregated = {
        "audit": [],
        "trade": [],
        "risk": [],
        "state": {},
        "positions": {},
        "signals": {}
    }
    
    if not projects_dir.exists():
        return aggregated

    for proj_dir in projects_dir.iterdir():
        if proj_dir.is_dir() and proj_dir.name.startswith("quant_v9_3_1_"):
            symbol = proj_dir.name.split("_")[-1].upper()
            
            audit_df = load_ndjson(proj_dir / paths.get("logs", {}).get("audit", ""))
            if not audit_df.empty:
                audit_df['symbol'] = symbol
                aggregated["audit"].append(audit_df)
                
            trade_df = load_csv(proj_dir / paths.get("logs", {}).get("trade", ""))
            if not trade_df.empty:
                trade_df['symbol'] = symbol
                aggregated["trade"].append(trade_df)
                
            aggregated["state"][symbol] = load_json(proj_dir / paths.get("runtime", {}).get("state", ""))
            aggregated["positions"][symbol] = load_json(proj_dir / paths.get("runtime", {}).get("positions", ""))
            aggregated["signals"][symbol] = load_json(proj_dir / paths.get("runtime", {}).get("signals", ""))
            
    if aggregated["audit"]: aggregated["audit"] = pd.concat(aggregated["audit"], ignore_index=True)
    else: aggregated["audit"] = pd.DataFrame()
    
    if aggregated["trade"]: aggregated["trade"] = pd.concat(aggregated["trade"], ignore_index=True)
    else: aggregated["trade"] = pd.DataFrame()
    
    return aggregated
