import sys, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude/gh2/stats-kit'); from stats_kit import check, table
X = pd.read_pickle('or3.pkl')
X['up1'] = (X.bs == 1).astype(float)
X['cup'] = (X.c1614 > X.o930).astype(float)
X['dl'] = X.sis_loc - X.loc959
X['l'] = X.loc959 - 0.5; X['sl'] = X.sis_loc - 0.5
print(X.groupby(pd.cut(X.loc959, [-.01, .25, .5, .75, 1.01])).up1.agg(['mean', 'size']).round(3))
rows = [check(X, 'up1 ~ l', 'l', test='first break up | own 10:00 location'),
        check(X, 'up1 ~ l + sl', 'sl', test='first break up | sisters\' location'),
        check(X, 'up1 ~ l + dl', 'dl', test='first break up | sisters minus own'),
        check(X, 'cup ~ l', 'l', test='RTH close > open | own location'),
        check(X, 'cl_b ~ l', 'l', test='close beyond | own location')]
T = table(rows); print(T[['coef', 'p', 'n', '18-24', 'p_18-24', '25-26', 'p_25-26', 'ES', 'NQ', 'RTY', 'ok']].to_string())
# midnight / 18:00 open: RTH touch vs placebo (same distance from the 09:30 open, other side)
D = pd.read_pickle('or2.pkl')
for nm in ('mid00', 'o18'):
    d = D.dropna(subset=[nm + '_hit']).copy()
    print(nm, 'hit', d[nm + '_hit'].mean().round(3), 'placebo', d[nm + '_plc'].mean().round(3), 'n', len(d))
    print(d.groupby(['sym', 'half'])[[nm + '_hit', nm + '_plc']].mean().round(3).to_string())
    # paired: by date clusters
    d['date'] = d.tday; d = d.set_index('date')
    L = pd.concat([d.assign(y=d[nm + '_hit'].astype(float), real=1.0), d.assign(y=d[nm + '_plc'].astype(float), real=0.0)])
    L['ld'] = np.log(L[nm + '_dist'] / L.atr10 + 1e-6)
    T = table([check(L, 'y ~ real + ld', 'real', test=f'{nm}: real vs placebo')]); print(T[['coef', 'p', '18-24', 'p_18-24', '25-26', 'p_25-26', 'ES', 'NQ', 'RTY', 'ok']].to_string())
