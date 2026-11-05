"""T9 (Zabimaru): the OR reclaim. OR = 09:30–09:59 1m high/low. After 10:00, the first break; then the first 1m close back
inside the OR (a reclaim) before 16:14. Race from the reclaim close: the opposite OR side vs a new extreme beyond the
break's high (low) so far. Null: per-bar sign flip after the reclaim bar, 4 replicates. Also: P(opposite side by 16:14)."""
import numpy as np, pandas as pd, sys
from numba import njit
sys.path.insert(0, '/home/claude/lr')
from lib import load, flipbar, D2025
from rat import ratio_diff


@njit(cache=True)
def race(H, L, C, t, e, up_lvl, dn_lvl, rep):
    cp = C[t]
    for j in range(t + 1, e + 1):
        if rep < 0: h = H[j]; l = L[j]
        else: h, l, cp = flipbar(H, L, C, j, cp, rep)
        u = h > up_lvl; d = l < dn_lvl
        if u and d: return -1
        if u: return 0
        if d: return 1
    return -1


@njit(cache=True)
def scan(H, L, C, tod, td, ct):
    n = len(H); rows = []
    i = 0
    while i < n:
        d = td[i]; j = i
        while j < n and td[j] == d: j += 1
        # RTH bars of this trading day
        s = -1; e = -1; oh = -1e18; ol = 1e18; ok = True
        for k in range(i, j):
            if tod[k] >= 570 and tod[k] < 600:
                if s < 0: s = k
                oh = max(oh, H[k]); ol = min(ol, L[k])
            if tod[k] >= 600 and tod[k] <= 974: e = k
        if s < 0 or e < 0 or ct[s] != ct[e]:
            i = j; continue
        k0 = s
        while k0 < j and tod[k0] < 600: k0 += 1
        side = 0; ext = 0.0; rec = -1
        for k in range(k0, e + 1):
            if side == 0:
                if H[k] > oh and L[k] < ol: break
                if H[k] > oh: side = 1; ext = H[k]
                elif L[k] < ol: side = -1; ext = L[k]
                if side != 0 and ((side == 1 and C[k] < oh) or (side == -1 and C[k] > ol)):
                    pass
                continue
            if side == 1:
                ext = max(ext, H[k])
                if C[k] < oh: rec = k; break
                if L[k] < ol: break
            else:
                ext = min(ext, L[k])
                if C[k] > ol: rec = k; break
                if H[k] > oh: break
        if rec > 0:
            if side == 1: up_lvl = ext; dn_lvl = ol
            else: up_lvl = -ext; dn_lvl = -oh
            r = [float(rec), float(side), (C[rec] - ol) / (oh - ol) if side == 1 else (oh - C[rec]) / (oh - ol), (ext - oh) / (oh - ol) if side == 1 else (ol - ext) / (oh - ol)]
            if side == 1:
                r.append(float(race(H, L, C, rec, e, up_lvl, dn_lvl, -1)))
                for rep in range(4): r.append(float(race(H, L, C, rec, e, up_lvl, dn_lvl, rep)))
            else:
                nH = -L; nL = -H; nC = -C
                r.append(float(race(nH, nL, nC, rec, e, up_lvl, dn_lvl, -1)))
                for rep in range(4): r.append(float(race(nH, nL, nC, rec, e, up_lvl, dn_lvl, rep)))
            rows.append(r)
        i = j
    out = np.empty((len(rows), 9))
    for a in range(len(rows)):
        for c in range(9): out[a, c] = rows[a][c]
    return out


res = []
for sym in ['NQ', 'ES', 'RTY']:
    m = load(sym)
    R = scan(m['H'], m['L'], m['C'], (m['ts'] % 1440).astype(np.int64), m['td'].astype(np.int64), m['ct'].astype(np.int64))
    df = pd.DataFrame(R, columns=['t', 'side', 'pos', 'ext', 'y', 'y0', 'y1', 'y2', 'y3'])
    df['td'] = m['td'][df.t.astype(int)]; df['sym'] = sym; res.append(df)
D = pd.concat(res, ignore_index=True); D['g'] = D.sym + D.td.astype(str); D['era'] = np.where(D.td >= D2025, 'score', 'fish')
print('days with a reclaim:', len(D))
for era in ['fish', 'score']:
    d = D[D.era == era]
    ar = (d.y == 1).astype(float); br = (d.y >= 0).astype(float)
    an = np.mean([(d[f'y{r}'] == 1).astype(float) for r in range(4)], 0); bn = np.mean([(d[f'y{r}'] >= 0).astype(float) for r in range(4)], 0)
    Pr, Pn, dd, se, ser, nb = ratio_diff(ar, br, an, bn, d.g)
    print(f'{era}: after a reclaim, the opposite OR side before a new extreme: real {100*Pr:.1f}% vs flip {100*Pn:.1f}% ({100*dd:+.1f} ± {100*se:.1f}), n={nb}')
