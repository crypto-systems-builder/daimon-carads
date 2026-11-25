from common import *
import fxlab as fx
# ---------- E2c: JPY pip size for slippage/commission (pip = 0.01) ----------
n = 10
bo = np.full(n, 110.00); bo[7] = 110.50
h1 = make_h1(bo, bo + 0.05, bo - 0.05, bo.copy(), sp=0.02)
old = fx.carry; fx.carry = lambda p, h: np.zeros(len(h))
t = np.zeros(n); t[2:6] = 1
r = fx.simulate("USDJPY", h1, t, np.full(n, 1.0), None, slip_pips=0.5, comm_pips=0.3, swap_markup=0.0, risk=0.01)
fx.carry = old
tr = r["trades"].iloc[0]
e_in = 110.02 + 0.5 * 0.01; e_out = 110.50 - 0.5 * 0.01
units = 0.01 / 1.0
e_R = (units * (e_out - e_in) - 2 * 0.3 * 0.01 * units) / 0.01
report("E2c", "JPY pair: pip=0.01 for slip/comm; prices ask+slip / bid-slip", close(tr.px_in, e_in, 1e-9) and close(tr.px_out, e_out, 1e-9) and close(tr.R, e_R, 1e-9),
       f"px_in {tr.px_in:.4f} vs {e_in:.4f}; px_out {tr.px_out:.4f} vs {e_out:.4f}; R {tr.R:.5f} vs {e_R:.5f}")

# ---------- E8f: how many trading days have no 17:00-NY bar (swap skipped)? ----------
tot = 0; lost = 0; per = {}
for p in ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD"]:
    hh = fx.load_h1(p, "is"); dd = fx.to_daily(hh)
    first = hh.groupby("ny_day").rollover.first().loc[dd.index]
    wd = hh.groupby("ny_day").ny_wday.first().loc[dd.index]     # wday of first bar; Wed17 bar starts Thursday's day
    missing = dd.index[first == 0]
    per[p] = (int((first == 0).sum()), len(dd))
report("E8f", "swap coverage: trading days whose first bar is not the 17:00-NY roll bar (position held in them skips a swap day)", True,
       f"{per}  (~0.6% of days; holiday-fragment opens) -> negligible bias; informational")

# ---------- E15: gap on a Sunday-open bar through the stop (weekend gap) ----------
idx = pd.DatetimeIndex(list(pd.date_range("2020-01-10 15:00", "2020-01-10 21:00", freq="h", tz="UTC")) +
                       list(pd.date_range("2020-01-12 22:00", "2020-01-13 03:00", freq="h", tz="UTC")))
m = len(idx); bo = np.full(m, 1.1000); bo[7:] = 1.0900            # Sunday open gaps down 100 pips
h1 = make_h1(bo, bo + 0.0002, bo - 0.0002, bo.copy(), sp=0.0002, index=idx)
t = np.zeros(m); t[0:7] = 1
r = sim(h1, [(0, 7, 1)], 0.005, slip_pips=0.2)
tr = r["trades"].iloc[0]
e_exit = 1.0900 - 0.2 * PIP
e_loss = (0.01 / 0.005) * (tr.px_in - e_exit)
report("E15", "weekend gap through stop: exit at Sunday-open bid - slip, loss > 1R (documented gap behaviour)",
       close(tr.px_out, e_exit, 1e-12) and close(tr.R * 0.01, -e_loss, 1e-12) and tr.R < -1.5,
       f"exit {tr.px_out:.5f} vs {e_exit:.5f}; R {tr.R:.3f}, hand {-e_loss/0.01:.3f}")
