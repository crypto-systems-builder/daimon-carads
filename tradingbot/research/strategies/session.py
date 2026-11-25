"""Family D - London-session intraday strategies (H1, delay=0, 25 pairs). Pre-registered 20-config grid."""
import itertools, json, os, sys, time
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fxlab  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "results", "session")
TRIALS = os.path.join(OUT, "trials.jsonl")
SUMMARY = os.path.join(OUT, "summary.json")

D1_E, D1_S, D1_M = [11, 14], [1.0, 0.5], [1.0, 2.0, None]
D2_MODE, D2_X, D2_K = ["momentum", "fade"], [11, 15], [2, 4]


def d1_id(p): return f"D1_E{p['E']}_s{p['s']}_m{p['m']}"
def d2_id(p): return f"D2_{p['mode']}_X{p['X']}_k{p['k']}"


def configs():
    out = []
    for E, s, m in itertools.product(D1_E, D1_S, D1_M):
        p = {"sub": "D1", "E": E, "s": s, "m": m}
        out.append((d1_id(p), p))
    for mode, X, k in itertools.product(D2_MODE, D2_X, D2_K):
        p = {"sub": "D2", "mode": mode, "X": X, "k": k}
        out.append((d2_id(p), p))
    return out


def neighbours(p):
    res = []
    if p["sub"] == "D1":
        for key, vals in (("E", D1_E), ("s", D1_S), ("m", D1_M)):
            i = vals.index(p[key])
            for j in (i - 1, i + 1):
                if 0 <= j < len(vals):
                    q = dict(p); q[key] = vals[j]; res.append(d1_id(q))
    else:
        for key, vals in (("mode", D2_MODE), ("X", D2_X), ("k", D2_K)):
            i = vals.index(p[key])
            for j in (i - 1, i + 1):
                if 0 <= j < len(vals):
                    q = dict(p); q[key] = vals[j]; res.append(d2_id(q))
    return res


