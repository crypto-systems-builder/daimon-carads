"""Out-of-sample verdict for the frozen candidates. One-way door: run once.

    python3 oos_eval.py            # refuses unless candidates_frozen.json is committed to git

Reads results/candidates_frozen.json (written and committed BEFORE the OOS
data is unsealed), unseals the 2020+ data, runs every candidate with its
in-sample parameters unchanged, and applies the pre-registered verdict from
docs/lab-notebook.md:

  PASS   = OOS Sharpe >= 0.4 AND stress Sharpe >= 0.2 AND >= 4 of 7 OOS years
           positive AND OOS max drawdown <= 2.5x IS max drawdown
  STRONG = PASS and OOS t-stat >= 2.0
  KILL   = OOS Sharpe < 0.2          (in between: FAIL, not deployed)
If >= 2 candidates PASS, the equal-risk ensemble (each scaled by its IS
volatility) is evaluated too.
"""
import importlib
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

import fxlab as fx

HERE = os.path.dirname(os.path.abspath(__file__))
FROZEN = os.path.join(HERE, "results", "candidates_frozen.json")
OUT = os.path.join(HERE, "results", "oos_verdict.json")
OOS_START = pd.Timestamp(fx.OOS_START)
STRESS = dict(spread_mult=2.0, slip_pips=0.5, swap_markup=0.02)


def frozen_is_committed() -> bool:
    rel = os.path.relpath(FROZEN, subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=HERE, text=True).strip())
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=HERE, capture_output=True).returncode == 0
    clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=HERE).returncode == 0
    return tracked and clean


def split_metrics(daily: pd.Series, trades: pd.DataFrame, oos: bool) -> dict:
    idx = pd.DatetimeIndex(daily.index)
    mask = idx >= OOS_START if oos else idx < OOS_START
    d = daily[mask]
    t = trades
    if len(t):
        tin = pd.DatetimeIndex(t["t_in"]).tz_localize(None)
        t = t[(tin >= OOS_START) if oos else (tin < OOS_START)]
    m = fx.metrics(d, t)
    m["yearly"] = {str(k): float(v) for k, v in d.groupby(pd.DatetimeIndex(d.index).year).sum().items()}
    return m


def run_candidate(c: dict, **cost) -> dict:
    sys.path.insert(0, os.path.join(HERE, "strategies"))
    mod = importlib.import_module(c["module"])
    make = getattr(mod, c.get("function", "make_signals"))
    r = fx.run_basket(c["pairs"], make, c["params"], split="oos", delay=c["delay"], **cost)
    daily = r["daily"].sum(axis=1) / len(c["pairs"])
    return {"daily": daily, "trades": r["trades"], "per_pair_daily": r["daily"]}


def verdict(is_m: dict, oos_m: dict, stress_m: dict) -> str:
    years_pos = sum(v > 0 for v in oos_m["yearly"].values())
    passed = (oos_m["sharpe"] >= 0.4 and stress_m["sharpe"] >= 0.2 and years_pos >= 4
              and abs(oos_m["max_dd"]) <= 2.5 * abs(is_m["max_dd"]))
    if passed:
        return "STRONG" if oos_m["t_stat"] >= 2.0 else "PASS"
    return "KILL" if oos_m["sharpe"] < 0.2 else "FAIL"


def main():
    if not frozen_is_committed():
        sys.exit("refusing: results/candidates_frozen.json must be committed (and unchanged) before unsealing")
    if not os.path.isdir(os.path.join(fx.DATA, "oos", "h1")):
        subprocess.run([sys.executable, os.path.join(HERE, "build_dataset.py"), "unseal"], check=True)
    cands = [c for c in json.load(open(FROZEN))["candidates"] if c.get("params") is not None]
    out, series = {"candidates": []}, {}
    for c in cands:
        base = run_candidate(c)
        stress = run_candidate(c, **STRESS)
        is_m = split_metrics(base["daily"], base["trades"], oos=False)
        oos_m = split_metrics(base["daily"], base["trades"], oos=True)
        st_m = split_metrics(stress["daily"], stress["trades"], oos=True)
        v = verdict(is_m, oos_m, st_m)
        series[c["family"]] = base["daily"]
        out["candidates"].append({"family": c["family"], "config_id": c["config_id"], "verdict": v,
                                  "is": is_m, "oos": oos_m, "oos_stress": st_m,
                                  "agent_reported_is_sharpe": c.get("is_sharpe")})
        print(f"{c['family']:10s} {c['config_id']:24s} IS {is_m['sharpe']:+.2f} | OOS {oos_m['sharpe']:+.2f} "
              f"(t {oos_m['t_stat']:+.2f}, dd {oos_m['max_dd']:.3f}, yrs+ {sum(x > 0 for x in oos_m['yearly'].values())}/"
              f"{len(oos_m['yearly'])}) | stress {st_m['sharpe']:+.2f} -> {v}")
    passing = [c["family"] for c in out["candidates"] if c["verdict"] in ("PASS", "STRONG")]
    if len(passing) >= 2:
        is_mask = lambda s: pd.DatetimeIndex(s.index) < OOS_START
        scaled = [series[f] / series[f][is_mask(series[f])].std() for f in passing]
        ens = pd.concat(scaled, axis=1).fillna(0.0).mean(axis=1)
        e_is = fx.metrics(ens[is_mask(ens)])
        e_oos = fx.metrics(ens[~is_mask(ens)])
        out["ensemble"] = {"members": passing, "is": e_is, "oos": e_oos,
                           "beats_best_single": e_oos["sharpe"] > max(
                               c["oos"]["sharpe"] for c in out["candidates"] if c["family"] in passing)}
        print(f"ENSEMBLE {passing}: IS {e_is['sharpe']:+.2f} | OOS {e_oos['sharpe']:+.2f}")
    json.dump(out, open(OUT, "w"), indent=1, default=float)
    print("written", OUT)


if __name__ == "__main__":
    main()
