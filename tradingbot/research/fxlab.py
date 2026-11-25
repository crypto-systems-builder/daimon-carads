"""fxlab - shared data access, cost model, execution simulator and metrics.

Every strategy experiment in this folder goes through this module so that
costs, fill rules and metrics are identical across experiments.

Conventions (read before writing a strategy)
--------------------------------------------
* Time: all H1 bars are indexed by bar START time, UTC. The FX trading day
  ends at 17:00 New York (DST-aware); `ny_day` labels each H1 bar with the
  trading day it belongs to (the Sunday 17:00 NY open belongs to Monday).
* A strategy produces, on the H1 index:
      target[k]     in {-1, 0, +1}  desired direction, decided at the CLOSE of bar k
                    (it may use any information up to and including bar k's close)
      stop_dist[k]  > 0, stop distance in PRICE units for a trade entered after bar k
      tp_dist[k]    optional take-profit distance (price units, <=0 / NaN = none)
  The simulator fills the change at the OPEN of bar k+1+delay. Nothing else.
* Sizing mirrors the live bot: each trade risks `risk` (fraction of equity) to
  its stop: units = risk / stop_dist. Returns are therefore in "fraction of
  equity" (non-compounded); a stop-out costs ~ -risk plus costs.
* Fills: longs buy at ask, sell at bid; shorts the reverse. Actual FXCM bid/ask
  from the data, widened by `spread_mult`, plus `slip_pips` adverse slippage per
  side, plus `comm_pips` per side. Stops trigger on the exit side's high/low
  (long: bid low; short: ask high) and fill at the stop (or at the open if the
  market gapped through it). If stop and take-profit fall in the same bar, the
  stop is assumed hit first (conservative).
* Swap: a position held through a daily rollover (17:00 NY) pays/earns
  (r_base - r_quote) for longs, (r_quote - r_base) for shorts, minus
  `swap_markup` (annual, both sides), on its notional. Wednesday counts 3 days.
  Rates are central-bank policy rates (BIS), as known on that date.
* After a stop / take-profit / time exit, the same direction is not re-entered
  until the target changes (re-entry needs a fresh signal).
"""
from __future__ import annotations

import glob
import json
import math
import os
from functools import lru_cache

import numpy as np
import pandas as pd
from numba import njit

DATA = os.environ.get("FXDATA", "/home/user/fxdata")
CCY = ["EUR", "GBP", "AUD", "NZD", "USD", "CAD", "CHF", "JPY"]
PAIRS_ALL = [a + b for i, a in enumerate(CCY) for b in CCY[i + 1:]]
IS_START, IS_END = "2012-01-01", "2019-12-31"      # in-sample (research)
OOS_START = "2020-01-01"                            # out-of-sample (sealed)
NY = "America/New_York"


def pip_size(pair: str) -> float:
    return 0.01 if pair.endswith("JPY") else 0.0001


# --------------------------------------------------------------------------- data
def pairs_available(split: str = "is") -> list[str]:
    d = os.path.join(DATA, split, "h1")
    return sorted(os.path.basename(p)[:-8] for p in glob.glob(os.path.join(d, "*.parquet")))


@lru_cache(maxsize=64)
def load_h1(pair: str, split: str = "is") -> pd.DataFrame:
    """H1 bars for `pair`. split='is' (2012-2019) is the only split open to research."""
    path = os.path.join(DATA, split, "h1", f"{pair}.parquet")
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} (split '{split}' not available)")
    df = pd.read_parquet(path)
    ny = df.index.tz_convert(NY)
    df["ny_day"] = (ny + pd.Timedelta(hours=7)).normalize().tz_localize(None)
    df["ny_hour"] = ny.hour
    df["ny_wday"] = ny.weekday  # Mon=0 .. Sun=6
    df["rollover"] = (ny.hour == 17).astype(np.int8)
    for c in "ohlc":
        df["m" + c] = (df["b" + c] + df["a" + c]) / 2.0
    return df


def to_daily(h1: pd.DataFrame) -> pd.DataFrame:
    """Daily bars on the NY-17:00 trading day. Index = trading day (naive date).
    `last_bar` = start time of the H1 bar that closes the day (signals computed
    from this daily row are known at the close of that H1 bar)."""
    g = h1.groupby("ny_day", sort=True)
    d = pd.DataFrame({
        "mo": g["mo"].first(), "mh": g["mh"].max(), "ml": g["ml"].min(), "mc": g["mc"].last(),
        "bc": g["bc"].last(), "ac": g["ac"].last(), "bars": g["mc"].size(),
    })
    d["last_bar"] = h1.index.to_series().groupby(h1["ny_day"]).max()
    return d[d["bars"] >= 4]  # drop stub sessions (holiday fragments)


