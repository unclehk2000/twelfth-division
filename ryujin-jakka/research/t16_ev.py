"""Event-day effects on session ranges beyond the rest of the model: fit the model without the event flags on 2018–24, then the mean
residual on event days, clustered by date, by era and by symbol."""
import numpy as np, pandas as pd, sys
from sklearn.linear_model import LinearRegression
sys.path.insert(0, '/home/claude/lr'); from lib import D2025
X = pd.read_pickle('t16_rows.pkl'); X['prev'] = X.prev.fillna(X.l1)
X = X.replace([np.inf, -np.inf], np.nan).dropna(subset=['y', 'l1', 'l5', 'l20', 'soRg', 'soMv', 'prev', 'atrRel', 'vrel'])
F0 = ['l1', 'l5', 'l20', 'soRg', 'soMv', 'prev', 'atrRel', 'vrel', 'dow']
def cl(v, g):
    d = pd.DataFrame({'v': v, 'g': g}).groupby('g').v.agg(['sum', 'count']); m = d['sum'].sum() / d['count'].sum()
    r = d['sum'] - m * d['count']; se = np.sqrt((r ** 2).sum()) / d['count'].sum(); return m, se
out = []
for s in ['Asia', 'London', 'NYAM', 'NYPM']:
    A = X[X.sess == s].copy(); fish = A.td < D2025; ev = A.cpi + A.nfp + A.fomc == 0
    lr = LinearRegression().fit(A.loc[fish & ev, F0].values, A.loc[fish & ev, 'y'].values); A['e'] = A.y - lr.predict(A[F0].values)
    for nm in ['cpi', 'nfp', 'fomc']:
        B = A[A[nm] == 1]; m, se = cl(B.e.values, B.td.values)
        er = ''.join('+' if B[B.td < D2025].e.mean() > 0 else '−' for _ in [0]) + ''.join('+' if B[B.td >= D2025].e.mean() > 0 else '−' for _ in [0])
        sy = ''.join('+' if B[B.sym == k].e.mean() > 0 else '−' for k in ['NQ', 'ES', 'RTY'])
        ok = abs(m / se) > 1.96 and len(set(er + sy)) == 1
        print(f'{s:6s} {nm:4s} n {B.td.nunique():3d} days | {100*(np.exp(m)-1):+5.1f}% range (log {m:+.3f} ± {se:.3f}, t {m/se:+.1f}) | eras {er} syms {sy} | {"PASS" if ok else "—"} | 2025–26 {100*(np.exp(B[B.td >= D2025].e.mean())-1):+.1f}% n {B[B.td >= D2025].td.nunique()}')
