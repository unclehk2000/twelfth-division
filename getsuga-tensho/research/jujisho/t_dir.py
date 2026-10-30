"""Getsuga Jūjishō research, step 5: the direction state, checked hard. Is 'Monday's gap below Friday's → the week rises'
real, stable, more than Friday→Monday price change, and does it beat always-long?"""
import numpy as np, pandas as pd, statsmodels.formula.api as smf
from scipy import stats
W = pd.read_pickle('weeks_states.pkl')
D = pd.read_pickle('days.pkl').set_index('date')
bb = pd.read_pickle('/home/claude/kyw/bars_NQ_all.pkl')
TD = bb.groupby('tday').agg(dO=('Open', 'first'), dC=('Close', 'last'), t0=('ts', 'first'), t1=('ts', 'last'))
W['dn'] = (W.F > W.P0).astype(int)                       # Monday shifted down: Friday's CE above the set price
W['bp'] = 1e4 * W.ret
print('year by year: rest-of-week return (bp) after a down shift / an up shift, and always-long')
for y, g in W.groupby('yr'):
    a, b_ = g[g.dn == 1].bp, g[g.dn == 0].bp
    print(f"  {y}: down {a.mean():+6.0f} (n {len(a):2d})  up {b_.mean():+6.0f} (n {len(b_):2d})  all {g.bp.mean():+5.0f}  diff {a.mean() - b_.mean():+6.0f}")
for nm, g in (('2018-21', W[W.yr <= 2021]), ('2022-26', W[W.yr >= 2022]), ('2018-23', W[W.yr <= 2023]), ('2024-26', W[W.yr >= 2024])):
    t = stats.ttest_ind(g[g.dn == 1].bp, g[g.dn == 0].bp, equal_var=False)
    print(f"  {nm}: diff {g[g.dn == 1].bp.mean() - g[g.dn == 0].bp.mean():+.0f} bp  Welch p {t.pvalue:.3f}  (n {len(g)})")
mw = stats.mannwhitneyu(W[W.dn == 1].bp, W[W.dn == 0].bp); print(f"  Mann-Whitney (ranks, all years) p {mw.pvalue:.3f}")
tr = lambda v: stats.trim_mean(v, 0.05)
print(f"  5% trimmed means: down {tr(W[W.dn == 1].bp):+.0f}  up {tr(W[W.dn == 0].bp):+.0f}")
# 2) the same with plain prices: Friday's set-time price vs Monday's (no FVG), Friday close vs Monday 09:30 open
W['Fp0'] = W.Fday.map(D.P0); W['Fc'] = W.Fday.map(D.c_end); W['Mo'] = W.Mday.map(D.o930)
W['dn_px'] = (W.Fp0 > W.P0).astype(int); W['dn_wkend'] = (W.Fc > W.Mo).astype(int)
print('\nthe same split by other definitions of "Monday below Friday" (agreement with the FPFVG split, then the effect)')
for c in ('dn_px', 'dn_wkend'):
    g = W.dropna(subset=[c]); agree = (g[c] == g.dn).mean(); a, b_ = g[g[c] == 1].bp, g[g[c] == 0].bp
    t = stats.ttest_ind(a, b_, equal_var=False)
    print(f"  {c:9s}: agrees with the FPFVG split {agree:.2f}  down {a.mean():+.0f} up {b_.mean():+.0f}  diff {a.mean() - b_.mean():+.0f} bp p {t.pvalue:.3f}")
m = smf.ols('bp ~ dn + dn_px', W).fit(cov_type='HAC', cov_kwds={'maxlags': 2})
print(f"  both in one regression: FPFVG split {m.params['dn']:+.0f} bp (p {m.pvalues['dn']:.3f}), plain-price split {m.params['dn_px']:+.0f} bp (p {m.pvalues['dn_px']:.3f})")
W['shift'] = (W.P0 - W.Fp0) / W.awr                       # signed Friday → Monday move, AWR4
m = smf.ols('bp ~ shift', W).fit(cov_type='HAC', cov_kwds={'maxlags': 2}); print(f"  continuous: rest-of-week bp per 1 AWR4 of Friday→Monday move {m.params['shift']:+.0f} (p {m.pvalues['shift']:.3f})")
# 3) against always-long: long only after a down shift / long-short by the state / always long; per-week Sharpe
print('\nversus the always-long benchmark (rest of the week, set → Friday 16:59, no costs)')
for nm, g in (('all', W), ('2018-23', W[W.yr <= 2023]), ('2024-26', W[W.yr >= 2024])):
    al = g.bp; lo = np.where(g.dn == 1, g.bp, 0.0); ls = np.where(g.dn == 1, g.bp, -g.bp)
    def sh(v): v = np.asarray(v, float); return v.mean() / v.std(ddof=1) * np.sqrt(52)
    print(f"  {nm:8s} always-long {al.sum():+7.0f} bp (Sharpe {sh(al):.2f})  long after a down shift {lo.sum():+7.0f} (Sharpe {sh(lo):.2f}, in {g.dn.mean():.0%} of weeks)  long/short {ls.sum():+7.0f} (Sharpe {sh(ls):.2f})")
# 4) which days carry it: each day's 18:00 → 16:59 return (Monday from the set), by state
print('\nby day: mean return (bp) of each day after a down shift vs an up shift')
rows = []
for _, w in W.iterrows():
    days = [d for d in TD.index if w.wk <= d < w.wk + pd.Timedelta(days=5) and d >= w.Mday]
    for d in days:
        o = w.P0 if d == w.Mday else TD.at[d, 'dO']
        rows.append(dict(wk=w.wk, dn=w.dn, dow=d.dayofweek, r=1e4 * (TD.at[d, 'dC'] / o - 1)))
R = pd.DataFrame(rows)
out = []
for dw, g in R.groupby('dow'):
    a, b_ = g[g.dn == 1].r, g[g.dn == 0].r; t = stats.ttest_ind(a, b_, equal_var=False)
    out.append(dict(day=['Mon (from the set)', 'Tue', 'Wed', 'Thu', 'Fri'][dw], down=a.mean(), up=b_.mean(), all=g.r.mean(), diff=a.mean() - b_.mean(), p=t.pvalue, n=len(g)))
O = pd.DataFrame(out); O['p_bonf'] = np.minimum(O.p * 5, 1); print(O.round(3).to_string(index=False)); O.to_csv('dir_by_day.csv', index=False)
# 5) does price go back to Friday's CE more after a down shift? reach of 1 by state, vs the mirror
LV = pd.read_pickle('levels.pkl'); L1 = LV[(LV.kind == 'real') & (LV.f == 1.0)].merge(W[['wk', 'dn']], on='wk')
for s, g in L1.groupby('dn'):
    print(f"  Friday's CE (1) reached by Friday, {'down' if s else 'up'} shift: {g.hit.mean():.3f} vs the mirror level {g.mir.mean():.3f} (n {len(g)})")
W.to_pickle('weeks_dir.pkl')
