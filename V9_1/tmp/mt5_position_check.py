import json, pathlib, datetime
import yaml
import MetaTrader5 as mt5

# Paths
ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "projects" / "quant_v9_3_1_btcusd" / "config" / "mt5_demo.yaml"
LOG_PATH = ROOT_DIR / "logs" / "mt5_position_check.json"

# Load MT5 credentials safely (no password printed)
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
        mt5_cfg = cfg.get("mt5", {})
        login = mt5_cfg.get("login")
        password = mt5_cfg.get("password")
        server = mt5_cfg.get("server")
except Exception as e:
    raise RuntimeError(f"Failed to load MT5 config: {e}")

# Initialize MT5 terminal (uses default path if configured in system)
if not mt5.initialize():
    raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

# Login with credentials from config (do not log the password)
if not mt5.login(login=login, password=password, server=server):
    raise RuntimeError(f"MT5 login failed: {mt5.last_error()}")

# Gather account info
acct = mt5.account_info()
account_info = {
    "login": acct.login,
    "server": acct.server,
    "trade_mode": acct.trade_mode,
    "balance": acct.balance,
    "equity": acct.equity,
    "margin": acct.margin,
    "free_margin": acct.margin_free,
}

# Positions
positions = mt5.positions_get()
positions_list = []
btc_positions = 0
total_lots = 0.0
total_floating = 0.0
if positions:
    for p in positions:
        if p.symbol.upper() == "BTCUSD":
            btc_positions += 1
        holding_seconds = (datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(p.time)).total_seconds()
        entry = {
            "symbol": p.symbol,
            "ticket": p.ticket,
            "type": p.type,
            "lots": p.volume,
            "entry_price": p.price_open,
            "current_price": p.price_current,
            "sl": p.sl,
            "tp": p.tp,
            "floating_pnl": p.profit,
            "open_time": datetime.datetime.utcfromtimestamp(p.time).isoformat() + "Z",
            "holding_seconds": holding_seconds,
            "magic": p.magic,
            "comment": p.comment,
        }
        positions_list.append(entry)
        total_lots += p.volume
        total_floating += p.profit

# History deals (not used in summary but collected for completeness)
history = mt5.history_deals_get()
# Convert to simple list of dicts (optional, could be omitted for brevity)
history_list = []
if history:
    for d in history:
        history_list.append({
            "ticket": d.ticket,
            "symbol": d.symbol,
            "volume": d.volume,
            "price": d.price,
            "profit": d.profit,
            "type": d.type,
            "time": datetime.datetime.utcfromtimestamp(d.time).isoformat() + "Z",
        })

summary = {
    "positions_total": len(positions) if positions else 0,
    "btcusd_positions_count": btc_positions,
    "total_lots": total_lots,
    "total_floating_pnl": total_floating,
}

output = {
    "account": account_info,
    "positions": positions_list,
    "history_deals": history_list,
    "summary": summary,
}

# Ensure logs directory exists
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(LOG_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print(f"MT5 position check written to {LOG_PATH}")