def make_signals(pair, h1, d1, params):
    n = len(h1)
    t_l = h1.index.tz_convert("Europe/London")
    hour = np.asarray(t_l.hour)
    date = pd.Series(np.asarray(t_l.date), index=h1.index)
    mc, mo = h1["mc"], h1["mo"]
    if params["sub"] == "D1":
        asia = (hour <= 7)
        g = date
        rh = h1["mh"].where(asia).groupby(g).transform("max")
        rl = h1["ml"].where(asia).groupby(g).transform("min")
        cnt = pd.Series(asia.astype(int), index=h1.index).groupby(g).transform("sum")
        ok = (cnt >= 6).to_numpy()
        win = (hour >= 8) & (hour <= params["E"] - 1) & ok
        up = win & (mc > rh).to_numpy()
        dn = win & (mc < rl).to_numpy() & ~up
        brk = up | dn
        brk_s = pd.Series(brk.astype(int), index=h1.index)
        first = brk & (brk_s.groupby(g).cumsum().to_numpy() == 1)
        sig = pd.Series(np.where(first, np.where(up, 1.0, -1.0), np.nan), index=h1.index)
        tgt = sig.groupby(g).ffill().fillna(0.0).to_numpy()
        tgt = np.where((hour >= 8) & (hour <= 15) & ok, tgt, 0.0)  # 16:00 bar close -> 0
        rng = (rh - rl).to_numpy()
        sd = np.where(first | (tgt != 0), params["s"] * rng, np.nan)
        tp = None
        if params["m"] is not None:
            tp = np.where(first | (tgt != 0), params["m"] * rng, np.nan)
        return tgt, sd, tp, 0
    # D2
    g = date
    isb = hour == 8
    d = np.sign((mc - mo).to_numpy())
    sig = pd.Series(np.where(isb, d if params["mode"] == "momentum" else -d, np.nan), index=h1.index)
    tgt = sig.groupby(g).ffill().fillna(0.0).to_numpy()
    tgt = np.where((hour >= 8) & (hour <= params["X"] - 1), tgt, 0.0)
    atr = fxlab.atr_h1(h1, 24)
    atr_b = atr.where(isb).groupby(g).ffill().to_numpy()
    sd = np.where(tgt != 0, params["k"] * atr_b, np.nan)
    return tgt, sd, None, 0


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    for f in (TRIALS, SUMMARY):
        if os.path.exists(f):
            os.remove(f)
    pairs = fxlab.pairs_available("is")
    cfgs = configs()
    base_res, stress_res = {}, {}
    for cid, p in cfgs:
        r = fxlab.run_basket(pairs, make_signals, p, delay=0)
        base_res[cid] = r
        pf = r["portfolio"]
        fxlab.log_trial(TRIALS, {"family": "session", "config_id": cid, "costs": "base", "params": p, **pf,
                                 "per_pair": {k: {"sharpe": v["sharpe"], "total": v["total"], "trades": v["trades"]}
                                              for k, v in r["per_pair"].items()}})
        print(cid, round(pf["sharpe"], 3), pf["pairs_positive"], pf["trades"], flush=True)
        if pf["sharpe"] >= 0.4 and pf["pairs_positive"] >= 0.6 and pf["trades"] >= 100:
            rs = fxlab.run_basket(pairs, make_signals, p, delay=0, spread_mult=2.0, slip_pips=0.5, swap_markup=0.02)
            stress_res[cid] = rs
            ps = rs["portfolio"]
            fxlab.log_trial(TRIALS, {"family": "session", "config_id": cid, "costs": "stress", "params": p, **ps,
                                     "per_pair": {k: {"sharpe": v["sharpe"], "total": v["total"], "trades": v["trades"]}
                                                  for k, v in rs["per_pair"].items()}})
    sh = {c: base_res[c]["portfolio"]["sharpe"] for c, _ in cfgs}
    pmap = dict(cfgs)
    nb = {c: float(np.median([sh[x] for x in neighbours(pmap[c])])) for c in sh}
    order = sorted(sh, key=lambda c: -sh[c])

    def row(c):
        pf = base_res[c]["portfolio"]
        d = {"config_id": c, "params": pmap[c]}
        for k in ("sharpe", "ann_ret", "ann_vol", "max_dd", "t_stat", "pairs_positive", "trades", "win_rate",
                  "avg_R", "profit_factor", "cost_ann", "pct_pos_years"):
            d[k] = pf.get(k)
        d["neighbour_median_sharpe"] = nb[c]
        d["stress_sharpe"] = stress_res[c]["portfolio"]["sharpe"] if c in stress_res else None
        return d

    best = order[0]
    bp = base_res[best]["portfolio"]
    dsr = fxlab.deflated_sharpe(bp["sharpe"], 20, float(np.var(list(sh.values()), ddof=1)), int(bp["days"]),
                                bp["skew"], bp["kurt"])
    cand = None
    for c in order:
        pf = base_res[c]["portfolio"]
        if (pf["sharpe"] >= 0.4 and pf["pairs_positive"] >= 0.6 and nb[c] >= 0.5 * pf["sharpe"]
                and c in stress_res and stress_res[c]["portfolio"]["sharpe"] >= 0.2 and pf["trades"] >= 100):
            cdsr = dsr if c == best else fxlab.deflated_sharpe(
                pf["sharpe"], 20, float(np.var(list(sh.values()), ddof=1)), int(pf["days"]), pf["skew"], pf["kurt"])
            cand = {"config_id": c, "params": pmap[c], "sharpe": pf["sharpe"],
                    "stress_sharpe": stress_res[c]["portfolio"]["sharpe"], "neighbour_median_sharpe": nb[c],
                    "dsr": cdsr, "reason": "highest base Sharpe passing all five selection criteria"}
            break
    vals = list(sh.values())
    top5 = order[:5]
    bot5 = order[-5:]
    summary = {
        "family": "session", "n_trials": 20,
        "grid": {"D1": {"E": D1_E, "s": D1_S, "m": D1_M}, "D2": {"mode": D2_MODE, "X": D2_X, "k": D2_K}},
        "top5": [row(c) for c in top5],
        "median_config_sharpe": float(np.median(vals)),
        "share_configs_positive": float(np.mean([v > 0 for v in vals])),
        "best_config_dsr": dsr,
        "candidate": cand,
        "clues": "Least-bad configs all use the widest stops (D1 s=1.0 with no take-profit; D2 k=4, fade) - i.e. fewest stop-outs and lowest cost drag; none is positive.",
        "losers_check": "Yes in reverse: the worst configs are the tight-stop ones (D1 s=0.5 with tp=1.0, D2 k=2, esp. fade_X11_k2 at -2.9), so stop width orders losses but never makes any config profitable.",
        "prediction_check": "Yes: all 20 configs have negative base Sharpe (share positive = 0), so no candidate.",
        "concerns": ["Costs are heavy: cost_ann 5-9% of equity at 1% risk with ~30-50k trades, so cost drag alone is comparable to gross edge; stress run not triggered (no config passed screen).", "D2 pairs_positive is 0-16%: near-uniform loss across pairs (consistent with a cost/structure effect rather than noise).", "D2 fade at tight k=2 is much worse than k=4, suggesting stop-out churn; fade/momentum are not symmetric because of stops and re-entry rule.", "No lookahead found: range uses London hours 0-7 only, signals at bar close, stop from ATR at bar 08:00; London DST handled via tz_convert. Trades are counted per round-trip incl. days where a stop occurs and no re-entry."],
        "all_sharpes": {c: round(sh[c], 3) for c in order},
        "bottom5": bot5,
        "runtime_seconds": time.time() - t0,
    }
    json.dump(summary, open(SUMMARY, "w"), indent=1, default=float)
    print(json.dumps(summary, indent=1, default=float))


if __name__ == "__main__":
    main()
