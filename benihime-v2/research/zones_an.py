import sys, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude/gh2/stats-kit'); from stats_kit import check, table
Z = pd.read_pickle('zones.pkl'); Z['half'] = np.where(Z.tday.dt.year >= 2025, '25-26', '18-24')
z = Z[Z.hold.notna()].copy(); z['stk'] = z['stack'].clip(0, 3)
print(z.pivot_table(index='kind', columns='stk', values='hold', aggfunc='mean').round(3))
print(z.pivot_table(index='kind', columns='stk', values='hold', aggfunc='size'))
z['db'] = pd.cut(z.dist, [0, 0.5, 1, 2, 4, 99], labels=False)
z['tb'] = pd.cut(z.t, [0, 30, 90, 200, 405], labels=False)
z['stacked'] = (z['stack'] >= 1).astype(float); z['st2'] = (z['stack'] >= 2).astype(float)
z['date'] = z.tday; z = z.set_index('date')
re = z[z.real == 1]
rows = [check(z, 'hold ~ real + C(db) + C(tb)', 'real', test='gap levels vs placebo'),
        check(re, 'hold ~ stacked + C(kind) + C(db) + C(tb)', 'stacked', test='stacked (2+) vs single'),
        check(re, 'hold ~ st2 + C(kind) + C(db) + C(tb)', 'st2', test='3+ levels vs fewer'),
        check(z[z.real == 0], 'hold ~ stacked + C(db) + C(tb)', 'stacked', test='placebo near real levels')]
for k in ('edge', 'q', 'ce', 'sd1', 'sd2'):
    zz = z[(z.kind == k) | (z.real == 0)].assign(isk=lambda d: (d.kind == k).astype(float))
    rows.append(check(zz, 'hold ~ isk + C(db) + C(tb)', 'isk', test=f'{k} vs placebo'))
T = table(rows); print(T[['coef', 'p', 'n', '18-24', 'p_18-24', '25-26', 'p_25-26', 'ES', 'NQ', 'RTY', 'ok']].to_string())
print('base hold rate real', re.hold.mean().round(3), 'placebo', z[z.real == 0].hold.mean().round(3))
