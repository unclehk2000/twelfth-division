import numpy as np, pandas as pd, json
from sklearn.linear_model import LogisticRegression
T = pd.read_pickle('t1_rows.pkl'); T = T[T.dup == 0]
br = lambda p, y: np.mean((p - y) ** 2)
coef = {}
print('Reach odds per layer: logit = a + b·ln(d) + c·side(high); d = distance in unit-ATR(14). Fit 2018–24, score 2025–26')
for L in ('H', 'M15', 'M5', 'M1'):
    q = T[T.layer == L]; tr, te = q[q.yr <= 2024], q[q.yr >= 2025]
    for y in ('h20', 'hE'):
        Xf = lambda z: np.c_[np.log(z.d.clip(0.02)), (z.side == 1).astype(float)]
        m = LogisticRegression(C=1e4).fit(Xf(tr), tr[y]); p = m.predict_proba(Xf(te))[:, 1]
        b0 = br(np.full(len(te), tr[y].mean()), te[y].values)
        cal = pd.DataFrame({'p': p, 'y': te[y].values}); cal['b'] = pd.cut(cal.p, [0, .1, .25, .5, .75, .9, 1])
        cc = cal.groupby('b', observed=True).agg(pr=('p', 'mean'), ac=('y', 'mean')).mul(100).round(0)
        print(f'{L:4s} {y}: Brier {b0:.4f} → {br(p, te[y].values):.4f}  calib ' + ' · '.join(f'{int(r.pr)}→{int(r.ac)}' for r in cc.itertuples()))
        mf = LogisticRegression(C=1e4).fit(Xf(q), q[y]); coef[f'{L}_{y}'] = [round(mf.intercept_[0], 4), round(mf.coef_[0][0], 4), round(mf.coef_[0][1], 4)]
json.dump(coef, open('reach_coef.json', 'w')); print(coef)
