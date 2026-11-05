import numpy as np, pandas as pd, sys, pickle
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import GradientBoostingRegressor
sys.path.insert(0, '/home/claude/lr'); from lib import D2025
X = pd.read_pickle('/home/claude/rj/t16_rows.pkl')
X['prev'] = X.prev.fillna(X.l1)
X = X.replace([np.inf, -np.inf], np.nan).dropna(subset=['y', 'l1', 'l5', 'l20', 'soRg', 'soMv', 'prev', 'atrRel', 'vrel'])
X['era'] = np.where(X.td >= D2025, 'score', 'fish')
X['evS'] = np.where(X.sess == 'NYPM', X.fomc, np.where(X.sess == 'NYAM', X.cpi | X.nfp, 0))
FE = ['k', 'l1', 'l5', 'l20', 'soRg', 'soMv', 'prev', 'atrRel', 'vrel', 'dow', 'cpi', 'nfp', 'fomc', 'evS']
F = X[X.era == 'fish']; S = X[X.era == 'score']
def r2(y, p, ref): return 1 - np.sum((y - p) ** 2) / np.sum((y - ref) ** 2)
res = {}
print('session  n_score | R² (score era, vs the fish mean of that session): naive l20 · OLS · GBM | MAE OLS · GBM')
ols = {}; 
for s in ['Asia', 'London', 'NYAM', 'NYPM']:
    f = F[F.sess == s]; t = S[S.sess == s]; ref = f.y.mean()
    lr = LinearRegression().fit(f[FE[1:]].values, f.y.values); ols[s] = lr
    res[s] = (r2(t.y, t.l20, ref), r2(t.y, lr.predict(t[FE[1:]].values), ref))
gb = GradientBoostingRegressor(n_estimators=80, max_depth=3, learning_rate=0.1, subsample=0.7, min_samples_leaf=100, random_state=1).fit(F[FE].values, F.y.values)
pg = gb.predict(S[FE].values); S = S.assign(pg=pg)
po = np.zeros(len(S))
for s in ols: mk = (S.sess == s).values; po[mk] = ols[s].predict(S.loc[mk, FE[1:]].values)
S = S.assign(po=po)
for s in ['Asia', 'London', 'NYAM', 'NYPM']:
    t = S[S.sess == s]; ref = F[F.sess == s].y.mean()
    print(f'{s:7s} {len(t):5d} | {res[s][0]:.3f} · {res[s][1]:.3f} · {r2(t.y, t.pg, ref):.3f} | {np.mean(np.abs(t.y - t.po)):.3f} · {np.mean(np.abs(t.y - t.pg)):.3f}')
print('GBM importance', pd.Series(gb.feature_importances_, index=FE).sort_values(ascending=False).round(3).to_dict())
# OLS coefficients (standardised meaning) per session
for s in ols: print(s, 'OLS', dict(zip(FE[1:], np.round(ols[s].coef_, 3))), 'b0', round(ols[s].intercept_, 3))
# quantile bands from fish residuals (per session, GBM), coverage on score
pf = gb.predict(F[FE].values); F = F.assign(pg=pf)
Q = {}
for s in ['Asia', 'London', 'NYAM', 'NYPM']:
    e = (F[F.sess == s].y - F[F.sess == s].pg).values; q = np.quantile(e, [0.1, 0.25, 0.5, 0.75, 0.9]); Q[s] = q
    t = S[S.sess == s]; et = (t.y - t.pg).values
    print(f'{s:7s} residual q10..q90 {np.round(q, 3)} | score coverage p25–p75 {100*np.mean((et >= q[1]) & (et <= q[3])):.1f}% (50) · p10–p90 {100*np.mean((et >= q[0]) & (et <= q[4])):.1f}% (80) · below p50 {100*np.mean(et <= q[2]):.1f}% (50)')
for sy in ['NQ', 'ES', 'RTY']:
    t = S[S.sym == sy]; print(sy, 'R² GBM', round(r2(t.y, t.pg, F.y.mean()), 3), 'R² OLS', round(r2(t.y, t.po, F.y.mean()), 3), '(pooled ref)')
pickle.dump(dict(gb=gb, FE=FE, Q=Q, ols=ols), open('/home/claude/rj/t16_models.pkl', 'wb'))
print('\nOLS residual bands (fit 2018–24) and their coverage on 2025–26:')
QO = {}
for s in ['Asia', 'London', 'NYAM', 'NYPM']:
    f = F[F.sess == s]; e = f.y.values - ols[s].predict(f[FE[1:]].values); q = np.quantile(e, [0.1, 0.25, 0.5, 0.75, 0.9]); QO[s] = q
    t = S[S.sess == s]; et = t.y.values - t.po.values
    print(f'{s:7s} q {np.round(q, 3)} | p25–p75 {100*np.mean((et >= q[1]) & (et <= q[3])):.1f}% · p10–p90 {100*np.mean((et >= q[0]) & (et <= q[4])):.1f}% · ≤p50 {100*np.mean(et <= q[2]):.1f}% · ≥p90 {100*np.mean(et >= q[4]):.1f}%')
    # by year in the score era
    for yr, tt in t.groupby(pd.to_datetime(t.td, unit='D').dt.year):
        e2 = tt.y.values - tt.po.values; print(f'      {yr}: p25–p75 {100*np.mean((e2 >= q[1]) & (e2 <= q[3])):.1f}%  p10–p90 {100*np.mean((e2 >= q[0]) & (e2 <= q[4])):.1f}%  n {len(tt)}')
pickle.dump(dict(gb=gb, FE=FE, Q=Q, ols=ols, QO=QO), open('/home/claude/rj/t16_models.pkl', 'wb'))
