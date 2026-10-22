import sys, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude/gh2/stats-kit'); from stats_kit import check, table
D = pd.read_pickle('or2.pkl').sort_values(['sym', 'tday'])
D['pctl'] = D.groupby('sym').or_atr.transform(lambda s: s.rolling(250, min_periods=100).apply(lambda w: (w[:-1] < w[-1]).mean(), raw=True))
K = D[['sym', 'tday', 'th', 'tl', 'pctl', 'loc959', 'or_atr']]
wide = {s: K[K.sym == s].drop(columns='sym').set_index('tday').add_suffix('_' + s) for s in ('NQ', 'ES', 'RTY')}
Wd = wide['NQ'].join(wide['ES'], how='inner').join(wide['RTY'], how='inner')
print('days with all three', len(Wd))
X = D[D.bs != 0].join(Wd, on='tday', how='inner')
def sisters(r, f):
    return [s for s in ('NQ', 'ES', 'RTY') if s != r]
nc, nc5, sp, sl = [], [], [], []
for r in X.itertuples():
    sis = [s for s in ('NQ', 'ES', 'RTY') if s != r.sym]
    key = 'th' if r.bs == 1 else 'tl'
    v = [getattr(r, f'{key}_{s}') for s in sis]
    nc.append(sum(1 for x in v if x == x and x <= r.tbrk)); nc5.append(sum(1 for x in v if x == x and x <= r.tbrk + 5))
    sp.append(np.nanmean([getattr(r, f'pctl_{s}') for s in sis])); sl.append(np.nanmean([getattr(r, f'loc959_{s}') for s in sis]))
X['nconf'] = nc; X['nconf5'] = nc5; X['sis_pctl'] = sp; X['sis_loc'] = sl
X['rel_pctl'] = X.pctl - X.sis_pctl
X['lor'] = np.log(X.or_atr); X['tb'] = pd.cut(X.tbrk, [0, 35, 45, 60, 120, 999], labels=False)
for c in ('fail', 'x1', 'cl_b'):
    X[c] = X[c].astype(float)
X['date'] = X.tday; X = X.set_index('date')
print(X.groupby('nconf').agg(n=('fail', 'size'), fail=('fail', 'mean'), x1=('x1', 'mean'), cl=('cl_b', 'mean')).round(3))
print(X.groupby('nconf5').agg(n=('fail', 'size'), fail=('fail', 'mean'), x1=('x1', 'mean'), cl=('cl_b', 'mean')).round(3))
X['c0'] = (X.nconf == 0).astype(float)
ctl = ' + lor + C(tb)'
rows = [check(X, f'fail ~ nconf{ctl}', 'nconf', test='fail | sisters already broken (0-2)'),
        check(X, f'x1 ~ nconf{ctl}', 'nconf', test='ext 1x | sisters already broken'),
        check(X, f'cl_b ~ nconf{ctl}', 'nconf', test='close beyond | sisters already broken'),
        check(X, f'fail ~ c0{ctl}', 'c0', test='fail | lone break (0 sisters)'),
        check(X, f'fail ~ nconf5{ctl}', 'nconf5', test='fail | sisters within 5 min'),
        check(X, f'cl_b ~ nconf5{ctl}', 'nconf5', test='close beyond | sisters within 5 min'),
        check(X, f'x1 ~ nconf5{ctl}', 'nconf5', test='ext 1x | sisters within 5 min'),
        check(X.dropna(subset=['rel_pctl']), f'x1 ~ rel_pctl{ctl}', 'rel_pctl', test='ext 1x | OR pctl vs sisters'),
        check(X.dropna(subset=['rel_pctl']), f'fail ~ rel_pctl{ctl}', 'rel_pctl', test='fail | OR pctl vs sisters')]
T = table(rows); print(T[['coef', 'p', 'n', '18-24', 'p_18-24', '25-26', 'p_25-26', 'ES', 'NQ', 'RTY', 'ok']].to_string())
X.to_pickle('or3.pkl'); Wd.to_pickle('wide.pkl'); D.to_pickle('or2p.pkl')
