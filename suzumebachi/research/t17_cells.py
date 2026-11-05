"""The scenario table the script carries: every MSS cell (raid × FVG × risk) and BOS cell (prior-day-range location × midnight-open
side) per sensitivity, with the suite's rule: pooled 2018–26 all four markets p < 0.05 (clustered by day), the same sign in 2018–24
and 2025–26, the same sign on ES, YM, NQ and RTY. Win% of the 1R race for the break's direction."""
import numpy as np, pandas as pd, sys, json
sys.path.insert(0, '/home/claude/lr'); from lib import cse, D2025
X = pd.read_pickle('/home/claude/sz/t17_evx3.pkl')
X['raidY'] = (X.raid != 'no raid').astype(int); X['tight'] = (X.rA < 1.5).astype(int)
X['loc'] = np.where(X.pdx >= 0.75, 2, np.where(X.pdx < 0.25, 0, 1)); X.loc[X.pdx.isna(), 'loc'] = 1
X['mos'] = np.where(X.xMO.isna(), 0, np.where(X.xMO > 0, 1, 2))
X['cell'] = np.where(X.mss == 1, X.raidY * 4 + X.fvg * 2 + X.tight, 8 + X['loc'] * 3 + X.mos)
NAMES = {0: 'MSS no raid · no FVG · normal stop', 1: 'MSS no raid · no FVG · tight stop', 2: 'MSS no raid · FVG · normal', 3: 'MSS no raid · FVG · tight',
         4: 'MSS raid · no FVG · normal', 5: 'MSS raid · no FVG · tight', 6: 'MSS raid · FVG · normal', 7: 'MSS raid · FVG · tight'}
for l, ln in enumerate(['PD range low quarter', 'PD range middle', 'PD range top quarter+']):
    for s, sn in enumerate(['before 00:00', 'ICT side of midnight open', 'wrong side of midnight open']):
        NAMES[8 + l * 3 + s] = f'BOS {ln} · {sn}'
rows = []
for (u, k), A in X.groupby(['u', 'k']):
    for c, g in A.groupby('cell'):
        mu, se, n = cse(g.R1.values / 2, g.td.values)
        e1 = g[g.td < D2025].R1.mean(); e2 = g[g.td >= D2025].R1.mean()
        sy = [g[g.sym == q].R1.mean() for q in ['ES', 'YM', 'NQ', 'RTY']]
        ok = abs(mu / se) > 1.96 and np.sign(e1) == np.sign(e2) == np.sign(mu) and all(np.sign(v) == np.sign(mu) for v in sy)
        mT, sT, nT = cse(g[(g.td < D2025) & g.sym.isin(['ES', 'YM'])].R1.values / 2, g[(g.td < D2025) & g.sym.isin(['ES', 'YM'])].td.values)
        mH, sH, nH = cse(g[g.td >= D2025].R1.values / 2, g[g.td >= D2025].td.values)
        res = g.w1.notna(); mins = g[res].mins.median()
        rows.append(dict(u=u, k=k, cell=int(c), name=NAMES[int(c)], win=50 + 100 * mu, se=100 * se, n=n, t=mu / se, ok=ok, T=50 + 100 * mT, H=50 + 100 * mH, sH=100 * sH, nH=nH,
                         e1=50 + 50 * e1, e2=50 + 50 * e2, ES=50 + 50 * sy[0], YM=50 + 50 * sy[1], NQ=50 + 50 * sy[2], RTY=50 + 50 * sy[3], mins=mins, share=len(g) / len(A[A.mss == (1 if c < 8 else 0)])))
R = pd.DataFrame(rows); R.to_pickle('/home/claude/sz/cells.pkl')
pd.set_option('display.width', 260)
for (u, k), g in R.groupby(['u', 'k']):
    print(f'\n=== {u}m k{k} ===')
    print(g[['cell', 'name', 'win', 'se', 'n', 't', 'ok', 'T', 'H', 'sH', 'ES', 'YM', 'NQ', 'RTY', 'mins', 'share']].round(1).to_string(index=False))
print('\npassing cells:', R.ok.sum(), 'of', len(R))
