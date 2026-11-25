from common import *
import fxlab as fx
real = fx.load_h1("EURUSD", "is").index[5000:6500]
n = len(real)
def path(seed):
    g = np.random.default_rng(seed)
    bc = 1.1 + np.cumsum(g.normal(0, 5e-4, n))
    bo = np.r_[1.1, bc[:-1]] + np.where(g.random(n) < 0.03, g.normal(0, 3e-3, n), 0.0)
    hi = np.maximum(bo, bc) + g.random(n) * 4e-4; lo = np.minimum(bo, bc) - g.random(n) * 4e-4
    return make_h1(bo, hi, lo, bc, sp=g.integers(1, 4, n) * 1e-4, index=real)
g = np.random.default_rng(9)
tgt = np.zeros(n); i = 0
while i < n:
    L = g.integers(1, 12); tgt[i:i + L] = g.choice([-1, 0, 1]); i += L
sd = np.full(n, 0.002); tp = np.full(n, 0.003)
ok = True; det = []
for delay in (0, 1, 2):
    h1 = path(3)
    base = fx.simulate("EURUSD", h1, tgt, sd, tp, max_hold=9, delay=delay, slip_pips=0.3, comm_pips=0.1, spread_mult=1.5)
    for J in (300, 777, 1200):
        h2 = h1.copy()
        rr = np.random.default_rng(J)
        for c in ["bo", "bh", "bl", "bc", "ao", "ah", "al", "ac", "mo", "mh", "ml", "mc"]:
            h2.iloc[J + 1:, h2.columns.get_loc(c)] = h2[c].iloc[J + 1:].to_numpy() + rr.normal(0, 5e-3, n - J - 1)
        t2 = tgt.copy(); t2[J:] = rr.choice([-1, 0, 1], n - J)
        sd2 = sd.copy(); sd2[J:] = rr.uniform(0.001, 0.01, n - J)
        tp2 = tp.copy(); tp2[J:] = rr.uniform(0.001, 0.01, n - J)
        alt = fx.simulate("EURUSD", h2, t2, sd2, tp2, max_hold=9, delay=delay, slip_pips=0.3, comm_pips=0.1, spread_mult=1.5)
        same = np.array_equal(base["ret"].to_numpy()[:J + 1], alt["ret"].to_numpy()[:J + 1]) and \
               np.array_equal(base["cost"].to_numpy()[:J + 1], alt["cost"].to_numpy()[:J + 1])
        ok &= bool(same); det.append((delay, J, bool(same)))
report("E14", "simulate() causality: altering prices after bar J and decisions at k>=J leaves ret/cost[:J+1] bit-identical (delay 0,1,2)", ok, str(det))
