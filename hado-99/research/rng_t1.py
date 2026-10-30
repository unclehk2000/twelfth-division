"""Range by regime: does the macro regime (and DXY / CL volatility) say anything about the day's range beyond ADR20?
y = (H − L) / ADR20, CME day 18:00–17:00, front contract. Predictors from yesterday's closes only."""
import numpy as np, pandas as pd
from tests import check, table
DX = pd.read_pickle('dx_daily.pkl'); CL = pd.read_pickle('cl_daily.pkl')
# regime as the Pine computes it, from the prior day's values
R = pd.DataFrame(index=DX.index)
R['above'] = DX.c > DX.c.rolling(200).mean()
R['dxvol'] = DX.r.rolling(20).std() * np.sqrt(252) * 100
R['dxabs'] = DX.r.abs() * 100
C = pd.DataFrame(index=CL.index)
C['bk'] = -(CL.m2 / CL.m1 - 1) * 12 * 100
C['cl20'] = CL.r.rolling(20).sum() * 100
C['clvol'] = CL.r.rolling(20).std() * np.sqrt(252) * 100
C['clabs'] = CL.r.abs() * 100
out = []
for S in ('NQ', 'ES', 'RTY'):
    D = pd.read_pickle(f'idx_{S}.pkl')
    D = D[['h', 'l', 'adr20', 'vix']].copy()
    D['y'] = (D.h - D.l) / D.adr20
    # yesterday's macro values: last DXY / CL observation strictly before the trading day
    m = pd.merge_asof(D.reset_index().sort_values('date'), R.shift(0).reset_index().rename(columns={'date': 'dd'}).assign(date=lambda x: x.dd + pd.Timedelta(days=1)).drop(columns='dd').sort_values('date'), on='date', direction='backward')
    m = pd.merge_asof(m, C.reset_index().rename(columns={'date': 'dd'}).assign(date=lambda x: x.dd + pd.Timedelta(days=1)).drop(columns='dd').sort_values('date'), on='date', direction='backward')
    m['sym'] = S
    out.append(m)
P = pd.concat(out).dropna(subset=['y', 'above', 'bk', 'cl20']).set_index('date')
P = P[P.index >= '2018-03-01']
P['shock'] = ((P.bk > 15) & (P.cl20 > 10)).astype(float)
P['strong'] = ((P.above.astype(bool)) & (P.shock == 0)).astype(float)
P['reg'] = np.where(P.shock == 1, 'shock', np.where(P.strong == 1, 'strong', 'weak'))
P['half'] = np.where(P.index < '2025-01-01', '18-24', '25-26')
# volatility relative to its own trailing year (so 1 = normal)
for k in ('dxvol', 'clvol'):
    P[k + 'r'] = P.groupby('sym')[k].transform(lambda s: s / s.rolling(250, min_periods=120).mean().shift(1))
P['dxabsr'] = P.dxabs / (P.dxvol / np.sqrt(252))
P['clabsr'] = P.clabs / (P.clvol / np.sqrt(252))
P.to_pickle('P_rng.pkl')
print('mean range / ADR20 by regime\n', P.groupby(['reg', 'sym']).y.mean().unstack().round(3), '\nshare', P.groupby('reg').size() / len(P))
rows = []
for t, f, term in [('shock vs weak', 'y ~ shock + strong', 'shock'), ('strong vs weak', 'y ~ shock + strong', 'strong'),
                   ('DXY vol vs its year', 'y ~ dxvolr', 'dxvolr'), ('CL vol vs its year', 'y ~ clvolr', 'clvolr'),
                   ('yday |DXY| (in daily sd)', 'y ~ dxabsr', 'dxabsr'), ('yday |CL| (in daily sd)', 'y ~ clabsr', 'clabsr'),
                   ('DXY vol, given regime', 'y ~ dxvolr + clvolr + shock + strong', 'dxvolr'), ('CL vol, given regime', 'y ~ dxvolr + clvolr + shock + strong', 'clvolr'),
                   ('shock, given vols', 'y ~ dxvolr + clvolr + shock + strong', 'shock')]:
    r = check(P.dropna(subset=['dxvolr', 'clvolr', 'dxabsr', 'clabsr']), f, term); r['test'] = t; rows.append(r)
pd.set_option('display.width', 220)
print(table(rows).round(4).to_string())
