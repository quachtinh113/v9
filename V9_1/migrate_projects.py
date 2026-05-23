import os
import shutil
from pathlib import Path

SOURCE_ROOT = Path(r"d:\05_Quant\quant_v9_3_1_repos")
TARGET_ROOT = Path(__file__).resolve().parent / "projects"

SYMBOLS = ["GBPUSD", "EURUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "US30", "US100", "US500", "XAUUSD", "BTCUSD"]

def migrate_projects():
    TARGET_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"Migrating projects to {TARGET_ROOT}...")
    
    for sym in SYMBOLS:
        repo_name = f"quant_v9_3_1_{sym.lower()}"
        src = SOURCE_ROOT / repo_name
        dst = TARGET_ROOT / repo_name
        
        if src.exists():
            print(f"Copying {repo_name}...")
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"Done: {dst}")
        else:
            print(f"Warning: Source {src} not found")

if __name__ == "__main__":
    migrate_projects()
