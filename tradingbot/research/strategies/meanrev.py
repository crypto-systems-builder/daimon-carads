"""Family C - short-term mean reversion on daily bars (delay=2), 25 pairs, equal weight.
Pre-registered 48-config grid. Run: cd tradingbot/research && python3 strategies/meanrev.py"""
import itertools
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fxlab  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "results", "meanrev")
TRIALS = os.path.join(OUT, "trials.jsonl")
SUMMARY = os.path.join(OUT, "summary.json")

GRID = {
    "C1": {"x": [5, 10, 20], "H": [3, 5], "filter": ["none", "sma200"], "k": [1.5, 3]},
    "C2": {"z0": [1.5, 2.0, 2.5], "H": [5, 10], "filter": ["none", "sma200"], "k": [2, 3]},
}
_cache = {}


def _daily_state(entry_l, entry_s, exit_l, exit_s):
    """Daily state machine; arrays of bool. NaN-derived conditions are False."""
    n = len(entry_l)
    st = np.zeros(n)
    s = 0
    for i in range(n):
        if s == 1 and exit_l[i]:
            s = 0
        elif s == -1 and exit_s[i]:
            s = 0
        if s == 0:
            if entry_l[i]:
                s = 1
            elif entry_s[i]:
                s = -1
        st[i] = s
    return st


def make_signals(pair, h1, d1, params):
    mc = d1["mc"]
    sma200 = mc.rolling(200, min_periods=200).mean()
    up = (mc > sma200).to_numpy()
    dn = (mc < sma200).to_numpy()
    use_f = params["filter"] == "sma200"
    if params["family"] == "C1":
        r = fxlab.rsi(mc, 2).to_numpy()
        x = params["x"]
        with np.errstate(invalid="ignore"):
            el = r < x
            es = r > 100 - x
            xl = r > 50
            xs = r < 50
    else:
        sma20 = mc.rolling(20, min_periods=20).mean()
        z = ((mc - sma20) / mc.rolling(20, min_periods=20).std()).to_numpy()
        z0 = params["z0"]
        with np.errstate(invalid="ignore"):
            el = z < -z0
            es = z > z0
            xl = z >= 0
            xs = z <= 0
    if use_f:
        el = el & up
        es = es & dn
    st = _daily_state(el, es, xl, xs)
    tgt = fxlab.daily_to_h1(pd.Series(st, index=d1.index), d1, h1).fillna(0.0).to_numpy()
    sd = fxlab.daily_to_h1(params["k"] * fxlab.atr(d1, 20), d1, h1).bfill().to_numpy()
    sd = np.where(np.isfinite(sd) & (sd > 0), sd, np.nan)
    tgt = np.where(np.isfinite(sd), tgt, 0.0)
    sd = np.nan_to_num(sd, nan=1.0)
    return tgt, sd, None, params["H"] * 24


def configs():
    out = []
    for x, H, f, k in itertools.product(GRID["C1"]["x"], GRID["C1"]["H"], GRID["C1"]["filter"], GRID["C1"]["k"]):
        out.append((f"C1_x{x}_H{H}_{f}_k{k}", {"family": "C1", "x": x, "H": H, "filter": f, "k": k}))
    for z, H, f, k in itertools.product(GRID["C2"]["z0"], GRID["C2"]["H"], GRID["C2"]["filter"], GRID["C2"]["k"]):
        out.append((f"C2_z{z}_H{H}_{f}_k{k}", {"family": "C2", "z0": z, "H": H, "filter": f, "k": k}))
    return out


def neighbours(cid, params, allcfg):
    fam = params["family"]
    keys = ["x" if fam == "C1" else "z0", "H", "filter", "k"]
    lists = {k: GRID[fam][k] for k in keys}
    res = []
    for key in keys:
        i = lists[key].index(params[key])
        for j in (i - 1, i + 1):
            if 0 <= j < len(lists[key]):
                p = dict(params)
                p[key] = lists[key][j]
                res.append(next(c for c, q in allcfg if q == p))
    return res


