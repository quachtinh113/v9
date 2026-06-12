import json
import pathlib
import sys

# Paths
# Use V9_1 root directory (parent of this script) instead of V9 root
base_dir = pathlib.Path(__file__).resolve().parents[0]  # V9_1 directory
status_path = base_dir / "logs" / "fleet_startup_status.json"
deployed_path = base_dir / "logs" / "deployed_pids.json"


# Load status
with open(status_path, "r", encoding="utf-8") as f:
    status = json.load(f)

EXPECTED_AGENTS = 11  # total agents that should be launched
expected = EXPECTED_AGENTS
actual = len(status)
if actual != EXPECTED_AGENTS:
    print(f"[WARNING] Discovered {actual} agents, expected {EXPECTED_AGENTS}. Validation will FAIL.")
    # keep expected as the required count for final comparison
else:
    # All agents discovered as expected
    pass
alive = sum(1 for s in status if s.get("alive"))
failed_entries = [s for s in status if not s.get("alive")]

# Determine runtime log folder (common prefix of stdout logs)
if status:
    runtime_folder = pathlib.Path(status[0]["stdout_log"]).parent
else:
    runtime_folder = None

# Check if deployed_pids.json was updated (exists and non‑empty)
deployed_updated = deployed_path.is_file() and deployed_path.stat().st_size > 0

# Prepare output
print("---RESULT---")
print(f"Total agents expected = {expected}")
print(f"Total agents alive = {alive}")
print(f"Failed agents = {', '.join([e['bot'] for e in failed_entries]) if failed_entries else 'None'}")
print(f"fleet_startup_status.json path = {status_path}")
print(f"deployed_pids.json updated? {'YES' if deployed_updated else 'NO'}")
print(f"Runtime log folder = {runtime_folder}")
print(f"Any stderr errors? {'YES' if failed_entries else 'NO'}")
# Show supervisor.log tail if available
if runtime_folder:
    sup_log = runtime_folder / "supervisor.log"
    if sup_log.is_file():
        print("--- supervisor.log tail ---")
        try:
            with open(sup_log, "r", encoding="utf-8") as f:
                lines = f.readlines()
                tail = lines[-50:]
                for line in tail:
                    sys.stdout.write(line)
        except Exception as e:
            print(f"Could not read supervisor.log: {e}")
# Determine final status
if expected > 0 and alive == 0:
    final_status = 'LAUNCH_LOOP_FAILED'
else:
    final_status = 'SUPERVISED_STARTUP_PASS' if alive == expected else 'SUPERVISED_STARTUP_FAIL'
print(f"Final status: {final_status}")
if failed_entries:
    for entry in failed_entries:
        err_path = pathlib.Path(entry["stderr_log"])
        print(f"--- {entry['bot']} stderr tail ---")
        try:
            with open(err_path, "r", encoding="utf-8") as ef:
                lines = ef.readlines()
                tail = lines[-20:]
                for line in tail:
                    sys.stdout.write(line)
        except Exception as e:
            print(f"Could not read {err_path}: {e}")
print(f"Final status: {'SUPERVISED_STARTUP_PASS' if alive == expected else 'SUPERVISED_STARTUP_FAIL'}")
