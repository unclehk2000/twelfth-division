# Benihime v3: (1) the sisters term in the live fill / CE odds — at each checkpoint, how many of the other two index futures
# have already filled (reached the CE of) their own RTH gap; (2) ICT's "CE by 10:00" as a live odds row. Same path data,
# same model form as v2; fitted on 2018–24, scored on 2025–26, refit on all for the script.
import numpy as np, pandas as pd, statsmodels.formula.api as smf, warnings, json
warnings.filterwarnings('ignore')
R = pd.read_pickle('feat.pkl'); R = R[R.ratio.notna()]
P = pd.read_pickle('path.pkl')
P = P.join(R[['ce_min']], on='idx')
R0 = R.copy(); R0['idx'] = R0.index
P0 = pd.DataFrame(dict(idx=R0.idx, ck=0, dist=1.0, retr=0.0, fill=R0.fill_rth.astype(float)))
P0 = P0.join(R[['sym', 'tday', 'half', 'bk', 'lr', 'ratio', 'on_loc', 'fill_rth', 'o1_rth', 'ce_min']], on='idx')
P = pd.concat([P0, P], ignore_index=True)
P['distc'] = P.dist.clip(0, 3); P['retrc'] = P.retr.clip(0, 1); P['onl'] = P.on_loc.clip(0, 1.2)
P['ce'] = (P.ce_min.notna()).astype(float)
# sisters: fill / CE minutes of the other two on the same day (a sister with no gap that day counts as not filled)
S = R[['sym', 'tday', 'fill_min', 'ce_min']].copy()
piv_f = S.pivot_table(index='tday', columns='sym', values='fill_min', aggfunc='first')
piv_c = S.pivot_table(index='tday', columns='sym', values='ce_min', aggfunc='first')
def nsis(df, piv):
    out = np.zeros(len(df))
    for s in ('NQ', 'ES', 'RTY'):
        m = (df.sym == s).values
        sub = df[m]
        cnt = np.zeros(m.sum())
        for t in ('NQ', 'ES', 'RTY'):
            if t == s or t not in piv: continue
            v = piv[t].reindex(sub.tday).values
            cnt += (np.nan_to_num(v, nan=1e9) < sub.ck.values)
        out[m] = cnt
    return out
P['nsis'] = nsis(P, piv_f); P['nsisc'] = nsis(P, piv_c)
tr, te = P[P.half == '18-24'], P[P.half == '25-26']
def ev(f, a, b, y):
    m = smf.logit(f, a).fit(disp=0); p = m.predict(b); return np.mean((p - b[y]) ** 2), m
base = 'fill ~ C(ck) + lr + distc + retrc + onl'
for f in (base, base + ' + nsis'):
    br, m = ev(f, tr, te, 'fill'); print(f'FILL {f:50s} OOS Brier {br:.5f}')
mm = smf.logit(base + ' + nsis', tr).fit(disp=0, cov_type='cluster', cov_kwds={'groups': pd.factorize(tr.tday)[0]})
mt = smf.logit(base + ' + nsis', te).fit(disp=0, cov_type='cluster', cov_kwds={'groups': pd.factorize(te.tday)[0]})
print('  nsis train %.3f (z %.2f)  test %.3f (z %.2f)' % (mm.params.nsis, mm.tvalues.nsis, mt.params.nsis, mt.tvalues.nsis))
for s in ('NQ', 'ES', 'RTY'):
    q = P[P.sym == s]; m_ = smf.logit(base + ' + nsis', q).fit(disp=0, cov_type='cluster', cov_kwds={'groups': pd.factorize(q.tday)[0]})
    print('   ', s, round(m_.params.nsis, 3), 'z', round(m_.tvalues.nsis, 2))
Q = P[(P.retr < 0.5) & ((P.ce_min.isna()) | (P.ce_min >= P.ck))].copy(); Q['dce'] = (Q.dist - 0.5).clip(0, 3)
qtr, qte = Q[Q.half == '18-24'], Q[Q.half == '25-26']
cb = 'ce ~ C(ck) + lr + dce + retrc + onl'
for f in (cb, cb + ' + nsisc'):
    br, m = ev(f, qtr, qte, 'ce'); print(f'CE   {f:50s} OOS Brier {br:.5f}')
mm = smf.logit(cb + ' + nsisc', qtr).fit(disp=0, cov_type='cluster', cov_kwds={'groups': pd.factorize(qtr.tday)[0]})
mt = smf.logit(cb + ' + nsisc', qte).fit(disp=0, cov_type='cluster', cov_kwds={'groups': pd.factorize(qte.tday)[0]})
print('  nsisc train %.3f (z %.2f)  test %.3f (z %.2f)' % (mm.params.nsisc, mm.tvalues.nsisc, mt.params.nsisc, mt.tvalues.nsisc))
# ICT's CE by 10:00: rows at 09:30 and 09:45 with the CE not yet reached; outcome = CE by 10:00 (ce_min <= 30)
C10 = Q[Q.ck.isin([0, 15])].copy(); C10['ce10'] = (C10.ce_min.notna() & (C10.ce_min <= 30)).astype(float)
c10f = 'ce10 ~ C(ck) + lr + dce + onl'
br, m10 = ev(c10f, C10[C10.half == '18-24'], C10[C10.half == '25-26'], 'ce10')
brb, _ = ev('ce10 ~ C(ck)', C10[C10.half == '18-24'], C10[C10.half == '25-26'], 'ce10')
print(f'CE by 10:00: OOS Brier {brb:.4f} (time only) -> {br:.4f};  rate {C10[C10.ck == 0].ce10.mean():.3f} at 09:30')
mf = smf.logit(base + ' + nsis', P).fit(disp=0); m10a = smf.logit(c10f, C10).fit(disp=0)
print(mf.params.round(3).to_string()); print(m10a.params.round(3).to_string())
json.dump(dict(fill={k: float(v) for k, v in mf.params.items()}, ce10={k: float(v) for k, v in m10a.params.items()}), open('coef_v3.json', 'w'), indent=1)
# typical size of the sister term in points
for p0 in (0.2, 0.4, 0.6):
    lo = np.log(p0 / (1 - p0)); print(p0, [round(100 * (1 / (1 + np.exp(-(lo + k * mf.params.nsis))) - p0), 1) for k in (1, 2)])
