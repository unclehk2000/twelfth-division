"""Getsuga Jūjishō research, step 3: do the eighths matter? Reach, first-touch holds and day extremes on the grid,
each against a grid of the same spacing shifted by a random fraction of an eighth (same week, same range)."""
import numpy as np, pandas as pd, statsmodels.formula.api as smf, statsmodels.api as sm
from scipy import stats
W = pd.read_pickle('weeks.pkl'); W = W[~W.roll].copy()
LV = pd.read_pickle('levels.pkl'); LV = LV[LV.wk.isin(W.wk)].copy()
PH = pd.read_pickle('phases.pkl'); PH = PH[PH.wk.isin(W.wk)].copy()
LV['real'] = (LV.kind == 'real').astype(int); LV['hit'] = LV.hit.astype(int)
LV['yr'] = pd.DatetimeIndex(LV.wk).year; LV['half'] = np.where(LV.yr >= 2025, 'B', 'A')
out = []
def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h
# 1) reach: real vs shifted, controlling for distance (in AWR4, capped at 3) with a flexible curve, errors clustered by week
X = LV[LV.d <= 3].copy(); X['sd'] = np.sqrt(X.d)
m = smf.glm('hit ~ real + d + sd + I(d**2) + up', X, family=sm.families.Binomial()).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(X.wk)[0]})
print('REACH by Friday, real grid vs shifted grid (logit, distance-controlled, clustered by week)')
print(f"  real coef {m.params['real']:+.3f}  SE {m.bse['real']:.3f}  p {m.pvalues['real']:.3f}   n levels {len(X)}  weeks {X.wk.nunique()}")
for hf in ('A', 'B'):
    Y = X[X.half == hf]
    mm = smf.glm('hit ~ real + d + sd + I(d**2) + up', Y, family=sm.families.Binomial()).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(Y.wk)[0]})
    print(f"  {'2018-24' if hf == 'A' else '2025-26'}: real coef {mm.params['real']:+.3f} p {mm.pvalues['real']:.3f}")
# per level: observed vs the shifted-grid curve's prediction at the same distance
ms = smf.glm('hit ~ d + sd + I(d**2) + up', X[X.real == 0], family=sm.families.Binomial()).fit()
R_ = X[X.real == 1].copy(); R_['pred'] = ms.predict(R_)
tab = R_.groupby('f').agg(n=('hit', 'size'), hit=('hit', 'mean'), pred=('pred', 'mean'), mir=('mir', 'mean'), d=('d', 'median'))
tab['diff'] = tab.hit - tab.pred
# per level z from a week-bootstrap would be heavy; use binomial SE on the difference
tab['z'] = tab['diff'] / np.sqrt(tab.pred * (1 - tab.pred) / tab.n)
tab['p'] = 2 * stats.norm.sf(tab.z.abs())
print('\nPER LEVEL (reach by Friday 16:59 from the set): observed, predicted from the shifted grid at the same distance, mirror')
print(tab.round(3).to_string())
tab.to_csv('reach_by_level.csv')
# 2) first-touch holds
print('\nFIRST-TOUCH HOLD (bounces B before it goes B through), real vs shifted grid, |f| range -1..2')
for B in ('hold5', 'hold10'):
    Z = LV.dropna(subset=[B])
    a = Z[Z.real == 1][B]; c = Z[Z.real == 0][B]
    mm = smf.ols(f'{B} ~ real', Z).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(Z.wk)[0]})
    print(f"  {B}: real {a.mean():.3f} (n {len(a)})  shifted {c.mean():.3f} (n {len(c)})  diff {mm.params['real']:+.3f}  p {mm.pvalues['real']:.3f}")
    for hf in ('A', 'B'):
        Y = Z[Z.half == hf]; mh = smf.ols(f'{B} ~ real', Y).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(Y.wk)[0]})
        print(f"     {'2018-24' if hf == 'A' else '2025-26'}: diff {mh.params['real']:+.3f} p {mh.pvalues['real']:.3f}")
def tier(f):
    if np.isnan(f): return 'shifted'
    if f in (0.0, 1.0): return 'anchors 0/1'
    if f == 0.5: return 'EQ 0.5'
    if f in (1.5, -0.5): return 'SDs 1.5/-0.5'
    if f in (2.0, -1.0): return 'SDs 2/-1'
    if f in (0.25, 0.75): return 'quarters'
    if 0 < f < 1: return 'eighths (inside)'
    return 'eighths (outside)'
