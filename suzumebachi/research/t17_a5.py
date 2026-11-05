"""Breakdown of the confirmed contexts into exact scenarios (cells), win% of the 1R race for the break's direction.
T = ES + YM 2018–24 (trained) | H = all four 2025–26 (independent in time) | O1 = NQ + RTY 2018–24 | signs in 2025–26 ES YM NQ RTY."""
import numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/claude/lr'); from lib import cse
X = pd.read_pickle('/home/claude/sz/t17_evx3.pkl')
X['raidY'] = np.where(X.raid == 'no raid', 'no raid', 'raid'); X['riskY'] = np.where(X.rA < 1.5, 'tight', 'normal')
X['loc'] = np.where(X.pdx >= 0.75, 'ICT PD q4+', np.where(X.pdx < 0.25, 'PD q1-', 'PD mid'))
def st(g): mu, se, n = cse(g.R1.values / 2, g.td.values); return 50 + 100 * mu, 100 * se, n
def line(lbl, g):
    s = ' | '.join('{:5.1f}±{:3.1f} {:5d}'.format(*st(g[g.g4 == q])) for q in ['T', 'H', 'O1'])
    sy = ''.join('+' if g[(g.sym == q) & (g.g4 == 'H')].R1.mean() > 0 else '−' for q in ['ES', 'YM', 'NQ', 'RTY'])
    return f'  {lbl:44s} {s} | {sy}'
for (u, k) in [(5, 2), (5, 3), (5, 5), (5, 8), (15, 2)]:
    A = X[(X.u == u) & (X.k == k)]
    print(f'\n=== {u}m k{k} ===   T | H (2025–26, all four) | O1 | signs')
    M = A[A.mss == 1]
    for keys, g in M.groupby(['raidY', 'fv', 'riskY']):
        if len(g) > 400: print(line('MSS ' + ' · '.join(keys), g))
    B = A[A.mss == 0]
    for keys, g in B.groupby(['loc', 'mo']):
        if len(g) > 400: print(line('BOS ' + ' · '.join(keys), g))
