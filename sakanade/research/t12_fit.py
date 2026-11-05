import numpy as np, pandas as pd, sys, time, pickle
from scipy.stats import norm
from scipy.optimize import minimize
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, '/home/claude/lr'); from lib import D2025
D = pd.read_pickle('/home/claude/sk/t12_rows.pkl')
D = D[np.isfinite(D.z) & np.isfinite(D.xPD) & np.isfinite(D.xPW)].copy()
D['era'] = np.where(D.td >= D2025, 'score', 'fish')
def lg(p): p = np.clip(p, 1e-6, 1 - 1e-6); return np.log(p / (1 - p))
def bm(z, k): return np.clip(2 * norm.cdf(k * z) - 1, 1e-6, 1 - 1e-6)
F = D[D.era == 'fish']; S = D[D.era == 'score']
# M0: Brownian with a fitted scale + calibration
best = None
for k in np.arange(0.5, 3.01, 0.1):
    x = lg(bm(F.z.values, k)); X = np.c_[np.ones(len(x)), x]
    r = minimize(lambda p: np.mean(np.logaddexp(0, X @ p) - F.y.values * (X @ p)), np.zeros(2), method='BFGS')
    if best is None or r.fun < best[0]: best = (r.fun, k, r.x)
k0, (a0, b0) = best[1], best[2]
D['lbm'] = lg(bm(D.z.values, k0))
F = D[D.era == 'fish']; S = D[D.era == 'score']
p0 = 1 / (1 + np.exp(-(a0 + b0 * S.lbm.values)))
FEAT = ['lbm', 'side', 'r', 'dist', 'ru', 'age', 'pos', 'xPD', 'xPW', 'opn', 'tEx', 'dow', 'ev']
def score(p, y, lab):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    br = np.mean((p - y) ** 2); ll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
    cal = pd.DataFrame({'p': p, 'y': y}).groupby(pd.cut(p, np.linspace(0, 1, 11)), observed=True).mean()
    print(f'{lab:28s} Brier {br:.4f}  logloss {ll:.4f}  | ' + ' '.join(f'{100*a:.0f}→{100*b:.0f}' for a, b in zip(cal.p, cal.y)))
    return ll
y = S.y.values
score(np.full(len(y), F.y.mean()), y, 'flat rate')
l0 = score(p0, y, f'Brownian k={k0:.1f}')
# M1: logistic on the features (standardised)
mu = F[FEAT].mean(); sd = F[FEAT].std()
lr = LogisticRegression(C=1.0, max_iter=500).fit(((F[FEAT] - mu) / sd).values, F.y.values)
p1 = lr.predict_proba(((S[FEAT] - mu) / sd).values)[:, 1]; l1 = score(p1, y, 'logistic, all features')
# M2: gradient-boosted trees, depth 3 (exportable to Pine)
rng = np.random.default_rng(1); idx = rng.choice(len(F), size=min(400000, len(F)), replace=False)
t0 = time.time()
gb = GradientBoostingClassifier(n_estimators=60, max_depth=3, learning_rate=0.15, subsample=0.7, min_samples_leaf=400, random_state=1)
gb.fit(F[FEAT].values[idx], F.y.values[idx]); print('GBM fit', round(time.time() - t0), 's')
p2 = gb.predict_proba(S[FEAT].values)[:, 1]; l2 = score(p2, y, 'GBM 60×depth 3')
imp = pd.Series(gb.feature_importances_, index=FEAT).sort_values(ascending=False); print('importance', imp.round(3).to_dict())
# day-clustered bootstrap of the logloss gain GBM vs Brownian
ll = lambda p: -(y * np.log(np.clip(p, 1e-6, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-6, 1)))
g = ll(p0) - ll(p2); days = S.td.values; ud, inv = np.unique(days, return_inverse=True)
sums = np.bincount(inv, weights=g); cnt = np.bincount(inv)
bs = [sums[ix].sum() / cnt[ix].sum() for ix in [rng.integers(0, len(ud), len(ud)) for _ in range(300)]]
print(f'logloss gain GBM over Brownian (score era): {g.mean():.4f}  95% CI {np.percentile(bs, 2.5):.4f} – {np.percentile(bs, 97.5):.4f}')
for sd_ in ['NQ', 'ES', 'RTY']:
    mk = S.sym.values == sd_; print(sd_, f'Brier Brownian {np.mean((p0[mk]-y[mk])**2):.4f}  GBM {np.mean((p2[mk]-y[mk])**2):.4f}')
pickle.dump(dict(k0=k0, a0=a0, b0=b0, gb=gb, FEAT=FEAT), open('/home/claude/sk/t12_models.pkl', 'wb'))
