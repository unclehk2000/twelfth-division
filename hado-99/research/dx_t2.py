"""DXY lead tests: daily (next overnight / RTH / 5 days), weekly (next week's range, return, premium), and a
combined dollar + oil 'pressure' regime."""
import sys; sys.path.insert(0, '/home/claude/xa')
import pandas as pd, numpy as np
from tests import check, table
P = pd.read_pickle('/home/claude/xa/P_dx.pkl')
g = P.groupby('sym')
P['rth'] = np.log(P.p1600 / P.o0930).where(P.p1600_c == P.o0930_c) * 100
P['on'] = np.log(P.o0930 / g.p1700.shift(1)).where(P.o0930_c == g.p1700_c.shift(1)) * 100
g = P.groupby('sym')
P['n_rth'] = g.rth.shift(-1); P['n_on'] = g.on.shift(-1)
P['n5'] = g.y.transform(lambda s: s[::-1].rolling(5).sum()[::-1].shift(-1))
P['rngA'] = (P.h - P.l) / P.adr20
P['n_rngA'] = g.rngA.shift(-1)
P['ax'] = P.x.abs()
rows = []
for y in ('n_on', 'n_rth', 'n5'):
    rows.append(dict(test=f'{y} ~ DXY day', **check(P.dropna(subset=[y]), f'{y} ~ x', 'x')))
    rows.append(dict(test=f'{y} ~ DXY day × dUp', **check(P.dropna(subset=[y]), f'{y} ~ x * dUp', 'x:dUp')))
    rows.append(dict(test=f'{y} ~ DXY 20d trend', **check(P.dropna(subset=[y, 'x_tr20']), f'{y} ~ x_tr20', 'x_tr20')))
rows.append(dict(test='next range ~ |DXY| | own range, VIX', **check(P.dropna(subset=['n_rngA', 'rngA', 'vix']), 'n_rngA ~ rngA + np.log(vix) + ax', 'ax')))
rows.append(dict(test='next range ~ DXY vol20 | own, VIX', **check(P.dropna(subset=['n_rngA', 'rngA', 'vix', 'x_vol20']), 'n_rngA ~ rngA + np.log(vix) + x_vol20', 'x_vol20')))
print(table(rows).round(4).to_string())
P.to_pickle('/home/claude/xa/P_dx.pkl')
