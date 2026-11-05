# T5 level filter: did the OB's sweep candle take a standing LTF IPDA look-back level of the matching layer?
import numpy as np, pandas as pd
from lay import load, units
def cl(x, g):
    x = pd.Series(np.asarray(x, float)); g = pd.Series(np.asarray(g)); m = x.notna(); x, g = x[m], g[m]
    mu = x.mean(); r = (x - mu).groupby(g.values).sum(); return mu, np.sqrt((r ** 2).sum()) / len(x), len(x)
X = pd.read_pickle('t5_rows.pkl'); X = X[X.filled == 1].copy(); X['day'] = (X.tsC // 1440).astype(int)
lay_of = {'1-15': 'M5', '5-60': 'M15', '15-240': 'H'}
X['lvl'] = np.nan
for sym in ('NQ', 'ES', 'RTY'):
    m = load(sym)
    for tf, layer in lay_of.items():
        U = units(m, layer); ps = U['ps']; uts = U['ts']
        cH = U['H']; cL = U['L']
        sel = (X.sym == sym) & (X.tf == tf)
        res = []
        for tsw, swL, side in zip(X.loc[sel, 'tsSw'].values.astype(np.int64), X.loc[sel, 'swL'].values, X.loc[sel, 'side'].values):
            j = np.searchsorted(uts, tsw, 'right') - 1
            kk = np.searchsorted(ps, j, 'right') - 1
            if kk < 1 or ps[kk - 1] < 61:
                res.append(np.nan); continue
            a = ps[kk - 1]
            took = 0.0
            for N in (20, 40, 60):
                if side == 1:
                    lv = cL[a - N:a].min(); stand = (cL[a:j].min() if j > a else np.inf) > lv
                    if stand and swL <= lv: took = 1.0
                else:
                    lv = cH[a - N:a].max(); stand = (cH[a:j].max() if j > a else -np.inf) < lv
                    if stand and -swL >= lv: took = 1.0
            res.append(took)
        X.loc[sel, 'lvl'] = res
X['half'] = np.where(X.yr >= 2025, 'test', 'train')
print('T5 with the IPDA-level filter (sweep candle took a standing look-back level of the matching layer): 2R win vs the flip null')
for tf in ('1-15', '5-60', '15-240'):
    for h in ('train', 'test'):
        for lv in (1.0, 0.0):
            z = X[(X.tf == tf) & (X.half == h) & (X.lvl == lv) & (X.preM < 2)]
            w = (z.mfe >= 2).astype(float); nf = sum((z[f'f{i}'] >= 2).astype(float) for i in range(3)) / 3
            a = cl(w - nf, z.day)
            print(f'{tf:6s} {h:5s} {"at a level " if lv else "no level   "} n {len(z):5d} 2R {100*w.mean():4.1f} flip {100*nf.mean():4.1f} ex {100*a[0]:+4.1f}±{100*a[1]:.1f}')
X.to_pickle('t5_rows_lvl.pkl')
