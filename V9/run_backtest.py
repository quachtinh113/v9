"""Run full pipeline backtest."""
import sys
sys.path.insert(0, r"d:\05_Quant\quant_v9_3_1_repos\quant_v9_3_1_gbpusd")
sys.argv = ["main", "--mode", "backtest"]
from src.main import main
main()
