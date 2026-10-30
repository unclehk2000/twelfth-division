import sys, numpy as np, pandas as pd
from scipy.special import ndtr, expit, logit
from liqfit import fitp, predp
R = pd.read_pickle('liq_rows.pkl'); P = pd.read_pickle('par_liq.pkl')['PAR']
R['p20'] = np.nan
for s in (1, -1):
    m = R.side == s; R.loc[m, 'p20'] = predp(P[(s, '20')], R.d[m].values, 20.0)
g = R.groupby('yr').agg(pred=('p20', 'mean'), act=('y20', 'mean'), n=('y20', 'size')); g['ratio'] = g.act / g.pred
print(g.round(3).to_string())
# walk-forward by year: fit on prior years, score the year; reliability of the pooled out-of-sample predictions
oos = []
for y in range(2014, 2027):
    tr = R[R.yr < y]; te = R[R.yr == y].copy()
    for s in (1, -1):
        p = fitp(tr[tr.side == s].d.values, tr[tr.side == s].y20.values, 20.0); m = te.side == s
        te.loc[m, 'q'] = predp(p, te.d[m].values, 20.0)
    oos.append(te)
O = pd.concat(oos); b = pd.cut(O.q, [0, .1, .3, .5, .7, .9, 1])
print('walk-forward 2014–26 reliability:', ' · '.join(f'{100 * r.pred:.0f}→{100 * r.act:.0f}%' for r in O.groupby(b, observed=True).agg(pred=('q', 'mean'), act=('y20', 'mean')).itertuples()))
