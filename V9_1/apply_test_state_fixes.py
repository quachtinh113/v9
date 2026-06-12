import os
import re
import shutil
from datetime import datetime
from pathlib import Path

root_dir = Path(r"c:\Quant Trade\v9\V9_1")
logs_dir = root_dir / "logs"
archive_dir = logs_dir / "archive"
db_path = logs_dir / "risk_state.db"

# 1. Backup and clear DB
archive_dir.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
backup_path = archive_dir / f"risk_state_mock_failed_{timestamp}.db"

if db_path.exists():
    shutil.copy2(db_path, backup_path)
    db_path.unlink()
    print(f"Backed up and cleared risk_state.db to {backup_path}")

# 2. Update pipeline_live.py across all projects
projects_dir = root_dir / "projects"
for proj in os.listdir(projects_dir):
    proj_path = projects_dir / proj
    if proj_path.is_dir():
        pl_path = proj_path / "src" / "pipeline_live.py"
        if pl_path.exists():
            with open(pl_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace hardcoded DB path with ENV var
            # Look for: self.fleet_state = FleetStateManager(self.root.parents[1] / "logs" / "risk_state.db")
            new_init = """
        db_env = os.environ.get("RISK_STATE_DB_PATH")
        if db_env:
            db_path_resolved = Path(db_env)
        else:
            db_path_resolved = self.root.parents[1] / "logs" / "risk_state.db"
        self.fleet_state = FleetStateManager(db_path_resolved)
"""
            # Replace only if not already using os.environ
            if 'os.environ.get("RISK_STATE_DB_PATH")' not in content:
                content = re.sub(r'self\.fleet_state = FleetStateManager\(self\.root\.parents\[1\] / "logs" / "risk_state\.db"\)', new_init.strip(), content)
                
            with open(pl_path, 'w', encoding='utf-8') as f:
                f.write(content)

# 3. Update dry_run_validation.py
dry_run_path = root_dir / "dry_run_validation.py"
if dry_run_path.exists():
    with open(dry_run_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if 'os.environ["RISK_STATE_DB_PATH"]' not in content:
        # inject at the top right after imports
        injection = '\nimport os\nos.environ["RISK_STATE_DB_PATH"] = str(Path("c:/Quant Trade/v9/V9_1/logs/test_risk_state.db").resolve())\n'
        content = re.sub(r'(from pathlib import Path\n)', r'\1' + injection, content, count=1)
        
        with open(dry_run_path, 'w', encoding='utf-8') as f:
            f.write(content)

print(f"Patching complete. Backup path: {backup_path}")
