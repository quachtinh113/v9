import os
import sys
import json
import csv
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Setup project import paths
V9_1_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = V9_1_DIR / "projects"
sys.path.insert(0, str(PROJECTS_DIR / "quant_v9_3_1_us30"))

from src.core.microstructure import MicrostructureDetector
from src.core.regime_engine import detect_regime

SYMBOLS = ["GBPUSD", "EURUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "US30", "US100", "US500", "XAUUSD", "BTCUSD"]

# Base Transaction Costs by symbol (in basis points)
BASE_COSTS = {
    "GBPUSD": {"spread": 1.0, "slippage": 0.5},
    "EURUSD": {"spread": 1.0, "slippage": 0.5},
    "USDJPY": {"spread": 1.2, "slippage": 0.6},
    "AUDUSD": {"spread": 1.0, "slippage": 0.5},
    "USDCAD": {"spread": 1.0, "slippage": 0.5},
    "USDCHF": {"spread": 1.0, "slippage": 0.5},
    "US30":   {"spread": 1.5, "slippage": 1.0},
    "US100":  {"spread": 1.5, "slippage": 1.0},
    "US500":  {"spread": 1.5, "slippage": 1.0},
    "XAUUSD": {"spread": 2.0, "slippage": 1.0},
    "BTCUSD": {"spread": 2.5, "slippage": 1.5},
}

def load_symbol_data(symbol: str) -> pd.DataFrame:
    """Find and load the M1 CSV for a given symbol."""
    proj_dir = PROJECTS_DIR / f"quant_v9_3_1_{symbol.lower()}"
    raw_dir = proj_dir / "data" / "raw"
    
    if not raw_dir.exists():
        return None
        
    csv_files = list(raw_dir.glob("*.csv"))
    if not csv_files:
        return None
        
    df = pd.read_csv(csv_files[0])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df

def simulate_validation_trade(
    df: pd.DataFrame, 
    trigger_idx: int, 
    direction: str, 
    base_spread: float, 
    base_slippage: float,
    tp_mult: float = 1.5, 
    sl_mult: float = 1.0, 
    max_bars: int = 60,
    cost_multiplier: float = 1.0
) -> Dict[str, Any]:
    """
    Simulates a trade with regime-sensitive latency delay and dynamic transaction costs.
    Returns:
        Dict containing gross_return_pct, net_return_pct, cost_bps, entry_delay, and exit_reason.
    """
    if trigger_idx >= len(df) - 1:
        return {"gross_return_pct": 0.0, "net_return_pct": 0.0, "cost_bps": 0.0, "entry_delay": 0, "exit_reason": "End of Data", "regime": "sideway", "session": "Other"}
        
    # 1. Regime-sensitive latency delay
    # Detect regime at trigger bar
    row_dict = df.loc[trigger_idx].to_dict()
    try:
        regime_state = detect_regime(row_dict, trend_adx_min=20)
    except Exception as e:
        print(f"[DEBUG CRASH] trigger_idx={trigger_idx}, type(row_dict)={type(row_dict)}, row_dict={row_dict}")
        print(f"[DEBUG CRASH] df type={type(df)}, df len={len(df)}")
        raise e
    regime = regime_state.regime
    
    if regime == "shock":
        latency_bars = 3
    elif regime in ("trend", "transition"):
        latency_bars = 1
    else:
        latency_bars = 0 # Low volatility / sideway / off_session
        
    entry_idx = min(trigger_idx + latency_bars, len(df) - 1)
    if entry_idx >= len(df) - 1:
        return {"gross_return_pct": 0.0, "net_return_pct": 0.0, "cost_bps": 0.0, "entry_delay": latency_bars, "exit_reason": "End of Data", "regime": regime, "session": df.loc[trigger_idx, "session_type"]}
        
    # 2. Setup SL and TP relative to structural price at trigger bar
    trigger_price = df.loc[trigger_idx, "close"]
    atr = df.loc[trigger_idx, "atr"]
    if atr <= 0:
        atr = 0.001
        
    if direction == "long":
        tp = trigger_price + tp_mult * atr
        sl = trigger_price - sl_mult * atr
    else:
        tp = trigger_price - tp_mult * atr
        sl = trigger_price + sl_mult * atr
        
    # Execution entry price
    entry_price = df.loc[entry_idx, "close"]
    
    # 3. Walk-forward exit tracking
    exit_price = None
    exit_reason = "Timeout"
    
    for offset in range(1, max_bars + 1):
        idx = entry_idx + offset
        if idx >= len(df):
            exit_price = df.loc[len(df)-1, "close"]
            exit_reason = "Timeout"
            break
            
        high = df.loc[idx, "high"]
        low = df.loc[idx, "low"]
        close = df.loc[idx, "close"]
        
        if direction == "long":
            if low <= sl:
                exit_price = sl
                exit_reason = "SL"
                break
            if high >= tp:
                exit_price = tp
                exit_reason = "TP"
                break
        else: # short
            if high >= sl:
                exit_price = sl
                exit_reason = "SL"
                break
            if low <= tp:
                exit_price = tp
                exit_reason = "TP"
                break
                
    if exit_price is None:
        # Exit at timeout bar
        exit_idx = min(entry_idx + max_bars, len(df) - 1)
        exit_price = df.loc[exit_idx, "close"]
        exit_reason = "Timeout"
        
    # 4. Gross Return Calculation
    gross_return = (exit_price - entry_price) / entry_price if direction == "long" else (entry_price - exit_price) / entry_price
    gross_return_pct = gross_return * 100.0
    
    # 5. Dynamic Transaction Costs
    # Scale spread and slippage by volatility (atr_ratio) and session
    atr_ratio = df.loc[trigger_idx, "atr_ratio"]
    session = df.loc[trigger_idx, "session_type"]
    
    spread_scale = 1.0
    slippage_scale = 1.0
    
    # Volatility / News scaling
    if atr_ratio > 1.5:
        spread_scale *= 1.5
        slippage_scale *= 2.0
    if regime == "shock":
        slippage_scale *= 3.0
        
    # Out of session / Lunch scaling (thin liquidity)
    if session in ("Lunch Session", "Other"):
        spread_scale *= 1.5
        
    spread_cost = base_spread * spread_scale
    slippage_cost = base_slippage * slippage_scale
    
    total_cost_bps = (spread_cost + slippage_cost) * cost_multiplier
    
    # 6. Net Return Calculation
    net_return_pct = gross_return_pct - (total_cost_bps / 100.0) # BPS to Percent
    
    return {
        "gross_return_pct": float(gross_return_pct),
        "net_return_pct": float(net_return_pct),
        "cost_bps": float(total_cost_bps),
        "entry_delay": latency_bars,
        "exit_reason": exit_reason,
        "regime": regime,
        "session": session
    }

def run_monte_carlo(net_returns: np.ndarray, num_bootstrap: int = 1000) -> Dict[str, float]:
    """Runs bootstrap resampling on trade returns to measure edge stability."""
    if len(net_returns) == 0:
        return {"5th_pnl": 0.0, "mean_pnl": 0.0, "95th_pnl": 0.0, "pf_5th": 0.0, "sharpe_5th": 0.0}
        
    expectancies = []
    pfs = []
    sharpes = []
    
    for _ in range(num_bootstrap):
        sample = np.random.choice(net_returns, size=len(net_returns), replace=True)
        # Expectancy
        expectancies.append(np.mean(sample))
        # Profit Factor
        gains = sample[sample > 0]
        losses = sample[sample < 0]
        pf = np.sum(gains) / abs(np.sum(losses)) if len(losses) > 0 and np.sum(losses) != 0 else 999.0
        pfs.append(pf)
        # Sharpe
        std = np.std(sample)
        sharpe = (np.mean(sample) / std) if std > 0 else 0.0
        sharpes.append(sharpe)
        
    return {
        "5th_pnl": float(np.percentile(expectancies, 5)),
        "mean_pnl": float(np.mean(expectancies)),
        "95th_pnl": float(np.percentile(expectancies, 95)),
        "pf_5th": float(np.percentile(pfs, 5)),
        "sharpe_5th": float(np.percentile(sharpes, 5))
    }

def validate_setup_for_symbol(
    symbol: str, 
    df: pd.DataFrame, 
    setup_name: str, 
    triggers_df: pd.Series, 
    directions: pd.Series, 
    base_spread: float, 
    base_slippage: float
) -> Dict[str, Any]:
    """Runs full validation pipeline for a specific setup on a symbol."""
    trigger_indices = df[triggers_df].index.tolist()
    
    trades = []
    for idx in trigger_indices:
        direc = directions.loc[idx]
        if direc not in ("long", "short"):
            continue
        trade = simulate_validation_trade(df, idx, direc, base_spread, base_slippage)
        trades.append(trade)
        
    sample_size = len(trades)
    if sample_size < 100:
        return {"status": "REJECTED", "reason": f"Low sample size ({sample_size} < 100)"}
        
    net_returns = np.array([t["net_return_pct"] for t in trades])
    gross_returns = np.array([t["gross_return_pct"] for t in trades])
    
    # Calculate stats
    gains = net_returns[net_returns > 0]
    losses = net_returns[net_returns < 0]
    pf = np.sum(gains) / abs(np.sum(losses)) if len(losses) > 0 and np.sum(losses) != 0 else 999.0
    expectancy = np.mean(net_returns)
    std = np.std(net_returns)
    sharpe = (expectancy / std) if std > 0 else 0.0
    
    # 1. Monte Carlo Robustness
    mc_results = run_monte_carlo(net_returns)
    
    # 2. Rejection Logic Check
    # Reject if Monte Carlo 5th percentile expectancy is negative or Sharpe/PF is unstable
    is_unstable = mc_results["5th_pnl"] < 0 or mc_results["pf_5th"] < 1.0
    is_realism_sensitive = expectancy <= 0 or pf < 1.1
    
    status = "ACCEPTED"
    reason = "Passes all robustness filters"
    
    if is_unstable:
        status = "REJECTED"
        reason = f"Unstable in Monte Carlo (5th percentile expectancy: {mc_results['5th_pnl']:.3f}%)"
    elif is_realism_sensitive:
        status = "REJECTED"
        reason = f"Fragile to transaction costs (Net Exp: {expectancy:.3f}%, PF: {pf:.2f})"
        
    # 3. Cost Fragility Sweep
    cost_sweeps = []
    fragility_threshold = 4.0
    for mult in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]:
        sweep_trades = [simulate_validation_trade(df, idx, directions.loc[idx], base_spread, base_slippage, cost_multiplier=mult) for idx in trigger_indices]
        sweep_returns = np.array([t["net_return_pct"] for t in sweep_trades])
        sweep_exp = np.mean(sweep_returns)
        sweep_gains = sweep_returns[sweep_returns > 0]
        sweep_losses = sweep_returns[sweep_returns < 0]
        sweep_pf = np.sum(sweep_gains) / abs(np.sum(sweep_losses)) if len(sweep_losses) > 0 and np.sum(sweep_losses) != 0 else 999.0
        
        cost_sweeps.append({"multiplier": mult, "expectancy": float(sweep_exp), "pf": float(sweep_pf)})
        if (sweep_exp < 0 or sweep_pf < 1.0) and mult < fragility_threshold:
            fragility_threshold = mult
            
    # 4. Regime Fragility Sweep
    regime_fragility = {}
    for r in ["trend", "sideway", "transition", "shock"]:
        r_trades = [t for t in trades if t["regime"] == r]
        if len(r_trades) > 0:
            r_returns = np.array([t["net_return_pct"] for t in r_trades])
            regime_fragility[r] = {
                "count": len(r_trades),
                "expectancy": float(np.mean(r_returns)),
                "winrate": float(np.mean(r_returns > 0))
            }
        else:
            regime_fragility[r] = {"count": 0, "expectancy": 0.0, "winrate": 0.0}
            
    # 5. Session Persistence Sweep
    session_persistence = {}
    for s in ["London Open", "NY Open", "Lunch Session", "Pre-News", "Post-News", "Other"]:
        s_trades = [t for t in trades if t["session"] == s]
        if len(s_trades) > 0:
            s_returns = np.array([t["net_return_pct"] for t in s_trades])
            session_persistence[s] = {
                "count": len(s_trades),
                "expectancy": float(np.mean(s_returns)),
                "winrate": float(np.mean(s_returns > 0))
            }
        else:
            session_persistence[s] = {"count": 0, "expectancy": 0.0, "winrate": 0.0}
            
    return {
        "status": status,
        "reason": reason,
        "sample_size": sample_size,
        "expectancy_pct": float(expectancy),
        "pf": float(pf),
        "sharpe": float(sharpe),
        "monte_carlo": mc_results,
        "cost_fragility": cost_sweeps,
        "fragility_threshold": float(fragility_threshold),
        "regime_fragility": regime_fragility,
        "session_persistence": session_persistence
    }

