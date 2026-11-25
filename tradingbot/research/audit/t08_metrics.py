from common import *
import fxlab as fx
from statistics import NormalDist
idx = pd.to_datetime(["2018-12-27", "2018-12-28", "2018-12-31", "2019-01-01", "2019-01-02", "2019-01-03"])
x = pd.Series([0.01, -0.02, 0.03, 0.00, -0.01, 0.02], index=idx)
m = fx.metrics(x)
mu = 0.03 / 6; sd = (1750e-6 / 5) ** 0.5
e = {"sharpe": mu / sd * 260 ** 0.5, "t_stat": mu / sd * 6 ** 0.5, "max_dd": -0.02, "ann_ret": mu * 260, "ann_vol": sd * 260 ** 0.5,
     "total": 0.03, "days": 6, "pct_pos_years": 1.0}   # 2018 sum +0.02, 2019 sum +0.01
bad = {k: (m[k], v) for k, v in e.items() if not close(m[k], v, 1e-12)}
report("E12a", "metrics: Sharpe=mean/std(ddof1)*sqrt(260), t_stat, ann_ret/vol, total, max_dd, pct_pos_years vs hand", not bad,
       f"sharpe {m['sharpe']:.6f} (hand {e['sharpe']:.6f}); t {m['t_stat']:.6f} ({e['t_stat']:.6f}); maxdd {m['max_dd']} (-0.02); mismatches {bad}")

# max_dd when the curve starts with a loss: peak must include the initial equity (0)
y = pd.Series([-0.01, -0.02, 0.005], index=idx[:3])
my = fx.metrics(y)
# hand: equity path from initial 0: 0,-0.01,-0.03,-0.025 -> max drawdown = -0.03
report("E12b", "max_dd measured from initial equity 0 when first days lose", close(my["max_dd"], -0.03, 1e-12),
       f"fxlab max_dd={my['max_dd']:.4f}, hand={-0.03:.4f}  (peak taken as first day's equity instead of 0). Repro: fx.metrics(pd.Series([-0.01,-0.02,0.005], index=pd.to_datetime(['2018-12-27','2018-12-28','2018-12-31'])))['max_dd']")
y2 = pd.Series([-0.05, 0.0, 0.0], index=idx[:3])
report("E12b2", "max_dd for a series whose only loss is day 1 (equity never recovers)", close(fx.metrics(y2)["max_dd"], -0.05, 1e-12),
       f"fxlab {fx.metrics(y2)['max_dd']:.4f}, hand -0.0500")

# trade stats
tr = pd.DataFrame({"R": [2.0, -1.0, -1.0, 0.5], "bars": [3, 5, 7, 9]})
mt = fx.metrics(x, tr, pd.Series([0.001] * 6, index=idx))
okt = (mt["trades"] == 4 and close(mt["win_rate"], 0.5) and close(mt["avg_R"], 0.125) and close(mt["profit_factor"], 1.25)
       and close(mt["avg_bars"], 6.0) and close(mt["cost_ann"], 0.001 * 260))
report("E12c", "metrics trade stats (win rate, avg R, profit factor, avg bars, cost_ann)", okt, str({k: mt[k] for k in ["trades", "win_rate", "avg_R", "profit_factor", "avg_bars", "cost_ann"]}))

x = pd.Series([0.01, -0.02, 0.03, 0.00, -0.01, 0.07], index=idx); m = fx.metrics(x)
# skew / kurt vs hand (sample skew & excess kurt unbiased as pandas); document kurt returned = excess+3
xs = x.to_numpy(); nn = len(xs); mm = xs.mean(); s2 = ((xs - mm) ** 2).sum() / (nn - 1)
g1 = (nn / ((nn - 1) * (nn - 2))) * (((xs - mm) ** 3).sum() / s2 ** 1.5)
g2 = (nn * (nn + 1) / ((nn - 1) * (nn - 2) * (nn - 3))) * (((xs - mm) ** 4).sum() / s2 ** 2) - 3 * (nn - 1) ** 2 / ((nn - 2) * (nn - 3))
report("E12d", "skew and kurt (non-excess = excess+3) vs hand formulas", close(m["skew"], g1, 1e-9) and close(m["kurt"], g2 + 3, 1e-9),
       f"skew {m['skew']:.6f} vs {g1:.6f}; kurt {m['kurt']:.6f} vs {g2+3:.6f}")

# deflated Sharpe vs Bailey & Lopez de Prado (2014) using stdlib NormalDist (independent of scipy)
def dsr_ref(sr_a, N, var_a, T, skew, kurt):
    nd = NormalDist(); g = 0.5772156649015329
    sr = sr_a / 260 ** 0.5; v = var_a / 260
    sr0 = v ** 0.5 * ((1 - g) * nd.inv_cdf(1 - 1 / N) + g * nd.inv_cdf(1 - 1 / (N * 2.718281828459045)))
    return nd.cdf((sr - sr0) * (T - 1) ** 0.5 / (1 - skew * sr + (kurt - 1) / 4 * sr * sr) ** 0.5), sr0
rows = []; ok = True
for args in [(1.5, 20, 0.5, 1000, -0.3, 5.0), (0.8, 100, 0.25, 2000, 0.0, 3.0), (2.0, 5, 1.0, 500, -0.5, 8.0)]:
    got = fx.deflated_sharpe(*args); ref, sr0 = dsr_ref(*args)
    ok &= close(got, ref, 1e-12); rows.append((args, round(got, 8), round(ref, 8), round(sr0 * 260 ** 0.5, 5)))
# known anchor: SR exactly at SR0 -> 0.5
sr0a = dsr_ref(1.0, 50, 0.4, 1000, 0, 3)[1] * 260 ** 0.5
anchor = fx.deflated_sharpe(sr0a, 50, 0.4, 1000, 0.0, 3.0)
ok &= close(anchor, 0.5, 1e-9)
report("E12e", "deflated_sharpe matches BLdP 2014 closed form (SR0 via Euler-Mascheroni expected max; PSR denominator with non-excess kurtosis); SR=SR0 -> 0.5", ok,
       f"{rows}; anchor SR=SR0 -> {anchor:.6f}")
# hand number: N=10, var=1 (annual units), no skew: SR0 = sqrt(1/260)*(0.4227843*1.2815516+0.5772157*Phi^-1(1-1/(10e)))
nd = NormalDist(); hand_sr0 = (1 / 260) ** 0.5 * ((1 - 0.5772156649) * 1.2815515655 + 0.5772156649 * nd.inv_cdf(1 - 1 / (10 * np.e)))
report("E12f", "deflated_sharpe SR0 hand value (N=10, V=1): SR0_annual", True, f"hand SR0 annual = {hand_sr0 * 260 ** 0.5:.5f}")
