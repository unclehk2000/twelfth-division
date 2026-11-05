"""Countermeasure model: one small logistic model per market and timeframe (individual sensitivity) on the readings that passed,
for 'C3 closes up'. Fit 2018–24, scored 2025–26: log-loss gain over the market's base rate (day-clustered bootstrap), and the
spread of predictions (top / bottom fifth realised). Also: which readings carry weight, per market."""
import numpy as np, pandas as pd, sys
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, '/home/claude/lr'); from lib import cse, D2025
sys.path.insert(0, '/home/claude/pdm'); from t18_a3 import ll, boot
SY = ['NQ', 'ES', 'YM', 'RTY']
FE = ['expUp', 'expDn', 'bullC2', 'bearC2', 'pspG', 'pspR', 'heldHi', 'heldLo', 'spread', 'all4bull', 'bullSMT', 'bearSMT']
def feats(L):
    X = pd.DataFrame(index=L.index)
    X['expUp'] = (L.form == 'expUp').astype(int); X['expDn'] = (L.form == 'expDn').astype(int)
    X['bullC2'] = (L.form == 'bullC2').astype(int); X['bearC2'] = (L.form == 'bearC2').astype(int)
    X['pspG'] = ((L.psp == 1) & (L.body > 0)).astype(int); X['pspR'] = ((L.psp == 1) & (L.body < 0)).astype(int)
    X['heldHi'] = ((L.shi == 0) & (L.nPhi >= 1)).astype(int); X['heldLo'] = ((L.slo == 0) & (L.nPlo >= 1)).astype(int)
    X['spread'] = L.spread.clip(-3, 3).fillna(0); X['all4bull'] = ((L.form == 'bullC2') & (L.nPbull == 3)).astype(int)
    X['bullSMT'] = ((L.form == 'bullC2') & (L.nPlo < 3)).astype(int); X['bearSMT'] = ((L.form == 'bearC2') & (L.nPhi < 3)).astype(int)
    return X
M = {}
for tf in ['15', '60', '240']:
    L = pd.read_pickle(f'/home/claude/pdm/long_{tf}.pkl').reset_index(drop=True); X = feats(L)
    print(f'\n===== {tf} =====')
    allp = []
    for s in SY:
        k = (L.sym == s).values; F = k & (L.td < D2025).values; S = k & (L.td >= D2025).values
        y = (L.r3 > 0).astype(int).values
        lr = LogisticRegression(C=1.0).fit(X[F], y[F]); p = lr.predict_proba(X[S])[:, 1]; base = y[F].mean()
        g, ci = boot(ll(y[S], np.full(S.sum(), base)) - ll(y[S], p), L.td.values[S])
        q = np.quantile(p, [0.2, 0.8]); top = y[S][p >= q[1]].mean(); bot = y[S][p <= q[0]].mean()
        M[(tf, s)] = dict(b0=lr.intercept_[0], coef=dict(zip(FE, lr.coef_[0])), base=base)
        print(f'  {s:3s} OOS gain {1000*g:+.2f} mnat [{1000*ci[0]:+.2f}, {1000*ci[1]:+.2f}] | 2025–26 up-rate: top fifth {100*top:.1f}%, bottom fifth {100*bot:.1f}%, all {100*y[S].mean():.1f}% | '
              + ' '.join(f'{f}{c:+.2f}' for f, c in zip(FE, lr.coef_[0])))
        allp.append(pd.DataFrame({'td': L.td.values[S], 'y': y[S], 'p': p, 'base': base}))
    A = pd.concat(allp); g, ci = boot(ll(A.y.values, A.base.values) - ll(A.y.values, A.p.values), A.td.values)
    A['bin'] = pd.cut(A.p, [0, 0.46, 0.48, 0.50, 0.52, 0.54, 0.56, 1])
    print(f'  pooled OOS gain {1000*g:+.2f} mnat [{1000*ci[0]:+.2f}, {1000*ci[1]:+.2f}] | calibration (2025–26):', ' '.join(f'{100*b.p.mean():.1f}→{100*b.y.mean():.1f}({len(b)})' for _, b in A.groupby('bin', observed=True)))
pd.to_pickle(M, '/home/claude/pdm/logit_models.pkl')
