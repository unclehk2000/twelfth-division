"""The catch-up regression: own C2 return minus the other three markets' mean C2 return (ATR units) → C3 up? Per market and
timeframe (individual sensitivity): logistic fit on 2018–24, log-loss gain over the market's base rate on 2025–26 (day-clustered
bootstrap), and the laggard / leader fifths against the base rate with the suite's rule."""
import numpy as np, pandas as pd, sys
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, '/home/claude/lr'); from lib import cse, D2025
sys.path.insert(0, '/home/claude/pdm'); from t18_a3 import ll, boot
SY = ['NQ', 'ES', 'YM', 'RTY']
out = {}
for tf in ['15', '60', '240']:
    L = pd.read_pickle(f'/home/claude/pdm/ml_{tf}.pkl'); L['spread'] = L.spread.clip(-4, 4)
    print(f'\n===== {tf} =====')
    for k, s in enumerate(SY):
        A = L[L.sym == k].dropna(subset=['spread']); F = A[A.td < D2025]; S = A[A.td >= D2025]
        lr = LogisticRegression(C=1e3).fit(F[['spread']], F.up); p = lr.predict_proba(S[['spread']])[:, 1]
        base = F.up.mean(); g, ci = boot(ll(S.up.values, np.full(len(S), base)) - ll(S.up.values, p), S.td.values)
        q = F.spread.quantile([0.2, 0.8]).values; sd = F.spread.std()
        row = []
        for era, E in [('18–24', F), ('25–26', S)]:
            b0 = E.up.mean()
            lo = E[E.spread <= q[0]]; hi = E[E.spread >= q[1]]
            m1, s1, n1 = cse(lo.up.values - b0, lo.td.values); m2, s2, n2 = cse(hi.up.values - b0, hi.td.values)
            row.append((m1, s1, m2, s2, b0))
        ok = all(r[0] > 0 and r[2] < 0 for r in row) and row[0][0] / row[0][1] > 2 and row[1][0] / row[1][1] > 1.0
        out[(tf, s)] = dict(a=lr.intercept_[0], b=lr.coef_[0][0], q20=q[0], q80=q[1], sd=sd, base=base, gain=g, ci=ci, row=row)
        print(f'  {s:3s} logit b {lr.coef_[0][0]:+.3f} per ATR (sd of spread {sd:.2f}) | OOS gain {1000*g:+.2f} mnat [{1000*ci[0]:+.2f}, {1000*ci[1]:+.2f}] | '
              + ' | '.join(f'{era}: laggard fifth {100*r[0]:+.1f}±{100*r[1]:.1f}, leader fifth {100*r[2]:+.1f}±{100*r[3]:.1f} (base {100*r[4]:.1f}%)' for era, r in zip(['18–24', '25–26'], row)))
pd.to_pickle(out, '/home/claude/pdm/catchup.pkl')
