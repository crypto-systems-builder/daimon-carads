import sys, os
sys.path.insert(0, "/home/user/daimon-carads/tradingbot/research")
os.environ.setdefault("NUMBA_CACHE_DIR", "/tmp/numba_audit_cache")
import numpy as np, pandas as pd
import fxlab

PIP = 1e-4
RESULTS = []

def report(tid, name, ok, detail):
    RESULTS.append((tid, ok))
    print(f"{'PASS' if ok else 'FAIL'} {tid} {name} :: {detail}", flush=True)

def close(a, b, tol=1e-9):
    return abs(a - b) <= tol

def make_h1(bo, bh=None, bl=None, bc=None, sp=0.0002, start="2020-01-06 12:00", index=None):
    """bid OHLC arrays (bo required); ask = bid + sp (scalar or array). UTC hourly index
    (Mon 2020-01-06 12:00 UTC = 07:00 NY, winter) unless `index` given. Derived cols as load_h1."""
    bo = np.asarray(bo, float); n = len(bo)
    bh = bo + 0.0002 if bh is None else np.asarray(bh, float)
    bl = bo - 0.0002 if bl is None else np.asarray(bl, float)
    bc = bo + 0.0001 if bc is None else np.asarray(bc, float)
    sp = np.broadcast_to(np.asarray(sp, float), (n,))
    if index is None:
        index = pd.date_range(start, periods=n, freq="h", tz="UTC")
    df = pd.DataFrame({"bo": bo, "bh": bh, "bl": bl, "bc": bc,
                       "ao": bo + sp, "ah": bh + sp, "al": bl + sp, "ac": bc + sp}, index=index)
    ny = df.index.tz_convert(fxlab.NY)
    df["ny_day"] = (ny + pd.Timedelta(hours=7)).normalize().tz_localize(None)
    df["ny_hour"] = ny.hour
    df["ny_wday"] = ny.weekday
    df["rollover"] = (ny.hour == 17).astype(np.int8)
    for c in "ohlc":
        df["m" + c] = (df["b" + c] + df["a" + c]) / 2.0
    return df

def sim(h1, target, sd, carry=0.0, tp=None, **kw):
    n = len(h1)
    kw.setdefault("swap_markup", 0.0)
    kw.setdefault("slip_pips", 0.0)
    kw.setdefault("risk", 0.01)
    old = fxlab.carry
    fxlab.carry = lambda pair, h: np.full(len(h), float(carry))
    try:
        t = np.zeros(n); 
        for (a, b, v) in target: t[a:b] = v
        sdv = np.full(n, sd) if np.isscalar(sd) else np.asarray(sd, float)
        return fxlab.simulate("EURUSD", h1, t, sdv, tp, **kw)
    finally:
        fxlab.carry = old
