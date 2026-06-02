import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

class FleetStateManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER UNIQUE,
                    symbol TEXT,
                    direction TEXT,
                    entry_time DATETIME,
                    exit_time DATETIME,
                    pnl REAL,
                    status TEXT
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_trades_exit_time ON trades(exit_time)')
            conn.commit()

    def record_trade(self, ticket_id, symbol, direction, entry_time, exit_time, pnl, status):
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            # We use COALESCE to keep existing data if we pass None for updates
            conn.execute('''
                INSERT INTO trades (ticket_id, symbol, direction, entry_time, exit_time, pnl, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticket_id) DO UPDATE SET
                    status=excluded.status,
                    exit_time=COALESCE(excluded.exit_time, trades.exit_time),
                    entry_time=COALESCE(excluded.entry_time, trades.entry_time),
                    pnl=COALESCE(excluded.pnl, trades.pnl),
                    direction=COALESCE(excluded.direction, trades.direction),
                    symbol=COALESCE(excluded.symbol, trades.symbol)
            ''', (ticket_id, symbol, direction, entry_time, exit_time, pnl, status))
            conn.commit()

    def get_fleet_metrics(self, symbol):
        now = datetime.now(timezone.utc)
        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            cursor = conn.cursor()
            
            # Trades last hour (symbol)
            cursor.execute("SELECT COUNT(*) FROM trades WHERE symbol = ? AND entry_time >= ?", (symbol, one_hour_ago))
            trades_last_hour = cursor.fetchone()[0] or 0
            
            # Open trades (symbol)
            cursor.execute("SELECT COUNT(*) FROM trades WHERE symbol = ? AND status = 'OPEN'", (symbol,))
            open_trades_per_symbol = cursor.fetchone()[0] or 0
            
            # Open directions
            cursor.execute("SELECT DISTINCT direction FROM trades WHERE symbol = ? AND status = 'OPEN'", (symbol,))
            open_directions = [row[0] for row in cursor.fetchall() if row[0]]

            # Last trade time
            cursor.execute("SELECT MAX(entry_time) FROM trades WHERE symbol = ?", (symbol,))
            last_trade_time_str = cursor.fetchone()[0]
            seconds_since_last_trade = 999999
            if last_trade_time_str:
                last_trade_time = datetime.fromisoformat(last_trade_time_str)
                if last_trade_time.tzinfo is None:
                    last_trade_time = last_trade_time.replace(tzinfo=timezone.utc)
                seconds_since_last_trade = (now - last_trade_time).total_seconds()
            
            # Consecutive losses symbol
            cursor.execute("SELECT pnl FROM trades WHERE symbol = ? AND status = 'CLOSED' ORDER BY exit_time DESC LIMIT 10", (symbol,))
            symbol_history = cursor.fetchall()
            consecutive_losses_symbol = 0
            for row in symbol_history:
                if row[0] is not None and row[0] < 0:
                    consecutive_losses_symbol += 1
                else:
                    break
                    
            # Consecutive losses fleet
            cursor.execute("SELECT pnl FROM trades WHERE status = 'CLOSED' ORDER BY exit_time DESC LIMIT 20")
            fleet_history = cursor.fetchall()
            fleet_loss_streak = 0
            for row in fleet_history:
                if row[0] is not None and row[0] < 0:
                    fleet_loss_streak += 1
                else:
                    break

            # Last loss time
            cursor.execute("SELECT MAX(exit_time) FROM trades WHERE pnl < 0 AND status = 'CLOSED'")
            last_loss_time_str = cursor.fetchone()[0]
            seconds_since_last_loss = 999999
            if last_loss_time_str:
                last_loss_time = datetime.fromisoformat(last_loss_time_str)
                if last_loss_time.tzinfo is None:
                    last_loss_time = last_loss_time.replace(tzinfo=timezone.utc)
                seconds_since_last_loss = (now - last_loss_time).total_seconds()

        return {
            "trades_last_hour": trades_last_hour,
            "open_positions": open_trades_per_symbol,
            "open_directions": open_directions,
            "consecutive_losses_symbol": consecutive_losses_symbol,
            "fleet_loss_streak": fleet_loss_streak,
            "seconds_since_last_trade": seconds_since_last_trade,
            "seconds_since_last_loss": seconds_since_last_loss
        }
