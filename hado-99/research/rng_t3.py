"""Does the macro range effect survive the index's own recent range? (a) + yesterday's range / ADR20; (b) + the overnight range / its ADR20."""
import numpy as np, pandas as pd
from tests import check, table
P = pd.read_pickle('P_rng.pkl')
P['mx'] = np.maximum(P.dxabsr, P.clabsr)
P['ylag'] = P.groupby('sym').y.shift(1)
P['big'] = (P.mx >= 2).astype(float)
rows = []
for t, f, term in [('mx', 'y ~ mx', 'mx'), ('mx | yday range', 'y ~ mx + ylag', 'mx'), ('≥2 sd day | yday range', 'y ~ big + ylag', 'big'),
                   ('DXY only | yday range', 'y ~ dxabsr + ylag', 'dxabsr'), ('CL only | yday range', 'y ~ clabsr + ylag', 'clabsr')]:
    r = check(P.dropna(subset=['mx', 'ylag']), f, term); r['test'] = t; rows.append(r)
pd.set_option('display.width', 220)
print(table(rows).round(4).to_string())
# conditional table: ≥2 sd macro day, split by whether the index itself had a big day
P2 = P.dropna(subset=['mx', 'ylag'])
P2['own'] = pd.cut(P2.ylag, [0, 1, 1.5, 99], right=False)
print(P2.groupby(['own', P2.mx >= 2], observed=True).y.agg(['mean', 'size']).round(3).unstack().to_string())
# (b) NY
Q = pd.read_pickle('P_rng_ny.pkl')
on_rows = []
for S in ('NQ', 'ES', 'RTY'):
    B = pd.read_pickle(f'/home/claude/kyw/bars_{S}_all.pkl')
    B = B[B.ts >= '2022-11-01']
    o = B[(B.hm >= 1800) | (B.hm < 925)].groupby('tday').agg(h=('High', 'max'), l=('Low', 'min'))
    o['orng'] = o.h - o.l; o['oadr'] = o.orng.rolling(20).mean().shift(1); o['oy'] = o.orng / o.oadr
    o['sym'] = S; o.index = pd.to_datetime(o.index)
    on_rows.append(o[['oy', 'sym']])
O = pd.concat(on_rows)
Q = Q.reset_index().merge(O.reset_index().rename(columns={'tday': 'date'}), on=['date', 'sym'], how='left').set_index('date').dropna()
Q['big'] = (Q.on >= 1.5).astype(float)
rows = []
for t, f, term in [('on', 'y ~ on', 'on'), ('on | overnight range', 'y ~ on + oy', 'on'), ('≥1.5 sd | overnight range', 'y ~ big + oy', 'big')]:
    r = check(Q, f, term); r['test'] = t; rows.append(r)
print(table(rows).round(4).to_string())
