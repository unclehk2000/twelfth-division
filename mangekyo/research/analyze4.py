"""Rejection on the touch day (ICT: the wick does the damage, the body respects): the touch day's wick enters the zone without
trading through (or without passing CE) and the day closes back outside on the near side."""
import numpy as np, pandas as pd
from split import clus, wkof
def add(o):
    o = o.copy(); t = o.tT >= 0
    o['rej'] = np.where(t, (o.deep <= 1) & (o.bodyPos <= 0), np.nan).astype(float)
    o['rejCE'] = np.where(t, (o.deep <= 0.5) & (o.bodyPos <= 0), np.nan).astype(float)
    o['inside'] = np.where(t, (o.deep <= 1), np.nan).astype(float)
    # first-touch follow-through: the next 5 days' best move away from the near edge, in ATR, minus the worst move through it
    return o
for nm, zf, cf in (('2010–26 SET (FVG only controls)', 'zones.pkl', 'ctl.pkl'), ('2018–26 by setting', 'zones_var.pkl', 'ctl_var.pkl')):
    Z = add(pd.read_pickle(zf)); Q = add(pd.read_pickle(cf))
    q = Q.groupby('of')[['rej', 'rejCE', 'inside']].mean(); Z = Z.join(q, rsuffix='_c')
    if 'var' not in Z: Z['var'] = 'SET'
    print(nm)
    for (v, k), g in Z.groupby(['var', 'kind']):
        if g.rej_c.notna().sum() < 50: continue
        s = []
        for m in ['inside', 'rej', 'rejCE']:
            mm, se, t, n = clus(g[m] - g[m + '_c'], wkof(g.date))
            sy = ''.join('+' if (gg[m] - gg[m + '_c']).mean() > 0 else '−' for _, gg in g.groupby('sym'))
            s.append(f"{m} {g[m].mean():.3f}/{g[m+'_c'].mean():.3f} {mm:+.3f} t{t:+.1f} {sy}")
        print(f"  {v:4s} {k:3s} n{g.rej.notna().sum():5d} | " + ' | '.join(s))
