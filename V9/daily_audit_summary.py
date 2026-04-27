import os
import json
from pathlib import Path
from datetime import datetime, timezone
import sys

# Add a sample path to import TelegramBot
sys.path.insert(0, r"d:\V9\projects\quant_v9_3_1_us30")
from src.utils.telegram_bot import TelegramBot

ROOT_DIR = Path(r"d:\V9\projects")
SYMBOLS = ["GBPUSD", "EURUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "US30", "US100", "US500", "XAUUSD"]
TG_TOKEN = "8711065588:AAGo-XiVpvASpB_A4ZEPmoQj15rWEBZ8U6c"
TG_CHAT_ID = "1958994081"

def summarize_blocks():
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    summary_lines = [f"📊 <b>BÁO CÁO CHẶN LỆNH HÔM NAY</b> ({today_str})\n"]
    total_risk_blocks = 0
    total_ml_blocks = 0

    for sym in SYMBOLS:
        repo_name = f"quant_v9_3_1_{sym.lower()}"
        audit_file = ROOT_DIR / repo_name / "logs" / "live_pipeline_audit.ndjson"
        
        risk_count = 0
        ml_count = 0
        reasons = {}

        if audit_file.exists():
            with open(audit_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        # Check if it's from today
                        if data.get("ts_utc", "").startswith(today_str):
                            if data.get("risk_action") != "ALLOW" and data.get("risk_action") != "N/A":
                                risk_count += 1
                                for r in data.get("risk_reasons", []):
                                    reasons[r] = reasons.get(r, 0) + 1
                            if data.get("ml_decision") == "BLOCK":
                                ml_count += 1
                    except: continue
        
        if risk_count > 0 or ml_count > 0:
            total_risk_blocks += risk_count
            total_ml_blocks += ml_count
            reason_str = ", ".join([f"{k}({v})" for k, v in reasons.items()])
            summary_lines.append(f"• <b>{sym}</b>: Risk-Block: {risk_count}, ML-Block: {ml_count}")
            if reason_str: summary_lines.append(f"  └ <i>Lý do: {reason_str}</i>")

    if total_risk_blocks == 0 and total_ml_blocks == 0:
        summary_lines.append("✅ Không có tín hiệu nào bị chặn. Thị trường yên tĩnh hoặc mọi lệnh đều được thông qua.")
    else:
        summary_lines.append(f"\n📈 <b>Tổng cộng</b>: {total_risk_blocks} Risk Blocks, {total_ml_blocks} ML Blocks")

    bot = TelegramBot(TG_TOKEN, TG_CHAT_ID)
    bot.send_message("\n".join(summary_lines))
    print("Summary sent to Telegram.")

if __name__ == "__main__":
    summarize_blocks()
