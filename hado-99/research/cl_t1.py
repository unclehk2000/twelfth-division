"""T1: CL → index elasticity (same-clock daily returns, 14:30 ET) by regime. Regime variables use the prior day."""
import sys; sys.path.insert(0, '/home/claude/xa')
import pandas as pd, numpy as np
from tests import check, table
P = pd.read_pickle('/home/claude/xa/P_cl.pkl')
P['x'] = P.x_r * 100; P['y'] = P.rI * 100
g = P.groupby('sym')
P['ts_l'] = g.x_ts12.shift(1)
P['cl20'] = g.x_r.transform(lambda s: s.rolling(20).sum().shift(1)) * 100
P['clv20'] = g.x_r.transform(lambda s: s.rolling(20).std().shift(1)) * np.sqrt(252) * 100
P['carry_l'] = g.carry.shift(1)
P['vix_l'] = g.vix.shift(1)
P['deepB'] = (P.ts_l < -15).astype(int)
P['contango'] = (P.ts_l > 0).astype(int)
P['clUp'] = (P.cl20 > 10).astype(int)
P['clDn'] = (P.cl20 < -10).astype(int)
P['hiCarry'] = (P.carry_l > 3).astype(int)
P['negCarry'] = (P.carry_l < 0).astype(int)
P['hiVix'] = (P.vix_l > 20).astype(int)
P['shock'] = ((P.ts_l < -15) & (P.cl20 > 10)).astype(int)
P['q'] = P.index.quarter
P['m'] = P.index.month
P = P.dropna(subset=['x', 'y'])
rows = [dict(test='beta (all)', **check(P, 'y ~ x', 'x'))]
for v in ('deepB', 'contango', 'clUp', 'clDn', 'hiCarry', 'negCarry', 'hiVix', 'shock'):
    rows.append(dict(test=f'beta × {v}', **check(P, f'y ~ x * {v}', f'x:{v}')))
print(table(rows).round(3).to_string())
# share of days in each regime by half
print(P.groupby('half')[['deepB', 'contango', 'clUp', 'clDn', 'hiCarry', 'negCarry', 'hiVix', 'shock']].mean().round(3).to_string())
# betas inside each regime (ES), by half
for v in ('deepB', 'shock', 'hiCarry', 'contango'):
    for h in ('18-24', '25-26'):
        for k in (0, 1):
            d = P[(P[v] == k) & (P.half == h)]
            if len(d) > 30:
                b = np.cov(d.y, d.x)[0, 1] / d.x.var(); c = np.corrcoef(d.y, d.x)[0, 1]
                print(v, h, k, len(d), 'beta %.3f corr %.2f' % (b, c))
P.to_pickle('/home/claude/xa/P_cl.pkl')
