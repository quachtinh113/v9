import json
import os
from pathlib import Path

def write_report(report_name: str, data: dict, output_dir: str = "reports") -> str:
    """Write a JSON report to the specified output directory.
    Returns the absolute path of the created report file.
    This tool does not modify any trading logic.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_file = output_path / f"{report_name}.json"
    with report_file.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    return str(report_file)

if __name__ == "__main__":
    import sys, pprint
    if len(sys.argv) < 3:
        print("Usage: report_writer_tool.py <report_name> <json_string>")
        sys.exit(1)
    name = sys.argv[1]
    try:
        payload = json.loads(sys.argv[2])
    except Exception as e:
        print(f"Invalid JSON payload: {e}")
        sys.exit(1)
    path = write_report(name, payload)
    pprint.pprint({"report_path": path})
