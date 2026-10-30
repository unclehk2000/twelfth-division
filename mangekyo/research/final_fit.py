"""Ship the all-years fits (2010–26; YM 2017–26), as Sharingan: the walk-forward 2014–26 read well calibrated."""
import numpy as np, pandas as pd, json
from scipy.optimize import minimize
from scipy.stats import norm
exec(open('wf.py').read().split('for side, nm')[0])
Z = pd.read_pickle('zones.pkl')
par = {}
for side, nm in ((-1, 'above'), (1, 'below')):
    g = R[R.side == side]
    best = None
    for k in np.arange(0.4, 1.61, 0.025):
        X = np.vstack([np.c_[np.ones(len(g)), rx(g.d.values, h, k)] for h in H]); y = np.concatenate([(g['first'] <= h).values for h in H]).astype(float)
        r = minimize(nll, np.zeros(2), args=(X, y), method='BFGS')
        if best is None or r.fun < best[0]: best = (r.fun, k, r.x)
    k, (a, b) = best[1], best[2]; par[nm] = [round(float(k), 4), round(float(a), 4), round(float(b), 4)]
    print(nm, par[nm], 'scale:', ' | '.join(f"d {d}: " + ' '.join(f"h{h} {100/(1+np.exp(-(a+b*rx(np.array([d]),h,k)[0]))):.0f}%" for h in (1, 5, 20)) for d in (0.5, 1, 2)))
F = Z[(Z.tT >= 0)].copy()
F['inside'] = (F.deep <= 1).astype(float); F['hold10'] = (~((F.tX >= 0) & (F.tX - F.tT <= 10))).astype(float); F['lw'] = np.log(F.w.clip(0.01))
def lnll(p, X, y): z = X @ p; return np.sum(np.logaddexp(0, z) - y * z)
for kind in ['FVG', 'SB', 'VI']:
    g = F[F.kind == kind]
    for v, cols in (('inside', ['lw', 'brk']), ('hold10', ['lw'])):
        X = np.c_[np.ones(len(g)), g[cols].values.astype(float)]
        r = minimize(lnll, np.zeros(X.shape[1]), args=(X, g[v].values), method='BFGS')
        par[f'{kind}_{v}'] = [round(float(x), 4) for x in r.x]
        print(kind, v, par[f'{kind}_{v}'], 'n', len(g), 'rate', round(g[v].mean(), 3))
# body position on the touch day → closed beyond within the next 10 trading days (touch day excluded)
F['bp'] = pd.cut(F.bodyPos, [-99, 0, 0.5, 1.0, 99], labels=['out', 'near', 'far', 'beyond'])
F['surv'] = (~((F.tX > F.tT) & (F.tX - F.tT <= 10)) & ~(F.tX == F.tT)).astype(float)
for kind in ['FVG', 'SB', 'VI']:
    g = F[(F.kind == kind) & (F.bp != 'beyond')]
    t = g.groupby('bp', observed=True).surv.agg(['mean', 'size'])
    p1 = g[g.yr <= 2024].groupby('bp', observed=True).surv.mean(); p2 = g[g.yr >= 2025].groupby('bp', observed=True).surv.mean()
    sy = g.groupby(['bp', 'sym'], observed=True).surv.mean().unstack().round(2)
    print(kind, 'survive 10 days after the touch day by its close:', {k: (round(r['mean'], 3), int(r['size'])) for k, r in t.iterrows()}, '2010–24', p1.round(2).to_dict(), '2025–26', p2.round(2).to_dict())
    print(sy.to_string())
    par[f'{kind}_body'] = [round(float(t.loc[k, 'mean']), 3) for k in ['out', 'near', 'far']]
json.dump(par, open('par_full.json', 'w'), indent=1)
