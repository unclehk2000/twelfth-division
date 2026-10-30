"""Getsuga Jūjishō research, step 4: states (coiled / uncoiled, direction, gap direction) and whether the gaps predict
volatility. Splits: fit 2018-23, test 2024-26 (out of sample); errors clustered by week or Newey-West."""
import numpy as np, pandas as pd, statsmodels.formula.api as smf, statsmodels.api as sm
from scipy import stats
W = pd.read_pickle('weeks.pkl'); W = W[~W.roll].copy()
W['r'] = W.aR / W.awr; W['yr'] = pd.DatetimeIndex(W.wk).year; W['oos'] = W.yr >= 2024
W['vol'] = (W.Hr - W.Lr) / W.awr                       # rest of the week (set → Fri 16:59) in AWR4
W['ret'] = W.Cw / W.P0 - 1; W['upw'] = (W.Cw > W.P0).astype(int)
W['monup'] = (W.R < 0).astype(int)                      # Monday's CE above Friday's: the range sits under price-at-set? no: 0 above 1
W['towardF'] = np.sign(W.F - W.P0)                     # +1 when Friday's CE is above the set price
W['movedF'] = np.sign(W.Cw - W.P0) == W.towardF
W['q'] = pd.qcut(W.r, 4, labels=['Q1 coiled', 'Q2', 'Q3', 'Q4 uncoiled'])
def ci(v):
    v = np.asarray(v, float); m = v.mean(); se = v.std(ddof=1) / np.sqrt(len(v)); return m, m - 1.96 * se, m + 1.96 * se
print('weeks', len(W), '| |R| / AWR4 quartile edges', W.r.quantile([.25, .5, .75]).round(3).tolist())
print('\n1) COILED → VOLATILITY? the rest of the week (set → Fri) in AWR4, by |R| / AWR4 quartile')
for q, g in W.groupby('q', observed=True):
    m, lo, hi = ci(g.vol); print(f"  {q:12s} n {len(g):3d}  rest-of-week range {m:.3f} [{lo:.3f}, {hi:.3f}] AWR4   |R| median {g.aR.median():.0f} pts")
rs = stats.spearmanr(W.r, W.vol); print(f"  Spearman |R|/AWR4 vs rest-of-week range/AWR4: {rs.statistic:+.3f} p {rs.pvalue:.3f}")
for nm, g in (('2018-23', W[~W.oos]), ('2024-26', W[W.oos])):
    rs = stats.spearmanr(g.r, g.vol); print(f"    {nm}: {rs.statistic:+.3f} p {rs.pvalue:.3f} n {len(g)}")
# the reach of a level at the same AWR4 distance: coiled vs uncoiled weeks (is a coiled week "more active"?)
LV = pd.read_pickle('levels.pkl'); LV = LV[(LV.kind == 'real') & LV.wk.isin(W.wk)].merge(W[['wk', 'r']], on='wk')
LV['hit'] = LV.hit.astype(int); LV['coil'] = (LV.r <= W.r.quantile(.25)).astype(int); LV['sd'] = np.sqrt(LV.d)
X = LV[LV.d <= 3]
m = smf.glm('hit ~ coil + d + sd + I(d**2) + up', X, family=sm.families.Binomial()).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(X.wk)[0]})
print(f"  a level the same AWR4 distance away, coiled (Q1) vs other weeks: logit coef {m.params['coil']:+.3f} p {m.pvalues['coil']:.3f}")
print('\n   ... and in the range\'s own units (what the grid shows): share of weeks reaching each level by Friday')
for f in (1.0, 1.5, 2.0, -0.5, -1.0):
    row = '  '.join(f"{q.split()[0]} {g[f'hitf'].mean():.2f}" for q, g in LV[LV.f == f].assign(hitf=lambda z: z.hit).merge(W[['wk', 'q']], on='wk').groupby('q', observed=True))
    print(f"   f {f:+.1f}: {row}")
