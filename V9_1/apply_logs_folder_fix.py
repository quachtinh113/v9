import os
from pathlib import Path

def patch_pipeline_live(proj_dir):
    pipe_path = proj_dir / "src" / "pipeline_live.py"
    if not pipe_path.exists():
        print(f"File not found: {pipe_path}")
        return False
        
    with open(pipe_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    target_str = '''        # 1. Local Heartbeat
        try:
            import json
            from datetime import datetime, timezone
            hb_entry = {'''
            
    replacement_str = '''        # 1. Local Heartbeat
        try:
            import json
            from datetime import datetime, timezone
            (self.root / "logs").mkdir(parents=True, exist_ok=True)
            hb_entry = {'''

    if target_str not in content:
        if "(self.root / \"logs\").mkdir" in content:
            print(f"Already patched logs folder fix in {proj_dir.name}")
            return True
        print(f"Could not find heartbeat block in {proj_dir.name}/src/pipeline_live.py")
        return False
        
    new_content = content.replace(target_str, replacement_str)
    
    with open(pipe_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    # Also pre-create the logs folder just in case
    (proj_dir / "logs").mkdir(parents=True, exist_ok=True)
    print(f"Patched and pre-created logs folder for {proj_dir.name} successfully.")
    return True

def main():
    projects_dir = Path("c:/Quant Trade/v9/V9_1/projects")
    patched_count = 0
    
    for proj in projects_dir.iterdir():
        if proj.is_dir() and proj.name.startswith("quant_v9_3_1_"):
            if patch_pipeline_live(proj):
                patched_count += 1
                
    print(f"\nLogs Folder Telemetry Fix Patched: {patched_count} pipelines updated.")

if __name__ == "__main__":
    main()
