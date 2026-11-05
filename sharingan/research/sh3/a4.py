import numpy as np, pandas as pd
def cl(x, g):
    x = pd.Series(np.asarray(x, float)); g = pd.Series(np.asarray(g)); m = x.notna(); x, g = x[m], g[m]
    mu = x.mean(); r = (x - mu).groupby(g.values).sum(); return mu, np.sqrt((r ** 2).sum()) / len(x), len(x)
X = pd.read_pickle('t4_rows.pkl')
X['g'] = X.sym + X.cid.astype('int64').astype(str)
print('T4 QT: real vs sign-flipped (r1-3). "Q2 extreme" = bullish cycle (close > true open) with its low in Q2, bearish with its high in Q2')
for cy in ('week', 'day', 'session', '90min'):
    q = X[X.cyc == cy]
    def stats(z):
        q2x = np.where(z.upT == 1, z.qL == 1, z.qH == 1).astype(float)
        brk = (z.b2H + z.b2L) == 1   # Q2 broke exactly one side of Q1
        jud = np.where(z.b2H == 1, z.upT == 0, z.upT == 1).astype(float)   # closed on the other side of the true open
        qh = z.qH.value_counts(normalize=True).reindex([0, 1, 2, 3]).fillna(0).values
        return q2x, brk, jud, qh
    re = q[q.r == 0]; nu = q[q.r > 0]
    a, b, c, d = stats(re); a0, b0, c0, d0 = stats(nu)
    print(f'{cy:8s} n {len(re):6d} | Q2 holds the counter extreme: real {100*a.mean():5.1f} null {100*a0.mean():5.1f} | '
          f'Judas (Q2 breaks one side, cycle closes other side of true open): real {100*c[b].mean():5.1f} null {100*c0[b0].mean():5.1f} (n {b.sum()})')
    hiQ = re.qH.value_counts(normalize=True).sort_index().mul(100).round(1).tolist(); loQ = re.qL.value_counts(normalize=True).sort_index().mul(100).round(1).tolist()
    hiN = nu.qH.value_counts(normalize=True).sort_index().mul(100).round(1).tolist(); loN = nu.qL.value_counts(normalize=True).sort_index().mul(100).round(1).tolist()
    print(f'         high by quarter real {hiQ} null {hiN} | low real {loQ} null {loN}')
    # split-half: by symbol and by period
    for sy in ('NQ', 'ES', 'RTY'):
        r1 = re[re.sym == sy]; n1 = nu[nu.sym == sy]
        a1 = stats(r1)[0].mean(); a2 = stats(n1)[0].mean()
        print(f'           {sy}: Q2 counter extreme real {100*a1:5.1f} null {100*a2:5.1f}', end='')
    print()
