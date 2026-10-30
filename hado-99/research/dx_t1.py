"""DXY → index: same-clock daily elasticity (index 17:00 vs DXY daily close ≈ 16–17:00 ET) by regime, lead tests,
seasonality. Regime variables from the prior day."""
import sys; sys.path.insert(0, '/home/claude/xa')
import pandas as pd, numpy as np
from tests import check, table
from xpanel import panel
X = pd.read_pickle('/home/claude/xa/dx_daily.pkl')
P = panel(X, '1700')
CLs = pd.read_pickle('/home/claude/xa/P_cl.pkl')
cl = CLs[CLs.sym == 'ES'][['shock', 'deepB', 'x_r']].rename(columns={'x_r': 'cl_r'})
P = P.join(cl, how='left')
P['x'] = P.x_r * 100; P['y'] = P.rI * 100
g = P.groupby('sym')
for k in ('x_tr20', 'x_ma200', 'x_vol20', 'carry', 'vix'):
    P[k + '_l'] = g[k].shift(1)
P['dUp'] = (P.x_tr20_l > 2).astype(int)
P['dDn'] = (P.x_tr20_l < -2).astype(int)
P['dAbove'] = (P.x_ma200_l > 0).astype(int)
P['hiVix'] = (P.vix_l > 20).astype(int)
P['hiCarry'] = (P.carry_l > 3).astype(int)
P['shock_l'] = P.groupby('sym').shock.shift(1)
P['q'] = P.index.quarter; P['m'] = P.index.month
P = P.dropna(subset=['x', 'y'])
def bc(d):
    return pd.Series({'n': len(d), 'corr': round(np.corrcoef(d.y, d.x)[0, 1], 2), 'beta': round(np.cov(d.y, d.x)[0, 1] / d.x.var(), 3)})
print(P.groupby(['sym', P.index.year]).apply(bc).unstack(0).to_string())
rows = [dict(test='beta (all)', **check(P, 'y ~ x', 'x'))]
for v in ('dUp', 'dDn', 'dAbove', 'hiVix', 'hiCarry', 'shock_l'):
    rows.append(dict(test=f'beta × {v}', **check(P.dropna(subset=[v]), f'y ~ x * {v}', f'x:{v}')))
for k in (1, 2, 3, 4):
    P['Qk'] = (P.q == k).astype(int)
    rows.append(dict(test=f'beta × Q{k}', **check(P, 'y ~ x * Qk', 'x:Qk')))
for mth in range(1, 13):
    P['Mk'] = (P.m == mth).astype(int)
    rows.append(dict(test=f'beta × month {mth}', **check(P, 'y ~ x * Mk', 'x:Mk')))
print(table(rows).round(3).to_string())
P.to_pickle('/home/claude/xa/P_dx.pkl')
