"""T4 Quarterly Theory (A / M / D / X) on the week, day, 6-hour session and 90-minute cycles. NQ, ES, RTY 1-minute 2018–26.
Week: Mon / Tue / Wed / Thu (hourly units). Day: 18–00 / 00–06 / 06–12 / 12–17 ET (5-minute units). Session: its four 90-minute
quarters (1-minute units). 90 minutes: its four 22.5-minute quarters (1-minute units). True open = the open of Q2.
Per cycle: the quarter of its high and of its low, whether it closed above the true open, whether Q2 broke Q1's high / low.
Null: each unit's move sign-flipped at random, in place (keeps the volatility profile, drops direction); 3 replicates."""
import numpy as np, pandas as pd
from numba import njit
from lay import load, units

rng0 = np.random.default_rng(29)


@njit(cache=True)
def cyc(O, H, L, C, ct, cid, q, flips):
    out = []
    n = len(O)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and cid[j + 1] == cid[i]:
            j += 1
        ok = ct[i] == ct[j] and i > 0
        # all four quarters present, in order
        seen = np.zeros(4)
        for u in range(i, j + 1):
            if q[u] >= 0:
                seen[q[u]] = 1
        if ok and seen.sum() == 4:
            for r in range(4):            # r = 0 real, 1..3 sign-flipped
                c = C[i - 1]
                hi = -1e18; lo = 1e18; qh = -1; ql = -1
                h1 = -1e18; l1 = 1e18; h2 = -1e18; l2 = 1e18
                tro = np.nan; cl = np.nan; op = np.nan
                for u in range(i, j + 1):
                    if q[u] < 0:
                        continue
                    dO = O[u] - C[u - 1]; dH = H[u] - C[u - 1]; dL = L[u] - C[u - 1]; dC = C[u] - C[u - 1]
                    if r > 0 and flips[r - 1, u % flips.shape[1]]:
                        dO, dH, dL, dC = -dO, -dL, -dH, -dC
                    oo = c + dO; hh = c + dH; ll = c + dL; c = c + dC
                    if np.isnan(op):
                        op = oo
                    if q[u] == 1 and np.isnan(tro):
                        tro = oo
                    if hh > hi:
                        hi = hh; qh = q[u]
                    if ll < lo:
                        lo = ll; ql = q[u]
                    if q[u] == 0:
                        h1 = max(h1, hh); l1 = min(l1, ll)
                    if q[u] == 1:
                        h2 = max(h2, hh); l2 = min(l2, ll)
                    cl = c
                out.append((float(cid[i]), float(r), float(qh), float(ql), 1.0 if cl > tro else 0.0, 1.0 if cl > op else 0.0,
                            1.0 if h2 > h1 else 0.0, 1.0 if l2 < l1 else 0.0, 1.0 if cl > h1 else 0.0, 1.0 if cl < l1 else 0.0))
        i = j + 1
    return out


if __name__ == '__main__':
    flips = rng0.random((3, 100003)) < 0.5
    R = []
    for sym in ('NQ', 'ES', 'RTY'):
        m = load(sym)
        UH = units(m, 'H'); U5 = units(m, 'M5'); U1 = units(m, 'M1')
        wd = (UH['td'] + 3) % 7
        specs = [('week', UH, (UH['td'] - wd), np.where(wd <= 3, wd, -1)),
                 ('day', U5, U5['td'], np.select([(U5['ts'] % 1440) >= 1080, (U5['ts'] % 1440) < 360, (U5['ts'] % 1440) < 720], [0, 1, 2], 3)),
                 ('session', U1, U1['ts'] // 360, (U1['ts'] % 360) // 90),
                 ('90min', U1, U1['ts'] // 90, ((U1['ts'] % 90) * 2) // 45)]
        for nm, U, cid, q in specs:
            o = cyc(U['O'], U['H'], U['L'], U['C'], U['ct'], cid.astype(np.int64), q.astype(np.int64), flips)
            X = pd.DataFrame(o, columns=['cid', 'r', 'qH', 'qL', 'upT', 'upO', 'b2H', 'b2L', 'cAbove1', 'cBelow1'])
            X['cyc'] = nm; X['sym'] = sym; R.append(X)
            print(sym, nm, (X.r == 0).sum(), flush=True)
    X = pd.concat(R, ignore_index=True)
    X.to_pickle('t4_rows.pkl')
