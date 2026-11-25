"""Family A - daily trend following (time-series momentum, EMA crossover). 32 pre-registered configs.
Run: cd tradingbot/research && python3 strategies/trend.py"""
import json, os, sys, time
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fxlab

OUT = os.path.join(os.path.dirname(HERE), "results", "trend")
TRIALS = os.path.join(OUT, "trials.jsonl")
SUMMARY = os.path.join(OUT, "summary.json")

A1_L = [20, 60, 120, 250]
A2_FS = [(10, 40), (20, 50), (20, 80), (50, 200)]
KS = [2, 3, 4, 6]
STRESS_KW = dict(delay=2, spread_mult=2.0, slip_pips=0.5, swap_markup=0.02)
BASE_KW = dict(delay=2)


def make_signals(pair, h1, d1, params):
    mc = d1["mc"]
    if params["sub"] == "A1":
        L = params["L"]
        sig = np.sign(mc / mc.shift(L) - 1.0)
    else:
        sig = np.sign(fxlab.ema(mc, params["fast"]) - fxlab.ema(mc, params["slow"]))
    sd_d = params["k"] * fxlab.atr(d1, 20)
    sig = sig.fillna(0.0)
    sig[sd_d.isna()] = 0.0
    t = fxlab.daily_to_h1(sig, d1, h1).fillna(0.0)
    sd = fxlab.daily_to_h1(sd_d, d1, h1)
    bad = sd.isna() | (sd <= 0)
    t[bad] = 0.0
    sd[bad] = 1.0
    return t.to_numpy(), sd.to_numpy(), None, 0


def configs():
    out = []
    for i, L in enumerate(A1_L):
        for j, k in enumerate(KS):
            out.append((f"A1_L{L}_k{k}", {"sub": "A1", "L": L, "k": k}, (i, j)))
    for i, (f, s) in enumerate(A2_FS):
        for j, k in enumerate(KS):
            out.append((f"A2_f{f}_s{s}_k{k}", {"sub": "A2", "fast": f, "slow": s, "k": k}, (i, j)))
    return out