print('\n   where the week closes, in the range\'s units (0 = Monday\'s CE, 1 = Friday\'s), by quartile')
for q, g in W.groupby('q', observed=True):
    xc = g.xC; print(f"   {q:12s} between 0 and 1: {((xc >= 0) & (xc <= 1)).mean():.2f}  past 1: {(xc > 1).mean():.2f}  past 0: {(xc < 0).mean():.2f}  beyond the SDs (>1.5 or <-0.5): {((xc > 1.5) | (xc < -0.5)).mean():.2f}")
print('\n2) DIRECTION: does the week move toward Friday\'s CE (fill back) or away (continue Monday\'s shift)?')
k, n = W.movedF.sum(), len(W); bt = stats.binomtest(int(k), n, 0.5)
print(f"  closed toward Friday's CE {k}/{n} = {k / n:.3f}  p {bt.pvalue:.3f}")
for nm, g in (('2018-23', W[~W.oos]), ('2024-26', W[W.oos])):
    print(f"    {nm}: {g.movedF.mean():.3f} (n {len(g)})")
# split by which side Friday sits: Friday above (towardF=+1) means "down from Friday to Monday"
for s, g in W.groupby('towardF'):
    nm = "Friday's CE above the set price (Monday shifted down)" if s > 0 else "Friday's CE below (Monday shifted up)"
    m_, lo, hi = ci(g.upw); print(f"  {nm}: week up from the set {m_:.3f} [{lo:.3f}, {hi:.3f}] n {len(g)}  mean return {1e4 * g.ret.mean():+.0f} bp")
m_, lo, hi = ci(W.upw); print(f"  all weeks (the always-long benchmark): up {m_:.3f} [{lo:.3f}, {hi:.3f}]  mean {1e4 * W.ret.mean():+.0f} bp")
mm = smf.ols('ret ~ towardF', W).fit(cov_type='HAC', cov_kwds={'maxlags': 2}); print(f"  return on toward-F sign: {1e4 * mm.params['towardF']:+.1f} bp p {mm.pvalues['towardF']:.3f}")
print('\n3) GAP DIRECTION (Monday\'s FPFVG bullish / bearish) and agreement with Friday\'s')
D = pd.read_pickle('days.pkl'); D = D[D.fp.notna() & ~D.half].copy()
D['dret'] = D.c_end / D.P0 - 1; D['dup'] = (D.c_end > D.P0).astype(int)
for nm, g in D.groupby('fp'):
    m_, lo, hi = ci(g.dup); print(f"  every day, {'bull' if nm > 0 else 'bear'} FPFVG: closed 16:59 above the gap's third candle {m_:.3f} [{lo:.3f}, {hi:.3f}] n {len(g)} mean {1e4 * g.dret.mean():+.1f} bp")
mm = smf.ols('dret ~ fp', D).fit(cov_type='HAC', cov_kwds={'maxlags': 5}); print(f"  day return on gap direction: {1e4 * mm.params['fp']:+.1f} bp per side p {mm.pvalues['fp']:.3f}")
for nm, g in W.groupby('Mdir'):
    m_, lo, hi = ci(g.upw); print(f"  week: Monday's gap {'bull' if nm > 0 else 'bear'}: week up from the set {m_:.3f} [{lo:.3f}, {hi:.3f}] n {len(g)}")
W['agree'] = W.Fdir == W.Mdir
for nm, g in W.groupby('agree'):
    m_, lo, hi = ci(g.vol); print(f"  Friday and Monday gaps {'agree' if nm else 'disagree'}: rest-of-week range {m_:.3f} AWR4 [{lo:.3f}, {hi:.3f}] n {len(g)}; up {g.upw.mean():.3f}")
print('\n4) DO THE GAPS PREDICT VOLATILITY? every NQ day: log range after the gap → 16:59, fit 2018-23, scored 2024-26')
D = D.dropna(subset=['radr5', 'rest_rng', 'pre_rng', 'gap']).copy()
D = D[(D.rest_rng > 0) & (D.pre_rng > 0)]
D['ly'] = np.log(D.rest_rng); D['la'] = np.log(D.radr5); D['lp'] = np.log(D.pre_rng); D['lg'] = np.log(D.gap); D['mins'] = D.fpt % 100 - 30
D['lam'] = np.log(D.am_rng.clip(lower=0.25)); D['oos'] = D.date.dt.year >= 2024
tr, te = D[~D.oos], D[D.oos]
def oos(fml, y='ly'):
    mm = smf.ols(fml.replace('Y', y), tr).fit(); pr = mm.predict(te); r2 = 1 - ((te[y] - pr) ** 2).sum() / ((te[y] - te[y].mean()) ** 2).sum()
    return mm, r2
