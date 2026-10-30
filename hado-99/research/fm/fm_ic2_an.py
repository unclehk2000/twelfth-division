import numpy as np, pandas as pd, statsmodels.api as sm
R = pd.concat([pd.read_pickle(f'IC2_{s}.pkl') for s in ('NQ', 'ES', 'RTY')], ignore_index=True)
R['held'] = R.held.astype(float)
R['prot'] = (R.kind == 'protected').astype(float)
R['half'] = np.where(pd.to_datetime(R.tday) < '2025-01-01', '18-24', '25-26')
R['db'] = pd.qcut(R.dist, 10, labels=False, duplicates='drop')
R['hb'] = R.h.clip(upper=28)
R['early'] = R.early.astype(float)
def fe(d, y, x, cells):
    """within-cell (fixed-effect) slope of y on x, errors clustered by date"""
    g = d.groupby(cells, observed=True)
    yd = d[y] - g[y].transform('mean'); xd = d[x] - g[x].transform('mean')
    m = sm.OLS(yd.to_numpy(), xd.to_numpy()[:, None]).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.tday)[0]})
    return m.params[0], m.pvalues[0]
def check(d, y, x, cells, name):
    b, p = fe(d, y, x, cells); out = dict(test=name, coef=round(100 * b, 1), p=p, n=len(d)); sg = [np.sign(b)]
    for k in ('half', 'sym'):
        for v, g in d.groupby(k):
            bb, pp = fe(g, y, x, cells); out[v] = round(100 * bb, 1); sg.append(np.sign(bb))
    out['ok'] = '✓' if p < 0.05 and len(set(sg)) == 1 else ''
    return out
rows = [check(R.assign(one=0), 'held', 'prot', ['one'], 'raw'),
        check(R, 'held', 'prot', ['hb', 'db'], 'same bars left × distance decile'),
        check(R, 'held', 'prot', ['hb', 'db', 'sym', 'side'], '+ symbol, side'),
        check(R[R.kind == 'protected'], 'held', 'early', ['hb', 'db'], 'protected: CISD in C2 vs later')]
pd.set_option('display.width', 200)
print(pd.DataFrame(rows).set_index('test').to_string())
P = R[R.kind == 'protected']; S = R[R.kind == 'swing']
bins = [-1, 5, 10, 15, 20, 28]
t = pd.DataFrame({'prot': P.groupby(pd.cut(P.h, bins), observed=True).held.mean() * 100,
                  'n': P.groupby(pd.cut(P.h, bins), observed=True).size(),
                  'swing': S.groupby(pd.cut(S.h, bins), observed=True).held.mean() * 100})
for k in ('half', 'sym'):
    for v, g in P.groupby(k):
        t[v] = g.groupby(pd.cut(g.h, bins), observed=True).held.mean() * 100
print(t.round(1).to_string())
print('overall protected %.1f%%, swing %.1f%%' % (100 * P.held.mean(), 100 * S.held.mean()))
