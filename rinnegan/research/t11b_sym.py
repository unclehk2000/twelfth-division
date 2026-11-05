"""T11b: DR/IDR as a direction call with a variance-free null. From the confirmation close c (long; short mirrored):
S1 the opposite DR side vs the same distance beyond c the confirmed way: which trades first (random walk 50%).
S2 back to the IDR edge vs the same distance beyond: which first. Session end = unresolved (dropped)."""
import numpy as np, pandas as pd, sys
from numba import njit
sys.path.insert(0, '/home/claude/lr'); from lib import load, D2025
SESS = {'RDR': (930, 990, 1320), 'ODR': (540, 600, 870), 'ADR': (90, 150, 480)}


@njit(cache=True)
def first(H, L, a, e, lo, hi):
    for j in range(a, e + 1):
        u = H[j] >= hi; d = L[j] <= lo
        if u and d: return -1
        if u: return 1
        if d: return 0
    return -1


@njit(cache=True)
def run(O, H, L, C, rel, td, s0, s1, s2):
    n = len(O); out = []
    i = 0
    while i < n:
        d = td[i]; j = i
        while j < n and td[j] == d: j += 1
        a = -1; b = -1; e = -1
        for k in range(i, j):
            if rel[k] >= s0 and a < 0: a = k
            if rel[k] < s1: b = k
            if rel[k] < s2: e = k
        if a >= 0 and b > a and e > b and rel[a] - s0 < 3 and s1 - rel[b] < 3 and s2 - rel[e] < 15:
            dH = -1e18; dL = 1e18; iH = -1e18; iL = 1e18; o5 = O[a]
            for k in range(a, b + 1):
                dH = max(dH, H[k]); dL = min(dL, L[k])
                if (rel[k] - s0) % 5 == 0: o5 = O[k]
                if (rel[k] + 1) % 5 == 0 or k == b:
                    iH = max(iH, max(o5, C[k])); iL = min(iL, min(o5, C[k]))
            cf = -1; dr = 0
            for k in range(b + 1, e + 1):
                if (rel[k] + 1) % 5 == 0:
                    if C[k] > dH: cf = k; dr = 1; break
                    if C[k] < dL: cf = k; dr = -1; break
            if cf >= 0 and cf < e:
                c = C[cf]
                if dr == 1:
                    s1r = first(H, L, cf + 1, e, dL, c + (c - dL))          # 1 = continuation first
                    s2r = first(H, L, cf + 1, e, iH, c + (c - iH))
                else:
                    r = first(H, L, cf + 1, e, c - (dH - c), dH); s1r = -1 if r < 0 else 1 - r
                    r = first(H, L, cf + 1, e, c - (iL - c), iL); s2r = -1 if r < 0 else 1 - r
                out.append((float(d), float(dr), float(s1r), float(s2r)))
        i = j
    A = np.empty((len(out), 4))
    for q in range(len(out)):
        for z in range(4): A[q, z] = out[q][z]
    return A


rows = []
for sym in ['NQ', 'ES', 'RTY']:
    m = load(sym); rel = (((m['ts'] % 1440) - 1080) % 1440).astype(np.int64)
    for nm, (s0, s1, s2) in SESS.items():
        A = run(m['O'], m['H'], m['L'], m['C'], rel, m['td'].astype(np.int64), s0, s1, s2)
        df = pd.DataFrame(A, columns=['td', 'dr', 's1', 's2']); df['sym'] = sym; df['sess'] = nm; rows.append(df)
D = pd.concat(rows); D['era'] = np.where(D.td >= D2025, 'score', 'fish')
def cl(y, g):
    _, inv = np.unique(g, return_inverse=True); mu = y.mean(); s = np.bincount(inv, weights=y - mu); return mu, np.sqrt((s ** 2).sum()) / len(y)
for s in SESS:
    for era in ['fish', 'score']:
        d = D[(D.sess == s) & (D.era == era)]
        out = []
        for col, lab in [('s1', 'opposite DR side vs same distance beyond: beyond first'), ('s2', 'IDR edge vs same distance beyond: beyond first')]:
            x = d[d[col] >= 0]; mu, se = cl(x[col].values, x.td.values)
            out.append(f'{lab} {100*mu:4.1f}% ±{100*se:3.1f} (n={len(x)})')
        print(s, era, ' | '.join(out))
D.to_pickle('/home/claude/lr/t11b_rows.pkl')
