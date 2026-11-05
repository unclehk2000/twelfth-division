"""Mangekyō v1.3 research: weekly gaps as a second layer. Weekly candles (Mon–Fri) built from the back-adjusted daily front
month (NQ, ES, RTY 2010–26, YM 2017–26); ATR = Wilder RMA(14) of the weekly true range. Same detection and lifecycle as the
daily gaps (gaps.py), same matched controls (5 three-week windows with no gap, same symbol and direction, within ±2 years, the
middle candle's body and candle 3's close position matched), horizons in weeks. Errors clustered by week of formation."""
import numpy as np, pandas as pd
from data import daily, SYMS, atr
from gaps import detect, lifecycle
from feats import controls
from split import clus

def weekly(sym):
    D = daily(sym)
    g = D.groupby('wk')
    W = pd.DataFrame({'bo': g.bo.first(), 'bh': g.bh.max(), 'bl': g.bl.min(), 'bc': g.bc.last(), 'n': g.bc.size()})
    W = W[W.n >= 3]
    W['atrB'] = atr(W.bh.values, W.bl.values, W.bc.values)
    W['wk'] = W.index; W['dow'] = 0
    return W

def feats(W, z):
    O, H, L, C = (W['b' + x].values for x in 'ohlc'); A = W.atrB.values
    t0 = z.t0.values; d = z.dir.values; c2 = np.where(z.kind.values == 'VI', t0, t0 - 1)
    z = z.copy()
    z['w'] = (z.top - z.bot).values / A[t0]
    near = np.where(d == 1, z.top.values, z.bot.values)
    z['d0'] = (C[t0] - near) * d / A[t0]
    z['c2body'] = (C[c2] - O[c2]) * d / A[t0]
    z['date'] = W.index[t0]; z['yr'] = W.index[t0].year
    return z

R = []; Q = []
for s in SYMS:
    W = weekly(s)
    O, H, L, C = (W['b' + x].values for x in 'ohlc'); A = W.atrB.values
    z = detect(O, H, L, C, A)
    z = lifecycle(z, O, H, L, C, A, horizon=150, k_bounce=1.0, race=12)
    z = feats(W, z); z['sym'] = s; z.index = [f'{s}w{i}' for i in range(len(z))]
    q = controls(W.rename(columns={}), z, M=5)
    q = lifecycle(q, O, H, L, C, A, horizon=150, k_bounce=1.0, race=12)
    q = feats(W, q); q['sym'] = s
    R.append(z); Q.append(q)
    yrs = W.index.year.nunique()
    print(s, 'weeks', len(W), {k: round((z.kind == k).sum() / yrs, 1) for k in ['FVG', 'SB', 'VI']}, 'per year · FVG median width', round(z[z.kind == 'FVG'].w.median(), 2), 'ATRw · controls', len(q))
Z = pd.concat(R); Q = pd.concat(Q, ignore_index=True)

def add(o):
    o = o.copy()
    o['T4'] = ((o.tT >= 0) & (o.tT - o.t0 <= 4)).astype(float)
    o['T12'] = ((o.tT >= 0) & (o.tT - o.t0 <= 12)).astype(float)
    o['M12'] = ((o.tM >= 0) & (o.tM - o.t0 <= 12)).astype(float)
    o['holdT'] = np.where(o.tT >= 0, (o.tF != o.tT), np.nan).astype(float)          # the touch week holds the far edge
    o['hold4'] = np.where(o.tT >= 0, ~((o.tX >= 0) & (o.tX - o.tT <= 4)), np.nan).astype(float)
    return o
Z = add(Z); Q = add(Q)
F = Z[Z.kind == 'FVG'].copy()
cols = ['T4', 'T12', 'M12', 'holdT', 'hold4', 'bounce']
q = Q.groupby('of')[cols].mean()
F = F.join(q, rsuffix='_c')
F['wkid'] = F.date.values
print(f'\nWeekly FVGs: {len(F)} ({F.tT.ge(0).sum()} touched), median width {F.w.median():.2f} weekly ATR')
lab = {'T4': 'near edge back within 4 weeks', 'T12': 'near edge back within 12 weeks', 'M12': 'CE traded within 12 weeks',
       'holdT': 'first touch week holds the far edge', 'hold4': 'not closed beyond within 4 weeks of the touch', 'bounce': '1 weekly ATR bounce before a close beyond'}
for v in cols:
    m, se, t, n = clus(F[v] - F[v + '_c'], F.wkid)
    per = ''.join('+' if (g[v] - g[v + '_c']).mean() > 0 else '−' for _, g in F.groupby('sym'))
    per_n = {sy: round(100 * (g[v] - g[v + '_c']).mean(), 1) for sy, g in F.groupby('sym')}
    pp = {('2010–24' if not p else '2025–26'): round(100 * (g[v] - g[v + '_c']).mean(), 1) for p, g in F.groupby(F.yr >= 2025)}
    print(f'  {lab[v]:45s} gap {100*F[v].mean():5.1f}%  no gap {100*F[v+"_c"].mean():5.1f}%  diff {100*m:+5.1f} ± {100*se:3.1f}  t {t:+.1f}  n {n}  {per_n} {pp}')
Z.to_pickle('/home/claude/mgk/wk_zones.pkl'); Q.to_pickle('/home/claude/mgk/wk_ctl.pkl')
