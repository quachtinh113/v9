import os, re, pathlib, sys

ROOT = pathlib.Path(r"c:\\Quant Trade\\v9\\V9_1")
TARGET_EXT = ".py"
OLD_ALIASES = [normalize_pandas_frequency("1H"),normalize_pandas_frequency("2H"),normalize_pandas_frequency("4H"),normalize_pandas_frequency("6H"),normalize_pandas_frequency("8H"),normalize_pandas_frequency("12H"),normalize_pandas_frequency("1T"),normalize_pandas_frequency("5T"),normalize_pandas_frequency("15T"),normalize_pandas_frequency("30T")]
ALIAS_PATTERN = re.compile(r"([\"'])(%s)\1" % "|".join(map(re.escape, OLD_ALIASES)))
IMPORT_LINE = "from utils.frequency import normalize_pandas_frequency"

changed_files = []

for py_path in ROOT.rglob(f"*{TARGET_EXT}"):
    if py_path.name == "frequency.py":
        continue  # skip the newly added utility
    text = py_path.read_text(encoding="utf-8")
    new_text, count = ALIAS_PATTERN.subn(lambda m: f"normalize_pandas_frequency({m.group(0)})", text)
    if count > 0:
        # ensure import line exists
        if IMPORT_LINE not in new_text:
            # insert after the last import statement or after docstring
            lines = new_text.splitlines()
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.lstrip().startswith("import ") or line.lstrip().startswith("from "):
                    insert_idx = i + 1
            lines.insert(insert_idx, IMPORT_LINE)
            new_text = "\n".join(lines)
        py_path.write_text(new_text, encoding="utf-8")
        changed_files.append(str(py_path))

# Write a simple summary file for later use
summary_path = ROOT / "frequency_fix_summary.txt"
with open(summary_path, "w", encoding="utf-8") as f:
    for fp in changed_files:
        f.write(fp + "\n")
print(f"Modified {len(changed_files)} files. Summary written to {summary_path}")
