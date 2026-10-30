"""First pass: real gaps vs matched no-gap controls (FVG), reach and first-touch respect, pooled and per symbol / period."""
import numpy as np, pandas as pd
Z = pd.read_pickle('zones.pkl'); Q = pd.read_pickle('ctl.pkl')
Z['key'] = Z.index
def add(o):
    o = o.copy()
    o['T5'] = ((o.tT >= 0) & (o.tT - o.t0 <= 5)).astype(float)
    o['T20'] = ((o.tT >= 0) & (o.tT - o.t0 <= 20)).astype(float)
    o['M20'] = ((o.tM >= 0) & (o.tM - o.t0 <= 20)).astype(float)
    o['F20'] = ((o.tF >= 0) & (o.tF - o.t0 <= 20)).astype(float)
    o['X20'] = ((o.tX >= 0) & (o.tX - o.t0 <= 20)).astype(float)
    # after the first touch: closed beyond the far edge within 10 days of the touch
    o['hold10'] = np.where(o.tT >= 0, ~((o.tX >= 0) & (o.tX - o.tT <= 10)), np.nan).astype(float)
    return o
Z = add(Z); Q = add(Q)
F = Z[Z.kind == 'FVG']
q = Q.groupby('of')[['T5', 'T20', 'M20', 'F20', 'X20', 'hold10', 'bounce']].mean()
F = F.join(q, rsuffix='_c')
def clus(diff, wk):
    d = pd.DataFrame({'d': diff, 'w': wk}).dropna()
    g = d.groupby('w').d.agg(['sum', 'count'])
    m = g['sum'].sum() / g['count'].sum()
    # cluster-robust SE of a mean
    e = (g['sum'] - m * g['count'])
    se = np.sqrt((e ** 2).sum()) / g['count'].sum()
    return m, se, m / se if se > 0 else np.nan, len(d)
F['wk'] = (F.date - pd.to_timedelta(F.date.dt.dayofweek, unit='D'))
print('FVG real vs control (5 matched no-gap windows each)')
for v in ['T5', 'T20', 'M20', 'F20', 'X20', 'hold10', 'bounce']:
    m, se, t, n = clus(F[v] - F[v + '_c'], F.wk)
    per = {s: round((g[v] - g[v + '_c']).mean(), 3) for s, g in F.groupby('sym')}
    pp = {p: round((g[v] - g[v + '_c']).mean(), 3) for p, g in F.groupby(F.yr >= 2025)}
    print(f"  {v:7s} real {F[v].mean():.3f} ctl {F[v+'_c'].mean():.3f} diff {m:+.3f} ±{se:.3f} t {t:+.1f} n {n}  by sym {per}  2010–24/25–26 {pp}")
