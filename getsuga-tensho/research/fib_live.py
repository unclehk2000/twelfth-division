import sys, json, numpy as np, pandas as pd, statsmodels.formula.api as smf, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude/gh2/stats-kit'); from stats_kit import check, table
K = pd.read_pickle('fck.pkl'); K['date'] = K.wk; K = K.set_index('date')
K['dc'] = K.d.clip(0, 3); K['lar'] = np.log(K.aR.clip(0.01))
cols = ['coef', 'p', 'n', '18-24', 'p_18-24', '25-26', 'p_25-26', 'ES', 'NQ', 'RTY', 'ok']
print(K.groupby(['lvl', 'ck']).y.mean().unstack().round(3).to_string())
F = K[K.lvl.isin(['-0.5', '0.0', '0.5', '1.0', '1.5'])].copy()
rows = [check(F, 'y ~ dc + C(ck) + C(lvl)', 'dc', test='fib level reached | distance (AWR4)')]
for lv in ('-0.5', '0.5', '1.0', '1.5'):
    rows.append(check(F, 'y ~ dc + C(ck) + C(lvl, Treatment("0.0"))', f'C(lvl, Treatment("0.0"))[T.{lv}]', test=f'level {lv} vs level 0'))
rows.append(check(F, 'y ~ dc + C(ck) + C(lvl) + lar', 'lar', test='fib size (log |R|/AWR4) given distance'))
# PW levels on the non-roll weeks: same distance model
P = K[K.lvl.isin(['PWH', 'PWL'])].copy()
rows.append(check(P, 'y ~ dc + C(ck)', 'dc', test='PWH/PWL reached | distance'))
A = K.assign(isPW=K.lvl.isin(['PWH', 'PWL']).astype(float))
A = A[A.lvl.isin(['PWH', 'PWL', '1.0', '1.5', '-0.5', '0.5'])]
rows.append(check(A, 'y ~ dc + C(ck) + isPW', 'isPW', test='PW level vs fib level, same distance'))
print(table(rows)[cols].to_string())
tr, te = F[F.half == '18-24'], F[F.half == '25-26']
for f in ('y ~ C(ck)', 'y ~ C(ck) + C(lvl)', 'y ~ dc + C(ck)', 'y ~ dc + C(ck) + C(lvl)', 'y ~ dc + C(ck) + C(lvl) + lar'):
    m = smf.logit(f, tr).fit(disp=0); p = m.predict(te); print(f'{f:36s} OOS Brier {np.mean((p - te.y) ** 2):.4f}')
m = smf.logit('y ~ dc + C(ck) + C(lvl)', F).fit(disp=0); print({k: round(v, 3) for k, v in m.params.items()})
mm = smf.logit('y ~ dc + C(ck) + C(lvl)', tr).fit(disp=0); te = te.copy(); te['p'] = mm.predict(te)
te['dec'] = pd.qcut(te.p.rank(method='first'), 8, labels=False); print(te.groupby('dec').agg(pred=('p', 'mean'), obs=('y', 'mean')).round(3).T.to_string())
json.dump({k: float(v) for k, v in m.params.items()}, open('fib_coef.json', 'w'), indent=1)
# PW model refit without roll weeks (for the PWH / PWL rows)
trp, tep = P[P.half == '18-24'], P[P.half == '25-26']
for f in ('y ~ C(ck)', 'y ~ dc + C(ck)'):
    m2 = smf.logit(f, trp).fit(disp=0); p = m2.predict(tep); print('PW', f'{f:20s} OOS Brier {np.mean((p - tep.y) ** 2):.4f}')
m2 = smf.logit('y ~ dc + C(ck)', P).fit(disp=0); print('PW', {k: round(v, 3) for k, v in m2.params.items()})
json.dump({k: float(v) for k, v in m2.params.items()}, open('pw_coef.json', 'w'), indent=1)
