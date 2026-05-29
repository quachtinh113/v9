import time, json, datetime, os, psutil, pathlib

LOG_PATH = pathlib.Path(__file__).parents[2] / "logs" / "runtime_health.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

HEARTBEAT_PATH = pathlib.Path(__file__).parents[2] / "logs" / "heartbeat.jsonl"

def heartbeat_ok():
    """Return True if a heartbeat entry was written within the last 20 seconds."""
    try:
        if not HEARTBEAT_PATH.exists():
            return False
        with open(HEARTBEAT_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if not lines:
                return False
            last = json.loads(lines[-1])
            ts = datetime.datetime.fromisoformat(last["timestamp"].replace("Z", "+00:00"))
            return (datetime.datetime.utcnow() - ts).total_seconds() <= 20
    except Exception:
        return False

def log_health():
    proc = psutil.Process(os.getpid())
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "runtime_mode": "PAPER",
        "memory_mb": proc.memory_info().rss / (1024 * 1024),
        "cpu_percent": proc.cpu_percent(interval=1.0),
        "heartbeat_ok": heartbeat_ok(),
        "thread_count": proc.num_threads(),
        "process_count": len(psutil.pids()),
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

if __name__ == "__main__":
    while True:
        try:
            log_health()
        except Exception as e:
            # In case logging fails, we still want the monitor to keep running.
            pass
        time.sleep(30)
