"""Second level: inside the passing cells, where does the failure concentrate? Fade win% (= 100 − the break's win%) by context.
Pooled 5m k2, k3, k5 (events can repeat across sensitivities; errors clustered by day). Suite rule per row. Plus costs."""
import numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/claude/lr'); from lib import cse, D2025
X = pd.read_pickle('/home/claude/sz/t17_evx3.pkl'); X = X[(X.u == 5) & X.k.isin([2, 3, 5])]
X['raidY'] = X.raid != 'no raid'; X['tight'] = X.rA < 1.5
W = X[(X.mss == 1) & ~X.raidY & ((X.fvg == 0) | X.tight)].copy(); W['grp'] = 'weak MSS'
P = X[(X.mss == 0) & (X.pdx >= 0.75) & (X.mo != 'ICT side of midnight open')].copy(); P['grp'] = 'BOS chasing the PD extreme'
TICK = {'ES': 0.25, 'YM': 1.0, 'NQ': 0.25, 'RTY': 0.1}
def row(lbl, g):
    f = -g.R1.values / 2      # the fade
    mu, se, n = cse(f, g.td.values); e1 = -g[g.td < D2025].R1.mean(); e2 = -g[g.td >= D2025].R1.mean()
    sy = [-g[g.sym == q].R1.mean() for q in ['ES', 'YM', 'NQ', 'RTY']]
    ok = abs(mu / se) > 1.96 and np.sign(e1) == np.sign(e2) == np.sign(mu) and all(np.sign(v) == np.sign(mu) for v in sy)
    return f'  {lbl:38s} fade {100*(0.5+mu):5.1f}±{100*se:3.1f} n {n:6d} | 18–24 {50+50*e1:5.1f} 25–26 {50+50*e2:5.1f} | ' + ' '.join(f'{50+50*v:4.1f}' for v in sy) + ('  PASS' if ok else '')
for G in [W, P]:
    print(f"\n=== {G.grp.iloc[0]} (fade = the 1R race against the break; ES YM NQ RTY) ===")
    print(row('all', G))
    for c in ['side', 'kz', 'h1', 'dd', 'speed', 'bigb', 'hq', 'mo', 'wop', 'smt1']:
        for v, g in G.groupby(c, observed=True):
            if len(g) >= 800: print(row(f'{c}: {v}', g))
    tk = G.sym.map(TICK); rt = G.risk / tk
    for cost in [1, 2]:
        net = -G.R1 - cost * tk / G.risk
        print(f'  median stop {rt.median():.0f} ticks · fade E[R] gross {(-G.R1).mean():+.3f}, net of {cost} tick(s) round trip {net.mean():+.3f}')
    for lo, hi in [(0, 8), (8, 16), (16, 32), (32, 1e9)]:
        g = G[(rt >= lo) & (rt < hi)]
        print(f'    stop {lo}-{hi if hi < 1e9 else "∞"} ticks: n {len(g)}, fade win {50 - 50 * g.R1.mean():.1f}%, net E[R] (2 ticks) {(-g.R1 - 2 * g.sym.map(TICK) / g.risk).mean():+.3f}')
