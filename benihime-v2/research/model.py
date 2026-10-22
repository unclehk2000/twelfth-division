import numpy as np, pandas as pd, statsmodels.formula.api as smf, warnings, json
warnings.filterwarnings('ignore')
R = pd.read_pickle('feat.pkl'); R = R[R.ratio.notna()]
P = pd.read_pickle('path.pkl')
P = P.join(R[['ce_min', 'o1_rth']].rename(columns={'o1_rth': 'o1x'}), on='idx')
# add checkpoint 0 (the open): dist 1, retr 0
R0 = R.copy(); R0['idx'] = R0.index
P0 = pd.DataFrame(dict(idx=R0.idx, ck=0, dist=1.0, retr=0.0, fill=R0.fill_rth.astype(float)))
P0 = P0.join(R[['sym', 'tday', 'half', 'bk', 'lr', 'ratio', 'on_loc', 'fill_rth', 'o1_rth', 'ce_min']], on='idx')
P = pd.concat([P0, P], ignore_index=True)
P['distc'] = P.dist.clip(0, 3); P['retrc'] = P.retr.clip(0, 1); P['onl'] = P.on_loc.clip(0, 1.2)
P['ce'] = (P.ce_min.notna()).astype(float)
tr, te = P[P.half == '18-24'], P[P.half == '25-26']
def ev(f, d_tr, d_te, y):
    m = smf.logit(f, d_tr).fit(disp=0); p = m.predict(d_te)
    return np.mean((p - d_te[y]) ** 2)
print('FILL OOS Brier')
for f in ('fill ~ C(bk):C(ck)', 'fill ~ C(ck) + lr + distc', 'fill ~ C(ck) + lr + distc + retrc', 'fill ~ C(ck) + lr + distc + retrc + onl'):
    print(f'  {f:45s} {ev(f, tr, te, "fill"):.4f}')
# CE sample: CE not reached by the checkpoint
Q = P[(P.retr < 0.5) & ((P.ce_min.isna()) | (P.ce_min >= P.ck))].copy()
Q['dce'] = (Q.dist - 0.5).clip(0, 3)
qtr, qte = Q[Q.half == '18-24'], Q[Q.half == '25-26']
print('CE OOS Brier  n', len(Q))
for f in ('ce ~ C(bk):C(ck)', 'ce ~ C(ck) + lr + dce', 'ce ~ C(ck) + lr + dce + retrc', 'ce ~ C(ck) + lr + dce + retrc + onl'):
    print(f'  {f:45s} {ev(f, qtr, qte, "ce"):.4f}')
# final fits on all data
mf = smf.logit('fill ~ C(ck) + lr + distc + retrc + onl', P).fit(disp=0)
mc = smf.logit('ce ~ C(ck) + lr + dce + retrc + onl', Q).fit(disp=0)
print(mf.params.round(3).to_string()); print(mc.params.round(3).to_string())
# calibration OOS of the fill model fit on 18-24
m = smf.logit('fill ~ C(ck) + lr + distc + retrc + onl', tr).fit(disp=0); te = te.copy(); te['p'] = m.predict(te)
te['dec'] = pd.qcut(te.p, 10, labels=False)
print(te.groupby('dec').agg(pred=('p', 'mean'), obs=('fill', 'mean'), n=('fill', 'size')).round(3).to_string())
for s in ('NQ', 'ES', 'RTY'):
    t = te[te.sym == s]; print(s, 'pred', round(t.p.mean(), 3), 'obs', round(t.fill.mean(), 3))
json.dump(dict(fill={k: float(v) for k, v in mf.params.items()}, ce={k: float(v) for k, v in mc.params.items()}), open('coef.json', 'w'), indent=1)
