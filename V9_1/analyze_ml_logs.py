import os
import json
import glob
from pathlib import Path

def main():
    projects_dir = Path("c:/Quant Trade/v9/V9_1/projects")
    print("Scanning log files across projects...")
    
    for proj in projects_dir.iterdir():
        if proj.is_dir() and proj.name.startswith("quant_v9_3_1_"):
            logs_dir = proj / "logs"
            if logs_dir.exists():
                files = list(logs_dir.glob("*"))
                if files:
                    print(f"\nProject: {proj.name}")
                    for f in files:
                        print(f"  - {f.name} ({f.stat().st_size} bytes)")
                        # Read first line if it's a file
                        if f.is_file() and f.stat().st_size > 0:
                            try:
                                with open(f, "r", encoding="utf-8") as file:
                                    first_line = file.readline().strip()
                                    print(f"    First line: {first_line[:150]}")
                            except Exception as e:
                                print(f"    Error reading: {e}")

if __name__ == "__main__":
    main()
