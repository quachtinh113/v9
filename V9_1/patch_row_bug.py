import os
import re
from pathlib import Path

def patch_all():
    root = Path("c:/Quant Trade/v9/V9_1/projects")
    symbols = ["gbpusd", "eurusd", "usdjpy", "audusd", "usdcad", "usdchf", "us30", "us100", "us500", "xauusd", "btcusd"]
    
    for sym in symbols:
        file_path = root / f"quant_v9_3_1_{sym}" / "src" / "pipeline_live.py"
        if not file_path.exists():
            continue
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # replace row.get with getattr(self, 'last_row', {}).get
        # inside the finally block of tick()
        # Be safe with regex
        new_content = re.sub(r'row\.get\((["\']rsi14_m15["\'])\)', r"getattr(self, 'last_row', {}).get(\1)", content)
        new_content = re.sub(r'row\.get\((["\']adx14_h1["\'])\)', r"getattr(self, 'last_row', {}).get(\1)", new_content)
        new_content = re.sub(r'row\.get\((["\']adx14_h4["\'])\)', r"getattr(self, 'last_row', {}).get(\1)", new_content)
        new_content = re.sub(r'row\.get\((["\']atr14_m1["\'])\)', r"getattr(self, 'last_row', {}).get(\1)", new_content)
        new_content = re.sub(r'row\.get\((["\']atr14_h1["\'])\)', r"getattr(self, 'last_row', {}).get(\1)", new_content)
        new_content = re.sub(r'row\.get\((["\']atr14_h4["\'])\)', r"getattr(self, 'last_row', {}).get(\1)", new_content)
        new_content = re.sub(r'row\.get\((["\']atr_ratio["\'])\)', r"getattr(self, 'last_row', {}).get(\1)", new_content)
        new_content = re.sub(r'row\.get\((["\']session_flag["\'])\)', r"getattr(self, 'last_row', {}).get(\1)", new_content)
        
        if new_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Patched {sym}")
        else:
            print(f"No changes needed for {sym}")

if __name__ == "__main__":
    patch_all()