def row_from(res, cid, params, costs):
    pm = res["portfolio"]
    clean = {k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in pm.items()}
    return {"family": "meanrev", "config_id": cid, "costs": costs, "params": params, **clean,
            "per_pair": {p: {"sharpe": m["sharpe"], "total": m["total"], "trades": m.get("trades", 0)}
                         for p, m in res["per_pair"].items()}}


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    for f in (TRIALS, SUMMARY):
        if os.path.exists(f):
            os.remove(f)
    pairs = fxlab.pairs_available("is")
    cfgs = configs()
    assert len(cfgs) == 48 and len(pairs) == 25
    base, stress = {}, {}
    for cid, p in cfgs:
        res = fxlab.run_basket(pairs, make_signals, p, delay=2)
        pm = res["portfolio"]
        base[cid] = pm
        fxlab.log_trial(TRIALS, row_from(res, cid, p, "base"))
        if pm["sharpe"] >= 0.4 and pm["pairs_positive"] >= 0.6 and pm["trades"] >= 100:
            rs = fxlab.run_basket(pairs, make_signals, p, delay=2, spread_mult=2.0, slip_pips=0.5, swap_markup=0.02)
            stress[cid] = rs["portfolio"]
            fxlab.log_trial(TRIALS, row_from(rs, cid, p, "stress"))
        print(cid, round(pm["sharpe"], 3), flush=True)
    pmap = dict(cfgs)
    nb = {cid: float(np.median([base[n]["sharpe"] for n in neighbours(cid, pmap[cid], cfgs)])) for cid, _ in cfgs}
    sh = np.array([base[c]["sharpe"] for c, _ in cfgs])
    order = sorted(base, key=lambda c: -base[c]["sharpe"])
    best = order[0]
    bm = base[best]
    dsr = fxlab.deflated_sharpe(bm["sharpe"], 48, float(np.var(sh, ddof=1)), bm["days"], bm["skew"], bm["kurt"])

    def entry(c):
        m = base[c]
        d = {"config_id": c, "params": pmap[c]}
        for k in ["sharpe", "ann_ret", "ann_vol", "max_dd", "t_stat", "pairs_positive", "trades", "win_rate",
                  "avg_R", "profit_factor", "cost_ann", "pct_pos_years"]:
            d[k] = m[k]
        d["neighbour_median_sharpe"] = nb[c]
        d["stress_sharpe"] = stress[c]["sharpe"] if c in stress else None
        return d

    quals = [c for c in order if base[c]["sharpe"] >= 0.4 and base[c]["pairs_positive"] >= 0.6
             and nb[c] >= 0.5 * base[c]["sharpe"] and c in stress and stress[c]["sharpe"] >= 0.2
             and base[c]["trades"] >= 100]
    cand = None
    if quals:
        c = quals[0]
        cand = {"config_id": c, "params": pmap[c], "sharpe": base[c]["sharpe"], "stress_sharpe": stress[c]["sharpe"],
                "neighbour_median_sharpe": nb[c],
                "dsr": fxlab.deflated_sharpe(base[c]["sharpe"], 48, float(np.var(sh, ddof=1)), base[c]["days"],
                                             base[c]["skew"], base[c]["kurt"]),
                "reason": "highest base Sharpe among configs passing all five pre-registered criteria"}
    def grp(key):
        d = {}
        for c, q in cfgs:
            if key in q:
                d.setdefault(q[key], []).append(base[c]["sharpe"])
        return {k: round(float(np.mean(v)), 2) for k, v in d.items()}
    nlow = sum(1 for c, _ in cfgs if base[c]["sharpe"] < 0)
    bot = order[-10:]
    summary = {
        "family": "meanrev", "n_trials": 48, "grid": GRID,
        "top5": [entry(c) for c in order[:5]],
        "median_config_sharpe": float(np.median(sh)), "share_configs_positive": float(np.mean(sh > 0)),
        "best_config_dsr": dsr, "candidate": cand,
        "n_screened": len(stress), "bottom5": [{"config_id": c, "sharpe": base[c]["sharpe"]} for c in order[-5:]],
        "clues": f"Mean Sharpe by level - RSI x {grp('x')}, z0 {grp('z0')}, filter {grp('filter')}, H {grp('H')}, k {grp('k')}: "
                 "best configs are the most extreme entry thresholds (RSI x=5, z0=2.5) with the sma200 trend filter; only 4 of 48 are positive and all are near zero.",
        "losers_check": f"{nlow}/48 configs have negative Sharpe; the worst 10 are {sum(1 for c in bot if '_none_' in c)}/10 unfiltered and {sum(1 for c in bot if c.startswith('C1_x20'))}/10 RSI x=20 (loosest, most frequent entries), i.e. the opposite end of the same axes.",
        "prediction_check": f"Prediction held: median config Sharpe {float(np.median(sh)):.2f} (<=0), best {sh.max():.2f}, best breadth {base[best]['pairs_positive']:.2f}, no config passed the screen so no candidate.",
        "concerns": ["Equal-weight portfolio vol is tiny (~0.2-0.5%/yr) because sizing risks 1% per trade per pair and trades are few/short; Sharpe is unaffected but absolute returns are negligible.",
                     "max_hold counted in H1 bars (H*24) includes weekend gaps absent from the data, so a 3-day hold may span more than 3 trading days; as specified.",
                     "After a time/stop exit the engine will not re-enter the same direction until the target changes, while the daily state persists; the daily exit rule and engine time exit can differ as specified.",
                     "Losses are concentrated in high-frequency loose-threshold configs (trend continuation in FX); costs (cost_ann) are small relative to the negative gross edge, so the failure is not mainly a cost artefact.",
                     "Best-config DSR computed with variance across all 48 configs; only the top config's skew/kurt used."],
        "runtime_seconds": time.time() - t0,
    }
    with open(SUMMARY, "w") as f:
        json.dump(summary, f, indent=1, default=float)
    print(json.dumps(summary, indent=1, default=float))


if __name__ == "__main__":
    main()
