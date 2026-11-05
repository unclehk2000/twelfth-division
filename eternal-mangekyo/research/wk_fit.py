"""Weekly gaps (Mangekyō's sister): the card's odds. (1) Reach: at every weekly close, the nearest live untouched gap above and
below (formed within 52 weeks, default size filters), d = distance in weekly ATR(14), first = weeks to the near edge.
p = logistic(a + b·logit(2Φ(−d/(κ√h)))), walk-forward 2014–26, then fit on all years. (2) Holds from the width: the touch week
does not trade through the far edge; not closed beyond within 4 weeks of the touch. (3) The touch week's close (back outside /
near half / far half) → survives the next 4 weeks."""
import numpy as np, pandas as pd, json, sys
from scipy.optimize import minimize
from scipy.stats import norm
sys.path.insert(0, '/home/claude/mgk')
exec(open('/home/claude/mgk/wk_gaps.py').read().split('R = []; Q = []')[0])
FMIN, DMIN, SMIN, VMIN = 0.10, 0.25, 0.10, 0.05

def flt(z, W):
    O, C, A = W.bo.values, W.bc.values, W.atrB.values
    c2 = np.where(z.kind.values == 'VI', z.t0.values, z.t0.values - 1)
    disp = (C[c2] - O[c2]) * z.dir.values / A[z.t0.values]
    keep = ((z.kind == 'FVG') & (z.w >= FMIN) & (disp >= DMIN)) | ((z.kind == 'SB') & (z.w >= SMIN)) | ((z.kind == 'VI') & (z.w >= VMIN))
    return z[keep.values]

rows = []; Zs = []
for s in SYMS:
    W = weekly(s); O, H, L, C = (W['b' + x].values for x in 'ohlc'); A = W.atrB.values
    z = detect(O, H, L, C, A); z = lifecycle(z, O, H, L, C, A, horizon=150, k_bounce=1.0, race=12); z = feats(W, z); z['sym'] = s
    z = flt(z, W); Zs.append(z)
    yrs = W.index.year.nunique()
    print(s, 'after the default filters, per year:', {k: round((z.kind == k).sum() / yrs, 1) for k in ['FVG', 'SB', 'VI']})
    n = len(C)
    t0 = z.t0.values; tT = z.tT.values; d_ = z.dir.values; near = np.where(d_ == 1, z.top.values, z.bot.values)
    for t in range(30, n - 1):
        live = (t0 < t) & (t - t0 <= 52) & ((tT < 0) | (tT > t))
        if not live.any(): continue
        for side in (1, -1):        # 1: support below price (bull role), −1: resistance above
            m = live & ((near < C[t]) if side == 1 else (near > C[t]))
            if not m.any(): continue
            i = np.where(m)[0][np.argmin(np.abs(near[m] - C[t]))]
            first = (tT[i] - t) if tT[i] > t else 999
            rows.append((s, W.index[t].year, side, abs(near[i] - C[t]) / A[t], first))
R = pd.DataFrame(rows, columns=['sym', 'yr', 'side', 'd', 'first'])
def nll(p, X, y): z = X @ p; return np.sum(np.logaddexp(0, z) - y * z)
def logit(q): q = np.clip(q, 1e-5, 1 - 1e-5); return np.log(q / (1 - q))
def rx(d, h, k): return logit(2 * norm.cdf(-d / (k * np.sqrt(h))))
HH = (1, 2, 3, 4, 8, 12)
def fit(tr):
    best = None
    for k in np.arange(0.3, 4.01, 0.1):
        X = np.vstack([np.c_[np.ones(len(tr)), rx(tr.d.values, h, k)] for h in HH]); y = np.concatenate([(tr['first'] <= h).values for h in HH]).astype(float)
        r = minimize(nll, np.zeros(2), args=(X, y), method='BFGS')
        if best is None or r.fun < best[0]: best = (r.fun, k, r.x)
    return best[1], best[2]
par = {}
for side, nm in ((-1, 'above'), (1, 'below')):
    g = R[R.side == side]; out = []
    for yr in range(2014, 2027):
        k, (a, b) = fit(g[g.yr < yr]); te = g[g.yr == yr]
        for h in (4, 12):
            p = 1 / (1 + np.exp(-(a + b * rx(te.d.values, h, k))))
            out.append(pd.DataFrame({'yr': yr, 'h': h, 'p': p, 'y': (te['first'] <= h).values}))
    O_ = pd.concat(out)
    for h in (4, 12):
        o = O_[O_.h == h]
        cal = o.groupby(pd.cut(o.p, [0, .1, .3, .5, .7, .9, 1]), observed=True).agg(p=('p', 'mean'), y=('y', 'mean'), n=('y', 'size'))
        br = np.mean((o.p - o.y) ** 2); b0 = np.mean((o.y.mean() - o.y) ** 2)
        print(f"{nm} h={h}w walk-forward 2014–26: " + ', '.join(f"{r.p*100:.0f}→{r.y*100:.0f}% (n{r.n})" for r in cal.itertuples()) + f" | Brier {br:.3f} vs base {b0:.3f}")
    k, (a, b) = fit(g); par[nm] = [round(float(k), 4), round(float(a), 4), round(float(b), 4)]
    print(nm, 'all years', par[nm], 'rows', len(g), ' e.g. d=0.5/1/2 ATRw at 4 weeks:', ' '.join(f"{100/(1+np.exp(-(a+b*rx(np.array([d]),4,k)[0]))):.0f}%" for d in (0.5, 1, 2)))
Z = pd.concat(Zs, ignore_index=True)
F = Z[Z.tT >= 0].copy()
F['inside'] = (F.deep <= 1).astype(float); F['hold4'] = (~((F.tX >= 0) & (F.tX - F.tT <= 4))).astype(float); F['lw'] = np.log(F.w.clip(0.01))
def lnll(p, X, y): z = X @ p; return np.sum(np.logaddexp(0, z) - y * z)
for kind in ['FVG', 'SB', 'VI']:
    g = F[F.kind == kind]
    for v in ('inside', 'hold4'):
        X = np.c_[np.ones(len(g)), g.lw.values]
        r = minimize(lnll, np.zeros(2), args=(X, g[v].values), method='BFGS')
        par[f'{kind}_{v}'] = [round(float(x), 4) for x in r.x]
        print(kind, v, par[f'{kind}_{v}'], 'n', len(g), 'rate', round(g[v].mean(), 3), ' at 0.1/0.25/0.5/1 ATRw:', ' '.join(f"{100/(1+np.exp(-(r.x[0]+r.x[1]*np.log(w)))):.0f}%" for w in (0.1, 0.25, 0.5, 1.0)))
F['bp'] = pd.cut(F.bodyPos, [-99, 0, 0.5, 1.0, 99], labels=['out', 'near', 'far', 'beyond'])
F['surv'] = (~((F.tX > F.tT) & (F.tX - F.tT <= 4)) & ~(F.tX == F.tT)).astype(float)
for kind in ['FVG', 'SB', 'VI']:
    g = F[(F.kind == kind) & (F.bp != 'beyond')]
    t = g.groupby('bp', observed=True).surv.agg(['mean', 'size'])
    par[f'{kind}_body'] = [round(float(t.loc[k, 'mean']), 3) if k in t.index else None for k in ['out', 'near', 'far']]
    print(kind, 'survive 4 weeks after the touch week by its close (out/near/far):', par[f'{kind}_body'], t['size'].to_dict())
json.dump(par, open('/home/claude/mgk/wk_par.json', 'w'), indent=1)
