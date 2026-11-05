"""Every ICT matrix reading against the drift (each market's own base rate in that period), with the suite's rule:
pooled p < 0.05 clustered by day, the same sign in 2018–24 and 2025–26, the same sign on NQ, ES, YM and RTY."""
import numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/claude/lr'); from lib import cse, D2025
SY = ['NQ', 'ES', 'YM', 'RTY']
res = []
for tf in ['D', '240', '60', '15']:
    L = pd.read_pickle(f'/home/claude/pdm/long_{tf}.pkl'); L['era'] = np.where(L.td < D2025, 0, 1)
    L['base'] = L.groupby(['sym', 'era']).up.transform('mean')
    q = L.spread.quantile([0.2, 0.8]).values
    R = {
     'bull C2': (L.form == 'bullC2', 1), 'bear C2': (L.form == 'bearC2', -1), 'expansion up': (L.form == 'expUp', 1), 'expansion down': (L.form == 'expDn', -1),
     'inside': (L.form == 'inside', 1), 'outside': (L.form == 'outside', 1),
     'bull C2, all four swept the low': ((L.form == 'bullC2') & (L.nPlo == 3), 1), 'bull C2 + SMT (≥1 partner held its low)': ((L.form == 'bullC2') & (L.nPlo < 3), 1),
     'held the low while a partner swept it': ((L.slo == 0) & (L.nPlo >= 1), 1),
     'bear C2, all four swept the high': ((L.form == 'bearC2') & (L.nPhi == 3), -1), 'bear C2 + SMT (≥1 partner held its high)': ((L.form == 'bearC2') & (L.nPhi < 3), -1),
     'held the high while a partner swept it': ((L.shi == 0) & (L.nPhi >= 1), -1),
     'PSP, own green': ((L.psp == 1) & (L.body > 0), 1), 'PSP, own red': ((L.psp == 1) & (L.body < 0), -1),
     'laggard fifth (vs partners)': (L.spread <= q[0], 1), 'leader fifth (vs partners)': (L.spread >= q[1], -1),
     'all four bull C2': ((L.form == 'bullC2') & (L.nPbull == 3), 1), 'all four bear C2': ((L.form == 'bearC2') & (L.nPbear == 3), -1),
    }
    for nm, (mk, d) in R.items():
        g = L[mk]; y = d * (g.up - g.base)        # excess win in the reading's direction over the drift
        mu, se, n = cse(y.values, g.td.values)
        e = [d * (g[g.era == k].up - g[g.era == k].base).mean() for k in [0, 1]]; sy = [d * (g[g.sym == s].up - g[g.sym == s].base).mean() for s in SY]
        ok = abs(mu / se) > 1.96 and np.sign(e[0]) == np.sign(e[1]) == np.sign(mu) and all(np.sign(v) == np.sign(mu) for v in sy)
        res.append(dict(tf=tf, reading=nm, dir='long' if d == 1 else 'short', edge=100 * mu, se=100 * se, t=mu / se, n=n, e1=100 * e[0], e2=100 * e[1], NQ=100 * sy[0], ES=100 * sy[1], YM=100 * sy[2], RTY=100 * sy[3], ok=ok))
R = pd.DataFrame(res); R.to_pickle('/home/claude/pdm/readings.pkl')
pd.set_option('display.width', 250)
print(R.round(1).to_string(index=False))
print(f'\ntests {len(R)}, passing {R.ok.sum()} (≈ {0.05 * len(R) / 2:.1f} expected by chance on one side)')
