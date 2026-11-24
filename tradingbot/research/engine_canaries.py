"""Falsification tests for fxlab's simulator. Run: python3 engine_canaries.py

Each canary has a prediction that must hold if the engine is sound. A broken
engine (lookahead, mis-signed costs, wrong fills) fails at least one of them.
Predictions were written down before the first run (see docs/lab-notebook.md).
"""
import sys

import numpy as np
import pandas as pd

import fxlab as fx

PAIRS = fx.pairs_available("is")
fails = []


def daily_strategy(fn, **sim):
    def make(pair, h1, d1, params):
        sig = fn(d1)
        target = fx.daily_to_h1(sig, d1, h1)
        sd = fx.daily_to_h1(params.get("k", 3.0) * fx.atr(d1, 20), d1, h1)
        return target, sd, None, 0
    return make


def check(name, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    if not ok:
        fails.append(name)


# C1 oracle: knows tomorrow's direction. Must make money on every pair.
oracle = daily_strategy(lambda d1: np.sign(d1["mc"].shift(-1) - d1["mc"]))
r = fx.run_basket(PAIRS, oracle, {"k": 3.0}, delay=0)
s = [m["sharpe"] for m in r["per_pair"].values()]
check("C1 oracle", min(s) > 3.0, f"min pair Sharpe {min(s):.2f}, median {np.median(s):.2f}")

# C2 random coin flips, base costs: costs must make the average negative
rng = np.random.default_rng(7)
rand = daily_strategy(lambda d1: pd.Series(rng.choice([-1, 1], len(d1)), index=d1.index))
r = fx.run_basket(PAIRS, rand, {"k": 3.0}, delay=1)
s = np.array([m["sharpe"] for m in r["per_pair"].values()])
check("C2 random+costs", -1.2 < s.mean() < 0.0 and s.max() < 1.2,
      f"mean {s.mean():.2f}, max {s.max():.2f}, portfolio {r['portfolio']['sharpe']:.2f}")

# C3 random, zero friction (no spread/slippage/markup): average ~0
rng = np.random.default_rng(7)
r0 = fx.run_basket(PAIRS, rand, {"k": 3.0}, delay=1, spread_mult=0.0, slip_pips=0.0, swap_markup=0.0)
s0 = np.array([m["sharpe"] for m in r0["per_pair"].values()])
check("C3 random frictionless", abs(s0.mean()) < 0.2, f"mean {s0.mean():.2f}, sd {s0.std():.2f}")
check("C3b costs hurt", s.mean() < s0.mean(), f"with costs {s.mean():.2f} < without {s0.mean():.2f}")

# C4 lookahead trap: yesterday's oracle (stale by one day) must NOT keep the edge
stale = daily_strategy(lambda d1: np.sign(d1["mc"] - d1["mc"].shift(1)).shift(1))
r = fx.run_basket(PAIRS, stale, {"k": 3.0}, delay=0)
check("C4 stale oracle", abs(r["portfolio"]["sharpe"]) < 1.5, f"portfolio Sharpe {r['portfolio']['sharpe']:.2f}")

# C5 buy & hold EURUSD with an unreachable stop: sign follows price + carry
h1 = fx.load_h1("EURUSD")
res = fx.simulate("EURUSD", h1, np.ones(len(h1)), np.full(len(h1), 10.0), risk=0.01)
px_move = h1["mc"].iloc[-1] - h1["mo"].iloc[1]
units = 0.01 / 10.0
check("C5 buy&hold EURUSD", np.sign(res["ret"].sum()) == np.sign(px_move) and len(res["trades"]) == 0,
      f"strategy {res['ret'].sum():+.5f} vs price-only {units * px_move:+.5f} (diff = carry+costs)")

# C6 round-trip cost: open+close immediately, measured in pips vs data spread
pip = fx.pip_size("EURUSD")
tgt = np.zeros(len(h1))
tgt[1000:1001] = 1    # one-bar trade
res = fx.simulate("EURUSD", h1, tgt, np.full(len(h1), 0.01), risk=0.01, slip_pips=0.2)
tr = res["trades"].iloc[0]
# entry at open of bar 1001 (ask + slip), exit at open of bar 1002 (bid - slip)
spread_in = (h1["ao"].iloc[1001] - h1["bo"].iloc[1001]) / pip
spread_out = (h1["ao"].iloc[1002] - h1["bo"].iloc[1002]) / pip
mid_move = (h1["mo"].iloc[1002] - h1["mo"].iloc[1001]) / pip
paid = mid_move - (tr["px_out"] - tr["px_in"]) / pip
expected = spread_in / 2 + spread_out / 2 + 0.4
check("C6 round-trip cost", int(tr["i_in"]) == 1001 and int(tr["i_out"]) == 1002 and abs(paid - expected) < 0.05,
      f"paid {paid:.2f} pips vs expected {expected:.2f} (entry bar {int(tr['i_in'])}, exit bar {int(tr['i_out'])})")

# C7 stop discipline: with a 1-pip stop nearly every trade is stopped and loses ~1R
res = fx.simulate("EURUSD", h1, np.sign(np.sin(np.arange(len(h1)) / 50.0)),
                  np.full(len(h1), 1 * pip), risk=0.01)
t = res["trades"]
stopped = (t["reason"] == "stop").mean()
med_R = t.loc[t["reason"] == "stop", "R"].median()
check("C7 tight stops", stopped > 0.8 and -3.0 < med_R < -1.0, f"{stopped:.0%} stopped, median R {med_R:.2f}")

print("\nALL CANARIES PASSED" if not fails else f"\nFAILED: {fails}")
sys.exit(1 if fails else 0)
