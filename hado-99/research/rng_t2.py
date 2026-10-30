"""(a) buckets for yesterday's |DXY| / |CL| move vs today's range / ADR20 (2018–26);
(b) at 09:30: DXY's move since yesterday's 17:00 (in daily sd) vs the NY session range 09:30–16:00 / its own ADR20 (2023–26)."""
import numpy as np, pandas as pd
from tests import check, table
P = pd.read_pickle('P_rng.pkl')
P['mx'] = np.maximum(P.dxabsr, P.clabsr)
b = pd.cut(P.mx, [0, 0.5, 1, 1.5, 2, 99], right=False)
t = P.groupby([b, 'sym'], observed=True).y.mean().unstack()
t['all'] = P.groupby(b, observed=True).y.mean(); t['n'] = P.groupby(b, observed=True).size(); t['share'] = t.n / len(P)
for h, g in P.groupby('half'):
    t[h] = g.groupby(pd.cut(g.mx, [0, 0.5, 1, 1.5, 2, 99], right=False), observed=True).y.mean()
print('(a) range / ADR20 by the bigger of yesterday\'s |DXY| and |CL| move (daily sd)\n', t.round(3).to_string())
r = check(P.dropna(subset=['mx']), 'y ~ mx', 'mx'); print('mx slope', {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
# (b) NY session
DX = pd.read_pickle('dx_5m.pkl'); DX = DX.set_index('ts').sort_index()
DXd = pd.read_pickle('dx_daily.pkl')
sdd = (DXd.r.rolling(20).std() * 100).shift(1)                          # yesterday's 20-day daily sd, %
rows = []
for S in ('NQ', 'ES', 'RTY'):
    B = pd.read_pickle(f'/home/claude/kyw/bars_{S}_all.pkl')
    B = B[B.ts >= '2023-01-01']
    r = B[(B.hm >= 930) & (B.hm < 1600)].groupby('tday').agg(h=('High', 'max'), l=('Low', 'min'), n=('ts', 'size'), c0=('Contract', 'first'), c1=('Contract', 'last'))
    r = r[(r.n > 350) & (r.c0 == r.c1)]
    r['rng'] = r.h - r.l
    r['adr'] = r.rng.rolling(20).mean().shift(1)
    r['y'] = r.rng / r.adr
    for d in r.index:
        d = pd.Timestamp(d)
        t0 = d - pd.Timedelta(days=1) + pd.Timedelta(hours=16, minutes=55)
        t1 = d + pd.Timedelta(hours=9, minutes=25)
        a = DX.Close.loc[:t0]; z = DX.Close.loc[:t1]
        if len(a) == 0 or len(z) == 0 or (t0 - a.index[-1]) > pd.Timedelta(days=3) or (t1 - z.index[-1]) > pd.Timedelta(hours=1):
            continue
        s = sdd.loc[:d - pd.Timedelta(days=1)]
        if len(s) == 0 or np.isnan(s.iloc[-1]):
            continue
        rows.append(dict(date=d, sym=S, y=r.y.loc[d.date()] if d.date() in r.index else r.y.loc[d], on=abs(z.iloc[-1] / a.iloc[-1] - 1) * 100 / s.iloc[-1]))
Q = pd.DataFrame(rows).dropna().set_index('date')
Q['half'] = np.where(Q.index < '2025-01-01', '23-24', '25-26')
Q.to_pickle('P_rng_ny.pkl')
b = pd.cut(Q.on, [0, 0.25, 0.5, 1, 1.5, 99], right=False)
t = Q.groupby([b, 'sym'], observed=True).y.mean().unstack(); t['all'] = Q.groupby(b, observed=True).y.mean(); t['share'] = Q.groupby(b, observed=True).size() / len(Q)
for h, g in Q.groupby('half'):
    t[h] = g.groupby(pd.cut(g.on, [0, 0.25, 0.5, 1, 1.5, 99], right=False), observed=True).y.mean()
print('\n(b) NY range / its ADR20 by DXY\'s overnight move to 09:25 (daily sd)\n', t.round(3).to_string())
r = check(Q, 'y ~ on', 'on'); print('on slope', {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
