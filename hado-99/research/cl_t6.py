"""T6: minute lead-lag between CL and the index on the days with CL 1-minute data (FOMC weeks, 228 days).
corr(CL return in minute t, index return in minute t+k); then day-clustered regressions of the index's next 1–5
minutes on CL's minute, by regime (shock = deep backwardation and CL up 10%+ over 20 days, prior day)."""
import sys; sys.path.insert(0, '/home/claude/xa')
import pandas as pd, numpy as np
from tests import check, table
C = pd.read_pickle('/home/claude/xa/cl_1m.pkl')[['ts', 'Close', 'tday']].rename(columns={'Close': 'cl'})
C['rc'] = np.log(C.cl).diff().where(C.tday == C.tday.shift()) * 1e4            # basis points
P = pd.read_pickle('/home/claude/xa/P_cl.pkl')
reg = P[P.sym == 'ES'][['shock', 'deepB']]
out = []
for S in ('NQ', 'ES', 'RTY'):
    B = pd.read_pickle(f'/home/claude/kyw/bars_{S}_all.pkl')[['ts', 'Close', 'Contract', 'tday']]
    B = B[B.tday.isin(C.tday.unique())]
    B['ri'] = np.log(B.Close).diff().where((B.Contract == B.Contract.shift()) & (B.tday == B.tday.shift())) * 1e4
    J = C.merge(B[['ts', 'ri']], on='ts', how='inner').sort_values('ts')
    J['sym'] = S
    for k in range(1, 6):
        J[f'ri_f{k}'] = J.groupby('tday').ri.shift(-k)
    J['ri_f1_5'] = J[[f'ri_f{k}' for k in range(1, 6)]].sum(axis=1, min_count=5)
    J['rc_f1'] = J.groupby('tday').rc.shift(-1)
    J['hm'] = J.ts.dt.hour * 100 + J.ts.dt.minute
    J['rth'] = ((J.hm >= 930) & (J.hm < 1600)).astype(int)
    out.append(J)
J = pd.concat(out).dropna(subset=['rc', 'ri'])
J = J.join(reg, on='tday')
J = J.set_index('ts')
J['half'] = np.where(J.index < '2025-01-01', '18-24', '25-26')
print('rows', len(J), 'days', J.tday.nunique(), 'shock days', J[J.shock == 1].tday.nunique())
for lab, d in (('all', J), ('RTH', J[J.rth == 1]), ('shock', J[J.shock == 1]), ('normal', J[J.shock == 0])):
    cc = {k: round(d.rc.corr(d.groupby(['sym', 'tday']).ri.shift(-k) if k else d.ri), 3) for k in (-2, -1, 0, 1, 2, 3, 5)}
    print(lab, 'corr(CL_t, index_t+k)', cc)
rows = []
rows.append(dict(test='index next 1–5 min ~ CL minute', **check(J.dropna(subset=['ri_f1_5']), 'ri_f1_5 ~ rc', 'rc')))
rows.append(dict(test='index next 1 min ~ CL minute', **check(J.dropna(subset=['ri_f1']), 'ri_f1 ~ rc', 'rc')))
rows.append(dict(test='CL next 1 min ~ index minute', **check(J.dropna(subset=['rc_f1']), 'rc_f1 ~ ri', 'ri')))
big = J[J.rc.abs() > 4 * J.rc.std()]
print('big CL minutes', len(big))
rows.append(dict(test='index next 1–5 min ~ CL minute | |CL| > 4σ', **check(big.dropna(subset=['ri_f1_5']), 'ri_f1_5 ~ rc', 'rc')))
print(table(rows).round(4).to_string())
J.to_pickle('/home/claude/xa/J_cl1m.pkl')