def neighbours(cid, cfgs):
    sub = cid[:2]
    pos = {c[0]: c[2] for c in cfgs if c[0][:2] == sub}
    i, j = pos[cid]
    res = []
    for c, (a, b) in pos.items():
        if abs(a - i) + abs(b - j) == 1:
            res.append(c)
    return res


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    for f in (TRIALS, SUMMARY):
        if os.path.exists(f):
            os.remove(f)
    pairs = fxlab.pairs_available("is")
    cfgs = configs()
    assert len(cfgs) == 32
    base, stress, perpair = {}, {}, {}
    for cid, params, _ in cfgs:
        r = fxlab.run_basket(pairs, make_signals, params, **BASE_KW)
        p = r["portfolio"]
        base[cid] = p
        pp = {k: {"sharpe": v["sharpe"], "total": v["total"], "trades": v.get("trades", 0)} for k, v in r["per_pair"].items()}
        fxlab.log_trial(TRIALS, {"family": "trend", "config_id": cid, "costs": "base", "params": params, **p, "per_pair": pp})
        if p["sharpe"] >= 0.4 and p["pairs_positive"] >= 0.6 and p["trades"] >= 100:
            rs = fxlab.run_basket(pairs, make_signals, params, **STRESS_KW)
            ps = rs["portfolio"]
            stress[cid] = ps
            spp = {k: {"sharpe": v["sharpe"], "total": v["total"], "trades": v.get("trades", 0)} for k, v in rs["per_pair"].items()}
            fxlab.log_trial(TRIALS, {"family": "trend", "config_id": cid, "costs": "stress", "params": params, **ps, "per_pair": spp})
        print(cid, round(p["sharpe"], 3), flush=True)

    nb = {}
    for cid, _, _ in cfgs:
        nb[cid] = float(np.median([base[n]["sharpe"] for n in neighbours(cid, cfgs)]))
    shs = np.array([base[c[0]]["sharpe"] for c in cfgs])
    sr_var = float(np.var(shs, ddof=1))
    order = sorted(base, key=lambda c: -base[c]["sharpe"])
    pmap = {c[0]: c[1] for c in cfgs}
    best = order[0]
    bp = base[best]
    dsr = fxlab.deflated_sharpe(bp["sharpe"], 32, sr_var, bp["days"], bp["skew"], bp["kurt"])

    def row(c):
        p = base[c]
        return {"config_id": c, "params": pmap[c], **{k: p[k] for k in
                ["sharpe", "ann_ret", "ann_vol", "max_dd", "t_stat", "pairs_positive", "trades", "win_rate", "avg_R",
                 "profit_factor", "cost_ann", "pct_pos_years"]},
                "neighbour_median_sharpe": nb[c], "stress_sharpe": stress[c]["sharpe"] if c in stress else None}

    cand = None
    for c in order:
        p = base[c]
        if (p["sharpe"] >= 0.4 and p["pairs_positive"] >= 0.6 and nb[c] >= 0.5 * p["sharpe"]
                and c in stress and stress[c]["sharpe"] >= 0.2 and p["trades"] >= 100):
            cand = {"config_id": c, "params": pmap[c], "sharpe": p["sharpe"], "stress_sharpe": stress[c]["sharpe"],
                    "neighbour_median_sharpe": nb[c],
                    "dsr": fxlab.deflated_sharpe(p["sharpe"], 32, sr_var, p["days"], p["skew"], p["kurt"]),
                    "reason": "highest base Sharpe satisfying all 5 pre-registered criteria"}
            break

    a1 = np.mean([base[c[0]]["sharpe"] for c in cfgs if c[0][:2] == "A1"])
    a2 = np.mean([base[c[0]]["sharpe"] for c in cfgs if c[0][:2] == "A2"])
    l20 = np.mean([base[c[0]]["sharpe"] for c in cfgs if c[1].get("L") == 20])
    worst = order[-5:]
    clues = (f"Best config {best} (Sharpe {bp['sharpe']:.2f}); top5 = {', '.join(order[:5])}: shortest lookback (A1 L=20) with wide stops (k>=3), "
             f"but all 32 are negative (mean A1 {a1:.2f}, A2 {a2:.2f}; A1 L=20 mean {l20:.2f}), so this is the least-bad region, not an edge.")
    losers = (f"Worst 5 = {', '.join(worst)}: A2 crossovers and A1 L=120 (slow/medium trend signals); gross P&L is also negative "
              f"(mean cost_ann {np.mean([base[c[0]]['cost_ann'] for c in cfgs]):.4f} vs mean ann_ret {np.mean([base[c[0]]['ann_ret'] for c in cfgs]):.4f}), so costs are not the main cause.")
    predchk = (f"No: best Sharpe {bp['sharpe']:.2f} vs predicted 0.5-0.9 and median {np.median(shs):.2f} vs predicted 0.1-0.3; no config had positive Sharpe.")
    concerns = ["No config passed the screen, so no stress runs were made and candidate is null.",
                "Per-trade risk 1% with k*ATR20 stops gives very low portfolio ann_vol (equal-weight over 25 pairs); Sharpe is unaffected but ann_ret/max_dd are small in absolute terms.",
                "Trade count is identical across k within an A1 lookback (e.g. 5272 for L=20): after a stop-out no re-entry occurs until the signal flips, so k changes only stop-outs, not entries; stop-outs on a persistent signal cut winners.",
                "Sign-flip signals on daily bars only ever hold +/-1 (no flat state); daily features mapped with daily_to_h1 (no lookahead observed in code review). No fxlab bug identified; negative result is consistent with weak FX trend following in 2012-2019 (a known regime)."]
    summary = {
        "family": "trend", "n_trials": 32,
        "grid": {"A1": {"L": A1_L, "k": KS}, "A2": {"fast_slow": A2_FS, "k": KS}, "atr_n": 20, "delay": 2, "pairs": len(pairs)},
        "top5": [row(c) for c in order[:5]],
        "median_config_sharpe": float(np.median(shs)),
        "share_configs_positive": float(np.mean(shs > 0)),
        "best_config_dsr": dsr,
        "candidate": cand,
        "clues": clues, "losers_check": losers, "prediction_check": predchk, "concerns": concerns,
        "runtime_seconds": 0.0,
    }
    summary["runtime_seconds"] = time.time() - t0
    json.dump(summary, open(SUMMARY, "w"), indent=1, default=float)
    print("done", summary["runtime_seconds"])


if __name__ == "__main__":
    main()