def run_edge_validation_for_symbol(symbol: str) -> dict:
    df = load_symbol_data(symbol)
    if df is None or len(df) < 500:
        return None
        
    print(f"Running Microstructure Detection for {symbol}...")
    detector = MicrostructureDetector(df)
    res_df = detector.run_detection()
    
    # Setup triggers
    # 1. False Breakout Reversals
    fb_long = res_df["liquidity_pattern"] == "Downside False Breakout"
    fb_short = res_df["liquidity_pattern"] == "Upside False Breakout"
    fb_trigger = fb_long | fb_short
    fb_directions = pd.Series(np.where(fb_long, "long", np.where(fb_short, "short", "none")), index=res_df.index)
    
    # 2. Liquidity Sweeps
    sweep_long = (res_df["liquidity_pattern"] == "Downside Sweep") | (res_df["liquidity_pattern"] == "Downside Stop Hunt")
    sweep_short = (res_df["liquidity_pattern"] == "Upside Sweep") | (res_df["liquidity_pattern"] == "Upside Stop Hunt")
    sweep_trigger = sweep_long | sweep_short
    sweep_directions = pd.Series(np.where(sweep_long, "long", np.where(sweep_short, "short", "none")), index=res_df.index)
    
    # 3. Stop Hunts
    sh_long = res_df["liquidity_pattern"] == "Downside Stop Hunt"
    sh_short = res_df["liquidity_pattern"] == "Upside Stop Hunt"
    sh_trigger = sh_long | sh_short
    sh_directions = pd.Series(np.where(sh_long, "long", np.where(sh_short, "short", "none")), index=res_df.index)
    
    # 4. Squeeze Expansion
    is_squeeze = (res_df["volatility_state"] == "Squeeze").astype(int)
    prev_squeeze = is_squeeze.shift(1).rolling(5).max().fillna(0).astype(bool)
    sq_expansion = (res_df["volatility_state"] == "Expansion") & prev_squeeze
    sq_directions = pd.Series(np.where(res_df["close"] > res_df["bb_mid"], "long", "short"), index=res_df.index)
    
    # 5. London Judo Reversal
    # Downside sweep/sh/fb during London Open is buy, Upside sweep/sh/fb is sell
    judo_trigger = (res_df["session_type"] == "London Open") & (res_df["liquidity_pattern"] != "None")
    judo_long = judo_trigger & res_df["liquidity_pattern"].str.contains("Downside")
    judo_directions = pd.Series(np.where(judo_long, "long", "short"), index=res_df.index)
    
    # 6. Rollover Reversal
    # Time-window 23:30-00:30 (labeled as 23h30-00h30 in previous step)
    # Let's map timestamp hour/minute directly to avoid missing labels
    res_df["dt"] = pd.to_datetime(res_df["timestamp"])
    res_df["hour"] = res_df["dt"].dt.hour
    res_df["minute"] = res_df["dt"].dt.minute
    res_df["time_val"] = res_df["hour"] * 60 + res_df["minute"]
    in_rollover = (res_df["time_val"] >= 23*60 + 30) | (res_df["time_val"] <= 30)
    rollover_trigger = in_rollover & (res_df["liquidity_pattern"] != "None")
    roll_long = rollover_trigger & res_df["liquidity_pattern"].str.contains("Downside")
    roll_directions = pd.Series(np.where(roll_long, "long", "short"), index=res_df.index)
    
    costs = BASE_COSTS[symbol]
    
    setups = {
        "false_breakout_reversals": (fb_trigger, fb_directions),
        "liquidity_sweeps": (sweep_trigger, sweep_directions),
        "stop_hunts": (sh_trigger, sh_directions),
        "atr_squeeze_expansion": (sq_expansion, sq_directions),
        "london_judo_reversal": (judo_trigger, judo_directions),
        "rollover_reversal": (rollover_trigger, roll_directions),
    }
    
    validation_results = {}
    
    for name, (trigger_series, dir_series) in setups.items():
        print(f"  Validating setup: {name} for {symbol}...")
        res = validate_setup_for_symbol(symbol, res_df, name, trigger_series, dir_series, costs["spread"], costs["slippage"])
        validation_results[name] = res
        
    # Save per-symbol data
    out_dir = V9_1_DIR / "reports" / "institutional_edge_validation" / symbol
    out_dir.mkdir(parents=True, exist_ok=True)
    
    with open(out_dir / f"{symbol}_validation.json", 'w', encoding='utf-8') as f:
        json.dump(validation_results, f, indent=4)
        
    # Generate HTML dashboard for this symbol
    generate_symbol_validation_report(symbol, validation_results, out_dir / f"{symbol}_validation_report.html")
    
    return validation_results

