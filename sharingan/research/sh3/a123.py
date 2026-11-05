import numpy as np, pandas as pd
def cl(x, g):
    x = pd.Series(np.asarray(x, float)); g = pd.Series(np.asarray(g)); m = x.notna(); x, g = x[m], g[m]
    mu = x.mean(); r = (x - mu).groupby(g.values).sum(); return mu, np.sqrt((r ** 2).sum()) / len(x), len(x)
T = pd.read_pickle('t1_rows.pkl'); T = T[T.dup == 0]; T['half'] = np.where(T.yr >= 2025, 'test', 'train')
print('T1 draw: level vs mirror (same distance, other side of the period open), pts; standing levels, unique prices')
for L in ('H', 'M15', 'M5', 'M1'):
    for h in ('train', 'test'):
        q = T[(T.layer == L) & (T.half == h)]
        a = cl(q.h20 - q.m20, q.td); b = cl(q.hE - q.mE, q.td)
        print(f'{L:4s} {h:5s} n {a[2]:7d}  lvl20 {100*q.h20.mean():5.1f} mir {100*q.m20.mean():5.1f} ex {100*a[0]:+5.1f}±{100*a[1]:.1f} | by+60 lvl {100*q.hE.mean():5.1f} mir {100*q.mE.mean():5.1f} ex {100*b[0]:+5.1f}±{100*b[1]:.1f}')
q = T[T.half == 'train']
print('train by side (hi/lo) ex20:', {L: tuple(round(100 * cl(q[(q.layer == L) & (q.side == s)].h20 - q[(q.layer == L) & (q.side == s)].m20, q[(q.layer == L) & (q.side == s)].td)[0], 1) for s in (1, -1)) for L in ('H', 'M15', 'M5', 'M1')})
print('train by N ex20:', {L: tuple(round(100 * (q[(q.layer == L) & (q.N == N)].h20 - q[(q.layer == L) & (q.N == N)].m20).mean(), 1) for N in (20, 40, 60)) for L in ('H', 'M15', 'M5', 'M1')})
print('reach by distance (train, within 20 units), all layers pooled: d ATR bins')
q = T[T.half == 'train'].copy(); q['b'] = pd.cut(q.d, [0, .5, 1, 2, 3, 5, 99])
print(q.groupby(['layer', 'b'], observed=True).h20.mean().unstack().mul(100).round(0).to_string())
T2 = pd.read_pickle('t2_rows.pkl')
def near(p): return ((abs(p - 20) <= 2) | (abs(p - 40) <= 2) | (p >= 58))
def ends(p): return ((p <= 2) | (p >= 58))
print('\nT2 timing: share of window highs/lows within ±2 of +20/+40 or at 58–60 (and at either end), real vs sign-flipped')
for L in ('H', 'M15', 'M5', 'M1'):
    for h, yy in (('train', T2.yr <= 2024), ('test', T2.yr >= 2025)):
        q = T2[(T2.layer == L) & yy]
        r = (near(q.pH).astype(float) + near(q.pL)) / 2
        nl = sum(near(q[f'nH{i}']).astype(float) + near(q[f'nL{i}']) for i in range(3)) / 6
        a = cl(r - nl, q.td)
        e1 = (ends(q.pH).astype(float) + ends(q.pL)) / 2; e0 = sum(ends(q[f'nH{i}']).astype(float) + ends(q[f'nL{i}']) for i in range(3)) / 6
        print(f'{L:4s} {h:5s} n {len(q):6d} marks real {100*r.mean():5.1f} null {100*nl.mean():5.1f} ex {100*a[0]:+5.1f}±{100*a[1]:.1f} | ends real {100*e1.mean():5.1f} null {100*e0.mean():5.1f}')
T3 = pd.read_pickle('t3_rows.pkl')
print('\nT3 order flow: P(20-unit high first) by 60-unit flow before the anchor, real vs sign-flipped (ties dropped)')
for L in ('H', 'M15', 'M5', 'M1'):
    for h, yy in (('train', T3.yr <= 2024), ('test', T3.yr >= 2025)):
        q = T3[(T3.layer == L) & yy & T3['first'].isin([1, -1])]
        for fl, ff in (('up', q.flow > 0), ('dn', q.flow < 0)):
            z = q[ff]; real = (z['first'] == 1).astype(float)
            nl = sum((z[f'n{i}'] == 1).astype(float) / (z[f'n{i}'].isin([1, -1])).astype(float).replace(0, np.nan) for i in range(3)) / 3
            a = cl(real - nl, z.td)
            print(f'{L:4s} {h:5s} flow {fl}: n {len(z):5d} high first {100*real.mean():5.1f} null {100*nl.mean():5.1f} ex {100*a[0]:+5.1f}±{100*a[1]:.1f}')
