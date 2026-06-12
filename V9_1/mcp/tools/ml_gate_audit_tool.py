import json
from pathlib import Path

def audit_ml_gatekeeper(root_path: str) -> dict:
    """Read the ML gatekeeper configuration and recent audit logs.
    Returns a dict with:
      - contract_path
      - contract_exists (bool)
      - contract_content (first 5 lines or None)
      - recent_audit_records (last 5 entries from live_pipeline_audit.ndjson)
    This tool is read‑only and does not affect trading.
    """
    contract_path = Path(root_path) / "configs" / "ml_model_contract.yaml"
    contract_exists = contract_path.is_file()
    contract_content = []
    if contract_exists:
        try:
            with contract_path.open('r', encoding='utf-8') as f:
                for _ in range(5):
                    line = f.readline()
                    if not line:
                        break
                    contract_content.append(line.strip())
        except Exception:
            contract_content = []
    # Read recent audit logs
    audit_path = Path(root_path) / "logs" / "live_pipeline_audit.ndjson"
    recent_audit = []
    if audit_path.is_file():
        try:
            with audit_path.open('r', encoding='utf-8') as f:
                lines = f.readlines()[-5:]
                for line in lines:
                    if line.strip():
                        recent_audit.append(json.loads(line))
        except Exception:
            recent_audit = []
    return {
        "contract_path": str(contract_path),
        "contract_exists": contract_exists,
        "contract_content": contract_content,
        "recent_audit_records": recent_audit,
    }

if __name__ == "__main__":
    import sys, pprint
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    pprint.pprint(audit_ml_gatekeeper(root))
