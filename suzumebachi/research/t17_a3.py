"""Scenario search: a shallow regression tree on the 1R race (R, null 0) per sensitivity, trained on ES + YM 2018–24 only; every leaf
scored on ES + YM 2025–26 and NQ + RTY (never trained). Plus gradient-boosted trees for the ranking power (top / bottom fifth)."""
import numpy as np, pandas as pd, sys
from sklearn.tree import DecisionTreeRegressor, export_text
from sklearn.ensemble import HistGradientBoostingRegressor
sys.path.insert(0, '/home/claude/lr'); from lib import cse, D2025
X = pd.read_pickle('/home/claude/sz/t17_evx2.pkl')
X['smt1'] = ((X.sw_sw == 1) & (X.p_sw == 0)).astype(int)
FE = ['dir', 'mss', 'f_pd', 'f_pw', 'f_as', 'f_lo', 'f_day', 'sw_sw', 'smt1', 'fvg', 'tr1', 'trd', 'pdx', 'hdx', 'pwx', 'xMO', 'xDO', 'xWO', 'rel', 'rA', 'rD', 'body', 'brk', 'dayR', 'bars_x', 'bars_leg', 'depth']
X[FE] = X[FE].replace([np.inf, -np.inf], np.nan)
def wr(g): mu, se, n = cse(g.R1.values / 2, g.td.values); return 0.5 + mu, se, n
def show(lbl, g):
    s = []
    for gg in ['T', 'S', 'O']:
        a, se, n = wr(g[g.grp == gg]); s.append(f'{100*a:5.1f}±{100*se:3.1f} {n:5d}')
    sy = ''.join('+' if g[g.sym == q].R1.mean() > 0 else '−' for q in ['ES', 'YM', 'NQ', 'RTY'])
    return f'{lbl:10s} ' + ' | '.join(s) + f' | {sy}'
for (u, k) in [(5, 3), (5, 8), (15, 2)]:
    A = X[(X.u == u) & (X.k == k)].copy(); Xf = A[FE].fillna(-9)
    T = A.grp == 'T'
    dt = DecisionTreeRegressor(max_depth=4, min_samples_leaf=max(1200, int(0.025 * T.sum())), random_state=0).fit(Xf[T], A.R1[T])
    A['leaf'] = dt.apply(Xf)
    print(f'\n=== {u}m k{k}: tree leaves (win% of the 1R race: train | ES+YM 25–26 | NQ+RTY 18–26 | sign ES YM NQ RTY) ===')
    print(export_text(dt, feature_names=FE, decimals=2, max_depth=4))
    for lf, g in sorted(A.groupby('leaf'), key=lambda z: -z[1][z[1].grp == 'T'].R1.mean()):
        print(show(f'leaf {lf}', g))
    gb = HistGradientBoostingRegressor(max_depth=3, max_iter=150, learning_rate=0.05, min_samples_leaf=400, l2_regularization=1.0, random_state=0).fit(Xf[T], A.R1[T])
    A['p'] = gb.predict(Xf)
    for gg in ['S', 'O']:
        B = A[A.grp == gg]; q = B.p.quantile([0.2, 0.8]).values
        print(f'  GBM {gg}: top fifth', show('', B[B.p >= q[1]]), '\n         bottom fifth', show('', B[B.p <= q[0]]))
    A[['leaf', 'p']].to_pickle(f'/home/claude/sz/a3_{u}_{k}.pkl')
