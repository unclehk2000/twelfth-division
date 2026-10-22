import numpy as np, pandas as pd, statsmodels.formula.api as smf, warnings, json, sys
warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude/gh2/stats-kit'); from stats_kit import check, table
exec(open('model.py').read().split("tr, te = P[P.half")[0])
tr, te = P[P.half == '18-24'], P[P.half == '25-26'].copy()
m0 = smf.logit('fill ~ C(bk):C(ck)', tr).fit(disp=0); te['p0'] = m0.predict(te)
print('size-only OOS pred', te.p0.mean().round(3), 'obs', te.fill.mean().round(3))
Q = P[(P.retr < 0.5) & ((P.ce_min.isna()) | (P.ce_min >= P.ck))].copy(); Q['dce'] = (Q.dist - 0.5).clip(0, 3)
mc = smf.logit('ce ~ C(ck) + lr + dce + onl', Q).fit(disp=0)
mf = smf.logit('fill ~ C(ck) + lr + distc + retrc + onl', P).fit(disp=0)
json.dump(dict(fill={k: float(v) for k, v in mf.params.items()}, ce={k: float(v) for k, v in mc.params.items()}), open('coef.json', 'w'), indent=1)
print(mc.params.round(3).to_string())
# after the fill: -1 SD (one gap beyond the prior close) by 16:14, by size and fill time
R = pd.read_pickle('feat.pkl'); R = R[R.ratio.notna() & R.fill_rth.astype(bool)].copy()
R['o1'] = R.o1_rth.astype(float); R['ftb'] = pd.cut(R.fill_min, [-1, 15, 60, 120, 999], labels=['<15m', '15-60m', '1-2h', '2h+'])
R['lft'] = np.log1p(R.fill_min)
R['date'] = R.tday; R = R.set_index('date')
print(R.pivot_table(index='bk', columns='ftb', values='o1', aggfunc='mean').mul(100).round(0))
print(R.pivot_table(index='bk', columns='ftb', values='o1', aggfunc='size'))
print(R.groupby('bk').o1.mean().mul(100).round(0))
T = table([check(R, 'o1 ~ lft + C(bk) + lr', 'lft', test='-1SD after fill: later fill'),
           check(R, 'o1 ~ onl + C(bk) + lr', 'onl', test='-1SD after fill: ON loc') if 'onl' in R else check(R.assign(onl=R.on_loc.clip(0,1.2)), 'o1 ~ onl + C(bk) + lr', 'onl', test='-1SD after fill: ON loc')])
print(T[['coef', 'p', 'n', '18-24', 'p_18-24', '25-26', 'p_25-26', 'ES', 'NQ', 'RTY', 'ok']].to_string())
