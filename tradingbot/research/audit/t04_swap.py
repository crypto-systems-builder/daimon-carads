from common import *
idx = pd.DatetimeIndex(list(pd.date_range("2020-01-07 13:00", "2020-01-10 21:00", freq="h", tz="UTC")) +
                       list(pd.date_range("2020-01-12 22:00", "2020-01-14 12:00", freq="h", tz="UTC")))
n = len(idx)
bo = np.full(n, 1.1000)
h1 = make_h1(bo, bo.copy(), bo.copy(), bo.copy(), sp=0.0, index=idx)
roll_pos = np.where(h1["rollover"].to_numpy() == 1)[0]
wd = h1["ny_wday"].to_numpy()
days_exp = {i: (3.0 if wd[i] == 2 else 1.0) for i in roll_pos}
c, mk_ = 0.02, 0.01
rows = []; ok = True
for dirn in (1, -1):
    r = sim(h1, [(0, n, dirn)], 0.01, carry=c, swap_markup=mk_)       # units = 0.01/0.01 = 1
    ret = r["ret"].to_numpy()
    exp = np.zeros(n)
    rate = (c if dirn > 0 else -c) - mk_
    for i, dd in days_exp.items():
        exp[i] = 1.0 * 1.1 * rate * dd / 365.0
    ok_d = np.allclose(ret[1:], exp[1:], atol=1e-15, rtol=0)
    ok &= bool(ok_d)
    rows.append((dirn, [(str(idx[i])[5:16], int(wd[i]), round(ret[i], 9), round(exp[i], 9)) for i in roll_pos]))
report("E8a", "swap only on 17:00-NY bars; Wed 3x; Sunday-open 1x; long (c-m), short (-c-m); = units*px*rate*days/365", ok,
       f"roll bars (utc, wday, got, exp) long: {rows[0][1]}")
report("E8a2", "swap short-side numbers", ok, f"{rows[1][1]}")

# Sunday bar specifically: position carried over weekend (last Fri bar -> Sun 22:00 UTC)
i_sun = [i for i in roll_pos if wd[i] == 6][0]
r = sim(h1, [(0, n, 1)], 0.01, carry=c, swap_markup=mk_)
e = 1.1 * (c - mk_) * 1 / 365
report("E8b", "Sunday-open roll bar charges 1 day (position held over weekend)", close(r["ret"].iloc[i_sun], e, 1e-15), f"got {r['ret'].iloc[i_sun]:.3e}, expected {e:.3e}")

# flat across a roll bar: no swap; entry AT the roll bar open: no swap on that bar; exit at roll-bar open: swap charged on the carried position
w = [i for i in roll_pos if wd[i] == 2][0]
r = sim(h1, [(w + 2, w + 6, 1)], 0.01, carry=c, swap_markup=mk_)       # flat through Wed roll
no_swap_flat = np.abs(r["ret"].to_numpy()[:w + 3]).max() == 0.0
# entry decided at close of bar (w-1) -> filled at open of the roll bar w  -> carried through nothing
r2 = sim(h1, [(w - 1, w + 3, 1)], 0.01, carry=c, swap_markup=mk_)
no_swap_entry_at_roll = close(r2["ret"].iloc[w], 0.0, 1e-15)
# decision to exit made at close of bar w-1 -> closed at roll bar open: position WAS carried into the bar
r3 = sim(h1, [(w - 5, w - 1, 1)], 0.01, carry=c, swap_markup=mk_)     # target 0 at k=w-1 -> exit at open of w
e3 = 1.1 * (c - mk_) * 3 / 365
exit_at_roll_charged = close(r3["ret"].iloc[w], e3, 1e-15)
report("E8c", "no swap if flat over roll; entry at roll-bar open uncharged; exit at the roll-bar open IS charged (3x Wed)",
       bool(no_swap_flat and no_swap_entry_at_roll), f"flat={no_swap_flat}, entry-at-roll={no_swap_entry_at_roll}, exit-at-roll charged={exit_at_roll_charged} (r={r3['ret'].iloc[w]:.3e}, 3-day={e3:.3e})")

# markup applied to both sides: with carry 0 both long and short pay markup
rl = sim(h1, [(0, n, 1)], 0.01, carry=0.0, swap_markup=0.01)["ret"].sum()
rs = sim(h1, [(0, n, -1)], 0.01, carry=0.0, swap_markup=0.01)["ret"].sum()
total_days = sum(days_exp.values())
e = -1.1 * 0.01 * total_days / 365
report("E8d", "swap_markup charged on both long and short when carry=0", close(rl, e, 1e-14) and close(rs, e, 1e-14),
       f"long {rl:.6e}, short {rs:.6e}, expected {e:.6e} (days {total_days})")

# real carry(): EURUSD rates file vs hand
import fxlab as fx
raw = pd.read_csv("/home/user/fxdata/rates/policy_rates_daily.csv", index_col=0, parse_dates=True)
h = fx.load_h1("EURUSD", "is")
cr = pd.Series(fx.carry("EURUSD", h), index=h.index)
bad = 0; chk = 0
for ts in ["2012-06-12 12:00", "2015-03-10 22:00", "2017-09-05 03:00", "2019-12-20 12:00"]:
    t = pd.Timestamp(ts, tz="UTC")
    if t not in cr.index:
        t = cr.index[cr.index.searchsorted(t)]
    day = t.tz_localize(None).normalize()
    row = raw.asfreq("D").ffill().loc[day]
    exp = (row["EUR"] - row["USD"]) / 100.0
    chk += 1; bad += (not close(cr.loc[t], exp, 1e-12))
report("E8e", "carry() = (r_base - r_quote)/100 on the bar's UTC date", bad == 0, f"{chk} spot checks, {bad} mismatches; nan count {int(cr.isna().sum())}")
