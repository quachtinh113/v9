import sys
from pathlib import Path

# Add US30 repo to path
us30_root = Path(__file__).resolve().parent / "projects" / "quant_v9_3_1_us30"
sys.path.insert(0, str(us30_root))

# Import main from US30 repo
from src.main import main

# Mock sys.argv to run backtest
sys.argv = ["main", "--mode", "backtest"]

if __name__ == "__main__":
    main()
