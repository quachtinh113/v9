import pytest
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from src.core.fleet_state import FleetStateManager

@pytest.fixture
def temp_db(tmp_path):
    return tmp_path / "risk_state.db"

def test_fleet_state_concurrency(temp_db):
    # Test that multiple threads can write to the sqlite database without "database is locked" errors
    # due to our timeout=10 and connection retry mechanism.
    state = FleetStateManager(temp_db)
    
    def write_worker(start_id, symbol):
        local_state = FleetStateManager(temp_db)
        now = datetime.now(timezone.utc).isoformat()
        for i in range(10):
            ticket = start_id + i
            local_state.record_trade(ticket, symbol, "long", now, None, 0, "OPEN")
            local_state.record_trade(ticket, symbol, "long", now, now, -10.0, "CLOSED")

    threads = []
    threads.append(threading.Thread(target=write_worker, args=(100, "BTCUSD")))
    threads.append(threading.Thread(target=write_worker, args=(200, "ETHUSD")))
    threads.append(threading.Thread(target=write_worker, args=(300, "SOLUSD")))
    
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    metrics = state.get_fleet_metrics("BTCUSD")
    
    # We wrote 10 negative PNLs for BTCUSD
    assert metrics["consecutive_losses_symbol"] == 10
    
    # We wrote 30 negative PNLs across fleet
    assert metrics["fleet_loss_streak"] >= 20 # capped by LIMIT 20 in query

def test_fleet_metrics_query(temp_db):
    state = FleetStateManager(temp_db)
    now = datetime.now(timezone.utc)
    
    # 2 hours ago
    past = (now - timedelta(hours=2)).isoformat()
    # 30 mins ago
    recent = (now - timedelta(minutes=30)).isoformat()
    
    # 1. Trade > 1 hour ago
    state.record_trade(1, "USDJPY", "long", past, past, 50, "CLOSED")
    # 2. Trade < 1 hour ago (recent)
    state.record_trade(2, "USDJPY", "short", recent, recent, -10, "CLOSED")
    # 3. Open trade
    state.record_trade(3, "USDJPY", "long", recent, None, 0, "OPEN")
    
    metrics = state.get_fleet_metrics("USDJPY")
    
    assert metrics["trades_last_hour"] == 2 # trades 2 and 3 are recent
    assert metrics["open_positions"] == 1
    assert "long" in metrics["open_directions"]
    assert metrics["consecutive_losses_symbol"] == 1 # 1 loss
    assert metrics["fleet_loss_streak"] == 1
