import numpy as np, pandas as pd, statsmodels.formula.api as smf, warnings, json
warnings.filterwarnings('ignore')
R = pd.read_pickle('feat.pkl'); R = R[R.ratio.notna()].copy()
R['onl'] = R.on_loc.clip(0, 1.2)
print('mean onl', R.onl.mean().round(3), R.groupby('bk').onl.mean().round(2).to_dict())
F = R[R.fill_rth.astype(bool)].copy(); F['o1'] = F.o1_rth.astype(float); F['lft'] = np.log1p(F.fill_min)
tr, te = F[F.half == '18-24'], F[F.half == '25-26']
for f in ('o1 ~ C(bk)', 'o1 ~ lr + lft', 'o1 ~ lr + lft + onl'):
    m = smf.logit(f, tr).fit(disp=0); p = m.predict(te); print(f'{f:25s} OOS Brier {np.mean((p - te.o1) ** 2):.4f}')
m = smf.logit('o1 ~ lr + lft + onl', F).fit(disp=0); print(m.params.round(3).to_dict())
c = json.load(open('coef.json')); c['after'] = {k: float(v) for k, v in m.params.items()}; json.dump(c, open('coef.json', 'w'), indent=1)
# sanity: model predictions vs table for typical cases
for lr in (np.log(0.3), 0, np.log(2)):
    for fm in (5, 45, 150):
        x = m.params; z = x.Intercept + x.lr * lr + x.lft * np.log1p(fm) + x.onl * 0.72
        print(f'ratio {np.exp(lr):.1f} fill at {fm:3d}m -> -1SD {100/(1+np.exp(-z)):.0f}%')
