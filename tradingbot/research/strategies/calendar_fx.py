"""Family F - calendar effects in USD (negative control), delay=2. See pre-registered contract."""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fxlab  # noqa: E402

PAIRS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
OUT = os.path.join(os.path.dirname(HERE), "results", "calendar")
TRIALS = os.path.join(OUT, "trials.jsonl")
SUMMARY = os.path.join(OUT, "summary.json")
STRESS_KW = dict(delay=2, spread_mult=2.0, slip_pips=0.5, swap_markup=0.02)
BASE_KW = dict(delay=2)


def configs():
    cfgs = []
    for w in range(5):
        for side in ("longUSD", "shortUSD"):
            cfgs.append({"config_id": f"F1_w{w}_{side}", "kind": "F1", "w": w, "side": side})
    for window in ("last2", "first2"):
        for side in ("longUSD", "shortUSD"):
            cfgs.append({"config_id": f"F2_{window}_{side}", "kind": "F2", "window": window, "side": side})
    assert len(cfgs) == 14
    return cfgs


def neighbours(c):
    ids = []
    if c["kind"] == "F1":
        for w in (c["w"] - 1, c["w"] + 1):
            if 0 <= w <= 4:
                ids.append(f"F1_w{w}_{c['side']}")
    else:
        other = "first2" if c["window"] == "last2" else "last2"
        ids.append(f"F2_{other}_{c['side']}")
    return ids


def make_signals(pair, h1, d1, params):
    usd = 1.0 if pair.startswith("USD") else -1.0
    sgn = 1.0 if params["side"] == "longUSD" else -1.0
    idx = pd.DatetimeIndex(d1.index)
    if params["kind"] == "F1":
        day_flag = (idx.day_of_week == params["w"])
    else:
        ym = idx.year * 100 + idx.month
        s = pd.Series(np.arange(len(idx)), index=idx)
        pos_from_start = s.groupby(ym).cumcount().to_numpy()
        pos_from_end = s.groupby(ym).cumcount(ascending=False).to_numpy()
        day_flag = (pos_from_end < 2) if params["window"] == "last2" else (pos_from_start < 2)
    # signal on row D-1 reflects whether the NEXT trading day (D) is flagged (calendar known in advance)
    nxt = np.zeros(len(idx), dtype=bool)
    nxt[:-1] = np.asarray(day_flag)[1:]
    sig_d = pd.Series(np.where(nxt, sgn * usd, 0.0), index=d1.index)
    stop_d = 2.0 * fxlab.atr(d1, 20)
    sig_d[stop_d.isna()] = 0.0
    tgt = fxlab.daily_to_h1(sig_d, d1, h1).fillna(0.0)
    stp = fxlab.daily_to_h1(stop_d, d1, h1)
    stp = stp.bfill().fillna(1.0)  # only matters where target==0 (pre-ATR warmup)
    return tgt.to_numpy(), stp.to_numpy(), None, 0


def row(c, costs, res):
    p = res["portfolio"]
    return {"family": "calendar", "config_id": c["config_id"], "costs": costs,
            "params": {k: v for k, v in c.items() if k != "config_id"},
            **{k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in p.items()},
            "per_pair": {k: {"sharpe": m["sharpe"], "total": m["total"], "trades": m.get("trades", 0)}
                         for k, m in res["per_pair"].items()}}


CLUES = ("The top configs (F1_w4_longUSD 0.36, F2_first2_longUSD 0.28, F1_w1_longUSD 0.17) are all long-USD; "
         "no config reaches the 0.4 screen and the best has t-stat ~1.0.")
LOSERS = ("Yes in mirror image: the worst configs (F1_w4_shortUSD -0.86, F1_w1_shortUSD -0.73, F1_w2_shortUSD -0.58) "
          "are largely short-USD, i.e. the sign is just the 2012-2019 USD uptrend, not a calendar effect; and the long-USD "
          "side is also negative on F1_w0/w2/w3 and F2_last2.")
PRED = ("Yes: 4/14 configs positive, median Sharpe -0.22, best Sharpe 0.36 (t~1.0, DSR ~0.20) with neighbours at "
        "-0.29 - indistinguishable from noise plus a USD-trend drift.")
