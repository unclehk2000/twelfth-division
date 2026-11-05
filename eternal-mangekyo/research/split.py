import numpy as np, pandas as pd
def clus(diff, wk):
    d = pd.DataFrame({'d': np.asarray(diff, float), 'w': np.asarray(wk)}).dropna()
    if len(d) < 10: return np.nan, np.nan, np.nan, len(d)
    g = d.groupby('w').d.agg(['sum', 'count'])
    m = g['sum'].sum() / g['count'].sum(); e = g['sum'] - m * g['count']
    se = np.sqrt((e ** 2).sum()) / g['count'].sum()
    return m, se, (m / se if se > 0 else np.nan), len(d)
def wkof(dates): return (dates - pd.to_timedelta(dates.dt.dayofweek, unit='D')).values
def show(F, v, by, label=None, ctl=True):
    print(f"--- {v} by {label or by}")
    for k, g in F.groupby(by, observed=True):
        if ctl:
            m, se, t, n = clus(g[v] - g[v + '_c'], wkof(g.date))
            sy = ''.join('+' if (gg[v] - gg[v + '_c']).mean() > 0 else '−' for s, gg in g.groupby('sym'))
            pe = ''.join('+' if (gg[v] - gg[v + '_c']).mean() > 0 else '−' for s, gg in g.groupby(g.yr >= 2025))
            print(f"  {str(k):22s} n {n:5d} real {g[v].mean():.3f} ctl {g[v+'_c'].mean():.3f} diff {m:+.3f} t {t:+.1f} sym {sy} per {pe}")
        else:
            print(f"  {str(k):22s} n {g[v].notna().sum():5d} rate {g[v].mean():.3f}")
