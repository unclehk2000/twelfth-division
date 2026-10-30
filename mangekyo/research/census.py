import numpy as np, pandas as pd, sys
from data import daily, SYMS
from gaps import detect, lifecycle
rows = []
for s in SYMS:
    D = daily(s)
    for ser in ('b', 'u'):
        O, H, L, C = (D[ser + x].values for x in 'ohlc'); A = D.atrB.values
        z = detect(O, H, L, C, A)
        z = lifecycle(z, O, H, L, C, A)
        z['sym'] = s; z['ser'] = ser
        z['w'] = (z.top - z.bot) / A[z.t0.values]
        z['date'] = D.index[z.t0.values]
        z['roll'] = D.roll.values[z.t0.values] | D.roll.values[np.maximum(z.t0.values - 1, 0)] | D.roll.values[np.maximum(z.t0.values - 2, 0)]
        rows.append(z)
Z = pd.concat(rows, ignore_index=True)
Z.to_pickle('/home/claude/mgk/zones_census.pkl')
Z['days'] = 1
def frac(x, h): return ((x >= 0) & (x - Z.loc[x.index, 't0'] <= h)).mean()
for (ser, kind), g in Z.groupby(['ser', 'kind']):
    yrs = {s: (g[g.sym == s].date.dt.year.nunique()) for s in SYMS}
    per = g.groupby('sym').size() / pd.Series(yrs)
    print(f"{ser} {kind:3s} per year {per.round(1).to_dict()}  median width {g.w.median():.2f} ATR  "
          f"touch≤5d {((g.tT>=0)&(g.tT-g.t0<=5)).mean():.2f} ≤20d {((g.tT>=0)&(g.tT-g.t0<=20)).mean():.2f}  "
          f"CE≤20d {((g.tM>=0)&(g.tM-g.t0<=20)).mean():.2f}  traded through≤20d {((g.tF>=0)&(g.tF-g.t0<=20)).mean():.2f}  "
          f"closed through≤60d {((g.tX>=0)&(g.tX-g.t0<=60)).mean():.2f}  on/after roll {g.roll.mean():.3f}")
