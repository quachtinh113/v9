import os
import json
from pathlib import Path

def main():
    projects_dir = Path("c:/Quant Trade/v9/V9_1/projects")
    
    for proj in projects_dir.iterdir():
        if proj.is_dir() and proj.name.startswith("quant_v9_3_1_"):
            demo_j = proj / "logs" / "demo_journal.jsonl"
            if demo_j.exists():
                print(f"\nKeys for {proj.name}/logs/demo_journal.jsonl:")
                count = 0
                with open(demo_j, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            print(f"\nEvent {count+1}: Type={event.get('event_type')}")
                            # Print up to 10 keys of the top-level
                            print(f"Top-level keys: {list(event.keys())}")
                            payload = event.get("payload", {})
                            if isinstance(payload, dict):
                                print(f"Payload keys: {list(payload.keys())}")
                                # Print some select values
                                print(f"Sample values: direction={payload.get('direction') or payload.get('signal_direction') or payload.get('decision')}, ml_score={payload.get('ml_score') or payload.get('ml_filter_score')}, pnl={payload.get('pnl')}")
                            else:
                                print(f"Payload: {payload}")
                            count += 1
                            if count >= 3:
                                break
                        except Exception as e:
                            print(f"Error parsing line: {e}")
                break

if __name__ == "__main__":
    main()
