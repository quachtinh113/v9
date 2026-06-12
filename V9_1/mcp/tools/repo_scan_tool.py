import os
import json
from pathlib import Path

def scan_repo(root_path: str) -> dict:
    """Recursively scan the repository for Python files and return a summary.
    Returns a dict with keys:
      - total_files: total number of files scanned
      - python_files: list of relative paths to .py files
      - import_map: mapping of file -> list of import statements (first level only)
    """
    root = Path(root_path)
    python_files = []
    import_map = {}
    total_files = 0
    for path in root.rglob('*'):
        if path.is_file():
            total_files += 1
            if path.suffix == '.py':
                rel = str(path.relative_to(root))
                python_files.append(rel)
                # simple import extraction
                imports = []
                try:
                    with path.open('r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('import ') or line.startswith('from '):
                                imports.append(line)
                except Exception:
                    pass
                import_map[rel] = imports
    return {
        'total_files': total_files,
        'python_files': python_files,
        'import_map': import_map,
    }

if __name__ == '__main__':
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    result = scan_repo(root)
    print(json.dumps(result, indent=2))
