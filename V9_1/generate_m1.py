import pandas as pd, pathlib, sys
from utils.frequency import normalize_pandas_frequency

def resample_to_m1(src_path, dst_path):
    df = pd.read_csv(src_path, parse_dates=['timestamp'])
    df.set_index('timestamp', inplace=True)
    m1 = df.resample(normalize_pandas_frequency('1T')).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    m1.to_csv(dst_path, index=True, date_format='%Y-%m-%d %H:%M:%S')
    print(f"Created {dst_path}")

projects_root = pathlib.Path(r"c:\\Quant Trade\\v9\\V9_1\\projects")
symbols = ["eurusd", "gbpusd", "usdjpy"]
for sym in symbols:
    proj_path = projects_root / f"quant_v9_3_1_{sym}"
    raw_dir = proj_path / "data" / "raw"
    if not raw_dir.is_dir():
        print(f"Raw data folder missing for {sym}")
        continue
    # try to find an existing M1 file first
    existing_m1 = list(raw_dir.glob(f"{sym.upper()}_M1_sample.csv"))
    if existing_m1:
        print(f"M1 already exists for {sym}")
        continue
    # otherwise pick the highest‑frequency source file
    src = None
    for pattern in ["*_M5_sample.csv", "*_M30_sample.csv", "*_H1_sample.csv"]:
        matches = list(raw_dir.glob(pattern))
        if matches:
            src = matches[0]
            break
    if src is None:
        print(f"No source CSV found for {sym}")
        continue
    dst = raw_dir / f"{sym.upper()}_M1_sample.csv"
    resample_to_m1(src, dst)