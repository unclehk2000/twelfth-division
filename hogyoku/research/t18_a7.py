"""Reach odds for the forming candle (C3), per market and timeframe (individual sensitivity): does C3 trade above C2's high,
below C2's low, above C1's high, below C1's low? Model at C3's open: p = logistic(a + b·logit(2Φ(−d/κ))), d = the distance from
C2's close to the level in ATR (0 or less = already through → excluded), κ = 1, a and b fit per market on 2018–24. Scored on 2025–26."""
import numpy as np, pandas as pd, sys
from scipy.stats import norm
from scipy.optimize import minimize
sys.path.insert(0, '/home/claude/lr'); from lib import D2025
sys.path.insert(0, '/home/claude/pdm'); from t18_a3 import ll, boot
SY = ['NQ', 'ES', 'YM', 'RTY']
def lg(p): p = np.clip(p, 1e-6, 1 - 1e-6); return np.log(p / (1 - p))
def fitk(d, y):
    from sklearn.linear_model import LogisticRegression
    z = lg(2 * norm.cdf(-d)).reshape(-1, 1); m = LogisticRegression(C=1e4).fit(z, y); return 1.0, m.intercept_[0], m.coef_[0][0]
P = {}
for tf in ['15', '60', '240', 'D']:
    W = pd.read_pickle(f'/home/claude/pdm/mat_{tf}.pkl')
    print(f'\n===== {tf} =====')
    for s in SY:
        A = W[s]; F = A.td < D2025
        for lvl, dist, y in [('C2 high', (A.H - A.C) / A.atr, A.t3h), ('C2 low', (A.C - A.L) / A.atr, A.t3l),
                             ('C1 high', (A.H1 if 'H1' in A else A.H) * 0, None)]:
            pass
        # C1 levels: need C1 high / low: recover from sweeps (cl gives C2 close location in C1's range; use dh / dl: H − H1 = dh·atr)
        H1 = A.H - A.dh * A.atr; L1 = A.L + A.dl * A.atr
        for lvl, d, y in [('C2H', (A.H - A.C) / A.atr, A.t3h), ('C2L', (A.C - A.L) / A.atr, A.t3l), ('C1H', (H1 - A.C) / A.atr, A.t3h1), ('C1L', (A.C - L1) / A.atr, A.t3l1)]:
            ok = (d > 0) & d.notna()
            df, yf = d[ok & F].values, y[ok & F].values; ds, ys = d[ok & ~F].values, y[ok & ~F].values
            k, a, b = fitk(df, yf); p = 1 / (1 + np.exp(-(a + b * lg(2 * norm.cdf(-ds / k)))))
            base = yf.mean(); g, ci = boot(ll(ys, np.full(len(ys), base)) - ll(ys, p), A.td.values[(ok & ~F).values])
            bins = pd.cut(p, [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1]); cal = pd.DataFrame({'p': p, 'y': ys, 'b': bins}).groupby('b', observed=True).agg(p=('p', 'mean'), y=('y', 'mean'), n=('y', 'size'))
            P[(tf, s, lvl)] = (k, a, b)
            print(f'  {s:3s} {lvl}: κ {k:.3f} a {a:+.3f} b {b:.3f} | base {100*base:.1f}% | OOS gain {1000*g:+.0f} mnat | cal ' + ' '.join(f'{100*r.p:.0f}→{100*r.y:.0f}' for r in cal.itertuples() if r.n >= 50))
pd.to_pickle(P, '/home/claude/pdm/reach.pkl')
