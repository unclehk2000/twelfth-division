"""Weekly panel (W-FRI): index range, return and where the week traded against the prior week's range; CL and
index-carry state at the end of the week, as predictors of the next week."""
import pandas as pd, numpy as np

def weekly(P):
    out = []
    for S, d in P.groupby('sym'):
        d = d.sort_index()
        w = d.groupby('wk').agg(H=('ah', 'max'), L=('al', 'min'), C=('ac', 'last'), O=('ao', 'first'), adr=('adr20', 'first'),
                                n=('ac', 'size'), carry=('carry', 'last'), vix=('vix', 'last'),
                                x_r=('x_r', 'sum'), x_ts=('x_ts12', 'last'), x_m1=('x_m1', 'last'),
                                x_vol=('x_r', 'std'), shock=('shock', 'last'), deepB=('deepB', 'last'),
                                cl20=('cl20', 'last'), roll=('roll_week', 'max'), q=('q', 'last'), last=('ac', lambda s: s.index[-1]))
        w = w[w.n >= 3]
        w['rng'] = (w.H - w.L) / w.adr                                   # the week's range in ADR20
        w['ret'] = np.log(w.C / w.C.shift(1)) * 100
        mid = (w.H + w.L) / 2
        # next week against this week's range
        w['n_rng'] = w.rng.shift(-1)
        w['n_ret'] = w.ret.shift(-1)
        w['n_takeH'] = (w.H.shift(-1) > w.H).astype(float).where(w.H.shift(-1).notna())
        w['n_takeL'] = (w.L.shift(-1) < w.L).astype(float).where(w.L.shift(-1).notna())
        w['n_prem'] = (w.C.shift(-1) > mid).astype(float).where(w.C.shift(-1).notna())   # closes in this week's premium
        w['d_carry'] = w.carry.diff()
        w['d_ts'] = w.x_ts.diff()
        w['x_vol'] = w.x_vol * np.sqrt(252) * 100
        w['x_r'] = w.x_r * 100
        w['sym'] = S
        out.append(w)
    W = pd.concat(out)
    W.index = pd.DatetimeIndex(W.pop('last'), name='date')
    W['half'] = np.where(W.index < '2025-01-01', '18-24', '25-26')
    return W
