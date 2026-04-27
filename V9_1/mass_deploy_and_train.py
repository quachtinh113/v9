import os
import shutil
import sys
from pathlib import Path
import yaml
import subprocess

REPO_ROOT = Path(r"d:\V9\projects")
SOURCE_REPO = REPO_ROOT / "quant_v9_3_1_us30"

SYMBOLS = {
    "GBPUSD": {"type": "forex", "mt5_symbol": "GBPUSDm"},
    "EURUSD": {"type": "forex", "mt5_symbol": "EURUSDm"},
    "USDJPY": {"type": "forex", "mt5_symbol": "USDJPYm"},
    "AUDUSD": {"type": "forex", "mt5_symbol": "AUDUSDm"},
    "USDCAD": {"type": "forex", "mt5_symbol": "USDCADm"},
    "USDCHF": {"type": "forex", "mt5_symbol": "USDCHFm"},
    "US30":   {"type": "index", "mt5_symbol": "US30m"},
    "US100":  {"type": "index", "mt5_symbol": "USTEC"},
    "US500":  {"type": "index", "mt5_symbol": "US500m"},
    "XAUUSD": {"type": "gold",  "mt5_symbol": "XAUUSDm"},
}

def setup_repo(symbol, data):
    repo_name = f"quant_v9_3_1_{symbol.lower()}"
    target_path = REPO_ROOT / repo_name
    print(f"\n--- Setting up {symbol} at {target_path} ---")
    
    if not target_path.exists():
        target_path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory {target_path}")

    # Sync source code (src, config)
    if target_path != SOURCE_REPO:
        for folder in ["src", "config"]:
            src_folder = SOURCE_REPO / folder
            dst_folder = target_path / folder
            if dst_folder.exists():
                shutil.rmtree(dst_folder)
            shutil.copytree(src_folder, dst_folder)
    
    (target_path / "models").mkdir(exist_ok=True)
    (target_path / "logs").mkdir(exist_ok=True)
    (target_path / "reports").mkdir(exist_ok=True)
    (target_path / "data" / "raw").mkdir(parents=True, exist_ok=True)

    # Update symbol.yaml
    config_path = target_path / "config" / "symbol.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        config['symbol'] = symbol
        if data['type'] == 'index':
            config['entry']['trend_adx_min'] = 25
            config['position']['stop_atr_mult'] = 1.8
            config['position']['tp_atr_mult'] = 2.5
        elif data['type'] == 'gold':
            config['entry']['trend_adx_min'] = 28
            config['position']['stop_atr_mult'] = 2.0
            config['position']['tp_atr_mult'] = 3.0
        else: # forex
            config['entry']['trend_adx_min'] = 22
            config['position']['stop_atr_mult'] = 1.4
            config['position']['tp_atr_mult'] = 2.2
            
        with open(config_path, 'w') as f:
            yaml.dump(config, f)

    # Rename strategy
    strategy_dir = target_path / "src" / "strategies"
    for file in strategy_dir.glob("*_strategy.py"):
        if file.name != f"{symbol.lower()}_strategy.py":
            content = file.read_text()
            content = content.replace('"US30"', f'"{symbol}"')
            content = content.replace('us30_strategy', f'{symbol.lower()}_strategy')
            (strategy_dir / f"{symbol.lower()}_strategy.py").write_text(content)
            file.unlink()

    print(f"Setup complete for {symbol}")

def train_repo(symbol):
    repo_name = f"quant_v9_3_1_{symbol.lower()}"
    target_path = REPO_ROOT / repo_name
    print(f"\n--- Training {symbol} ---")
    
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(target_path)
        
        cmd = [sys.executable, "-m", "src.main", "--mode", "train"]
        result = subprocess.run(cmd, cwd=target_path, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Training SUCCESS for {symbol}")
            lines = result.stdout.splitlines()
            if lines: print(lines[-1])
        else:
            print(f"Training FAILED for {symbol}")
            print(result.stderr)
            print(result.stdout)
    except Exception as e:
        print(f"Error training {symbol}: {e}")

if __name__ == "__main__":
    for sym, data in SYMBOLS.items():
        setup_repo(sym, data)
    
    print("\n" + "="*60)
    print("  MASS SETUP COMPLETE. STARTING MASS TRAINING...")
    print("="*60)
    
    for sym in SYMBOLS.keys():
        train_repo(sym)
