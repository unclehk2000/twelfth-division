"""Card odds, fit on 2010–24 and checked on 2025–26 (all four symbols pooled).
1. Reach: the nearest live gap above (bearish) / below (bullish), look back 60 trading days, FVG or SB ≥ 0.1 ATR: chance its
   near edge trades within h trading days of the last close, p = logistic(a + b·logit(2Φ(−d/(κ√h)))), d = distance in ATR(14).
2. Touch day: chance the first touch day does not trade through the far edge, p = logistic(a + b·ln w + c·break), w = width in ATR.
3. Ten days on: chance it is not closed beyond within 10 trading days of the first touch (touch day included), same form."""
import numpy as np, pandas as pd, json
from scipy.optimize import minimize
from scipy.stats import norm
from data import daily, SYMS
Z = pd.read_pickle('zones.pkl')
def nll(p, X, y):
    z = X @ p; return np.sum(np.logaddexp(0, z) - y * z) + 1e-6 * np.sum(p ** 2)
def logit(q): q = np.clip(q, 1e-5, 1 - 1e-5); return np.log(q / (1 - q))
def reachX(d, h, k): return logit(2 * norm.cdf(-d / (k * np.sqrt(h))))
# 1. reach rows
rows = []
for s in SYMS:
    D = daily(s); H, L, C, A = D.bh.values, D.bl.values, D.bc.values, D.atrB.values; n = len(C)
    z = Z[(Z.sym == s) & Z.kind.isin(['FVG', 'SB']) & (Z.w >= 0.1)]
    t0 = z.t0.values; tX = z.tX.values; dr = z.dir.values; top = z.top.values; bot = z.bot.values
    for t in range(80, n - 21):
        live = (t0 <= t) & (t - t0 <= 60) & ((tX < 0) | (tX > t))
        for side in (-1, 1):
            m = live & (dr == side)
            if side == -1: m &= bot > C[t]; dist = (bot - C[t]) / A[t]
            else: m &= top < C[t]; dist = (C[t] - top) / A[t]
            if not m.any(): continue
            j = np.where(m)[0][dist[m].argmin()]; d = dist[j]; e = bot[j] if side == -1 else top[j]
            ff = H[t + 1:t + 21] if side == -1 else L[t + 1:t + 21]
            hit = (ff >= e) if side == -1 else (ff <= e)
            first = np.argmax(hit) + 1 if hit.any() else 99
            rows.append((s, D.index[t].year, side, d, first, D.dow.values[t]))
R = pd.DataFrame(rows, columns=['sym', 'yr', 'side', 'd', 'first', 'dow'])
R.to_pickle('reach_rows.pkl')
par = {}
for side, nm in ((-1, 'above'), (1, 'below')):
    g = R[R.side == side]; tr = g[g.yr <= 2024]; te = g[g.yr >= 2025]
    best = None
    for k in np.arange(0.3, 2.01, 0.05):
        Xs = []; ys = []
        for h in (1, 2, 3, 4, 5, 10, 20):
            Xs.append(np.c_[np.ones(len(tr)), reachX(tr.d.values, h, k)]); ys.append((tr['first'] <= h).values.astype(float))
        X = np.vstack(Xs); y = np.concatenate(ys)
        r = minimize(nll, np.zeros(2), args=(X, y), method='BFGS')
        if best is None or r.fun < best[0]: best = (r.fun, k, r.x)
    _, k, (a, b) = best; par[nm] = dict(k=round(float(k), 4), a=round(float(a), 4), b=round(float(b), 4))
    print(f"reach {nm}: κ {k:.2f} a {a:.4f} b {b:.4f}  rows {len(g)}")
    for h in (1, 3, 5, 20):
        p = 1 / (1 + np.exp(-(a + b * reachX(te.d.values, h, k)))); y = (te['first'] <= h).values
        bins = pd.cut(p, [0, .1, .3, .5, .7, .9, 1])
        cal = pd.DataFrame({'p': p, 'y': y}).groupby(bins, observed=True).agg(p=('p', 'mean'), y=('y', 'mean'), n=('y', 'size'))
        print(f"   h={h:2d} 2025–26: " + ', '.join(f"{r.p*100:.0f}→{r.y*100:.0f}% ({r.n})" for r in cal.itertuples()))
    for d in (0.5, 1, 2, 3):
        print(f"   scale d={d}: " + ' '.join(f"h{h} {100/(1+np.exp(-(a+b*reachX(np.array([d]),h,k)[0]))):.0f}%" for h in (1, 3, 5, 20)))
# 2./3. touch day and 10 days on
F = Z[(Z.tT >= 0)].copy()
F['inside'] = (F.deep <= 1).astype(float)
F['hold10'] = (~((F.tX >= 0) & (F.tX - F.tT <= 10))).astype(float)
F['lw'] = np.log(F.w.clip(0.01))
for kind in ['FVG', 'SB', 'VI']:
    g = F[F.kind == kind]; tr = g[g.yr <= 2024]; te = g[g.yr >= 2025]
    for v, cols in (('inside', ['lw', 'brk']), ('hold10', ['lw'])):
        X = np.c_[np.ones(len(tr)), tr[cols].values.astype(float)]
        r = minimize(nll, np.zeros(X.shape[1]), args=(X, tr[v].values), method='BFGS')
        Xt = np.c_[np.ones(len(te)), te[cols].values.astype(float)]
        p = 1 / (1 + np.exp(-(Xt @ r.x)))
        bins = pd.qcut(p, 4, duplicates='drop')
        cal = pd.DataFrame({'p': p, 'y': te[v].values}).groupby(bins, observed=True).agg(p=('p', 'mean'), y=('y', 'mean'), n=('y', 'size'))
        par[f'{kind}_{v}'] = [round(float(x), 4) for x in r.x]
        print(f"{kind} {v} {cols} coef {np.round(r.x,3)}  2025–26: " + ', '.join(f"{q.p*100:.0f}→{q.y*100:.0f}% ({q.n})" for q in cal.itertuples()))
        if kind == 'FVG':
            for w in (0.1, 0.25, 0.5, 1.0):
                xx = [1, np.log(w)] + ([0] if 'brk' in cols else []); xb = [1, np.log(w)] + ([1] if 'brk' in cols else [])
                print(f"     w {w}: {100/(1+np.exp(-np.dot(r.x, xx))):.0f}%" + (f" / with break {100/(1+np.exp(-np.dot(r.x, xb))):.0f}%" if 'brk' in cols else ''))
json.dump(par, open('par.json', 'w'), indent=1)
