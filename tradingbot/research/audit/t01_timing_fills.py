from common import *
# ---------- E1: fill timing for delay 0,1,2 (long and short) ----------
n = 14
bo = 1.1000 + 0.001 * np.arange(n)
h1 = make_h1(bo)
ao = h1["ao"].to_numpy(); bo_ = h1["bo"].to_numpy()
ok = True; det = []
for d in (0, 1, 2):
    for dirn in (+1, -1):
        r = sim(h1, [(2, 6, dirn)], 1.0, delay=d)           # decided at close of bars 2..5, flat at k=6
        tr = r["trades"]
        exp_in, exp_out = 3 + d, 7 + d
        e_pxin = (ao[exp_in] if dirn > 0 else bo_[exp_in])
        e_pxout = (bo_[exp_out] if dirn > 0 else ao[exp_out])
        good = (len(tr) == 1 and int(tr.i_in[0]) == exp_in and int(tr.i_out[0]) == exp_out
                and close(tr.px_in[0], e_pxin) and close(tr.px_out[0], e_pxout))
        early = np.abs(r["ret"].to_numpy()[:exp_in]).max() == 0.0
        # hand return on entry bar: units=0.01/1.0 ; mid close - entry px
        mc = (h1["bc"].iloc[exp_in] + h1["ac"].iloc[exp_in]) / 2
        e_ret = dirn * 0.01 * (mc - e_pxin)
        good &= close(r["ret"].iloc[exp_in], e_ret, 1e-12) and early
        det.append(f"d{d}/{dirn:+d}: i_in {int(tr.i_in[0]) if len(tr) else None} exp {exp_in}, px_in {tr.px_in[0]:.5f} exp {e_pxin:.5f}, i_out {int(tr.i_out[0])} exp {exp_out}")
        ok &= good
report("E1", "fill timing delay 0/1/2 long+short", ok, "; ".join(det[:3]) + " ... all 6 combos checked")

# first bar: target[0] decided at close of bar 0 fills at open of bar 1 (delay 0); bar 0 never traded
r = sim(h1, [(0, 4, 1)], 1.0, delay=0)
tr = r["trades"]
report("E1b", "first-bar decision fills at open of bar 1", len(tr) == 1 and int(tr.i_in[0]) == 1 and r["ret"].iloc[0] == 0,
       f"i_in={int(tr.i_in[0])} (expected 1)")

# ---------- E2: prices with spread_mult, slip, comm ----------
sp = 0.0002  # 2 pips full spread, half = 1 pip
n = 10
bo = np.full(n, 1.1000)
bo[7] = 1.1030                                    # exit-bar open differs
h1 = make_h1(bo, bh=bo + 0.0002, bl=bo - 0.0002, bc=bo, sp=sp)
res = []
for mult in (1.0, 3.0, 0.5):
    for dirn in (1, -1):
        slip, comm = 0.5, 0.3
        r = sim(h1, [(2, 6, dirn)], 0.01, slip_pips=slip, comm_pips=comm, spread_mult=mult)  # units = 0.01/0.01 = 1
        t = r["trades"].iloc[0]
        half = 1 * PIP; ext = (mult - 1) * half
        bid_in, ask_in = 1.1000 - ext, 1.1002 + ext
        bid_out, ask_out = 1.1030 - ext, 1.1032 + ext
        if dirn > 0:
            e_in, e_out = ask_in + slip * PIP, bid_out - slip * PIP
        else:
            e_in, e_out = bid_in - slip * PIP, ask_out + slip * PIP
        e_pnl = dirn * 1.0 * (e_out - e_in) - 2 * comm * PIP        # units=1
        e_R = e_pnl / 0.01
        ok = close(t.px_in, e_in, 1e-12) and close(t.px_out, e_out, 1e-12) and close(t.R, e_R, 1e-9) \
            and close(r["ret"].sum(), e_pnl, 1e-12)
        res.append((mult, dirn, ok, round(t.px_in, 6), round(e_in, 6), round(t.R, 4), round(e_R, 4)))
report("E2", "entry/exit prices ask+slip/bid-slip, spread_mult widening, comm per side",
       all(x[2] for x in res), str(res))
