"""Macro filter on C2 setups. Is a C2 whose candle had the dollar / oil moving its way more likely to see C3 take C2's
other extreme (take2) or C2's extreme hold (hold3), at the same close location?
15m: DXY 5-minute change across the C2 candle (2023–26; all tested DXY betas are negative, so 'with' a bull C2 = DXY down).
1D:  the regime-implied index move from DXY and CL on C2's day (tested two-factor betas for the regime, from the prior day)."""
import json, numpy as np, pandas as pd
from tests import check, table
pd.set_option('display.width', 220)
rows = []
# ── 15m
E = pd.read_pickle('fm/E_all_15.pkl')
E = E[(E.kind == 'C2') & (E.t0 >= '2023-01-03')].copy()
E['q'] = np.digitize(E.clv, [0.25, 0.5, 0.75])
DX = pd.read_pickle('dx_5m.pkl').drop_duplicates('ts').set_index('ts').Close.sort_index()
end = DX.reindex(E.t0 + pd.Timedelta(minutes=10)).to_numpy()
beg = DX.reindex(E.t0 - pd.Timedelta(minutes=5)).to_numpy()
E['dchg'] = (end / beg - 1) * 100
c15 = (DX.shift(-2) / DX.shift(1) - 1) * 100                       # every 15-minute change on the 5-minute grid
sd = c15.rolling(4000, min_periods=1000).std().shift(1)
E['dsd'] = sd.reindex(E.t0).to_numpy()
E = E.dropna(subset=['dchg', 'dsd'])
E['dir'] = np.where(E.side == 'bull', 1, -1)
E['wz'] = -E.dir * E.dchg / E.dsd                                    # > 0: the dollar moved the setup's way
E['w'] = (E.wz > 0.5).astype(float); E['a'] = (E.wz < -0.5).astype(float)
E['half'] = np.where(E.t0 < '2025-01-01', '23-24', '25-26')
E['date'] = pd.to_datetime(E.tday); E = E.set_index('date')
for y in ('take2', 'hold3'):
    E[y] = E[y].astype(float)
    for t, f, term in [(f'15m {y}: DXY with (z)', f'{y} ~ wz + C(q)', 'wz'), (f'15m {y}: with > 0.5 sd', f'{y} ~ w + a + C(q)', 'w'), (f'15m {y}: against > 0.5 sd', f'{y} ~ w + a + C(q)', 'a')]:
        r = check(E, f, term); r['test'] = t; rows.append(r)
print('15m C2s with DXY', len(E), ' share with/against/flat', round(E.w.mean(), 3), round(E.a.mean(), 3), round(1 - E.w.mean() - E.a.mean(), 3))
g = E.groupby([np.where(E.w == 1, 'with', np.where(E.a == 1, 'against', 'flat')), 'q'])[['take2', 'hold3']].mean().unstack().round(3)
print(g.to_string())
E.to_pickle('fm/E15_macro.pkl')
# ── 1D
T = json.load(open('regime_tables.json'))
D = pd.read_pickle('fm/E_all_D.pkl')
D = D[D.kind == 'C2'].copy()
D['q'] = np.digitize(D.clv, [0.25, 0.5, 0.75])
P = pd.read_pickle('P_rng.pkl')[['sym', 'reg']].reset_index()          # regime from the prior day, by date and symbol
DX = pd.read_pickle('dx_daily.pkl'); CL = pd.read_pickle('cl_daily.pkl')
D['date'] = pd.to_datetime(D.tday).dt.normalize()
D = D.merge(P, on=['date', 'sym'], how='left')
D['dxr'] = DX.r.reindex(D.date).to_numpy() * 100
D['clr'] = CL.r.reindex(D.date).to_numpy() * 100
key = {'weak': 'below', 'strong': 'above', 'shock': 'shock'}
D['bD'] = [T[s][key[g]]['b2D'] if isinstance(g, str) else np.nan for s, g in zip(D.sym, D.reg)]
D['bC'] = [T[s][key[g]]['b2C'] if isinstance(g, str) else np.nan for s, g in zip(D.sym, D.reg)]
D['imp'] = D.bD * D.dxr + D.bC * D.clr
D = D.dropna(subset=['imp'])
D['dir'] = np.where(D.side == 'bull', 1, -1)
sdi = D.groupby('sym').imp.transform(lambda s: s.abs().expanding(50).mean().shift(1))
D['wz'] = D.dir * D.imp / sdi
D['w'] = (D.wz > 0.5).astype(float); D['a'] = (D.wz < -0.5).astype(float)
D['half'] = np.where(D.date < '2025-01-01', '18-24', '25-26')
D = D.dropna(subset=['wz']).set_index('date')
for y in ('take2', 'hold3'):
    D[y] = D[y].astype(float)
    for t, f, term in [(f'1D {y}: macro with (z)', f'{y} ~ wz + C(q)', 'wz'), (f'1D {y}: with > 0.5', f'{y} ~ w + a + C(q)', 'w'), (f'1D {y}: against > 0.5', f'{y} ~ w + a + C(q)', 'a')]:
        r = check(D, f, term); r['test'] = t; rows.append(r)
print('1D C2s', len(D), ' share with/against', round(D.w.mean(), 3), round(D.a.mean(), 3))
print(D.groupby(np.where(D.w == 1, 'with', np.where(D.a == 1, 'against', 'flat')))[['take2', 'hold3']].agg(['mean', 'size']).round(3).to_string())
print(table(rows).round(4).to_string())
