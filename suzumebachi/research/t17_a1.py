"""Base rates: 1R race (null 50%) and 2R race (null 33.3%) per sensitivity and family. Train = ES + YM 2018–24; held out:
ES + YM 2025–26 (time) and NQ + RTY (markets never trained on). Errors clustered by day."""
import numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/claude/lr'); from lib import cse, D2025
X = pd.read_pickle('/home/claude/sz/t17_ev.pkl')
X = X[(X.a5 > 0) & (X.rA >= 0.5) & (X.rA <= 12) & X.w1.notna()].copy()
X['grp'] = np.where(X.sym.isin(['ES', 'YM']), np.where(X.td < D2025, 'train', 'ES+YM 25–26'), np.where(X.td < D2025, 'NQ+RTY 18–24', 'NQ+RTY 25–26'))
X['cl'] = X.sym + X.td.astype(str)
def cell(g, col='w1', null=0.5):
    mu, se, n = cse(g[col] - null, g.td.values)
    return f'{100*(mu+null):5.1f} ±{100*se:3.1f} ({n})'
for (u, k), A in X.groupby(['u', 'k']):
    for fam, B in [('all', A), ('MSS', A[A.mss == 1]), ('BOS', A[A.mss == 0])]:
        s = ' | '.join(cell(B[B.grp == g]) for g in ['train', 'ES+YM 25–26', 'NQ+RTY 18–24', 'NQ+RTY 25–26'])
        s2 = ' | '.join(cell(B[B.grp == g], 'w2', 1/3) for g in ['train', 'NQ+RTY 18–24'])
        print(f'{u:2d}m k{k} {fam:3s} 1R: {s} || 2R: {s2}')
