import os
from pathlib import Path

def patch_file(file_path, search_str, replace_str):
    if not file_path.exists():
        return False
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        if search_str in content:
            if replace_str in content:
                print(f"  Already patched: {file_path.name}")
                return True
            new_content = content.replace(search_str, replace_str)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"  Successfully patched: {file_path.name}")
            return True
        else:
            print(f"  Search string not found in: {file_path.name}")
            return False
    except Exception as e:
        print(f"  Error patching {file_path.name}: {e}")
        return False

def apply_fixes():
    print("=============================================================")
    # Scan both V9 and V9_1 directories
    workspaces = [Path(r"c:\Quant Trade\v9\V9"), Path(r"c:\Quant Trade\v9\V9_1")]
    
    live_adapter_search = """    def resolve_broker_symbol(self, base_symbol):
        if not self.connected: return base_symbol
        if mt5.symbol_select(base_symbol, True):"""
        
    live_adapter_replace = """    def resolve_broker_symbol(self, base_symbol):
        if not self.connected: return base_symbol
        if base_symbol.upper() == "US100":
            base_symbol = "USTEC"
        if mt5.symbol_select(base_symbol, True):"""

    adapter_search = """        # MT5 execution logic
        symbol = req.get("symbol", "US30")
        
        # Try to select the symbol
        if not mt5.symbol_select(symbol, True):"""

    adapter_replace = """        # MT5 execution logic
        symbol = req.get("symbol", "US30")
        if symbol.upper() == "US100":
            symbol = "USTEC"
        
        # Try to select the symbol
        if not mt5.symbol_select(symbol, True):"""

    for ws in workspaces:
        if not ws.exists():
            continue
        print(f"\nScanning workspace: {ws.name}")
        projects_dir = ws / "projects"
        if not projects_dir.exists():
            continue
            
        for proj in projects_dir.iterdir():
            if proj.is_dir() and proj.name.startswith("quant_v9_3_1_"):
                print(f"Project: {proj.name}")
                # 1. Patch mt5_live_adapter.py
                live_adapter_path = proj / "src" / "data" / "mt5_live_adapter.py"
                patch_file(live_adapter_path, live_adapter_search, live_adapter_replace)
                
                # 2. Patch mt5_adapter.py
                adapter_path = proj / "src" / "execution" / "mt5_adapter.py"
                patch_file(adapter_path, adapter_search, adapter_replace)

    # Patch the mass-deploy scripts templates as well so future deploys don't overwrite this fix
    print("\nPatching mass-deploy templates...")
    apply_live_data_fix_path = Path(r"c:\Quant Trade\v9\V9_1\apply_live_data_fix.py")
    if apply_live_data_fix_path.exists():
        patch_file(apply_live_data_fix_path, live_adapter_search, live_adapter_replace)

if __name__ == "__main__":
    apply_fixes()
