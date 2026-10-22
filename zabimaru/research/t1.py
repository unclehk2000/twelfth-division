import sys, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude/gh2/stats-kit'); from stats_kit import check, table
D = pd.read_pickle('or.pkl'); D = D[D.atr10.notna()].copy()
D['ort'] = pd.qcut(D.or_atr, [0, 0.25, 0.5, 0.75, 1], labels=['Q1', 'Q2', 'Q3', 'Q4'])
print('or_atr quartile edges', D.or_atr.quantile([0.25, 0.5, 0.75]).round(3).tolist())
D['both'] = D.took_h & D.took_l
D['none'] = ~D.took_h & ~D.took_l
D['bs'] = np.where(D.side == 1, 1, np.where(D.side == -1, -1, 0))
D['ext_b'] = np.where(D.bs == 1, D.ext_h, np.where(D.bs == -1, D.ext_l, np.nan))       # extension on the first-broken side
D['ext_o'] = np.where(D.bs == 1, D.ext_l, np.where(D.bs == -1, D.ext_h, np.nan))       # on the other side (neg = not taken)
D['fail'] = np.where(D.bs != 0, D.both, np.nan)
D['x1'] = np.where(D.bs != 0, D.ext_b >= 1, np.nan)
D['x05'] = np.where(D.bs != 0, D.ext_b >= 0.5, np.nan)
D['cl_b'] = np.where(D.bs == 1, D.c1614 > D.orh, np.where(D.bs == -1, D.c1614 < D.orl, np.nan))
g = D.groupby('ort')
print(g.agg(n=('sym', 'size'), anyb=('none', lambda s: 1 - s.mean()), both=('both', 'mean'), fail=('fail', 'mean'), x05=('x05', 'mean'), x1=('x1', 'mean'), close_beyond=('cl_b', 'mean'), tbrk_med=('tbrk', 'median')).round(3))
print(D.groupby('sym').agg(anyb=('none', lambda s: 1 - s.mean()), both=('both', 'mean'), fail=('fail', 'mean'), x1=('x1', 'mean'), cl=('cl_b', 'mean')).round(3))
D['date'] = D.tday; X = D.set_index('date')
X['lor'] = np.log(X.or_atr); X['vu'] = X.vol_up.astype(float)
for c in ('both', 'fail', 'x1', 'x05', 'cl_b'):
    X[c] = X[c].astype(float)
B = X[X.bs != 0]
rows = [check(B, 'x1 ~ lor', 'lor', test='ext 1x | OR/ATR (log)'),
        check(B, 'fail ~ lor', 'lor', test='fail | OR/ATR'),
        check(B, 'cl_b ~ lor', 'lor', test='close beyond | OR/ATR'),
        check(X, 'lor ~ vu', 'vu', test='OR/ATR | vol rising'),
        check(X, 'lor ~ volr', 'volr', test='OR/ATR | ATR5/ATR10'),
        check(B, 'x1 ~ vu + lor', 'vu', test='ext 1x | vol rising'),
        check(B, 'fail ~ vu + lor', 'vu', test='fail | vol rising'),
        check(B, 'x1 ~ volr + lor', 'volr', test='ext 1x | ATR5/ATR10'),
        check(B, 'fail ~ volr + lor', 'volr', test='fail | ATR5/ATR10'),
        check(X.assign(dr=np.log((X.rthH - X.rthL) / X.atr10)), 'dr ~ volr', 'volr', test='RTH range/ATR | ATR5/ATR10'),
        check(X.assign(dr=np.log((X.rthH - X.rthL) / X.atr10)), 'dr ~ vu', 'vu', test='RTH range/ATR | vol rising'),
        check(X.assign(dr=np.log((X.rthH - X.rthL) / X.atr10)), 'dr ~ lor', 'lor', test='RTH range/ATR | OR/ATR')]
T = table(rows); print(T[['coef', 'p', 'n', '18-24', 'p_18-24', '25-26', 'p_25-26', 'ES', 'NQ', 'RTY', 'ok']].to_string())
D.to_pickle('or2.pkl')