def generate_symbol_validation_report(symbol: str, results: dict, file_path: Path):
    """Generates a premium visual validation HTML report for a symbol."""
    card_html = ""
    tables_html = ""
    
    for setup, data in results.items():
        status_class = "APPROVED" if data["status"] == "ACCEPTED" else "DISABLED"
        exp_val = data.get("expectancy_pct", 0.0)
        pf_val = data.get("pf", 0.0)
        
        card_html += f"""
        <div class="setup-card">
            <div class="card-header">
                <span class="setup-name">{setup.replace('_', ' ').upper()}</span>
                <span class="badge {status_class}">{data['status']}</span>
            </div>
            <div class="card-desc">"{data.get('reason', '')}"</div>
            <div class="card-stats">
                <div class="stat-row"><span>Sample Size:</span> <b>{data.get('sample_size', 0)}</b></div>
                <div class="stat-row"><span>Net Expectancy:</span> <b style="color: #38bdf8;">{exp_val:.3f}%</b></div>
                <div class="stat-row"><span>Profit Factor:</span> <b>{pf_val:.2f}</b></div>
                <div class="stat-row"><span>Monte Carlo 5th:</span> <b style="color: #f43f5e;">{data.get('monte_carlo', {}).get('5th_pnl', 0.0):.3f}%</b></div>
                <div class="stat-row"><span>Fragility Threshold:</span> <b style="color: #fbbf24;">{data.get('fragility_threshold', 0.0):.1f}x cost</b></div>
            </div>
        </div>
        """
        
        if data["status"] == "ACCEPTED":
            # Add detailed sweeps
            regime_rows = ""
            for r, r_data in data.get("regime_fragility", {}).items():
                regime_rows += f"<tr><td>{r.capitalize()}</td><td>{r_data['count']}</td><td>{r_data['expectancy']:.3f}%</td><td>{r_data['winrate']:.1%}</td></tr>"
                
            session_rows = ""
            for s, s_data in data.get("session_persistence", {}).items():
                session_rows += f"<tr><td>{s}</td><td>{s_data['count']}</td><td>{s_data['expectancy']:.3f}%</td><td>{s_data['winrate']:.1%}</td></tr>"
                
            tables_html += f"""
            <div class="panel">
                <h2>Setup Detail: {setup.replace('_', ' ').title()}</h2>
                <div class="grid-2col">
                    <div>
                        <h3>Regime Robustness Profile</h3>
                        <table>
                            <thead><tr><th>Regime</th><th>Count</th><th>Net Expectancy</th><th>Win Rate</th></tr></thead>
                            <tbody>{regime_rows}</tbody>
                        </table>
                    </div>
                    <div>
                        <h3>Session Persistence Profile</h3>
                        <table>
                            <thead><tr><th>Session</th><th>Count</th><th>Net Expectancy</th><th>Win Rate</th></tr></thead>
                            <tbody>{session_rows}</tbody>
                        </table>
                    </div>
                </div>
            </div>
            """
            
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Edge Validation - {symbol}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: #0b0f19;
            color: #f1f5f9;
            margin: 0;
            padding: 30px;
        }}
        h1, h2, h3 {{
            color: #38bdf8;
            margin-top: 0;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #1e293b;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .card-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .setup-card {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid #334155;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .setup-name {{
            font-size: 15px;
            font-weight: bold;
            color: #38bdf8;
        }}
        .badge {{
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: bold;
        }}
        .APPROVED {{ background-color: #065f46; color: #34d399; }}
        .DISABLED {{ background-color: #7f1d1d; color: #f87171; }}
        .card-desc {{
            font-size: 12px;
            color: #94a3b8;
            margin-bottom: 15px;
            font-style: italic;
        }}
        .card-stats {{
            font-size: 13px;
            color: #cbd5e1;
        }}
        .stat-row {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px dashed #334155;
        }}
        .stat-row:last-child {{
            border-bottom: none;
        }}
        .panel {{
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 35px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px;
            border-bottom: 1px solid #334155;
            text-align: left;
            font-size: 13px;
        }}
        th {{
            background-color: #0f172a;
            color: #94a3b8;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #0f172a;
        }}
        .grid-2col {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }}
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Institutional Edge Robustness Validation</h1>
                <h2 style="color: #94a3b8; font-weight: 400; font-size: 16px;">Asset: {symbol}</h2>
            </div>
            <div>
                <span style="font-size: 13px; color: #64748b;">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}</span>
            </div>
        </div>
        
        <h2>Robustness Validation Status</h2>
        <div class="card-grid">
            {card_html}
        </div>
        
        {tables_html}
    </div>
</body>
</html>
"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html)

def generate_global_validation_report(global_results: dict, summary_dir: Path):
    """Generates a beautiful multi-asset summary dashboard showing which edges survive realism."""
    summary_dir.mkdir(parents=True, exist_ok=True)
    
    rows = ""
    for sym in SYMBOLS:
        sym_results = global_results.get(sym)
        if not sym_results: continue
        
        for setup, data in sym_results.items():
            status = data["status"]
            status_badge = f"""<span class="badge { 'APPROVED' if status == 'ACCEPTED' else 'DISABLED' }">{status}</span>"""
            
            exp_str = f"{data.get('expectancy_pct', 0.0):.3f}%" if status == "ACCEPTED" else "N/A"
            pf_str = f"{data.get('pf', 0.0):.2f}" if status == "ACCEPTED" else "N/A"
            fragility = f"{data.get('fragility_threshold', 0.0):.1f}x" if status == "ACCEPTED" else "N/A"
            
            rows += f"""
            <tr>
                <td><b>{sym}</b></td>
                <td><b>{setup.replace('_', ' ').upper()}</b></td>
                <td>{data.get('sample_size', 0)}</td>
                <td>{status_badge}</td>
                <td style="color: #38bdf8; font-weight: bold;">{exp_str}</td>
                <td>{pf_str}</td>
                <td>{fragility}</td>
                <td style="font-size: 12px; color: #94a3b8;">{data.get('reason', '')}</td>
            </tr>
            """
            
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Institutional Edge Validation Leaderboard - Quant V9</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: #0b0f19;
            color: #f1f5f9;
            margin: 0;
            padding: 30px;
        }}
        h1, h2, h3 {{
            color: #38bdf8;
            margin-top: 0;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #1e293b;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .panel {{
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 35px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 14px;
            border-bottom: 1px solid #334155;
            text-align: left;
            font-size: 13px;
        }}
        th {{
            background-color: #0f172a;
            color: #94a3b8;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #0f172a;
        }}
        .badge {{
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
        }}
        .APPROVED {{ background-color: #065f46; color: #34d399; }}
        .DISABLED {{ background-color: #7f1d1d; color: #f87171; }}
        .glass-hero {{
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(15, 23, 42, 0.6) 100%);
            border: 1px solid rgba(239, 68, 68, 0.2);
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
        }}
        .intro-text {{
            font-size: 15px;
            color: #cbd5e1;
            line-height: 1.6;
        }}
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Institutional Edge Validation Summary</h1>
                <h2 style="color: #94a3b8; font-weight: 400; font-size: 16px;">Quant V9 Realism Audit Layer</h2>
            </div>
            <div>
                <span style="font-size: 13px; color: #64748b;">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}</span>
            </div>
        </div>
        
        <div class="glass-hero">
            <h3>Execution Realism & Monte Carlo Validation Report</h3>
            <p class="intro-text">
                This report validates whether the discovered microstructure edges survive transaction costs (spread + slippage scaled by volatility) and regime-sensitive latency (execution delay up to 3 bars in high volatility). 
                Any setup failing Monte Carlo bootstrap stability (95% confidence lower-bound) or having less than 100 trades is marked as <b>REJECTED</b>.
            </p>
        </div>
        
        <div class="panel">
            <h2>Multi-Asset Edge Robustness Leaderboard</h2>
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Setup Name</th>
                        <th>Sample Size</th>
                        <th>Validation Status</th>
                        <th>Net Expectancy (%)</th>
                        <th>Profit Factor</th>
                        <th>Fragility Threshold</th>
                        <th>Status Reason / Filter Failed</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
    with open(summary_dir / "summary.html", 'w', encoding='utf-8') as f:
        f.write(html)

def main():
    global_results = {}
    
    print("\n============================================================")
    print(" STARTING INSTITUTIONAL EDGE REALISM VALIDATION")
    print("============================================================\n")
    
    for sym in SYMBOLS:
        try:
            res = run_edge_validation_for_symbol(sym)
            if res:
                global_results[sym] = res
        except Exception as e:
            print(f"Error validating symbol {sym}: {e}")
            import traceback
            traceback.print_exc()
            
    # Save global results
    summary_dir = V9_1_DIR / "reports" / "institutional_edge_validation"
    summary_dir.mkdir(parents=True, exist_ok=True)
    
    with open(summary_dir / "summary.json", 'w', encoding='utf-8') as f:
        json.dump(global_results, f, indent=4)
        
    # Generate global summary HTML report
    generate_global_validation_report(global_results, summary_dir)
    
    print("\n============================================================")
    print(" EDGE VALIDATION COMPLETED SUCCESSFULLY")
    print(f" Summary Leaderboard: {summary_dir / 'summary.html'}")
    print("============================================================\n")

if __name__ == "__main__":
    main()