def daily_to_h1(values: pd.Series, d1: pd.DataFrame, h1: pd.DataFrame) -> pd.Series:
    """Map a daily series onto the H1 grid without lookahead: the value computed
    for trading day D is placed on the H1 bar that closes D and carried forward."""
    # keep the UTC tz: .values would strip it and nothing would match the H1 index
    s = pd.Series(np.asarray(values, dtype=float), index=pd.DatetimeIndex(d1["last_bar"]))
    s = s[~s.index.duplicated(keep="last")]
    return s.reindex(h1.index).ffill()


@lru_cache(maxsize=1)
def policy_rates() -> pd.DataFrame:
    r = pd.read_csv(os.path.join(DATA, "rates", "policy_rates_daily.csv"), index_col=0, parse_dates=True)
    return r.asfreq("D").ffill()


def carry(pair: str, h1: pd.DataFrame) -> np.ndarray:
    """r_base - r_quote (decimal, annual) as known on each bar's UTC date."""
    r = policy_rates()
    diff = (r[pair[:3]] - r[pair[3:]]) / 100.0
    days = h1.index.tz_localize(None).normalize()
    return diff.reindex(days, method="ffill").to_numpy()


# --------------------------------------------------------------------------- indicators
def atr(d1: pd.DataFrame, n: int = 20) -> pd.Series:
    """Average true range on daily mid bars (simple mean of TR over n days)."""
    pc = d1["mc"].shift(1)
    tr = pd.concat([d1["mh"] - d1["ml"], (d1["mh"] - pc).abs(), (d1["ml"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def atr_h1(h1: pd.DataFrame, n: int = 24) -> pd.Series:
    pc = h1["mc"].shift(1)
    tr = pd.concat([h1["mh"] - h1["ml"], (h1["mh"] - pc).abs(), (h1["ml"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


# --------------------------------------------------------------------------- simulator
@njit(cache=True)
def _simulate(bo, bh, bl, bc, ao, ah, al, ac, roll, wday, carry_l, target, stop_dist, tp_dist,
              max_hold, risk, delay, slip, comm, spread_mult, swap_markup, out_ret, out_cost, tlog):
    n = bo.shape[0]
    pos = 0            # -1, 0, +1
    units = 0.0        # base units per 1.0 equity (>0)
    mark = 0.0         # last mark price (mid) of the open position
    stop = 0.0
    tp = 0.0
    entry_i = -1
    entry_px = 0.0
    trade_pnl = 0.0
    blocked = 0
    nt = 0
    for s in range(1, n):
        r = 0.0
        c = 0.0
        hs_o = 0.5 * (ao[s] - bo[s])            # actual half-spread at the open
        mo = 0.5 * (ao[s] + bo[s])
        ext = (spread_mult - 1.0) * hs_o        # extra half-spread under stress
        bid_o = bo[s] - ext
        ask_o = ao[s] + ext
        # ---- 1. rollover financing on the position carried into this bar
        if roll[s] == 1 and pos != 0:
            days = 3.0 if wday[s] == 2 else 1.0
            rate = (carry_l[s] if pos > 0 else -carry_l[s]) - swap_markup
            fin = units * mark * rate * days / 365.0
            r += fin
            trade_pnl += fin
        # ---- 2. stop / take-profit gapped through at the open
        exit_reason = -1
        exit_px = 0.0
        if pos > 0:
            if bid_o <= stop:
                exit_reason = 1
                exit_px = bid_o - slip
            elif tp > 0.0 and bid_o >= tp:
                exit_reason = 2
                exit_px = bid_o
        elif pos < 0:
            if ask_o >= stop:
                exit_reason = 1
                exit_px = ask_o + slip
            elif tp > 0.0 and ask_o <= tp:
                exit_reason = 2
                exit_px = ask_o
        if exit_reason >= 0:
            pnl = pos * units * (exit_px - mark) - units * comm
            r += pnl
            c += units * (comm + abs(exit_px - mo))
            trade_pnl += pnl
            tlog[nt, 0] = entry_i; tlog[nt, 1] = s; tlog[nt, 2] = pos; tlog[nt, 3] = entry_px
            tlog[nt, 4] = exit_px; tlog[nt, 5] = trade_pnl / risk; tlog[nt, 6] = exit_reason
            nt += 1
            blocked = pos
            pos = 0
            units = 0.0
        # ---- 3. act on the decision taken at the close of bar k
        k = s - 1 - delay
        if k >= 0:
            want = int(target[k])
            if want != blocked:
                blocked = 0
            if want != 0 and want == blocked:
                want = 0 if pos == 0 else pos
            if pos != 0 and max_hold > 0 and s - entry_i >= max_hold and want == pos:
                want = 0   # time exit only when the signal still wants to hold (a reversal fills normally)
                blocked = pos
                exit_reason = 3
            if want != pos:
                if pos != 0:  # close at the open
                    px = (bid_o - slip) if pos > 0 else (ask_o + slip)
                    pnl = pos * units * (px - mark) - units * comm
                    r += pnl
                    c += units * (comm + abs(px - mo))
                    trade_pnl += pnl
                    tlog[nt, 0] = entry_i; tlog[nt, 1] = s; tlog[nt, 2] = pos; tlog[nt, 3] = entry_px
                    tlog[nt, 4] = px; tlog[nt, 5] = trade_pnl / risk
                    tlog[nt, 6] = 3 if exit_reason == 3 else 0
                    nt += 1
                    pos = 0
                    units = 0.0
                d = stop_dist[k]
                if want != 0 and d > 0.0 and d == d:   # d == d rejects NaN
                    px = (ask_o + slip) if want > 0 else (bid_o - slip)
                    pos = want
                    units = risk / d
                    entry_px = px
                    entry_i = s
                    mark = px
                    stop = px - d if want > 0 else px + d
                    t = tp_dist[k]
                    tp = (px + t if want > 0 else px - t) if (t > 0.0 and t == t) else 0.0
                    trade_pnl = -units * comm
                    r -= units * comm
                    c += units * (comm + abs(px - mo))     # cost bookkeeping only
        # ---- 4. stop / take-profit inside the bar (stop first if both)
        if pos != 0:
            exit_reason = -1
            if pos > 0:
                if bl[s] - ext <= stop:
                    exit_reason = 1
                    exit_px = stop - slip
                elif tp > 0.0 and bh[s] - ext >= tp:
                    exit_reason = 2
                    exit_px = tp
            else:
                if ah[s] + ext >= stop:
                    exit_reason = 1
                    exit_px = stop + slip
                elif tp > 0.0 and al[s] + ext <= tp:
                    exit_reason = 2
                    exit_px = tp
            if exit_reason >= 0:
                pnl = pos * units * (exit_px - mark) - units * comm
                r += pnl
                c += units * (comm + (slip + hs_o * spread_mult if exit_reason == 1 else hs_o * spread_mult))
                trade_pnl += pnl
                tlog[nt, 0] = entry_i; tlog[nt, 1] = s; tlog[nt, 2] = pos; tlog[nt, 3] = entry_px
                tlog[nt, 4] = exit_px; tlog[nt, 5] = trade_pnl / risk; tlog[nt, 6] = exit_reason
                nt += 1
                blocked = pos
                pos = 0
                units = 0.0
        # ---- 5. mark to market at the mid close
        if pos != 0:
            mc = 0.5 * (ac[s] + bc[s])
            pnl = pos * units * (mc - mark)
            r += pnl
            trade_pnl += pnl
            mark = mc
        out_ret[s] = r
        out_cost[s] = c
    return nt


def simulate(pair: str, h1: pd.DataFrame, target, stop_dist, tp_dist=None, max_hold: int = 0,
             risk: float = 0.01, delay: int = 0, slip_pips: float = 0.2, comm_pips: float = 0.0,
             spread_mult: float = 1.0, swap_markup: float = 0.01) -> dict:
    """Run one pair. Returns {'ret': per-bar returns (Series), 'trades': DataFrame}."""
    n = len(h1)
    tgt = np.nan_to_num(np.asarray(target, dtype=float), nan=0.0)
    tgt = np.sign(tgt).astype(np.int64)
    sd = np.asarray(stop_dist, dtype=float)
    tpd = np.full(n, np.nan) if tp_dist is None else np.asarray(tp_dist, dtype=float)
    pip = pip_size(pair)
    ret = np.zeros(n)
    cost = np.zeros(n)
    tlog = np.zeros((n, 7))
    nt = _simulate(h1["bo"].to_numpy(), h1["bh"].to_numpy(), h1["bl"].to_numpy(), h1["bc"].to_numpy(),
                   h1["ao"].to_numpy(), h1["ah"].to_numpy(), h1["al"].to_numpy(), h1["ac"].to_numpy(),
                   h1["rollover"].to_numpy().astype(np.int64), h1["ny_wday"].to_numpy().astype(np.int64),
                   np.nan_to_num(carry(pair, h1)), tgt, sd, tpd, int(max_hold), float(risk), int(delay),
                   slip_pips * pip, comm_pips * pip, float(spread_mult), float(swap_markup), ret, cost, tlog)
    idx = h1.index
    tr = pd.DataFrame(tlog[:nt], columns=["i_in", "i_out", "dir", "px_in", "px_out", "R", "reason"])
    if nt:
        tr["t_in"] = idx[tr["i_in"].astype(int)]
        tr["t_out"] = idx[tr["i_out"].astype(int)]
        tr["bars"] = tr["i_out"] - tr["i_in"]
        tr["reason"] = tr["reason"].map({0: "signal", 1: "stop", 2: "tp", 3: "time"})
    return {"ret": pd.Series(ret, index=idx), "cost": pd.Series(cost, index=idx), "trades": tr}


# --------------------------------------------------------------------------- metrics
def daily_returns(ret_h1: pd.Series, h1: pd.DataFrame) -> pd.Series:
    return ret_h1.groupby(h1["ny_day"].to_numpy()).sum()


def metrics(daily: pd.Series, trades: pd.DataFrame | None = None, cost_daily: pd.Series | None = None) -> dict:
    """Metrics on a daily return series (fraction of equity, non-compounded)."""
    x = daily.dropna()
    n = len(x)
    mu, sd = x.mean(), x.std(ddof=1)
    sharpe = float(mu / sd * math.sqrt(260)) if sd > 0 else 0.0
    eq = x.cumsum()
    dd = float((eq - np.maximum(eq.cummax(), 0.0)).min()) if n else 0.0   # peak includes starting equity
    yearly = x.groupby(pd.DatetimeIndex(x.index).year).sum()
    out = {
        "days": n, "ann_ret": float(mu * 260), "ann_vol": float(sd * math.sqrt(260)),
        "sharpe": sharpe, "t_stat": float(mu / sd * math.sqrt(n)) if sd > 0 else 0.0,
        "max_dd": dd, "total": float(eq.iloc[-1]) if n else 0.0,
        "pct_pos_years": float((yearly > 0).mean()) if len(yearly) else 0.0,
        "skew": float(x.skew()), "kurt": float(x.kurt() + 3.0),
    }
    if trades is not None:
        t = trades
        wins, losses = t.loc[t["R"] > 0, "R"].sum(), -t.loc[t["R"] < 0, "R"].sum()
        out.update({
            "trades": int(len(t)), "win_rate": float((t["R"] > 0).mean()) if len(t) else 0.0,
            "avg_R": float(t["R"].mean()) if len(t) else 0.0,
            "profit_factor": float(wins / losses) if losses > 0 else float("inf") if wins > 0 else 0.0,
            "avg_bars": float(t["bars"].mean()) if len(t) and "bars" in t else 0.0,
        })
    if cost_daily is not None and n:
        out["cost_ann"] = float(cost_daily.sum() / n * 260)
    return out


def deflated_sharpe(sr_annual: float, n_trials: int, sr_var_annual: float, days: int,
                    skew: float = 0.0, kurt: float = 3.0) -> float:
    """Probability the true Sharpe > 0 after selecting the best of n_trials
    (Bailey & Lopez de Prado 2014). Inputs annualised; converted to daily."""
    from scipy.stats import norm
    if n_trials < 2 or days < 30:
        return float("nan")
    sr = sr_annual / math.sqrt(260)
    v = max(sr_var_annual, 1e-12) / 260
    g = 0.5772156649
    sr0 = math.sqrt(v) * ((1 - g) * norm.ppf(1 - 1 / n_trials) + g * norm.ppf(1 - 1 / (n_trials * math.e)))
    denom = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4 * sr * sr))
    return float(norm.cdf((sr - sr0) * math.sqrt(days - 1) / denom))


def run_basket(pairs, make_signals, params: dict, split: str = "is", **sim_kw) -> dict:
    """Evaluate one parameter set on many pairs. `make_signals(pair, h1, d1, params)`
    must return (target, stop_dist, tp_dist_or_None, max_hold_or_0) on the H1 index.
    Returns per-pair metrics and the equal-weight portfolio metrics."""
    per, rets, costs, all_tr = {}, [], [], []
    for p in pairs:
        h1 = load_h1(p, split)
        d1 = to_daily(h1)
        target, sd, tpd, mh = make_signals(p, h1, d1, params)
        res = simulate(p, h1, target, sd, tpd, mh or 0, **sim_kw)
        dr = daily_returns(res["ret"], h1)
        dc = daily_returns(res["cost"], h1)
        per[p] = metrics(dr, res["trades"], dc)
        rets.append(dr.rename(p))
        costs.append(dc.rename(p))
        if len(res["trades"]):
            all_tr.append(res["trades"].assign(pair=p))
    R = pd.concat(rets, axis=1).fillna(0.0)
    C = pd.concat(costs, axis=1).fillna(0.0)
    trades = pd.concat(all_tr) if all_tr else pd.DataFrame(columns=["R", "bars"])
    port = metrics(R.sum(axis=1) / len(pairs), trades, C.sum(axis=1) / len(pairs))
    port["pairs_positive"] = float(np.mean([m["total"] > 0 for m in per.values()]))
    return {"portfolio": port, "per_pair": per, "daily": R, "trades": trades}


def log_trial(path: str, row: dict) -> None:
    """Append one trial (all variables + metrics) as a JSON line."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(row, default=float) + "\n")
