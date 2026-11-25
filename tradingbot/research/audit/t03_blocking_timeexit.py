from common import *
SP = 0.0002
n = 16
def mk(patch=None):
    bo = np.full(n, 1.1000); bh = bo + 0.0002; bl = bo - 0.0002; bc = bo.copy()
    if patch: patch(bo, bh, bl, bc)
    return make_h1(bo, bh, bl, bc, sp=SP)

# ---------------- E6: max_hold time exit and re-entry block ----------------
h1 = mk(lambda bo, bh, bl, bc: bo.__setitem__(7, 1.1010))
tg = [(2, 9, 1), (10, 16, 1)]          # target 0 only at bar 9
r = sim(h1, tg, 0.01, slip_pips=0.2, max_hold=4)
tr = r["trades"]
e_exit_px = h1["bo"].iloc[7] - 0.2 * PIP
ok = (len(tr) == 2 and int(tr.i_in[0]) == 3 and int(tr.i_out[0]) == 7 and tr.reason[0] == "time"
      and close(tr.px_out[0], e_exit_px, 1e-12)
      and int(tr.i_in[1]) == 11)       # k=9 target 0 clears block at s=10, k=10 target +1 -> enter at open of bar 11
# no re-entry while target unchanged (bars 8..10 flat)
ok &= (r["ret"].iloc[8:11].abs().max() == 0.0)
report("E6", "max_hold exit after 4 bars (open of bar 7), blocked until target changes, re-entry at bar 11", ok,
       f"trades i_in/i_out/reason={[(int(a),int(b),c) for a,b,c in zip(tr.i_in,tr.i_out,tr.reason)]} expected [(3,7,time),(11,..)]")

# time exit coinciding with a reversal: doc says change is filled at open of k+1 (bar 7)
tg = [(2, 6, 1), (6, 16, -1)]
r = sim(h1, tg, 0.01, max_hold=4)
tr = r["trades"]
first_short = tr[tr.dir == -1]
got = int(first_short.i_in.iloc[0]) if len(first_short) else None
ok = got == 7
report("E6b", "time-exit coinciding with reversal: short must enter at open of bar 7 (k+1)", ok,
       f"short entered at bar {got}, expected 7 (long closed at {int(tr.i_out[0])} reason {tr.reason[0]})")
# control: reversal without time exit enters same bar
r = sim(h1, tg, 0.01)
tr = r["trades"]; fs = tr[tr.dir == -1]
report("E6c", "control: plain reversal closes long and opens short at the same open (bar 7)",
       int(tr.i_out[0]) == 7 and len(fs) == 0 and r["trades"].shape[0] == 1,
       f"closed long at {int(tr.i_out[0])}; (short still open so not logged)")

# ---------------- E7: re-entry blocking after stop-out ----------------
for delay in (0, 1, 2):
    stop_bar = 6 + delay
    def patch(bo, bh, bl, bc, sb=stop_bar):
        bl[sb] = 1.1002 - 0.005 - 0.0003
    h1s = mk(patch)
    # long stopped; target stays +1 until the end -> exactly 1 trade, no later returns
    r = sim(h1s, [(2, 16, 1)], 0.005, delay=delay)
    tr = r["trades"]
    ok = len(tr) == 1 and tr.reason[0] == "stop" and int(tr.i_out[0]) == stop_bar and r["ret"].iloc[stop_bar + 1:].abs().max() == 0.0
    # target goes flat for 1 bar then long again -> re-entry allowed
    r2 = sim(h1s, [(2, stop_bar + 1, 1), (stop_bar + 2, 16, 1)], 0.005, delay=delay)
    t2 = r2["trades"]
    exp_re = stop_bar + 3 + delay
    rr = r2["ret"].to_numpy()
    re_in = exp_re if (rr[exp_re] != 0.0) else None
    ok2 = (np.abs(rr[stop_bar + 1:exp_re]).max() == 0.0) and rr[exp_re] != 0.0
    # opposite direction right after the stop is allowed
    r3 = sim(h1s, [(2, stop_bar + 1, 1), (stop_bar + 1, 16, -1)], 0.005, delay=delay)
    t3 = r3["trades"]
    # short decided at k=stop_bar+1-? fill at k+1+delay ; short still open -> not logged; check ret nonzero afterwards
    first_short_fill = stop_bar + 1 + 1 + delay
    ok3 = r3["ret"].iloc[first_short_fill] != 0.0 and r3["ret"].iloc[stop_bar + 1:first_short_fill].abs().max() == 0.0
    report(f"E7.d{delay}", f"stop-out blocks same direction (delay={delay}); target change/opposite re-enter",
           ok and bool(ok2) and bool(ok3),
           f"blocked-trades={len(tr)} (exp 1); re-entry bar {re_in} (exp {exp_re}); opposite fill bar {first_short_fill} ret!=0 {r3['ret'].iloc[first_short_fill]!=0.0}")

# blocking also after gap-stop at the open
def gap(bo, bh, bl, bc):
    bo[6] = 1.0900; bh[6] = 1.0902; bl[6] = 1.0898; bc[6] = 1.0900
h1g = mk(gap)
r = sim(h1g, [(2, 16, 1)], 0.005)
report("E7g", "gap-stop also blocks re-entry", len(r["trades"]) == 1 and r["trades"].reason[0] == "stop" and r["ret"].iloc[7:].abs().max() == 0.0,
       f"trades={len(r['trades'])}")

# take-profit blocking
def tpp(bo, bh, bl, bc): bh[6] = 1.1002 + 0.003 + 0.0001
h1t = mk(tpp)
r = sim(h1t, [(2, 16, 1)], 0.005, tp=np.full(n, 0.003))
report("E7t", "take-profit blocks same-direction re-entry (docstring)", len(r["trades"]) == 1 and r["trades"].reason[0] == "tp" and r["ret"].iloc[7:].abs().max() == 0.0,
       f"trades={len(r['trades'])} reason={r['trades'].reason[0]}")