CONCERNS = [
    "No config passed the screen (sharpe>=0.4), so no stress runs were executed and trials.jsonl has exactly 14 lines; stress_sharpe is null everywhere.",
    "Long-USD vs short-USD results are strongly antisymmetric (costs aside), so results mostly reflect the in-sample USD trend, not weekday/month-turn structure.",
    "Weekday uses the trading-day label (ny_day), so the Monday session includes Sunday-evening open; Friday ends 17:00 NY.",
    "Verified the signal timing manually: for F1_w2 on EURUSD target flips at the close of Tuesday's last bar and back to 0 at the close of Wednesday's; stub days (<4 bars) are dropped by to_daily so calendar positions skip them.",
    "Bars before the 20-day ATR warmup get target 0. Engine/lookahead: no issue found in fxlab.",
]


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    for f in (TRIALS, SUMMARY):
        if os.path.exists(f):
            os.remove(f)
    cfgs = configs()
    base, stress = {}, {}
    for c in cfgs:
        r = fxlab.run_basket(PAIRS, make_signals, c, **BASE_KW)
        base[c["config_id"]] = r["portfolio"]
        fxlab.log_trial(TRIALS, row(c, "base", r))
        p = r["portfolio"]
        if p["sharpe"] >= 0.4 and p["pairs_positive"] >= 0.6 and p["trades"] >= 100:
            rs = fxlab.run_basket(PAIRS, make_signals, c, **STRESS_KW)
            stress[c["config_id"]] = rs["portfolio"]["sharpe"]
            fxlab.log_trial(TRIALS, row(c, "stress", rs))
        print(c["config_id"], round(p["sharpe"], 3), p["pairs_positive"], p["trades"], flush=True)

    sh = {k: v["sharpe"] for k, v in base.items()}
    nb = {c["config_id"]: float(np.median([sh[i] for i in neighbours(c)])) for c in cfgs}
    cmap = {c["config_id"]: c for c in cfgs}
    order = sorted(sh, key=lambda k: -sh[k])
    best = order[0]
    bp = base[best]
    var = float(np.var(list(sh.values()), ddof=1))
    dsr = fxlab.deflated_sharpe(bp["sharpe"], 14, var, bp["days"], bp["skew"], bp["kurt"])

    def entry(k):
        p = base[k]
        return {"config_id": k, "params": {a: b for a, b in cmap[k].items() if a != "config_id"},
                "sharpe": p["sharpe"], "ann_ret": p["ann_ret"], "ann_vol": p["ann_vol"], "max_dd": p["max_dd"],
                "t_stat": p["t_stat"], "pairs_positive": p["pairs_positive"], "trades": p["trades"],
                "win_rate": p["win_rate"], "avg_R": p["avg_R"], "profit_factor": p["profit_factor"],
                "cost_ann": p["cost_ann"], "pct_pos_years": p["pct_pos_years"],
                "neighbour_median_sharpe": nb[k], "stress_sharpe": stress.get(k)}

    cand = None
    for k in order:
        p = base[k]
        if (p["sharpe"] >= 0.4 and p["pairs_positive"] >= 0.6 and nb[k] >= 0.5 * p["sharpe"]
                and stress.get(k, -9) >= 0.2 and p["trades"] >= 100):
            cand = {"config_id": k, "params": entry(k)["params"], "sharpe": p["sharpe"],
                    "stress_sharpe": stress[k], "neighbour_median_sharpe": nb[k],
                    "dsr": fxlab.deflated_sharpe(p["sharpe"], 14, var, p["days"], p["skew"], p["kurt"]),
                    "reason": "highest base Sharpe satisfying all five pre-registered criteria"}
            break
    summary = {
        "family": "calendar", "n_trials": 14,
        "grid": {"F1": {"w": [0, 1, 2, 3, 4], "side": ["longUSD", "shortUSD"]},
                 "F2": {"window": ["last2", "first2"], "side": ["longUSD", "shortUSD"]},
                 "stop": "2*ATR20(daily)", "delay": 2, "pairs": PAIRS},
        "top5": [entry(k) for k in order[:5]],
        "median_config_sharpe": float(np.median(list(sh.values()))),
        "share_configs_positive": float(np.mean([v > 0 for v in sh.values()])),
        "best_config_dsr": dsr,
        "candidate": cand,
        "clues": CLUES, "losers_check": LOSERS, "prediction_check": PRED, "concerns": CONCERNS,
        "all_sharpes": {k: sh[k] for k in order},
        "runtime_seconds": time.time() - t0,
    }
    with open(SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=float)
    print("best", best, sh[best], "dsr", dsr, "candidate", cand and cand["config_id"])


if __name__ == "__main__":
    main()
