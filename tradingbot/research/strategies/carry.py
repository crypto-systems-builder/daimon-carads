"""Family E - Carry on daily bars, delay=2, 25 pairs equal weight. 18 configs.
Run: cd tradingbot/research && python3 strategies/carry.py"""
import itertools, json, os, statistics, sys, time
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fxlab  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "results", "carry")
TAUS = [0.0025, 0.01, 0.02]
FILTERS = ["none", "mom60", "mom120"]
KS = [3, 5]
STRESS = dict(delay=2, spread_mult=2.0, slip_pips=0.5, swap_markup=0.02)
BASE = dict(delay=2)


def make_signals(pair, h1, d1, params):
    r = fxlab.policy_rates()
    rb = r[pair[:3]].reindex(d1.index, method="ffill")
    rq = r[pair[3:]].reindex(d1.index, method="ffill")
    c = (rb - rq) / 100.0
    sig = np.sign(c).where(c.abs() > params["tau"], 0.0)
    f = params["filter"]
    if f != "none":
        L = int(f[3:])
        mom = np.sign(d1["mc"] / d1["mc"].shift(L) - 1.0)
        sig = sig.where(mom == np.sign(c), 0.0)
        sig = sig.where(mom.notna(), 0.0)
    stop = params["k"] * fxlab.atr(d1, 20)
    target = fxlab.daily_to_h1(sig, d1, h1).fillna(0.0).to_numpy()
    sd = fxlab.daily_to_h1(stop, d1, h1)
    sd = sd.bfill().to_numpy()  # NaN warm-up only matters where target==0 (atr NaN -> sig*... guarded below)
    atr_ok = fxlab.daily_to_h1(stop.notna().astype(float), d1, h1).fillna(0.0).to_numpy() > 0
    target = np.where(atr_ok, target, 0.0)
    sd = np.where(np.isfinite(sd) & (sd > 0), sd, 1.0)
    return target, sd, None, 0


def cid(tau, f, k):
    return f"E_tau{tau}_{f}_k{k}"


