from common import *
import fxlab as fx
rng = np.random.default_rng(12345)
real = fx.load_h1("EURUSD", "is").index[2000:3600]
n = len(real)

def path(seed, gap_prob=0.03):
    g = np.random.default_rng(seed)
    bc = 1.1 + np.cumsum(g.normal(0, 5e-4, n))
    bo = np.r_[1.1, bc[:-1]] + np.where(g.random(n) < gap_prob, g.normal(0, 3e-3, n), 0.0)
    hi = np.maximum(bo, bc) + g.random(n) * 4e-4
    lo = np.minimum(bo, bc) - g.random(n) * 4e-4
    sp = g.integers(1, 4, n) * 1e-4
    return make_h1(bo, hi, lo, bc, sp=sp, index=real)

def rand_target(seed):
    g = np.random.default_rng(seed)
    t = np.zeros(n); i = 0
    while i < n:
        L = g.integers(1, 15); t[i:i + L] = g.choice([-1, 0, 1, 1, -1]); i += L
    t[-6:] = 0                               # end flat
    return t

# ---------------- E10: mark-to-market sum == realised, independent reconstruction ----------------
cfgs = [dict(slip_pips=0.2, comm_pips=0.0, spread_mult=1.0, max_hold=0, tp=False),
        dict(slip_pips=0.5, comm_pips=0.3, spread_mult=2.0, max_hold=7, tp=True),
        dict(slip_pips=0.0, comm_pips=0.0, spread_mult=0.0, max_hold=0, tp=True)]
allok = True; det = []
for ci, cfg in enumerate(cfgs):
    h1 = path(100 + ci); tgt = rand_target(200 + ci)
    d = 0.0020; risk = 0.01; units = risk / d
    carry = 0.03; mk_ = 0.01
    tp = np.full(n, 0.0030) if cfg["tp"] else None
    old = fx.carry; fx.carry = lambda p, h: np.full(len(h), carry)
    r = fx.simulate("EURUSD", h1, tgt, np.full(n, d), tp, max_hold=cfg["max_hold"], risk=risk, delay=0,
                    slip_pips=cfg["slip_pips"], comm_pips=cfg["comm_pips"], spread_mult=cfg["spread_mult"], swap_markup=mk_)
    fx.carry = old
    tr = r["trades"]; ret = r["ret"].to_numpy()
    mc = ((h1["bc"] + h1["ac"]) / 2).to_numpy(); roll = h1["rollover"].to_numpy(); wd = h1["ny_wday"].to_numpy()
    comm = cfg["comm_pips"] * PIP
    bad_R = 0; bad_sum = 0; checked = 0
    for j, t in tr.iterrows():
        a, b = int(t.i_in), int(t.i_out)
        swap = 0.0
        for s in range(a + 1, b + 1):
            if roll[s]:
                rate = (carry if t.dir > 0 else -carry) - mk_
                swap += units * mc[s - 1] * rate * (3.0 if wd[s] == 2 else 1.0) / 365.0
        e_pnl = t.dir * units * (t.px_out - t.px_in) - 2 * comm * units + swap
        bad_R += not close(t.R * risk, e_pnl, 1e-12)
        prev_out = int(tr.i_out.iloc[j - 1]) if j > 0 else -9
        next_in = int(tr.i_in.iloc[j + 1]) if j + 1 < len(tr) else -9
        if prev_out != a and next_in != b:                  # no overlap with neighbouring trades on boundary bars
            checked += 1
            bad_sum += not close(ret[a:b + 1].sum(), e_pnl, 1e-12)
    tot_ok = close(ret.sum(), (tr.R * risk).sum(), 1e-11)
    good = bad_R == 0 and bad_sum == 0 and tot_ok and len(tr) > 20
    allok &= bool(good)
    det.append(f"cfg{ci}: trades={len(tr)}, R-vs-hand mismatches={bad_R}, per-trade ret-sum mismatches={bad_sum}/{checked}, sum(ret)={ret.sum():.8f} sum(R*risk)={(tr.R*risk).sum():.8f}")
report("E10", "sum of per-bar returns of a trade == realised P&L (hand-reconstructed from px_in/px_out, comm, swap)", allok, " | ".join(det))

