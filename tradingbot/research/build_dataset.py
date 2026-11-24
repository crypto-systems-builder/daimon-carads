"""Turn downloaded FXCM weekly files into per-pair H1 parquet, then seal OOS.

    python3 build_dataset.py build     # raw -> $FXDATA/full/h1 + $FXDATA/is/h1 (2012-2019)
    python3 build_dataset.py seal      # encrypt full/ + raw/ into sealed/oos.tar.enc, delete them
    python3 build_dataset.py unseal    # restore full/ -> $FXDATA/oos/h1 (only after candidates are frozen)

The out-of-sample period (2020-01-01 onward) is sealed with a random key kept
outside the repo, so strategy research cannot see it - not even by accident.
Unsealing is a one-way door: do it once, after the frozen candidate list is
committed to git.
"""
import glob
import os
import secrets
import subprocess
import sys

import numpy as np
import pandas as pd

DATA = os.environ.get("FXDATA", "/home/user/fxdata")
KEY = "/root/.fxlab_oos_key"
IS_END = pd.Timestamp("2020-01-01", tz="UTC")   # IS = everything before this


def read_pair(pair: str) -> pd.DataFrame:
    files = [f for f in glob.glob(os.path.join(DATA, "fxcm", "H1", pair, "*", "*.csv.gz")) if os.path.getsize(f)]
    if not files:
        return pd.DataFrame()
    df = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    df["t"] = pd.to_datetime(df["DateTime"], format="%m/%d/%Y %H:%M:%S.%f", utc=True)
    df = df.rename(columns={"BidOpen": "bo", "BidHigh": "bh", "BidLow": "bl", "BidClose": "bc",
                            "AskOpen": "ao", "AskHigh": "ah", "AskLow": "al", "AskClose": "ac"})
    df = df[["t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]].drop_duplicates("t").set_index("t").sort_index()
    return df


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Drop rows that cannot be real quotes; repair high/low consistency."""
    n0 = len(df)
    px = df[["bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]]
    bad = (px <= 0).any(axis=1) | px.isna().any(axis=1)
    df = df[~bad].copy()
    # ask below bid by more than a hair = corrupt quote
    sp = df["ac"] - df["bc"]
    med = sp.median()
    corrupt = (df["ao"] < df["bo"] - med) | (df["ac"] < df["bc"] - med)
    df = df[~corrupt].copy()
    for side in "ba":
        o, h, l, c = (df[side + x] for x in "ohlc")
        df[side + "h"] = np.maximum.reduce([h, o, c])
        df[side + "l"] = np.minimum.reduce([l, o, c])
    return df, {"rows_in": n0, "dropped_nonpositive": int(bad.sum()), "dropped_crossed": int(corrupt.sum()),
                "rows_out": len(df)}


def build():
    pairs = sorted(os.listdir(os.path.join(DATA, "fxcm", "H1")))
    os.makedirs(os.path.join(DATA, "full", "h1"), exist_ok=True)
    os.makedirs(os.path.join(DATA, "is", "h1"), exist_ok=True)
    report = []
    for p in pairs:
        df = read_pair(p)
        if df.empty:
            report.append({"pair": p, "rows_out": 0})
            continue
        df, info = clean(df)
        df.to_parquet(os.path.join(DATA, "full", "h1", f"{p}.parquet"))
        ins = df[df.index < IS_END]
        if len(ins) > 1000:
            ins.to_parquet(os.path.join(DATA, "is", "h1", f"{p}.parquet"))
        pip = 0.01 if p.endswith("JPY") else 0.0001
        spread = (ins["ac"] - ins["bc"]) / pip
        report.append({"pair": p, **info, "is_rows": len(ins),
                       "is_first": str(ins.index.min())[:10] if len(ins) else "",
                       "is_median_spread_pips": round(float(spread.median()), 2) if len(ins) else None})
        print(report[-1], flush=True)   # IS stats only - never print OOS figures
    pd.DataFrame(report).to_csv(os.path.join(DATA, "build_report_is.csv"), index=False)


def seal():
    if not os.path.exists(KEY):
        with open(KEY, "w") as f:
            f.write(secrets.token_hex(32))
        os.chmod(KEY, 0o600)
    out = os.path.join(DATA, "sealed")
    os.makedirs(out, exist_ok=True)
    tar = subprocess.run(["tar", "-C", DATA, "-cf", "-", "full", "fxcm"], check=True, capture_output=True).stdout
    subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-pass", f"file:{KEY}",
                    "-out", os.path.join(out, "oos.tar.enc")], input=tar, check=True)
    subprocess.run(["rm", "-rf", os.path.join(DATA, "full"), os.path.join(DATA, "fxcm")], check=True)
    print("sealed:", os.path.getsize(os.path.join(out, "oos.tar.enc")), "bytes")


def unseal():
    enc = os.path.join(DATA, "sealed", "oos.tar.enc")
    tar = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", f"file:{KEY}", "-in", enc],
                         check=True, capture_output=True).stdout
    subprocess.run(["tar", "-C", DATA, "-xf", "-", "full"], input=tar, check=True)
    os.makedirs(os.path.join(DATA, "oos"), exist_ok=True)
    if not os.path.exists(os.path.join(DATA, "oos", "h1")):
        os.rename(os.path.join(DATA, "full", "h1"), os.path.join(DATA, "oos", "h1"))
    print("unsealed to", os.path.join(DATA, "oos", "h1"))


if __name__ == "__main__":
    {"build": build, "seal": seal, "unseal": unseal}[sys.argv[1]]()