def row_metrics(res):
    return {k: v for k, v in res["portfolio"].items()}


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    tpath = os.path.join(OUT, "trials.jsonl")
    open(tpath, "w").close()
    pairs = fxlab.pairs_available("is")
    grid = list(itertools.product(TAUS, FILTERS, KS))
    cfg = {}
    for tau, f, k in grid:
        params = dict(tau=tau, filter=f, k=k)
        res = fxlab.run_basket(pairs, make_signals, params, **BASE)
        port = res["portfolio"]
        per = {p: {"sharpe": m["sharpe"], "total": m["total"], "trades": m["trades"]} for p, m in res["per_pair"].items()}
        cfg[cid(tau, f, k)] = dict(params=params, port=port, stress=None, idx=(TAUS.index(tau), FILTERS.index(f), KS.index(k)))
        fxlab.log_trial(tpath, dict(family="carry", config_id=cid(tau, f, k), costs="base", params=params, **port, per_pair=per))
        if port["sharpe"] >= 0.4 and port["pairs_positive"] >= 0.6 and port["trades"] >= 100:
            rs = fxlab.run_basket(pairs, make_signals, params, **STRESS)
            ps = rs["portfolio"]
            per_s = {p: {"sharpe": m["sharpe"], "total": m["total"], "trades": m["trades"]} for p, m in rs["per_pair"].items()}
            cfg[cid(tau, f, k)]["stress"] = ps
            fxlab.log_trial(tpath, dict(family="carry", config_id=cid(tau, f, k), costs="stress", params=params, **ps, per_pair=per_s))
        print(cid(tau, f, k), round(port["sharpe"], 3), flush=True)

    by_idx = {v["idx"]: n for n, v in cfg.items()}
    for n, v in cfg.items():
        nb = []
        for d, lens in enumerate((len(TAUS), len(FILTERS), len(KS))):
            for s in (-1, 1):
                j = list(v["idx"]); j[d] += s
                if 0 <= j[d] < lens:
                    nb.append(cfg[by_idx[tuple(j)]]["port"]["sharpe"])
        v["nms"] = float(statistics.median(nb))

    sharpes = [v["port"]["sharpe"] for v in cfg.values()]
    var = float(np.var(sharpes, ddof=1))
    order = sorted(cfg, key=lambda n: -cfg[n]["port"]["sharpe"])
    best = order[0]
    bp = cfg[best]["port"]
    dsr = fxlab.deflated_sharpe(bp["sharpe"], 18, var, bp["days"], bp["skew"], bp["kurt"])

    def entry(n):
        v = cfg[n]; p = v["port"]
        e = {"config_id": n, "params": v["params"]}
        for k in ["sharpe", "ann_ret", "ann_vol", "max_dd", "t_stat", "pairs_positive", "trades", "win_rate",
                  "avg_R", "profit_factor", "cost_ann", "pct_pos_years"]:
            e[k] = p[k]
        e["neighbour_median_sharpe"] = v["nms"]
        e["stress_sharpe"] = v["stress"]["sharpe"] if v["stress"] else None
        return e

    cand = None
    for n in order:
        v = cfg[n]; p = v["port"]
        if (p["sharpe"] >= 0.4 and p["pairs_positive"] >= 0.6 and v["nms"] >= 0.5 * p["sharpe"]
                and v["stress"] is not None and v["stress"]["sharpe"] >= 0.2 and p["trades"] >= 100):
            d = fxlab.deflated_sharpe(p["sharpe"], 18, var, p["days"], p["skew"], p["kurt"])
            cand = {"config_id": n, "params": v["params"], "sharpe": p["sharpe"], "stress_sharpe": v["stress"]["sharpe"],
                    "neighbour_median_sharpe": v["nms"], "dsr": d, "reason": "highest base Sharpe satisfying all 5 rule conditions"}
            break

    summary = {
        "family": "carry", "n_trials": 18,
        "grid": {"tau": TAUS, "filter": FILTERS, "k": KS, "delay": 2, "pairs": len(pairs)},
        "top5": [entry(n) for n in order[:5]],
        "median_config_sharpe": float(np.median(sharpes)),
        "share_configs_positive": float(np.mean([s > 0 for s in sharpes])),
        "best_config_dsr": dsr, "sr_var_annual": var,
        "all_configs": {n: {"sharpe": cfg[n]["port"]["sharpe"], "pairs_positive": cfg[n]["port"]["pairs_positive"],
                            "trades": cfg[n]["port"]["trades"], "nms": cfg[n]["nms"]} for n in cfg},
        "candidate": cand,
        "clues": "Best (still negative) configs share tau=0.02 with the mom60 filter and k=3 (best Sharpe -0.09, 346 trades); the 60-day trend filter is the only helpful dimension and k=3 beats k=5 in most neighbour pairs.",
        "losers_check": "Worst configs are mom120 and tau=0.01 none_k5 (-0.50), outside the mom60/tau=0.02 region; but all 18 configs are negative (0% positive, median -0.34), so there is no real winning region and differences are within noise.",
        "prediction_check": "No: pure carry Sharpe was -0.29 to -0.50 (predicted 0.0-0.4) and the best trend-filtered config was -0.09 (predicted 0.3-0.6).",
        "concerns": [
            "ENGINE LIMITATION: after a stop-out the engine does not re-enter the same direction until the target changes; carry signals change rarely, so unfiltered configs have only 17-40 trades total over 25 pairs and 4-16% pairs positive - once stopped, a pair stays flat for years. This tests carry-with-no-re-entry, not carry itself. Trades<100 also fails the screen for unfiltered configs.",
            "The momentum filter makes the target flip on/off so it re-enters; its slightly better results partly reflect re-entry, not trend information.",
            "Swap vs price split NOT measured: API cannot zero rates/markup. No config passed the screen so no stress runs exist for comparison.",
            "Low ann_vol (~0.2-0.9%) from 1% risk per trade at 3-5 ATR stops, equal weight over 25 pairs with many idle periods; Sharpe is scale-free but absolute returns are tiny.",
            "No lookahead found: rates reindexed ffill onto d1 dates, momentum from d1 closes, all mapped via daily_to_h1; ATR warm-up days forced flat."],
        "runtime_seconds": time.time() - t0,
    }
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=float)
    print(json.dumps({k: summary[k] for k in ("top5", "median_config_sharpe", "share_configs_positive", "best_config_dsr", "candidate")}, indent=1, default=float))


if __name__ == "__main__":
    main()
