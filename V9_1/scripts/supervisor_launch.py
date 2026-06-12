import os
import sys
import json
import subprocess
import datetime
import time
import traceback
from pathlib import Path

# Configuration
ROOT_DIR = Path(__file__).resolve().parents[1] / "projects"
MODE = "live"
ENV_VARS = {
    "ALLOW_REAL_TRADING": "true",
    "HUMAN_LIVE_CONFIRM": "YES_I_ACCEPT_LIVE_RISK",
    "QUANT_RUNTIME_MODE": "live",
    "LIVE_DEMO_ALLOWED": "true",
    "PYTHONPATH": ".",
}

# List of bots (name -> project folder name)
BOTS = [
    "gbpusd",
    "eurusd",
    "usdjpy",
    "audusd",
    "usdcad",
    "usdchf",
    "us30",
    "us100",
    "us500",
    "xauusd",
    "btcusd",
]

def main():
    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    runtime_dir = Path(__file__).resolve().parents[1] / "logs" / "runtime" / run_id
    runtime_dir.mkdir(parents=True, exist_ok=True)
    # Supervisor self‑log
    supervisor_log_path = runtime_dir / "supervisor.log"
    def slog(msg):
        timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
        with open(supervisor_log_path, "a", encoding="utf-8") as sup_log:
            sup_log.write(f"{timestamp} - {msg}\n")
    slog("Supervisor started")

    status_list = []
    deployed_pids = {}
    discovered_agents = 0
    launch_attempts = 0
    launch_success = 0

    for bot in BOTS:
        project_path = ROOT_DIR / f"quant_v9_3_1_{bot}"
        if not project_path.is_dir():
            slog(f"[WARN] Project directory for {bot} not found: {project_path}")
            continue
        discovered_agents += 1
        slog(f"DISCOVERED_AGENT: {bot} -> {project_path}")

        # Prepare env for this bot
        env = os.environ.copy()
        env.update(ENV_VARS)

        # Log file paths
        stdout_log = runtime_dir / f"stdout_{bot.upper()}.log"
        stderr_log = runtime_dir / f"stderr_{bot.upper()}.log"

        cmd = [sys.executable, "-m", "src.main", "--mode", MODE]
        start_ts = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
        # Verify src/main exists
        src_main = project_path / "src" / "main.py"
        src_exists = src_main.is_file()
        slog(f"EXISTS_SRC_MAIN ({bot}): {src_exists} at {src_main}")
        slog(f"LAUNCH_COMMAND ({bot}): {' '.join(cmd)}")
        slog(f"CWD ({bot}): {project_path}")
        slog(f"PYTHON_EXE ({bot}): {sys.executable}")

        launch_attempts += 1
        try:
            with open(stdout_log, "w", encoding="utf-8") as out, open(stderr_log, "w", encoding="utf-8") as err:
                out.write(f"Startup Timestamp: {start_ts}\nCommand: {' '.join(cmd)}\nWorkingDir: {project_path}\n\n")
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(project_path),
                    env=env,
                    stdout=out,
                    stderr=err,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
                pid = proc.pid
                out.write(f"PID: {pid}\n")
                out.flush()
            # Wait 10 seconds then verify
            time.sleep(10)
            alive = proc.poll() is None
            if alive:
                launch_success += 1
                deployed_pids[bot.upper()] = pid
            status = "STARTED" if alive else "STARTUP_FAILED"
            with open(stdout_log, "a", encoding="utf-8") as out:
                out.write(f"Status after 10s: {status}\n")
        except Exception as e:
            slog(f"LAUNCH_EXCEPTION ({bot}): {e}\n{traceback.format_exc()}")
            alive = False
            status = "LAUNCH_EXCEPTION"
            pid = None
        # Record status entry
        status_entry = {
            "bot": bot.upper(),
            "pid": pid,
            "alive": alive,
            "status": status,
            "stdout_log": str(stdout_log),
            "stderr_log": str(stderr_log),
            "startup_timestamp": start_ts,
        }
        status_list.append(status_entry)
        slog(f"RESULT ({bot}): PID={pid} alive={alive} status={status}")
        print(f"[INFO] {bot.upper()} -> PID {pid}, alive={alive}")

    # Write fleet startup status json
    fleet_status_path = Path(__file__).resolve().parents[1] / "logs" / "fleet_startup_status.json"
    with open(fleet_status_path, "w", encoding="utf-8") as f:
        json.dump(status_list, f, indent=2)
    # Write deployed_pids.json (only alive)
    deployed_path = Path(__file__).resolve().parents[1] / "logs" / "deployed_pids.json"
    with open(deployed_path, "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in deployed_pids.items()}, f, indent=2)
    slog(f"[DONE] Fleet startup status written to {fleet_status_path}")
    slog(f"[DONE] Deployed PIDs written to {deployed_path}")
    slog(f"Counters: discovered={discovered_agents} attempts={launch_attempts} successes={launch_success}")
    print(f"[DONE] Fleet startup status written to {fleet_status_path}")
    print(f"[DONE] Deployed PIDs written to {deployed_path}")

if __name__ == "__main__":
    main()
