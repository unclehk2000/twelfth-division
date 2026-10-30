import sys, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude/gh2/stats-kit'); from stats_kit import check, table
D = pd.read_pickle('fw.pkl'); D['date'] = D.wk; D = D.set_index('date')
D['rr'] = D.aR / D.awr
cols = ['coef', 'p', 'n', '18-24', 'p_18-24', '25-26', 'p_25-26', 'ES', 'NQ', 'RTY', 'ok']
# A. reach by Friday (from Monday 09:30)
print('reached by Fri 17:00, all weeks:')
print(pd.Series({f: D[f'h{f}'].mean() for f in (-1.0, -0.5, 0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0)}).round(3).to_dict())
print('mirror placebo:', pd.Series({f: D[f'p{f}'].mean() for f in (-1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0)}).round(3).to_dict())
D['rb'] = pd.qcut(D.rr, 4, labels=['Q1', 'Q2', 'Q3', 'Q4'])
print(D.groupby('rb')[['rr', 'h1.0', 'h0.5', 'h1.5', 'h-0.5', 'h2.0', 'h-1.0']].mean().round(3).to_string())
print('both SDs', (D['h1.5'] & D['h-0.5']).mean().round(3), 'neither', (~D['h1.5'] & ~D['h-0.5']).mean().round(3))
print('close inside 0..1', ((D.xC >= 0) & (D.xC <= 1)).mean().round(3), ' inside -0.5..1.5', ((D.xC >= -0.5) & (D.xC <= 1.5)).mean().round(3))
# B. magnet: real vs mirror (same distance from Monday 09:30, other side), paired
rows = []
for f in (-0.5, 0.0, 0.5, 1.0, 1.5):
    L = pd.concat([D.assign(y=D[f'h{f}'].astype(float), real=1.0), D.assign(y=D[f'p{f}'].astype(float), real=0.0)])
    rows.append(check(L, 'y ~ real', 'real', test=f'level {f} reached vs mirror'))
L = pd.concat([D.assign(y=D[f'h{f}'].astype(float), real=1.0, f=f) for f in (-0.5, 0.0, 0.5, 1.0, 1.5)] +
              [D.assign(y=D[f'p{f}'].astype(float), real=0.0, f=f) for f in (-0.5, 0.0, 0.5, 1.0, 1.5)])
rows.append(check(L, 'y ~ real + C(f)', 'real', test='key levels pooled vs mirror'))
print(table(rows)[cols].to_string())
# C. first-touch hold vs random levels in the same span
Z = pd.read_pickle('fz.pkl'); Z['date'] = Z.wk; Z = Z.set_index('date')
Z['db'] = pd.cut(Z.dist, [0, 0.05, 0.1, 0.25, 0.5, 99], labels=False)
print(Z.assign(k=Z.f.fillna(9)).groupby('k').hold.agg(['mean', 'size']).round(3).T.to_string())
rows = [check(Z, 'hold ~ real + C(db)', 'real', test='all fib eighths vs random')]
for f in (-0.5, 0.0, 0.5, 1.0, 1.5):
    zz = Z[(Z.f == f) | (Z.real == 0)].assign(isk=lambda d: (d.f == f).astype(float))
    rows.append(check(zz, 'hold ~ isk + C(db)', 'isk', test=f'level {f} hold vs random'))
print(table(rows)[cols].to_string())
# D. weekly extremes on the grid: distance to the nearest eighth (0 .. 0.5), real grid vs a randomly shifted grid
E = pd.concat([D.assign(x=D.xH, d8=D.d8H, q8=D.q8H, side='H'), D.assign(x=D.xL, d8=D.d8L, q8=D.q8L, side='L')])
E = E[(E.x >= -1.5) & (E.x <= 2.5) & (E.rr >= 0.1)]
P = pd.concat([E.assign(y=E.d8, real=1.0), E.assign(y=E.q8, real=0.0)])
print('extremes near an eighth: mean distance real', E.d8.mean().round(4), 'shifted', E.q8.mean().round(4), 'n', len(E))
print(table([check(P, 'y ~ real', 'real', test='extremes closer to the grid than shifted grid')])[cols].to_string())
# E. where the week's extremes land on the fib
for nm in ('xH', 'xL'):
    print(nm, D[nm].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round(2).tolist())
