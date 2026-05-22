import json
import csv
from pathlib import Path
from datetime import datetime

def generate_json_report(metrics: dict, output_dir: Path, symbol: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"{symbol}_audit.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=4)
    return file_path

def generate_csv_report(metrics: dict, output_dir: Path, symbol: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"{symbol}_audit.csv"
    
    # Flatten metrics for CSV
    flat_metrics = {"symbol": symbol, "timestamp": datetime.now().isoformat()}
    for k, v in metrics.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                flat_metrics[f"{k}_{sub_k}"] = sub_v
        else:
            flat_metrics[k] = v
            
    file_exists = file_path.exists()
    with open(file_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=flat_metrics.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(flat_metrics)
    return file_path

def generate_html_report(metrics: dict, output_dir: Path, symbol: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"{symbol}_audit.html"
    
    val = metrics.get('validation_metrics', {})
    fin = metrics.get('financial_metrics', {})
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Training Audit Report - {symbol}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            table {{ border-collapse: collapse; width: 50%; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            h2 {{ color: #333; }}
            .warning {{ color: red; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h2>Training Audit Report for {symbol}</h2>
        <p>Generated at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        
        {"<p class='warning'>OVERFITTING DETECTED!</p>" if metrics.get("overfitting_detected", False) else ""}
        
        <h3>Validation Metrics</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Winrate</td><td>{val.get('winrate', 0):.2%}</td></tr>
            <tr><td>Precision</td><td>{val.get('precision', 0):.4f}</td></tr>
            <tr><td>Recall</td><td>{val.get('recall', 0):.4f}</td></tr>
            <tr><td>F1 Score</td><td>{val.get('f1_score', 0):.4f}</td></tr>
        </table>
        
        <h3>Financial Simulation</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Max Drawdown</td><td>{fin.get('max_drawdown', 0):.2f}</td></tr>
            <tr><td>Profit Factor</td><td>{fin.get('profit_factor', 0):.2f}</td></tr>
            <tr><td>Avg Trade Duration</td><td>{fin.get('avg_trade_duration', 'N/A')}</td></tr>
        </table>
        
        <h3>Regime Distribution</h3>
        <table>
            <tr><th>Regime</th><th>Count</th></tr>
    """
    for regime, count in metrics.get('regime_distribution', {}).items():
        html += f"<tr><td>{regime}</td><td>{count}</td></tr>"
        
    html += """
        </table>
    </body>
    </html>
    """
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return file_path

def generate_all_reports(metrics: dict, output_dir: Path, symbol: str):
    generate_json_report(metrics, output_dir, symbol)
    generate_csv_report(metrics, output_dir, symbol)
    generate_html_report(metrics, output_dir, symbol)
