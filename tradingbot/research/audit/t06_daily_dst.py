from common import *
import fxlab as fx
from zoneinfo import ZoneInfo
NYZ = ZoneInfo("America/New_York")

h = fx.load_h1("EURUSD", "is")
# ---------- E11a: independent trading-day label (wall-clock 17:00 NY rule via zoneinfo) ----------
def label(ts):
    w = ts.to_pydatetime().astimezone(NYZ)
    d = w.date()
    return pd.Timestamp(d) + (pd.Timedelta(days=1) if w.hour >= 17 else pd.Timedelta(0))
mine = pd.DatetimeIndex([label(t) for t in h.index])
mism = (mine.values != h["ny_day"].values)
report("E11a", "ny_day label == independent zoneinfo wall-clock 17:00-NY rule for every EURUSD H1 bar (2012-2019, all DST switches)",
       mism.sum() == 0, f"{len(h)} bars compared, {int(mism.sum())} mismatches")

# ---------- E11b: specific DST weeks ----------
def info(day):
    g = h[h.ny_day == day]
    return len(g), str(g.index[0]), str(g.index[-1])
rows = []
ok = True
# spring: Sun 2015-03-08 02:00 EST->EDT. Sunday 17:00 EDT = 21:00 UTC, Friday before 16:00 EST = 21:00 UTC
exp = {"2015-03-06": ("2015-03-05 22:00:00+00:00", "2015-03-06 21:00:00+00:00"),
       "2015-03-09": ("2015-03-08 21:00:00+00:00", "2015-03-09 20:00:00+00:00"),
       # autumn: Sun 2015-11-01 02:00 EDT->EST. Sunday 17:00 EST = 22:00 UTC
       "2015-10-30": ("2015-10-29 21:00:00+00:00", "2015-10-30 20:00:00+00:00"),
       "2015-11-02": ("2015-11-01 22:00:00+00:00", "2015-11-02 21:00:00+00:00")}
for d, (a, b) in exp.items():
    nb, f, l = info(pd.Timestamp(d))
    g = (nb == 24 and f == a and l == b)
    rows.append((d, nb, f[5:16], l[5:16], g)); ok &= g
d1 = fx.to_daily(h)
for d in ["2015-03-06", "2015-03-09", "2015-10-30", "2015-11-02"]:
    lb = d1.loc[pd.Timestamp(d), "last_bar"]
    w = lb.tz_convert("America/New_York")
    rows.append((d, "last_bar NY", str(w)[:16], w.hour == 16)); ok &= (w.hour == 16)
report("E11b", "to_daily boundaries across 2015-03-08 and 2015-11-01: 24 bars/day, first bar = 17:00 NY, last bar starts 16:00 NY", ok, str(rows))

# daily OHLC vs independent groupby on my labels
ref = h.assign(day=mine).groupby("day")
dd = d1.copy()
mo = ref["mo"].first().reindex(dd.index); mh = ref["mh"].max().reindex(dd.index); ml = ref["ml"].min().reindex(dd.index); mc = ref["mc"].last().reindex(dd.index)
okd = np.allclose(dd.mo, mo) and np.allclose(dd.mh, mh) and np.allclose(dd.ml, ml) and np.allclose(dd.mc, mc)
report("E11c", "to_daily OHLC == independent aggregation of H1 mid bars by NY-17:00 day", okd, f"{len(dd)} days")

# ---------- E11d: daily_to_h1 mapping semantics ----------
vals = pd.Series(np.arange(len(d1), dtype=float), index=d1.index)           # value = day number
m = fx.daily_to_h1(vals, d1, h)
lb = d1["last_bar"]
bad_vis = 0; bad_hold = 0; chk = 0
pos = {d: i for i, d in enumerate(d1.index)}
# vectorised expectation: value visible at bar t iff t >= last_bar(D)  -> expected = number of days whose last_bar <= t, minus 1
lb_sorted = np.sort(lb.values.astype("datetime64[ns]"))
t_ns = h.index.tz_convert("UTC").tz_localize(None).values.astype("datetime64[ns]")
cnt = np.searchsorted(lb_sorted, t_ns, side="right")      # number of days fully closed (last bar start <= t)
exp_v = np.where(cnt > 0, cnt - 1, np.nan)
got = m.to_numpy()
same = np.array_equal(np.nan_to_num(got, nan=-1), np.nan_to_num(exp_v, nan=-1))
# explicit: no bar earlier than last_bar(D) sees value D
early = 0
for D, i in list(pos.items())[::25]:
    seen = m[m == i]
    if len(seen) and seen.index[0] != lb[D]:
        early += 1
report("E11d", "daily_to_h1: value of day D first visible exactly on the H1 bar that closes D (last_bar), carried forward after", same and early == 0,
       f"all {len(h)} bars equal expectation: {same}; days whose first-visible bar != last_bar (sampled every 25th): {early}")

# ---------- E11e: causality perturbation: change all bars after T, daily-derived signal up to T must not move ----------
rng = np.random.default_rng(5)
def sig(hh):
    dd_ = fx.to_daily(hh)
    s = (dd_["mc"] - dd_["mc"].rolling(5).mean()) / fx.atr(dd_, 10)       # uses only past + current day close
    return fx.daily_to_h1(s, dd_, hh), fx.daily_to_h1(fx.atr(dd_, 14), dd_, hh)
base_s, base_a = sig(h)
okc = True; det = []
for T in [20000, 30011, 40007, 47123]:
    h2 = h.copy()
    for c in ["bo", "bh", "bl", "bc", "ao", "ah", "al", "ac", "mo", "mh", "ml", "mc"]:
        h2.iloc[T + 1:, h2.columns.get_loc(c)] = h2[c].iloc[T + 1:].to_numpy() * (1 + rng.normal(0, 0.05, len(h2) - T - 1))
    s2, a2 = sig(h2)
    same_s = np.allclose(base_s.iloc[:T + 1].fillna(-9).to_numpy(), s2.iloc[:T + 1].fillna(-9).to_numpy(), atol=0, rtol=0)
    same_a = np.allclose(base_a.iloc[:T + 1].fillna(-9).to_numpy(), a2.iloc[:T + 1].fillna(-9).to_numpy(), atol=0, rtol=0)
    okc &= bool(same_s and same_a); det.append((T, same_s, same_a))
report("E11e", "no lookahead: perturbing every bar after T leaves daily->H1 signals (momentum z, ATR) at/before T bit-identical", okc, str(det))
