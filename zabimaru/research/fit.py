import sys, numpy as np, pandas as pd, statsmodels.formula.api as smf, warnings, json
warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude/gh2/stats-kit'); from stats_kit import check, table
D = pd.read_pickle('or2.pkl'); D = D[D.atr10.notna() & D.atr5.notna()].copy()
D['lor'] = np.log(D.or_atr); D['date'] = D.tday
X = D.set_index('date')
# (a) first break up, at 10:00
A = X[X.bs != 0].assign(up1=lambda d: (d.bs == 1).astype(float), l=lambda d: d.loc959.clip(0, 1))
# (b) each side taken by 16:14, from 10:00: distance from the 10:00 close to that side, in OR units
S = pd.concat([X.assign(y=X.took_h.astype(float), d=1 - X.loc959.clip(0, 1)), X.assign(y=X.took_l.astype(float), d=X.loc959.clip(0, 1))])
# (c) after the first break
B = X[X.bs != 0].copy(); B['ltb'] = np.log(B.tbrk - 29); B['x1'] = B.x1.astype(float); B['fail'] = B.fail.astype(float)
rows = [check(S, 'y ~ d + lor + volr', 'd', test='side taken | distance at 10:00'),
        check(S, 'y ~ d + lor + volr', 'lor', test='side taken | OR/ATR'),
        check(S, 'y ~ d + lor + volr', 'volr', test='side taken | ATR5/ATR10'),
        check(B, 'x1 ~ lor + volr + ltb', 'ltb', test='1x ext | later break'),
        check(B, 'fail ~ lor + volr + ltb', 'ltb', test='other side | later break'),
        check(B, 'x1 ~ lor + volr + ltb', 'volr', test='1x ext | ATR5/ATR10'),
        check(B, 'fail ~ lor + volr + ltb', 'volr', test='other side | ATR5/ATR10')]
T = table(rows); print(T[['coef', 'p', 'n', '18-24', 'p_18-24', '25-26', 'p_25-26', 'ES', 'NQ', 'RTY', 'ok']].to_string())
tr, te = lambda d: d[d.half == '18-24'], lambda d: d[d.half == '25-26']
def oos(f, d, y):
    m = smf.logit(f, tr(d)).fit(disp=0); p = m.predict(te(d)); return np.mean((p - te(d)[y]) ** 2)
print('OOS Brier first-up: base', round(oos('up1 ~ 1', A, 'up1'), 4), 'loc', round(oos('up1 ~ l', A, 'up1'), 4))
print('OOS Brier side: base', round(oos('y ~ 1', S, 'y'), 4), 'd', round(oos('y ~ d', S, 'y'), 4), 'full', round(oos('y ~ d + lor + volr', S, 'y'), 4))
print('OOS Brier 1x: base', round(oos('x1 ~ 1', B, 'x1'), 4), 'full', round(oos('x1 ~ lor + volr + ltb', B, 'x1'), 4))
print('OOS Brier fail: base', round(oos('fail ~ 1', B, 'fail'), 4), 'full', round(oos('fail ~ lor + volr + ltb', B, 'fail'), 4))
M = dict(first=smf.logit('up1 ~ l', A).fit(disp=0).params.to_dict(),
         side=smf.logit('y ~ d + lor + volr', S).fit(disp=0).params.to_dict(),
         ext=smf.logit('x1 ~ lor + volr + ltb', B).fit(disp=0).params.to_dict(),
         fail=smf.logit('fail ~ lor + volr + ltb', B).fit(disp=0).params.to_dict())
# OR/ATR percentiles (deciles) per symbol and pooled
M['dec'] = {s: [float(v) for v in np.quantile(D[D.sym == s].or_atr, np.arange(0.05, 1.0, 0.05))] for s in ('NQ', 'ES', 'RTY')}
M['dec']['ALL'] = [float(v) for v in np.quantile(D.or_atr, np.arange(0.05, 1.0, 0.05))]
M['volr_q'] = [float(v) for v in D.volr.quantile([0.1, 0.25, 0.5, 0.75, 0.9])]
json.dump(M, open('coef.json', 'w'), indent=1)
for k in ('first', 'side', 'ext', 'fail'):
    print(k, {a: round(b, 3) for a, b in M[k].items()})
print('volr quantiles', np.round(M['volr_q'], 3), 'share ascending', (D.volr > 0).mean().round(3))