# ---------------- E10c: cost series reconciles with friction actually paid ----------------
h1 = path(77); tgt = rand_target(78)
d = 0.0020; risk = 0.01; units = risk / d; slip = 0.4; comm_p = 0.2; mult = 1.7
old = fx.carry; fx.carry = lambda p, h: np.zeros(len(h))
r = fx.simulate("EURUSD", h1, tgt, np.full(n, d), np.full(n, 0.0030), risk=risk, slip_pips=slip, comm_pips=comm_p, spread_mult=mult, swap_markup=0.0)
fx.carry = old
tr = r["trades"]
mo = ((h1["bo"] + h1["ao"]) / 2).to_numpy(); hs = ((h1["ao"] - h1["bo"]) / 2).to_numpy()
gross = 0.0
for _, t in tr.iterrows():
    a, b = int(t.i_in), int(t.i_out)
    ref_in = mo[a]
    if t.reason in ("signal", "time") or (t.reason in ("stop", "tp") and False):
        ref_out = mo[b]
    elif t.reason == "stop":
        # in-bar stop at level S: fill = S -/+ slip. Gap-stop fills at open -> detect by comparing with bar open
        gap_long = t.dir > 0 and abs(t.px_out - (h1["bo"].iloc[b] - mult * 0 - (mult - 1) * hs[b] - slip * PIP)) < 1e-12
        gap_short = t.dir < 0 and abs(t.px_out - (h1["ao"].iloc[b] + (mult - 1) * hs[b] + slip * PIP)) < 1e-12
        if gap_long or gap_short:
            ref_out = mo[b]
        else:
            ref_out = t.px_out + t.dir * (slip * PIP + hs[b] * mult)
    else:  # tp
        gap_long = t.dir > 0 and abs(t.px_out - (h1["bo"].iloc[b] - (mult - 1) * hs[b])) < 1e-12
        gap_short = t.dir < 0 and abs(t.px_out - (h1["ao"].iloc[b] + (mult - 1) * hs[b])) < 1e-12
        ref_out = mo[b] if (gap_long or gap_short) else t.px_out + t.dir * hs[b] * mult
    gross += t.dir * units * (ref_out - ref_in)
net = r["ret"].sum(); cost = r["cost"].sum()
report("E10c", "cost series == (mid-to-mid gross - net P&L)  [no swap]", close(gross - net, cost, 1e-9) and (r["cost"] >= 0).all(),
       f"trades {len(tr)}: gross-net={gross-net:.8f}, sum(cost)={cost:.8f}, diff={gross-net-cost:.2e}")

# ---------------- E13: NaN handling, tp NaN ----------------
n2 = 12
bo = np.full(n2, 1.1000); h = make_h1(bo, bo + 0.0002, bo - 0.0002, bo.copy(), sp=0.0002)
t = np.array([0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0.0])
sdv = np.full(n2, np.nan)
r = fx.simulate("EURUSD", h, t, sdv, None, swap_markup=0.0, slip_pips=0.0)
a = len(r["trades"]) == 0 and np.abs(r["ret"].to_numpy()).max() == 0.0
# NaN stop at decision bar, valid one later while target unchanged -> engine enters LATE (at first valid stop bar)
sdv2 = np.full(n2, np.nan); sdv2[4:] = 0.005
r = fx.simulate("EURUSD", h, t, sdv2, None, swap_markup=0.0, slip_pips=0.0)
late = r["trades"]
r_open = r["ret"].to_numpy()
entered_bar = int(np.nonzero(r_open)[0][0]) if np.nonzero(r_open)[0].size else None
report("E13a", "NaN stop_dist => no trade (no unsized position)", a, f"no-trade ok={a}")
report("E13b", "NaN stop_dist at k=2,3 then valid at k=4 with target still +1: entry at open of k+1=5 using only bar-4 info (no lookahead, no phantom fill at bar 3)",
       entered_bar == 5, f"first non-zero P&L at bar {entered_bar} (hand expectation 5); NOTE the NaN-delayed entry is a late fill of an unchanged target, not lookahead")
# NaN target -> treated as 0 ; tp NaN -> none; tp<=0 -> none
tn = np.array([0, 0, 1, 1, np.nan, 1, 1, 1, 0, 0, 0, 0.0])
r = fx.simulate("EURUSD", h, tn, np.full(n2, 0.005), np.full(n2, np.nan), swap_markup=0.0, slip_pips=0.0)
tr = r["trades"]
report("E13c", "NaN target treated as flat (exit at bar k+1), NaN tp = no TP", len(tr) >= 1 and int(tr.i_out[0]) == 5 and tr.reason[0] == "signal",
       f"i_out={int(tr.i_out[0]) if len(tr) else None} (expected 5: NaN at k=4 -> flat at open of bar 5); a later +1 at k=5 re-enters at bar 6 (open trade not logged)")
