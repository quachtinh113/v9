import time, json, datetime, os, psutil, pathlib

HEARTBEAT_TIMEOUT_SECONDS = 45  # seconds

LOG_PATH = pathlib.Path(__file__).parents[2] / "logs" / "runtime_health.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

HEARTBEAT_PATH = pathlib.Path(__file__).parents[2] / "logs" / "heartbeat.jsonl"

def heartbeat_ok():
    """Return True if a heartbeat entry was written within the timeout."""
    try:
        if not HEARTBEAT_PATH.exists():
            return False
        # Read the last line efficiently
        with open(HEARTBEAT_PATH, "rb") as f:
            f.seek(-2, os.SEEK_END)
            while f.read(1) != b'\n':
                f.seek(-2, os.SEEK_CUR)
            last_line = f.readline().decode("utf-8")
        
        last = json.loads(last_line)
        ts = datetime.datetime.fromisoformat(last["timestamp"].replace("Z", "+00:00"))
        
        # Ensure UTC comparison
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=datetime.timezone.utc)
        
        age = (datetime.datetime.now(datetime.timezone.utc) - ts).total_seconds()
        return age <= HEARTBEAT_TIMEOUT_SECONDS
    except (OSError, (IndexError, json.JSONDecodeError, KeyError, ValueError)):
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
