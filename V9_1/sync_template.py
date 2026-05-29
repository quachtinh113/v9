import shutil
import os
from pathlib import Path

root_dir = Path(r"C:\Quant Trade\v9\V9_1\projects")
src_project = root_dir / "quant_v9_3_1_gbpusd"

target_projects = [
    "quant_v9_3_1_audusd",
    "quant_v9_3_1_eurusd",
    "quant_v9_3_1_us100",
    "quant_v9_3_1_us30",
    "quant_v9_3_1_us500",
    "quant_v9_3_1_usdcad",
    "quant_v9_3_1_usdchf",
    "quant_v9_3_1_usdjpy",
    "quant_v9_3_1_xauusd",
    "quant_v9_3_1_btcusd"
]

files_to_sync = [
    "src/core/models.py",
    "src/data/mt5_live_adapter.py",
    "src/execution/mt5_adapter.py",
    "src/execution/order_router.py",
    "src/execution/trade_journal.py",
    "src/pipeline_live.py",
    "tests/test_execution_logic.py",
    "src/core/signal_engine.py"
]

for target in target_projects:
    target_project_dir = root_dir / target
    print(f"Syncing to {target}...")
    for f in files_to_sync:
        src_file = src_project / f
        dst_file = target_project_dir / f
        
        # Ensure destination directory exists
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        
        if src_file.exists():
            shutil.copy2(src_file, dst_file)
            print(f"  Copied {f}")
        else:
            print(f"  Source file not found: {src_file}")

print("Sync complete.")
