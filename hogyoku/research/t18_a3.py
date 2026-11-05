"""Machine-learned matrix: gradient-boosted trees on own-only vs own + cross-market features, per target and timeframe, trained on
2018–24, scored on 2025–26. Targets: C3 closes up from C2's close; C3 trades above C1's high; C3 trades below C1's low; C3 trades
above C2's high; below C2's low. The cross-market increment is the log-loss gain of own + cross over own-only (same targets, same
own inputs), with a day-clustered bootstrap. Pooled over the four markets (market as an input) and per market (individual)."""
import numpy as np, pandas as pd, sys
from sklearn.ensemble import HistGradientBoostingClassifier as HGB
sys.path.insert(0, '/home/claude/lr'); from lib import D2025
SY = ['NQ', 'ES', 'YM', 'RTY']
OWNF = ['shi', 'slo', 'cl', 'r2', 'rng', 'rng1', 'uw', 'lw', 'dh', 'dl']
def prep(tf):
    W = pd.read_pickle(f'/home/claude/pdm/mat_{tf}.pkl'); rows = []
    for s in SY:
        P = [p for p in SY if p != s]; o = W[s][['td', 'blk'] + OWNF + ['body', 'r3', 't3h', 't3l', 't3h1', 't3l1']].copy(); o['sym'] = SY.index(s)
        for j, p in enumerate(P):
            for c in ['shi', 'slo', 'cl', 'r2', 'uw', 'lw', 'dh', 'dl']: o[f'p{j}_{c}'] = W[p][c].values
        o['spread'] = o.r2 - np.mean([W[p].r2 for p in P], axis=0)
        o['nPlo'] = sum(W[p].slo for p in P).values; o['nPhi'] = sum(W[p].shi for p in P).values
        o['psp'] = (sum((np.sign(W[p].body) != np.sign(W[s].body)).astype(int) for p in P) > 0).astype(int).values
        rows.append(o)
    L = pd.concat(rows).reset_index(drop=True)
    L['up'] = (L.r3 > 0).astype(int); L['dow'] = (L.td + 3) % 7
    num = [c for c in L.columns if c not in ['td']]
    L[num] = L[num].replace([np.inf, -np.inf], np.nan)
    for c in [c for c in L.columns if c.endswith('cl')]: L[c] = L[c].clip(-3, 4)
    return L
def ll(y, p): p = np.clip(p, 1e-6, 1 - 1e-6); return -(y * np.log(p) + (1 - y) * np.log(1 - p))
def boot(d, td, B=400, seed=1):
    g = pd.DataFrame({'d': d, 'td': td}).groupby('td').d.agg(['sum', 'count']); s, c = g['sum'].values, g['count'].values
    rng = np.random.default_rng(seed); idx = rng.integers(0, len(s), (B, len(s)))
    v = s[idx].sum(1) / c[idx].sum(1); return d.mean(), np.quantile(v, [0.025, 0.975])
if __name__ == '__main__':
    for tf in sys.argv[1:] or ['240', '60', '15']:
        L = prep(tf); F = L[L.td < D2025]; S = L[L.td >= D2025]
        crossF = [c for c in L.columns if c.startswith('p') and '_' in c] + ['spread', 'nPlo', 'nPhi', 'psp']
        base = ['sym', 'blk', 'dow']
        print(f'\n===== {tf}: fish {len(F)}, score {len(S)} =====')
        for tgt in ['up', 't3h1', 't3l1', 't3h', 't3l']:
            res = {}
            for nm, X in [('own', base + OWNF), ('own+cross', base + OWNF + crossF)]:
                m = HGB(max_depth=3, max_iter=200, learning_rate=0.05, min_samples_leaf=300, l2_regularization=1.0, random_state=0).fit(F[X], F[tgt])
                res[nm] = m.predict_proba(S[X])[:, 1]
            y = S[tgt].values; p0 = np.full(len(y), F[tgt].mean())
            # base-rate per market from fish
            p0 = S.sym.map(F.groupby('sym')[tgt].mean()).values
            l0, lo_, lc = ll(y, p0), ll(y, res['own']), ll(y, res['own+cross'])
            g1, ci1 = boot(l0 - lo_, S.td.values); g2, ci2 = boot(lo_ - lc, S.td.values)
            from sklearn.metrics import roc_auc_score
            print(f'  {tgt:5s} rate {100*y.mean():5.1f}% | own vs base: gain {1000*g1:+.2f} mnat [{1000*ci1[0]:+.2f}, {1000*ci1[1]:+.2f}] AUC {roc_auc_score(y, res["own"]):.3f} | cross increment: {1000*g2:+.2f} mnat [{1000*ci2[0]:+.2f}, {1000*ci2[1]:+.2f}] AUC {roc_auc_score(y, res["own+cross"]):.3f}')
        L.to_pickle(f'/home/claude/pdm/ml_{tf}.pkl')
