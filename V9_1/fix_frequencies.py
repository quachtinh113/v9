import os, glob, re
from utils.frequency import normalize_pandas_frequency

root = r"c:\\Quant Trade\\v9\\V9_1\\projects"
files = glob.glob(os.path.join(root, "*", "src", "data", "mtf_builder.py"))

for f in files:
    with open(f, "r", encoding="utf-8") as fp:
        content = fp.read()
    # replace resample normalize_pandas_frequency("1H") with "1h"
    new_content = re.sub(r'normalize_pandas_frequency("1H")', '"1h"', content)
    if new_content != content:
        with open(f, "w", encoding="utf-8") as fp:
            fp.write(new_content)
        print(f"Fixed frequency in {f}")
    else:
        print(f"No change needed in {f}")