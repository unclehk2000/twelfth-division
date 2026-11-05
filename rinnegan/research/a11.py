import numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/claude/lr'); from lib import D2025
D = pd.read_pickle('/home/claude/lr/t11_rows.pkl'); R = 4
D['era'] = np.where(D.td >= D2025, 'score', 'fish')
def cl(y, g):
    y = np.asarray(y, float); ok = ~np.isnan(y); y = y[ok]; g = np.asarray(g)[ok]
    _, inv = np.unique(g, return_inverse=True); mu = y.mean(); s = np.bincount(inv, weights=y - mu)
    return mu, np.sqrt((s ** 2).sum()) / len(y), len(y)
def comp(d, col, f=lambda x: x):
    real = f(d[col]); fl = np.mean([f(d[f'{col}_{r}']) for r in range(R)], 0)
    mu, se, n = cl(real - fl, d.td)
    return f'{100*np.nanmean(real):5.1f}% vs {100*np.nanmean(fl):5.1f}  ({100*mu:+4.1f}±{100*se:3.1f}, n={n})'
for s in ['RDR', 'ODR', 'ADR']:
    print(f'===== {s}')
    for era in ['fish', 'score']:
        d = D[(D.sess == s) & (D.era == era)]
        c = d[d.dr != 0]
        print(f' {era}: confirmed {100*len(c)/len(d):.1f}% of {len(d)} days; median DR width/IDR width {np.median(c.drW/c.idrW):.2f}')
        print('   A opposite DR side traded      ', comp(c, 'oT'))
        print('   A opposite DR side 5m close     ', comp(c, 'oC'))
        print('   B back into the IDR             ', comp(c, 'bk'))
        for k in [0.5, 1.0, 2.0, 3.0]:
            print(f'   C extension ≥ {k:.1f} IDR       ', comp(c, 'ex', lambda x, k=k: (x >= k).astype(float)))
        print('   D last close beyond IDR mid     ', comp(c, 'cl'))
        # E: confirmed side vs hour colour; real vs flipped from the hour's close
        e = d[d.sR != 0]
        for col in ['up']:
            agreeR = (e.sR == e.up).astype(float)
            agreeF = np.mean([np.where(e[f'sF{r}'] == 0, np.nan, (e[f'sF{r}'] == e.up).astype(float)) for r in range(R)], 0)
            mu, se, n = cl(agreeR - agreeF, e.td)
            print(f'   E first confirm = hour colour   {100*agreeR.mean():5.1f}% vs {100*np.nanmean(agreeF):5.1f}  ({100*mu:+4.1f}±{100*se:3.1f}, n={n})')
