import numpy as np, pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm
R = pd.read_pickle('reach_rows.pkl')
def nll(p, X, y):
    z = X @ p; return np.sum(np.logaddexp(0, z) - y * z)
def logit(q): q = np.clip(q, 1e-5, 1 - 1e-5); return np.log(q / (1 - q))
def rx(d, h, k): return logit(2 * norm.cdf(-d / (k * np.sqrt(h))))
H = (1, 2, 3, 4, 5, 10, 20)
def fit(tr):
    best = None
    for k in np.arange(0.4, 1.61, 0.1):
        X = np.vstack([np.c_[np.ones(len(tr)), rx(tr.d.values, h, k)] for h in H]); y = np.concatenate([(tr['first'] <= h).values for h in H]).astype(float)
        r = minimize(nll, np.zeros(2), args=(X, y), method='BFGS')
        if best is None or r.fun < best[0]: best = (r.fun, k, r.x)
    return best[1], best[2]
for side, nm in ((-1, 'above'), (1, 'below')):
    g = R[R.side == side]; out = []
    for yr in range(2014, 2027):
        k, (a, b) = fit(g[g.yr < yr]); te = g[g.yr == yr]
        for h in (5, 20):
            p = 1 / (1 + np.exp(-(a + b * rx(te.d.values, h, k))))
            out.append(pd.DataFrame({'yr': yr, 'h': h, 'p': p, 'y': (te['first'] <= h).values, 'sym': te.sym.values}))
    O = pd.concat(out)
    for h in (5, 20):
        o = O[O.h == h]
        cal = o.groupby(pd.cut(o.p, [0, .1, .3, .5, .7, .9, 1]), observed=True).agg(p=('p', 'mean'), y=('y', 'mean'), n=('y', 'size'))
        yr = o.groupby('yr').apply(lambda x: x.y.mean() / x.p.mean())
        sy = o.groupby('sym').apply(lambda x: x.y.mean() / x.p.mean())
        print(f"{nm} h={h} walk-forward 2014–26: " + ', '.join(f"{r.p*100:.0f}→{r.y*100:.0f}%" for r in cal.itertuples()) +
              f" | years actual/pred {yr.min():.2f}–{yr.max():.2f} (2025 {yr.get(2025, np.nan):.2f}, 2026 {yr.get(2026, np.nan):.2f}) | by sym " + ' '.join(f"{k} {v:.2f}" for k, v in sy.items()))
