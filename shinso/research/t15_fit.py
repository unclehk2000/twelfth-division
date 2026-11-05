import numpy as np, pandas as pd, sys, pickle
from scipy.stats import norm
from scipy.optimize import minimize
from sklearn.ensemble import GradientBoostingClassifier
sys.path.insert(0, '/home/claude/lr'); from lib import D2025
def lg(p): p = np.clip(p, 1e-6, 1 - 1e-6); return np.log(p / (1 - p))
def score(p, y, lab):
    p = np.clip(p, 1e-6, 1 - 1e-6); br = np.mean((p - y) ** 2); ll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
    cal = pd.DataFrame({'p': p, 'y': y}).groupby(pd.cut(p, np.linspace(0, 1, 11)), observed=True).mean()
    print(f'  {lab:28s} Brier {br:.4f}  logloss {ll:.4f} | ' + ' '.join(f'{100*a:.0f}→{100*b:.0f}' for a, b in zip(cal.p, cal.y))); return p
def boot(pa, pb, y, days, rng):
    ll = lambda p: -(y * np.log(p) + (1 - y) * np.log(1 - p)); g = ll(pa) - ll(pb)
    ud, inv = np.unique(days, return_inverse=True); su = np.bincount(inv, weights=g); cn = np.bincount(inv)
    bs = [su[ix].sum() / cn[ix].sum() for ix in [rng.integers(0, len(ud), len(ud)) for _ in range(300)]]
    return g.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)
rng = np.random.default_rng(1); out = {}
# ── pools
D = pd.read_pickle('/home/claude/sn/t15_pools.pkl'); D['era'] = np.where(D.td >= D2025, 'score', 'fish')
F = D[D.era == 'fish']
best = None
for k in np.arange(0.5, 3.01, 0.05):
    x = lg(2 * norm.cdf(-k * F.z.values)); X = np.c_[np.ones(len(x)), x]
    r = minimize(lambda p: np.mean(np.logaddexp(0, X @ p) - F.y.values * (X @ p)), np.zeros(2), method='BFGS')
    if best is None or r.fun < best[0]: best = (r.fun, k, r.x)
k0, (a0, b0) = best[1], best[2]; D['lz'] = lg(2 * norm.cdf(-k0 * D.z.values))
F = D[D.era == 'fish']; S = D[D.era == 'score']; y = S.y.values
print(f'== pools: fish {len(F)}, score {len(S)}, taken rate {F.y.mean():.3f}; Brownian k={k0:.2f} a={a0:.3f} b={b0:.3f}')
print('  taken by 16:59 (score) by pool type:', S.groupby('typ').y.mean().round(3).to_dict(), ' n', S.typ.value_counts().sort_index().to_dict())
score(np.full(len(y), F.y.mean()), y, 'flat rate')
p0 = score(1 / (1 + np.exp(-(a0 + b0 * S.lz.values))), y, 'Brownian')
FE = ['lz', 'typ', 'side', 'r', 'nb', 'cf', 'opp', 'same', 'tow', 'ev', 'dow']
idx = rng.choice(len(F), 400000, replace=False)
gb = GradientBoostingClassifier(n_estimators=50, max_depth=3, learning_rate=0.2, subsample=0.7, min_samples_leaf=400, random_state=1).fit(F[FE].values[idx], F.y.values[idx])
p2 = score(gb.predict_proba(S[FE].values)[:, 1], y, 'GBM 50×3')
print('  importance', pd.Series(gb.feature_importances_, index=FE).sort_values(ascending=False).round(3).to_dict())
g, lo, hi = boot(np.clip(p0, 1e-6, 1 - 1e-6), np.clip(p2, 1e-6, 1 - 1e-6), y, S.td.values, rng); print(f'  logloss gain GBM over Brownian {g:.4f} (95% CI {lo:.4f} – {hi:.4f})')
for s_ in ['NQ', 'ES', 'RTY']:
    mk = S.sym.values == s_; print(f'  {s_} Brier Brownian {np.mean((p0[mk]-y[mk])**2):.4f}  GBM {np.mean((p2[mk]-y[mk])**2):.4f}')
# ICT draw claims at the same Brownian odds: residual of the outcome over the Brownian prediction, by condition
S = S.assign(res=y - p0)
for nm, mk in [('opposite side already taken today', S.opp > 0), ('nothing taken on the opposite side', S.opp == 0), ('stacked (another pool within 0.15 ATR)', S.cf > 0), ('pool in the direction of the day\'s move', S.tow > 0), ('against the day\'s move', S.tow < 0)]:
    x = S.res[mk]; ud, inv = np.unique(S.td[mk], return_inverse=True); su = np.bincount(inv, weights=x - x.mean()); se = np.sqrt((su ** 2).sum()) / len(x)
    print(f'  residual vs Brownian, {nm:42s} {100*x.mean():+5.1f} ± {100*se:3.1f} pts (n={len(x)})')
out['pool'] = dict(k0=k0, a0=a0, b0=b0, gb=gb, FE=FE)
# ── race: nearest buy-side vs sell-side pool, which first
R = pd.read_pickle('/home/claude/sn/t15_race.pkl'); R['era'] = np.where(R.td >= D2025, 'score', 'fish')
R['base'] = R.dS / (R.dB + R.dS); R['lb'] = lg(R.base)
F = R[R.era == 'fish']; S = R[R.era == 'score']; y = S.y.values
print(f'== race: fish {len(F)}, score {len(S)}, buy-side first {F.y.mean():.3f}')
score(np.full(len(y), F.y.mean()), y, 'flat rate')
pb = score(S.base.values, y, 'position (gambler\'s ruin)')
FR = ['lb', 'tB', 'tS', 'nTB', 'nTS', 'opn', 'r']
gr = GradientBoostingClassifier(n_estimators=40, max_depth=3, learning_rate=0.15, subsample=0.7, min_samples_leaf=300, random_state=1).fit(F[FR].values, F.y.values)
pr = score(gr.predict_proba(S[FR].values)[:, 1], y, 'GBM 40×3')
print('  importance', pd.Series(gr.feature_importances_, index=FR).sort_values(ascending=False).round(3).to_dict())
g, lo, hi = boot(np.clip(pb, 1e-6, 1 - 1e-6), np.clip(pr, 1e-6, 1 - 1e-6), y, S.td.values, rng); print(f'  logloss gain GBM over position {g:.4f} (95% CI {lo:.4f} – {hi:.4f})')
out['race'] = dict(gb=gr, FE=FR)
pickle.dump(out, open('/home/claude/sn/t15_models.pkl', 'wb'))
