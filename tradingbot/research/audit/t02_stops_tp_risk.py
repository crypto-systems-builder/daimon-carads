from common import *
SP = 0.0002
def flat(n=12, **over):
    bo = np.full(n, 1.1000); bh = bo + 0.0002; bl = bo - 0.0002; bc = bo.copy()
    for k, v in over.items():
        arr = {"bo": bo, "bh": bh, "bl": bl, "bc": bc}
        i, val = v
        arr[k][i] = val
    return bo, bh, bl, bc

def run(dirn, d=0.005, slip=0.2, comm=0.0, mult=1.0, tp=None, patch=None, n=12, **kw):
    bo, bh, bl, bc = flat(n)
    if patch: patch(bo, bh, bl, bc)
    h1 = make_h1(bo, bh, bl, bc, sp=SP)
    tpd = None if tp is None else np.full(n, tp)
    r = sim(h1, [(2, n, dirn)], d, tp=tpd, slip_pips=slip, comm_pips=comm, spread_mult=mult, **kw)
    return h1, r

slip = 0.2
# ---------------- E3: in-bar stop ----------------
rows = []; ok = True
# long: entry px = ask_o(1.1002)+slip ; stop = px - d
px_l = 1.1002 + slip * PIP; stop_l = px_l - 0.005
px_s = 1.1000 - slip * PIP; stop_s = px_s + 0.005
def p_long_hit(bo, bh, bl, bc): bl[6] = stop_l - 0.0001      # bid low through stop
def p_long_no(bo, bh, bl, bc): bl[6] = stop_l + 0.00005      # bid low just above -> no trigger
def p_short_hit(bo, bh, bl, bc): bh[6] = stop_s + 0.0001 - SP  # ask high = bid high + SP = stop+1e-4
def p_short_no(bo, bh, bl, bc): bh[6] = stop_s - 0.00005 - SP  # ask high just below stop
for name, dirn, patch, expect in [("long hit", 1, p_long_hit, True), ("long near-miss", 1, p_long_no, False),
                                  ("short hit", -1, p_short_hit, True), ("short near-miss", -1, p_short_no, False)]:
    h1, r = run(dirn, patch=patch)
    tr = r["trades"]
    hit = len(tr) == 1 and tr.reason[0] == "stop" and int(tr.i_out[0]) == 6
    if expect:
        e_exit = stop_l - slip * PIP if dirn > 0 else stop_s + slip * PIP
        good = hit and close(tr.px_out[0], e_exit, 1e-12)
    else:
        good = len(tr) == 0
    rows.append((name, bool(good), None if len(tr) == 0 else round(tr.px_out[0], 6)))
    ok &= bool(good)
# short-side uses ASK high, not bid high: bid high through stop but ask... ask high >= bid high always, so check long uses BID low:
# make ask low (always >= bid low) irrelevant: bid low above stop but ask-low far below is impossible; verify long ignores ask via bl only (done above)
report("E3", "in-bar stop triggers on bid low (long)/ask high (short), fills at stop -/+ slip", ok, str(rows))

# spread_mult=3 widening of the trigger (ext = 2 pips): trigger iff bl - 2p <= stop
rows = []; ok = True
for off_pips, expect in [(1.5, True), (2.5, False)]:
    def p(bo, bh, bl, bc, off=off_pips): bl[6] = stop_l_m + off * PIP
    px_m = 1.1002 + 2 * PIP + slip * PIP; stop_l_m = px_m - 0.005
    h1, r = run(1, mult=3.0, patch=p)
    tr = r["trades"]
    hit = len(tr) == 1 and tr.reason[0] == "stop"
    good = hit == expect and (not hit or close(tr.px_out[0], stop_l_m - slip * PIP, 1e-12))
    rows.append((off_pips, expect, hit, bool(good)))
    ok &= bool(good)
report("E3b", "spread_mult widens stop trigger (bl - ext <= stop)", ok, str(rows))

# ---------------- E4: gap through stop at the open ----------------
rows = []; ok = True
def pg_long(bo, bh, bl, bc):
    bo[6] = stop_l - 0.0020; bh[6] = bo[6] + 0.0002; bl[6] = bo[6] - 0.0002; bc[6] = bo[6]
def pg_short(bo, bh, bl, bc):
    bo[6] = stop_s + 0.0020 - SP; bh[6] = bo[6] + 0.0002; bl[6] = bo[6] - 0.0002; bc[6] = bo[6]  # ask open = stop_s+0.002
