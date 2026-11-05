"""T11c: live reach odds for the DR/IDR levels. Every 5 minutes after the confirmation until the session ends, for three
targets (the opposite DR side; 1 and 2 IDR widths beyond the IDR the confirmed way), whether price trades it before the end.
Model (Brownian touch): P = 2·(1 − Φ(k · d / (W · √(T/60)))), d = distance now, W = the DR's width, T = minutes left.
k fitted per session on 2018–24; scored on 2025–26 (Brier vs the base rate; calibration by tenths)."""
import numpy as np, pandas as pd, sys
from numba import njit
from scipy.optimize import minimize_scalar
from scipy.stats import norm
sys.path.insert(0, '/home/claude/lr'); from lib import load, D2025
SESS = {'RDR': (930, 990, 1320), 'ODR': (540, 600, 870), 'ADR': (90, 150, 480)}


@njit(cache=True)
def run(O, H, L, C, rel, td, s0, s1, s2):
    n = len(O); out = []
    i = 0
    while i < n:
        dd = td[i]; j = i
        while j < n and td[j] == dd: j += 1
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
            if cf >= 0 and cf < e and iH > iL:
                W = dH - dL; w = iH - iL
                tg = np.empty(3)
                if dr == 1:
                    tg[0] = dL; tg[1] = iH + w; tg[2] = iH + 2 * w
                else:
                    tg[0] = dH; tg[1] = iL - w; tg[2] = iL - 2 * w
                # first touch index of each target after cf (or −1)
                ft = np.full(3, -1, np.int64)
                for k in range(cf + 1, e + 1):
                    for z in range(3):
                        if ft[z] < 0 and L[k] <= tg[z] <= H[k]: ft[z] = k
                        elif ft[z] < 0 and ((z == 0) == (dr == 1)) and L[k] <= tg[z]: ft[z] = k
                        elif ft[z] < 0 and ((z == 0) != (dr == 1)) and H[k] >= tg[z]: ft[z] = k
                for k in range(cf, e, 5):
                    T = float(rel[e] - rel[k])
                    if T < 5: break
                    for z in range(3):
                        if ft[z] >= 0 and ft[z] <= k: continue
                        dist = abs(C[k] - tg[z])
                        out.append((float(dd), float(z), dist / W, T, 1.0 if ft[z] > k else 0.0))
        i = j
    A = np.empty((len(out), 5))
    for q in range(len(out)):
        for c in range(5): A[q, c] = out[q][c]
    return A


rows = []
for sym in ['NQ', 'ES', 'RTY']:
    m = load(sym); rel = (((m['ts'] % 1440) - 1080) % 1440).astype(np.int64)
    for nm, (s0, s1, s2) in SESS.items():
        A = run(m['O'], m['H'], m['L'], m['C'], rel, m['td'].astype(np.int64), s0, s1, s2)
        df = pd.DataFrame(A, columns=['td', 'tg', 'x', 'T', 'y']); df['sess'] = nm; df['sym'] = sym; rows.append(df)
D = pd.concat(rows, ignore_index=True); D['era'] = np.where(D.td >= D2025, 'score', 'fish')
D['u'] = D.x / np.sqrt(D['T'] / 60.0)
P = lambda k, u: np.clip(2 * (1 - norm.cdf(k * u)), 1e-6, 1 - 1e-6)
K = {}
for s in SESS:
    f = D[(D.sess == s) & (D.era == 'fish')]
    r = minimize_scalar(lambda k: -np.mean(f.y * np.log(P(k, f.u)) + (1 - f.y) * np.log(1 - P(k, f.u))), bounds=(0.1, 5), method='bounded')
    K[s] = r.x
    sc = D[(D.sess == s) & (D.era == 'score')]
    p = P(r.x, sc.u)
    br = np.mean((p - sc.y) ** 2); b0 = np.mean((sc.y.mean() - sc.y) ** 2)
    tb = pd.DataFrame(dict(p=p, y=sc.y)).groupby(pd.cut(p, [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0]), observed=True).mean().round(3)
    print(s, f'k={r.x:.3f}  score Brier {br:.4f} vs base {b0:.4f}  n={len(sc)}')
    print('   predicted→actual:', ' '.join(f'{100*a:.0f}→{100*b:.0f}' for a, b in zip(tb.p, tb.y)))
    for z, nm in [(0, 'opposite side'), (1, '+1 IDR'), (2, '+2 IDR')]:
        q = sc[sc.tg == z]; pq = P(r.x, q.u)
        print(f'   {nm:13s} predicted {100*pq.mean():.1f}%  actual {100*q.y.mean():.1f}%')
import json; json.dump(K, open('/home/claude/lr/t11c_k.json', 'w')); print(K)
D['yr'] = pd.to_datetime(D.td, unit='D').dt.year
for s in SESS:
    ks = []
    for yr, f in D[D.sess == s].groupby('yr'):
        r = minimize_scalar(lambda k: -np.mean(f.y * np.log(P(k, f.u)) + (1 - f.y) * np.log(1 - P(k, f.u))), bounds=(0.1, 5), method='bounded'); ks.append(f'{yr}:{r.x:.2f}')
    print(s, ' '.join(ks))
D.to_pickle('/home/claude/lr/t11c_rows.pkl')
