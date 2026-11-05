"""One context at a time: the 1R race as a win rate (unresolved races scored by their mark-to-market R, so the null is exactly 50%).
Train ES + YM 2018–24 | held out ES + YM 2025–26 | NQ + RTY 2018–26."""
import numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/claude/lr'); from lib import cse, D2025
X = pd.read_pickle('/home/claude/sz/t17_ev.pkl')
X = X[(X.a5 > 0) & (X.rA >= 0.5) & (X.rA <= 12)].copy()
X['R1'] = np.where(X.w1.isna(), X.mtm.clip(-1, 1), 2 * X.w1 - 1); X['R2'] = np.where(X.w2.isna(), X.mtm.clip(-1, 2), np.where(X.w2 == 0.5, 0.5, 3 * X.w2 - 1))
X['grp'] = np.where(X.sym.isin(['ES', 'YM']), np.where(X.td < D2025, 'T', 'S'), 'O')
X['pdx'] = np.where(X.dir == -1, X.pdr, 1 - X.pdr); X['hdx'] = np.where(X.dir == -1, X.hdr, 1 - X.hdr)
X['oct'] = np.clip(np.floor(X.pdx * 8), -1, 8); X['hoct'] = np.clip(np.floor(X.hdx * 8), -1, 8)
X['sess'] = pd.cut(X.rel, [-1, 360, 480, 660, 810, 930, 1050, 1170, 1320, 1440], labels=['18-00', '00-02', 'LO 02-05', '05-07:30', '07:30-09:30', 'AM1 09:30-11:30', 'lunch', 'PM', 'close'])
X['swp'] = np.select([X.sw_pw == 1, X.sw_pd == 1, (X.sw_as == 1) | (X.sw_lo == 1), X.sw_day == 1, X.sw_sw == 1], ['PW', 'PD', 'session', 'day', 'swing'], 'none')
X['smt'] = np.where(X.sw_sw == 1, np.where(X.p_sw == 0, 'SMT', np.where(X.p_sw == 1, 'both swept', 'na')), 'no sweep')
X['bodyb'] = pd.cut(X.body, [-1, 0.5, 1, 2, 99]); X['rAb'] = pd.cut(X.rA, [0, 1.5, 2.5, 4, 12]); X['dayb'] = pd.cut(X.dayR, [0, 0.3, 0.6, 1, 9])
X['bxb'] = pd.cut(X.bars_x, [-1, 2, 5, 10, 999]); X['depb'] = pd.cut(X.depth, [-99, 0, 0.5, 1.5, 99])
X.to_pickle('/home/claude/sz/t17_evx.pkl')
def w(g):
    mu, se, n = cse(g.R1.values / 2, g.td.values); return mu, se, n
def row(lbl, A):
    out = []
    for gg in ['T', 'S', 'O']:
        mu, se, n = w(A[A.grp == gg]); out.append(f'{100*(0.5+mu):5.1f}±{100*se:3.1f} {n:6d}')
    return f'  {lbl:22s} ' + ' | '.join(out)
FEATS = ['mss', 'swp', 'smt', 'tr1', 'trd', 'oct', 'hoct', 'sess', 'fvg', 'bodyb', 'rAb', 'dayb', 'bxb', 'depb']
if __name__ == '__main__':
    for (u, k) in [(5, 3), (5, 8), (15, 2)]:
        A = X[(X.u == u) & (X.k == k)]
        print(f'\n=== {u}m k{k}  (win% of the 1R race: train | ES+YM 25–26 | NQ+RTY) ===')
        for fam, B in [('MSS', A[A.mss == 1]), ('BOS', A[A.mss == 0])]:
            print(row(fam + ' all', B))
            for f in FEATS[1:]:
                for v, g in B.groupby(f, observed=True):
                    if len(g) > 300: print(row(f'{fam} {f}={v}', g))
