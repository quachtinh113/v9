import os
import glob

projects_dir = r"c:\Quant Trade\v9\V9\projects"
main_files = glob.glob(os.path.join(projects_dir, "*", "src", "main.py"))

live_block = """    elif args.mode == "live":
        from src.pipeline_live import LivePipeline
        print(f"Starting Live Pipeline for {config['symbol']}...")
        pipeline = LivePipeline(root)
        pipeline.run_loop()"""

for file_path in main_files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "elif args.mode == \"live\":" not in content:
        # We find the place to insert.
        # Let's insert it before 'if __name__ == "__main__": main()'
        # But wait, there is a function 'def main():'. We should insert it at the end of the if-elif block inside main.
        
        # We can split the file by the last 'print(f"Backtest Complete...'
        parts = content.split("print(f\"Backtest Complete")
        if len(parts) == 2:
            # We need to insert after the line 'print(f"Backtest Complete for {config['symbol']} | PnL: {result['net_pnl']:.2f}")'
            # Let's do a more robust replace
            search_str = "print(f\"Backtest Complete for {config['symbol']} | PnL: {result['net_pnl']:.2f}\")"
            if search_str in content:
                new_content = content.replace(search_str, search_str + "\n" + live_block)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Fixed: {file_path}")
            else:
                print(f"Could not find search string in {file_path}")
        else:
            print(f"Could not parse {file_path}")
    else:
        print(f"Already fixed: {file_path}")
