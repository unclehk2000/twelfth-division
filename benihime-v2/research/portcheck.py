"""Pine's model functions (constants rounded as in the script) vs the fitted models, on the research rows."""
import numpy as np, pandas as pd, statsmodels.formula.api as smf, warnings, json
warnings.filterwarnings('ignore')
exec(open('model.py').read().split("tr, te = P[P.half")[0])
CKM = [0, 15, 30, 45, 60, 90, 120, 180, 240, 300, 360, 405]
FCK = [0.0, -0.514, -0.694, -0.884, -0.987, -1.245, -1.446, -1.779, -2.128, -2.595, -3.284, -3.801]
CCK = [0.0, -0.139, -0.258, -0.412, -0.519, -0.725, -0.882, -1.158, -1.499, -1.960, -2.718, -3.286]
cl = lambda v, a, b: max(a, min(b, v))
def ck(A, m):
    m = cl(m, 0, 405); i = 0
    while i < 10 and CKM[i + 1] <= m: i += 1
    f = (m - CKM[i]) / (CKM[i + 1] - CKM[i]); return A[i] * (1 - f) + A[i + 1] * f
sig = lambda z: 100 / (1 + np.exp(-z))
pF = lambda mi, lr, d, r, o: sig(2.026 + ck(FCK, mi) - 1.071 * lr - 1.174 * cl(d, 0, 3) + 1.323 * cl(r, 0, 1) - 0.815 * cl(o, 0, 1.2))
pC = lambda mi, lr, d, o: sig(2.523 + ck(CCK, mi) - 1.022 * lr - 1.389 * cl(d - 0.5, 0, 3) - 0.864 * cl(o, 0, 1.2))
mf = smf.logit('fill ~ C(ck) + lr + distc + retrc + onl', P).fit(disp=0)
S = P.sample(3000, random_state=1).copy()
S['py'] = mf.predict(S) * 100
S['pine'] = [pF(r.ck, r.lr, r.dist, r.retr, r.on_loc) for r in S.itertuples()]
print('fill: max |diff|', (S.py - S.pine).abs().max().round(3), 'mean', (S.py - S.pine).abs().mean().round(4))
Q = P[(P.retr < 0.5) & ((P.ce_min.isna()) | (P.ce_min >= P.ck))].copy(); Q['dce'] = (Q.dist - 0.5).clip(0, 3)
mc = smf.logit('ce ~ C(ck) + lr + dce + onl', Q).fit(disp=0)
S = Q.sample(3000, random_state=1).copy(); S['py'] = mc.predict(S) * 100
S['pine'] = [pC(r.ck, r.lr, r.dist, r.on_loc) for r in S.itertuples()]
print('CE: max |diff|', (S.py - S.pine).abs().max().round(3))
# at the open, by size bucket: model (average open location) vs the published size table
R0 = P[P.ck == 0]
R0 = R0.assign(pm=[pF(0, r.lr, 1, 0, r.on_loc) for r in R0.itertuples()])
print(R0.groupby('bk').agg(model=('pm', 'mean'), observed=('fill', 'mean')).assign(observed=lambda d: d.observed * 100).round(1))
