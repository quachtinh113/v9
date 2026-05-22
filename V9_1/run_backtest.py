"""Run full pipeline backtest."""
import sys
from pathlib import Path
gbpusd_dir = Path(__file__).resolve().parent / "projects" / "quant_v9_3_1_gbpusd"
sys.path.insert(0, str(gbpusd_dir))
sys.argv = ["main", "--mode", "backtest"]
from src.main import main
main()
