import os
import sys
import py_compile
import json
from pathlib import Path

def is_production_critical(file_path: Path) -> bool:
    # Heuristic: files in src/ (excluding tests), not in utils/tmp/scripts/release
    parts = file_path.parts
    if "src" in parts and "tests" not in parts:
        # Exclude utility subfolders under src like utils, but keep core modules
        if any(p in ["utils", "tmp", "scripts", "release"] for p in parts):
            return False
        return True
    # Top‑level runnable scripts under project root (e.g., run_and_monitor_fleet.py)
    if file_path.name.endswith('.py') and file_path.parent == Path('.').resolve():
        return True
    return False

def audit_repo(root: Path):
    failures = []
    for py_file in root.rglob('*.py'):
        try:
            py_compile.compile(str(py_file), doraise=True)
        except Exception as e:
            # e is usually SyntaxError or py_compile.PyCompileError with details
            err_msg = str(e)
            line_no = getattr(e, 'lineno', None)
            failures.append({
                "filename": py_file.name,
                "path": str(py_file),
                "error": err_msg,
                "line": line_no,
                "production_critical": is_production_critical(py_file)
            })
    return failures

if __name__ == '__main__':
    repo_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
    result = audit_repo(repo_root)
    print(json.dumps(result, indent=2))
