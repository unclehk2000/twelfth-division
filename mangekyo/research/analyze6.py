import numpy as np, pandas as pd
from split import show, clus, wkof
from data import daily
exec(open('analyze4.py').read().split("for nm, zf")[0])
Z = add(pd.read_pickle('zones.pkl')); Q = add(pd.read_pickle('ctl.pkl'))
for o in (Z, Q):
    o['hold10'] = np.where(o.tT >= 0, ~((o.tX >= 0) & (o.tX - o.tT <= 10)), np.nan).astype(float)
q = Q.groupby('of')[['rej', 'inside', 'hold10', 'bounce']].mean(); F = Z[Z.kind == 'FVG'].join(q, rsuffix='_c')
# FVG with a body gap (volume imbalance) on either side of candle 2, under the settlement close
vi = []
for s in F.sym.unique():
    D = daily(s); O, C = D.bo.values, D.bc.values; bt = np.maximum(O, C); bb = np.minimum(O, C)
    g = F[F.sym == s]; t = g.t0.values; d = g.dir.values
    a = np.where(d == 1, bb[t - 1] > bt[t - 2], bt[t - 1] < bb[t - 2]); b = np.where(d == 1, bb[t] > bt[t - 1], bt[t] < bb[t - 1])
    vi.append(pd.Series(np.where(a & b, 'VI both sides', np.where(a | b, 'VI one side', 'no VI')), index=g.index))
F['vi'] = pd.concat(vi)
F['disp'] = np.where(F.c2body >= 1.0, 'c2 body ≥ 1 ATR', 'c2 body < 1 ATR')
F['major'] = np.where((F.w >= 0.5), 'gap ≥ 0.5 ATR', 'gap < 0.5 ATR')
for v in ['inside', 'hold10', 'bounce']:
    for by in ['vi', 'disp', 'major']:
        show(F[F[v].notna()], v, by)
# where inside the zone does the touch day's wick stop?  (deep in zone units, 0 = near edge, 1 = far edge)
Zi = Z[(Z.kind == 'FVG') & (Z.deep >= 0) & (Z.deep <= 1)]; Qi = Q[(Q.deep >= 0) & (Q.deep <= 1)]
bins = np.linspace(0, 1, 9)
hz = np.histogram(Zi.deep, bins)[0] / len(Zi); hq = np.histogram(Qi.deep, bins)[0] / len(Qi)
print('touch-day extreme inside the zone, by octant (real vs control):')
for i in range(8): print(f'  {bins[i]:.3f}–{bins[i+1]:.3f}  {hz[i]:.3f}  {hq[i]:.3f}')
ce = lambda x: (np.abs(x - 0.5) <= 0.0625).mean()
print('within ±1/16 of CE: real', round(ce(Zi.deep), 3), 'ctl', round(ce(Qi.deep), 3), 'n', len(Zi), len(Qi))
