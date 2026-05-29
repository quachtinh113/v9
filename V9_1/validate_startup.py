import subprocess
import time
import os
from pathlib import Path

projects = [
    "quant_v9_3_1_audusd",
    "quant_v9_3_1_btcusd",
    "quant_v9_3_1_eurusd",
    "quant_v9_3_1_gbpusd",
    "quant_v9_3_1_us100",
    "quant_v9_3_1_us30",
    "quant_v9_3_1_us500",
    "quant_v9_3_1_usdcad",
    "quant_v9_3_1_usdchf",
    "quant_v9_3_1_usdjpy",
    "quant_v9_3_1_xauusd"
]

root_dir = Path(r"C:\Quant Trade\v9\V9_1\projects")

print("Starting validation...")
for p in projects:
    proj_dir = root_dir / p
    print(f"\n--- Testing {p} ---")
    
    # Start the process
    process = subprocess.Popen(
        ["python", "-m", "src.main", "--mode", "paper"],
        cwd=proj_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Wait for output
    start_time = time.time()
    success = False
    output_lines = []
    
    # We will read output for up to 10 seconds
    # using non-blocking approach (or just polling process.poll() and reading a bit)
    import threading
    
    def read_output():
        for line in process.stdout:
            print(f"[{p}] {line.strip()}")
            output_lines.append(line.strip())
            
    t = threading.Thread(target=read_output)
    t.daemon = True
    t.start()
    
    time.sleep(10) # wait 10 seconds for it to print diagnostics
    
    # Terminate process
    process.terminate()
    process.wait()
    
    # Check if diagnostics are present
    diagnostics_found = False
    for line in output_lines:
        if "Runtime Mode" in line and "PAPER" in line.upper():
            diagnostics_found = True
            break
            
    if diagnostics_found:
        print(f"[PASS] {p} started correctly.")
    else:
        print(f"[FAIL] {p} failed to print correct diagnostics.")
        
    print("Waiting 30 seconds before next project...")
    time.sleep(30)

print("\nValidation complete.")
