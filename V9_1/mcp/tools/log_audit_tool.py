import json
import os
from pathlib import Path

def read_audit_logs(log_dir: str) -> dict:
    """Read latest audit log files (NDJSON) and return summary stats.
    Returns dict with keys:
      - total_records
      - recent_records (last 10 entries)
    """
    logs = []
    for path in Path(log_dir).rglob('*.ndjson'):
        try:
            with path.open('r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        logs.append(json.loads(line))
        except Exception:
            continue
    total = len(logs)
    recent = logs[-10:] if total >= 10 else logs
    return {'total_records': total, 'recent_records': recent}

if __name__ == '__main__':
    import sys, pprint
    dir_path = sys.argv[1] if len(sys.argv) > 1 else '.'
    result = read_audit_logs(dir_path)
    pprint.pprint(result)
