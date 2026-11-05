import numpy as np, pandas as pd, sys, time, pickle
from scipy.stats import norm
from scipy.optimize import minimize
from sklearn.ensemble import GradientBoostingClassifier
sys.path.insert(0, '/home/claude/lr'); from lib import D2025
def lg(p): p = np.clip(p, 1e-6, 1 - 1e-6); return np.log(p / (1 - p))
def bm(z, k): return np.clip(2 * norm.cdf(k * z) - 1, 1e-6, 1 - 1e-6)
def score(p, y, lab):
    p = np.clip(p, 1e-6, 1 - 1e-6); br = np.mean((p - y) ** 2); ll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
    cal = pd.DataFrame({'p': p, 'y': y}).groupby(pd.cut(p, np.linspace(0, 1, 11)), observed=True).mean()
    print(f'  {lab:26s} Brier {br:.4f}  logloss {ll:.4f} | ' + ' '.join(f'{100*a:.0f}→{100*b:.0f}' for a, b in zip(cal.p, cal.y)))
    return p
out = {}
for nm, f, FE, NT in [('day', 't13_day.pkl', ['lz', 'side', 'r', 'ru', 'age', 'pos', 'xRef', 'opn', 'tEx', 'evA', 'dow'], 50),
                      ('week', 't13_wk.pkl', ['lz', 'side', 'r', 'barsLeft', 'ru', 'age', 'pos', 'xRef', 'opn', 'tEx', 'evA'], 50)]:
    D = pd.read_pickle('/home/claude/sk/' + f); D = D[np.isfinite(D.z) & np.isfinite(D.xRef)].copy()
    D['era'] = np.where(D.td >= D2025, 'score', 'fish')
    F = D[D.era == 'fish']
    best = None
    for k in np.arange(0.5, 3.01, 0.05):
        x = lg(bm(F.z.values, k)); X = np.c_[np.ones(len(x)), x]
        r = minimize(lambda p: np.mean(np.logaddexp(0, X @ p) - F.y.values * (X @ p)), np.zeros(2), method='BFGS')
        if best is None or r.fun < best[0]: best = (r.fun, k, r.x)
    k0, (a0, b0) = best[1], best[2]; D['lz'] = lg(bm(D.z.values, k0))
    F = D[D.era == 'fish']; S = D[D.era == 'score']; y = S.y.values
    print(f'== {nm}: fish {len(F)}, score {len(S)}, hold rate {F.y.mean():.3f}; Brownian k={k0:.2f}, a={a0:.3f}, b={b0:.3f}')
    score(np.full(len(y), F.y.mean()), y, 'flat rate')
    p0 = score(1 / (1 + np.exp(-(a0 + b0 * S.lz.values))), y, 'Brownian')
    rng = np.random.default_rng(1); idx = rng.choice(len(F), size=min(400000, len(F)), replace=False)
    gb = GradientBoostingClassifier(n_estimators=NT, max_depth=3, learning_rate=0.2, subsample=0.7, min_samples_leaf=400, random_state=1).fit(F[FE].values[idx], F.y.values[idx])
    p2 = score(gb.predict_proba(S[FE].values)[:, 1], y, f'GBM {NT}×3')
    print('  importance', pd.Series(gb.feature_importances_, index=FE).sort_values(ascending=False).round(3).to_dict())
    ll = lambda p: -(y * np.log(p) + (1 - y) * np.log(1 - p))
    g = ll(p0) - ll(p2); ud, inv = np.unique(S.td.values, return_inverse=True); sums = np.bincount(inv, weights=g); cnt = np.bincount(inv)
    bs = [sums[ix].sum() / cnt[ix].sum() for ix in [rng.integers(0, len(ud), len(ud)) for _ in range(300)]]
    print(f'  logloss gain GBM over Brownian, 2025–26: {g.mean():.4f} (95% CI {np.percentile(bs, 2.5):.4f} – {np.percentile(bs, 97.5):.4f})')
    for s_ in ['NQ', 'ES', 'RTY']:
        mk = S.sym.values == s_; print(f'  {s_} Brier Brownian {np.mean((p0[mk]-y[mk])**2):.4f}  GBM {np.mean((p2[mk]-y[mk])**2):.4f}')
    out[nm] = dict(k0=k0, a0=a0, b0=b0, gb=gb, FE=FE)
pickle.dump(out, open('/home/claude/sk/t13_models.pkl', 'wb'))