LV['tier'] = LV.f.apply(tier)
print('\n  hold10 by tier:')
Z = LV.dropna(subset=['hold10'])
base = Z[Z.real == 0].hold10.mean()
for tname, g in Z.groupby('tier'):
    k, n = g.hold10.sum(), len(g); lo, hi = wilson(k, n)
    print(f"    {tname:20s} {k / n:.3f} [{lo:.3f}, {hi:.3f}] n {n}")
# 3) day extremes and closes on the grid: share within ±0.1 of an eighth (20% if uniform), weeks with eighth >= 5 points
print('\nDAY EXTREMES / CLOSES ON THE GRID (|phase| < 0.1 eighth; uniform = 20%), weeks with an eighth >= 5 pts')
Wk = W.set_index('wk'); PH['e8'] = PH.wk.map(Wk.aR) / 8; P = PH[PH.e8 >= 5]
for what in ('high', 'low', 'close'):
    g = P[P.what == what]; r_ = (g.ph.abs() < 0.1).mean(); s_ = (g.phs.abs() < 0.1).mean()
    z = (r_ - s_) / np.sqrt(0.2 * 0.8 * 2 / len(g))
    ray = np.mean(np.cos(2 * np.pi * g.ph)); rays = np.mean(np.cos(2 * np.pi * g.phs))
    print(f"  {what:5s}: real {r_:.3f} shifted {s_:.3f} (n {len(g)}) z {z:+.2f} | mean cos real {ray:+.3f} shifted {rays:+.3f}")
DN = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri'}
print('  by day (highs + lows):')
for dw, g in P[P.what != 'close'].groupby('dow'):
    r_ = (g.ph.abs() < 0.1).mean(); s_ = (g.phs.abs() < 0.1).mean(); z = (r_ - s_) / np.sqrt(0.2 * 0.8 * 2 / len(g))
    print(f"    {DN.get(dw, dw)}: real {r_:.3f} shifted {s_:.3f} n {len(g)} z {z:+.2f} p {2 * stats.norm.sf(abs(z)):.3f}")
# 4) day of week: which day the levels are first reached; holds by the day of the touch
print('\nFIRST REACH BY DAY (share of the levels reached that week, real grid; shifted in brackets)')
for kind in ('real', 'shift'):
    g = LV[(LV.kind == kind) & LV.hit.astype(bool)]
    print(f"  {kind}: " + '  '.join(f"{DN[k]} {v:.3f}" for k, v in g.hday.value_counts(normalize=True).sort_index().items()))
print('\nHOLD10 BY DAY OF THE TOUCH, real vs shifted (clustered by week)')
rows = []
for dw in range(5):
    Z = LV.dropna(subset=['hold10']); Z = Z[Z.hday == dw]
    mm = smf.ols('hold10 ~ real', Z).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(Z.wk)[0]})
    rows.append(dict(day=DN[dw], real=Z[Z.real == 1].hold10.mean(), shifted=Z[Z.real == 0].hold10.mean(), n=int((Z.real == 1).sum()), diff=mm.params['real'], p=mm.pvalues['real']))
DD = pd.DataFrame(rows); DD['p_bonf'] = np.minimum(DD.p * 5, 1); print(DD.round(3).to_string(index=False))
DD.to_csv('hold_by_day.csv', index=False)
print('\nREACH BY DAY (real vs shifted, distance-controlled, levels not yet reached at the start of that day)')
# per day: among levels not reached before day dw, was it reached on day dw? (hazard by day)
rows = []
for dw in range(5):
    Z = X[(X.hday == -1) | (X.hday >= dw)].copy(); Z['hd'] = (Z.hday == dw).astype(int)
    mm = smf.glm('hd ~ real + d + sd + I(d**2) + up', Z, family=sm.families.Binomial()).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(Z.wk)[0]})
    rows.append(dict(day=DN[dw], real=Z[Z.real == 1].hd.mean(), shifted=Z[Z.real == 0].hd.mean(), coef=mm.params['real'], p=mm.pvalues['real']))
RD = pd.DataFrame(rows); RD['p_bonf'] = np.minimum(RD.p * 5, 1); print(RD.round(3).to_string(index=False))
RD.to_csv('reach_by_day.csv', index=False)
