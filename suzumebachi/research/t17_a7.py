"""The exact scenarios, named, with the suite's rule (5m k2 / k3 / k5 pooled, all four markets, fade = back to the leg extreme first)."""
import numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/claude/lr'); from lib import cse, D2025
X = pd.read_pickle('/home/claude/sz/t17_evx3.pkl'); X = X[(X.u == 5) & X.k.isin([2, 3, 5])]
raid = X.raid != 'no raid'; tight = X.rA < 1.5; short = X.dir == -1; top = X.pdx >= 0.75; notMO = X.mo != 'ICT side of midnight open'
weak = (X.mss == 1) & ~raid & ((X.fvg == 0) | tight); chase = (X.mss == 0) & top & notMO
kz = X.kz.astype(str)
S = {
 'Weak MSS (no raid; no FVG or a tight stop)': weak,
 '  … short': weak & short, '  … long': weak & ~short,
 '  … no raid, no FVG, tight stop': (X.mss == 1) & ~raid & (X.fvg == 0) & tight,
 '  … no raid, FVG, tight stop': (X.mss == 1) & ~raid & (X.fvg == 1) & tight,
 '  … short, 00:00–02:00': weak & short & (kz == '00-02'),
 '  … short, NY PM 13:30–16:00': weak & short & (kz == 'NY PM 13:30-16'),
 '  … short, break ≤ 2 candles after the extreme': weak & short & (X.bars_x <= 2),
 'Chasing BOS (top quarter of the prior day or beyond, not the ICT side of 00:00)': chase,
 '  … short (sell BOS near / above PDH)': chase & short, '  … long (buy BOS near / below PDL)': chase & ~short,
 '  … short, Asia 20:00–00:00': chase & short & (kz == 'Asia 20-00'),
 '  … short, London 02:00–05:00': chase & short & (kz == 'London 02-05'),
 '  … short, 20:00–05:00': chase & short & kz.isin(['Asia 20-00', '00-02', 'London 02-05']),
 '  … short, NY lunch 11:30–13:30': chase & short & (kz == 'lunch'),
 'Textbook MSS (raid + FVG + normal stop)': (X.mss == 1) & raid & (X.fvg == 1) & ~tight,
 '  … fresh PDH / PDL raid + FVG': (X.mss == 1) & (X.raid == 'fresh PD') & (X.fvg == 1) & ~tight,
 '  … fresh Asia / London raid + FVG': (X.mss == 1) & (X.raid == 'fresh session') & (X.fvg == 1) & ~tight,
 '  … SMT + FVG': (X.mss == 1) & (X.smt1 == 'SMT') & (X.fvg == 1) & ~tight,
}
for lbl, mk in S.items():
    g = X[mk]; f = -g.R1.values / 2
    mu, se, n = cse(f, g.td.values); e1 = -g[g.td < D2025].R1.mean(); e2 = -g[g.td >= D2025].R1.mean()
    sy = [-g[g.sym == q].R1.mean() for q in ['ES', 'YM', 'NQ', 'RTY']]
    ok = abs(mu / se) > 1.96 and np.sign(e1) == np.sign(e2) == np.sign(mu) and all(np.sign(v) == np.sign(mu) for v in sy)
    br = 'break' if 'Textbook' in lbl or (lbl.startswith('  …') and ('raid +' in lbl or 'SMT' in lbl)) else 'fade'
    val = (0.5 - mu) if br == 'break' else (0.5 + mu)
    print(f'{lbl:80s} {br} {100*val:5.1f}±{100*se:3.1f} n {n:6d} days {g.td.nunique():5d} | 18–24 {50+50*(e1 if br=="fade" else -e1):5.1f} · 25–26 {50+50*(e2 if br=="fade" else -e2):5.1f} | ' + ' '.join(f'{50+50*(v if br=="fade" else -v):4.1f}' for v in sy) + ('  PASS' if ok else ''))