for y, lab in (('ly', 'rest of the day (after the gap → 16:59)'), ('lam', 'NY AM (after the gap → 10:59)')):
    print(f"  target: {lab}")
    for fml in ('Y ~ la', 'Y ~ lg', 'Y ~ la + lg', 'Y ~ la + lp', 'Y ~ la + lp + lg', 'Y ~ la + lp + lg + mins'):
        mm, r2 = oos(fml, y)
        extra = f"  gap coef {mm.params['lg']:+.3f} (t {mm.tvalues['lg']:.1f})" if 'lg' in fml else ''
        print(f"    {fml.replace('Y', 'log range'):40s} in-sample R² {mm.rsquared:.3f}  out-of-sample R² {r2:.3f}{extra}")
# the gap in ADR units, quintiles → range in ADR units (descriptive)
D['gn'] = D.gap / D.radr5; D['yn'] = D.rest_rng / D.radr5
D['gq'] = pd.qcut(D.gn, 5, labels=['G1 smallest', 'G2', 'G3', 'G4', 'G5 largest'])
print('  gap size (÷ RTH ADR5) quintile → the rest of the day (÷ RTH ADR5):')
for q, g in D.groupby('gq', observed=True):
    print(f"    {q:12s} gap {g.gap.median():5.2f} pts  rest of day {g.yn.mean():.3f}×ADR5  09:30→gap {(g.pre_rng / g.radr5).mean():.3f}×ADR5  n {len(g)}")
# by weekday: gap coefficient after ADR and the 09:30 range
print('  gap coefficient by weekday (log rest-of-day ~ log ADR5 + log 09:30 range + log gap, all years, Newey-West):')
for dw, g in D.groupby('dow'):
    mm = smf.ols('ly ~ la + lp + lg', g).fit(cov_type='HAC', cov_kwds={'maxlags': 5})
    print(f"    {['Mon', 'Tue', 'Wed', 'Thu', 'Fri'][dw]}: {mm.params['lg']:+.3f} p {mm.pvalues['lg']:.3f} (n {len(g)})")
print('\n5) WEEK LEVEL: rest-of-week range ÷ AWR4 from the range and the two gaps (fit 2018-23, scored 2024-26)')
W['lv'] = np.log(W.vol); W['lr'] = np.log(W.r); W['lmg'] = np.log(W.Mgap / W.Mradr); W['lfg'] = np.log(W.Fgap / W.Fradr); W['lmp'] = np.log(W.Mpre / W.Mradr)
W['lawr'] = np.log(W.awr); W['lmr'] = np.log(W.Mradr / W.awr)
Wt = W.dropna(subset=['lv', 'lr', 'lmg', 'lfg', 'lmp', 'lmr']); a, bb = Wt[~Wt.oos], Wt[Wt.oos]
for fml in ('lv ~ lmr', 'lv ~ lr', 'lv ~ lmr + lr', 'lv ~ lmr + lmp', 'lv ~ lmr + lmp + lmg + lfg', 'lv ~ lmr + lmp + lmg + lfg + lr'):
    mm = smf.ols(fml, a).fit(cov_type='HAC', cov_kwds={'maxlags': 2}); pr = mm.predict(bb)
    r2 = 1 - ((bb.lv - pr) ** 2).sum() / ((bb.lv - bb.lv.mean()) ** 2).sum()
    co = ' '.join(f"{k} {v:+.3f}(p{mm.pvalues[k]:.2f})" for k, v in mm.params.items() if k != 'Intercept')
    print(f"  {fml:32s} in {mm.rsquared:.3f}  out {r2:+.3f}   {co}")
W.to_pickle('weeks_states.pkl')