for name, dirn, patch in [("long", 1, pg_long), ("short", -1, pg_short)]:
    h1, r = run(dirn, patch=patch)
    tr = r["trades"].iloc[0]
    if dirn > 0:
        e = h1["bo"].iloc[6] - slip * PIP
    else:
        e = h1["ao"].iloc[6] + slip * PIP
    stop_px = stop_l - slip * PIP if dirn > 0 else stop_s + slip * PIP
    good = close(tr.px_out, e, 1e-12) and tr.reason == "stop" and not close(tr.px_out, stop_px, 1e-6)
    rows.append((name, round(tr.px_out, 6), round(e, 6), "stop-fill would be", round(stop_px, 6)))
    ok &= bool(good)
report("E4", "gap through stop fills at the open (+/- slip), not at the stop", ok, str(rows))

# ---------------- E5: take profit; stop+TP same bar ----------------
rows = []; ok = True
tpd = 0.003
tp_l = px_l + tpd; tp_s = px_s - tpd
def pt_long(bo, bh, bl, bc): bh[6] = tp_l + 0.0001
def pt_short(bo, bh, bl, bc): bl[6] = tp_s + 0.0001 - SP   # ask low = bid low + SP = tp_s + 1e-4 ... need <= tp : use tp_s - 1e-4
def pt_short2(bo, bh, bl, bc): bl[6] = tp_s - 0.0001 - SP   # ask low = tp_s - 1e-4 <= tp_s
h1, r = run(1, tp=tpd, patch=pt_long); t = r["trades"].iloc[0]
g = t.reason == "tp" and close(t.px_out, tp_l, 1e-12) and int(t.i_out) == 6; rows.append(("long tp", t.reason, round(t.px_out, 6), round(tp_l, 6))); ok &= bool(g)
h1, r = run(-1, tp=tpd, patch=pt_short2); t = r["trades"].iloc[0]
g = t.reason == "tp" and close(t.px_out, tp_s, 1e-12) and int(t.i_out) == 6; rows.append(("short tp", t.reason, round(t.px_out, 6), round(tp_s, 6))); ok &= bool(g)
def both_l(bo, bh, bl, bc): bh[6] = tp_l + 0.0001; bl[6] = stop_l - 0.0001
def both_s(bo, bh, bl, bc): bl[6] = tp_s - 0.0001 - SP; bh[6] = stop_s + 0.0001 - SP
h1, r = run(1, tp=tpd, patch=both_l); t = r["trades"].iloc[0]
g = t.reason == "stop" and close(t.px_out, stop_l - slip * PIP, 1e-12); rows.append(("long both->stop", t.reason, round(t.px_out, 6))); ok &= bool(g)
h1, r = run(-1, tp=tpd, patch=both_s); t = r["trades"].iloc[0]
g = t.reason == "stop" and close(t.px_out, stop_s + slip * PIP, 1e-12); rows.append(("short both->stop", t.reason, round(t.px_out, 6))); ok &= bool(g)
# TP gapped at open: fills at the open (bid), better than tp
def gap_tp(bo, bh, bl, bc):
    bo[6] = tp_l + 0.0010; bh[6] = bo[6] + 0.0002; bl[6] = bo[6] - 0.0002; bc[6] = bo[6]
h1, r = run(1, tp=tpd, patch=gap_tp); t = r["trades"].iloc[0]
g = t.reason == "tp" and close(t.px_out, h1["bo"].iloc[6], 1e-12); rows.append(("long tp gap", t.reason, round(t.px_out, 6))); ok &= bool(g)
report("E5", "take-profit fill at tp; stop wins when both in same bar; TP gap fills at open", ok, str(rows))

# ---------------- E9: risk sizing, R ~ -1 ----------------
rows = []; ok = True
for dirn in (1, -1):
    for d, slp, cm in [(0.005, 0.2, 0.1), (0.0123, 0.5, 0.0), (0.0030, 0.2, 0.3)]:
        px_l_ = 1.1002 + slp * PIP; px_s_ = 1.1000 - slp * PIP
        st_l = px_l_ - d; st_s = px_s_ + d
        def pp(bo, bh, bl, bc, st_l=st_l, st_s=st_s, dirn=dirn):
            if dirn > 0: bl[6] = st_l - 0.0001
            else: bh[6] = st_s + 0.0001 - SP
        h1, r = run(dirn, d=d, slip=slp, comm=cm, patch=pp)
        t = r["trades"].iloc[0]
        units = 0.01 / d
        e_loss = units * (d + slp * PIP) + units * 2 * cm * PIP
        eR = -e_loss / 0.01
        good = t.reason == "stop" and close(t.R, eR, 1e-9) and close(r["ret"].sum(), -e_loss, 1e-12)
        rows.append((dirn, d, round(t.R, 5), round(eR, 5)))
        ok &= bool(good)
report("E9", "risk sizing: stop-out loses risk + slip + 2*comm (R ~ -1.00x)", ok, str(rows))
