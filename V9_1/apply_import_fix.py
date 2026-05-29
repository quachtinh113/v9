import pathlib, shutil, re

ROOT = pathlib.Path(r"c:\\Quant Trade\\v9\\V9_1\\projects")
UTIL_SRC = pathlib.Path(r"c:\\Quant Trade\\v9\\V9_1\\utils\\frequency.py")

changed_files = []

for proj in ROOT.iterdir():
    if not proj.is_dir():
        continue
    # 1. ensure src/utils package exists
    utils_dir = proj / "src" / "utils"
    utils_dir.mkdir(parents=True, exist_ok=True)
    # copy frequency.py if not present or overwrite to be safe
    dst_freq = utils_dir / "frequency.py"
    shutil.copy2(UTIL_SRC, dst_freq)
    # ensure __init__.py
    (utils_dir / "__init__.py").write_text("# utils package\n", encoding="utf-8")

    # 2. replace imports in all .py files under the project
    for py_path in proj.rglob("*.py"):
        text = py_path.read_text(encoding="utf-8")
        if "from utils.frequency import normalize_pandas_frequency" in text:
            new_text = text.replace(
                "from utils.frequency import normalize_pandas_frequency",
                "from src.utils.frequency import normalize_pandas_frequency"
            )
            py_path.write_text(new_text, encoding="utf-8")
            changed_files.append(str(py_path))

# write a summary file
summary_path = ROOT.parent / "import_fix_summary.txt"
summary_path.write_text("\n".join(changed_files), encoding="utf-8")
print(f"Processed {len(changed_files)} files, created utils in each project.")
