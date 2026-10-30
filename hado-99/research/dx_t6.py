"""DX futures 5-minute vs index 5-minute (2023 – Aug 2026): contemporaneous link and lead-lag, by session and regime."""
import sys; sys.path.insert(0, '/home/claude/xa')
import pandas as pd, numpy as np
from tests import check, table
M = pd.read_pickle('/home/claude/xa/dx_5m.pkl').set_index('ts')
# DX bars are labelled by their start; 5-minute close-to-close return, same contract
M['rd'] = np.log(M.Close).diff().where(M.Contract == M.Contract.shift()) * 1e4
P = pd.read_pickle('/home/claude/xa/P_dx.pkl')
reg = P[P.sym == 'ES'][['dUp', 'dAbove', 'shock_l']]
out = []
for S in ('NQ', 'ES', 'RTY'):
    B = pd.read_pickle(f'/home/claude/kyw/bars_{S}_all.pkl')
    B = B[(B.ts >= '2023-01-02') & (B.ts <= '2026-08-28')].set_index('ts')
    b = B.Close.resample('5min', label='left', closed='left').last()
    c = B.Contract.resample('5min', label='left', closed='left').last()
    td = B.tday.resample('5min', label='left', closed='left').last()
    I = pd.DataFrame({'ci': b, 'ctr': c, 'tday': td}).dropna()
    I['ri'] = np.log(I.ci).diff().where((I.ctr == I.ctr.shift()) & (I.tday == I.tday.shift())) * 1e4
    J = I.join(M[['rd']], how='inner').dropna(subset=['ri', 'rd'])
    J['ri_f1'] = J.ri.shift(-1).where(J.tday.shift(-1) == J.tday)
    J['ri_f3'] = J.ri.rolling(3).sum().shift(-3).where(J.tday.shift(-3) == J.tday)
    J['rd_f1'] = J.rd.shift(-1).where(J.tday.shift(-1) == J.tday)
    J['sym'] = S
    out.append(J)
J = pd.concat(out)
J = J.join(reg, on='tday')
J['hm'] = J.index.hour * 100 + J.index.minute
J['rth'] = ((J.hm >= 930) & (J.hm < 1600)).astype(int)
J['half'] = np.where(J.index < '2025-01-01', '18-24', '25-26')
print('rows', len(J), 'corr same 5m', round(J.ri.corr(J.rd), 3), 'RTH', round(J[J.rth == 1].ri.corr(J[J.rth == 1].rd), 3))
for k in (-2, -1, 1, 2, 3):
    print('corr(DX_t, index_t+%d)' % k, round(J.rd.corr(J.groupby(['sym', 'tday']).ri.shift(-k)), 4))
rows = [dict(test='index next 5m ~ DX 5m', **check(J.dropna(subset=['ri_f1']), 'ri_f1 ~ rd', 'rd')),
        dict(test='index next 15m ~ DX 5m', **check(J.dropna(subset=['ri_f3']), 'ri_f3 ~ rd', 'rd')),
        dict(test='DX next 5m ~ index 5m', **check(J.dropna(subset=['rd_f1']), 'rd_f1 ~ ri', 'ri'))]
big = J[J.rd.abs() > 4 * J.rd.std()]
rows.append(dict(test='index next 15m ~ DX 5m | |DX| > 4σ', **check(big.dropna(subset=['ri_f3']), 'ri_f3 ~ rd', 'rd')))
r = J[J.rth == 1]
rows.append(dict(test='RTH: index next 15m ~ DX 5m', **check(r.dropna(subset=['ri_f3']), 'ri_f3 ~ rd', 'rd')))
print(table(rows).round(4).to_string())
