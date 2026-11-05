import numpy as np, pandas as pd
def cl(x, g):
    x = pd.Series(np.asarray(x, float)); g = pd.Series(np.asarray(g)); m = x.notna(); x, g = x[m], g[m]
    mu = x.mean(); r = (x - mu).groupby(g.values).sum(); return mu, np.sqrt((r ** 2).sum()) / len(x), len(x)
X = pd.read_pickle('t6_rows.pkl'); X = X[(X.smt >= 0) & (X.res != 0)]
X['rev'] = (X.res == 1).astype(float) + 0.5 * (X.res == 0.5)
X['half'] = np.where(X.yr >= 2025, 'test', 'train'); X['g'] = X.sym + X.td.astype(int).astype(str)
print('T6: after the first sweep of a standing look-back level: reversal (1 unit-ATR back before 1 beyond), SMT vs none')
for L in ('H', 'M15', 'M5'):
    for h in ('train', 'test'):
        q = X[(X.layer == L) & (X.half == h)]
        s1 = q[q.smt == 1]; s0 = q[q.smt == 0]
        d = s1.rev.mean() - s0.rev.mean()
        # clustered SE of the difference via regression on a dummy
        y = q.rev - q.groupby('smt').rev.transform('mean')
        se = np.sqrt((cl(y[q.smt == 1], q.g[q.smt == 1])[1]) ** 2 + (cl(y[q.smt == 0], q.g[q.smt == 0])[1]) ** 2)
        print(f'{L:4s} {h:5s} SMT n {len(s1):5d} rev {100*s1.rev.mean():5.1f} | no SMT n {len(s0):6d} rev {100*s0.rev.mean():5.1f} | diff {100*d:+5.1f}±{100*se:.1f}')
q = X[X.half == 'train']
print('train by symbol (SMT rev / no-SMT rev):', {s: (round(100 * z[z.smt == 1].rev.mean(), 1), round(100 * z[z.smt == 0].rev.mean(), 1)) for s, z in q.groupby('sym')})
