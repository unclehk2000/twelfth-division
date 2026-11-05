import numpy as np, pandas as pd
def cl(x, g):
    x = pd.Series(np.asarray(x, float)); g = pd.Series(np.asarray(g)); m = x.notna(); x, g = x[m], g[m]
    mu = x.mean(); r = (x - mu).groupby(g.values).sum(); return mu, np.sqrt((r ** 2).sum()) / len(x), len(x)
X = pd.read_pickle('t5_rows.pkl'); X['day'] = (X.tsC // 1440).astype(int); X['half'] = np.where(X.yr >= 2025, 'test', 'train')
print('T5 again, against the sign-flipped path after the fill (same bars, same R, no direction)')
for tf in ('1-15', '5-60', '15-240'):
    for h in ('train', 'test'):
        q = X[(X.tf == tf) & (X.half == h) & (X.filled == 1)]
        line = f'{tf:6s} {h:5s} n {len(q):5d} |'
        for R in (1, 2, 3):
            z = q[q.preM < R]; w = (z.mfe >= R).astype(float); nf = sum((z[f'f{i}'] >= R).astype(float) for i in range(3)) / 3
            a = cl(w - nf, z.day)
            line += f' {R}R {100*w.mean():4.1f} vs flip {100*nf.mean():4.1f} ex {100*a[0]:+4.1f}±{100*a[1]:.1f} |'
        print(line)
print('median risk (points) by tf/sym:', X[X.filled == 1].groupby(['tf', 'sym']).R.median().round(2).to_dict())
