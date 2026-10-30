"""Fractal Model tests (linear probability models, errors clustered by date; ✓ = p < 0.05 pooled, same sign in
2018–24 and 2025–26 and on NQ, ES and RTY)."""
import sys; sys.path.insert(0, '/home/claude/xa')
import pandas as pd, numpy as np
from tests import check, table
HTF = sys.argv[1]
E = pd.concat([pd.read_pickle(f'/home/claude/xa/fm/E_{s}_{HTF}.pkl') for s in ('NQ', 'ES', 'RTY')])
E = E.set_index(pd.DatetimeIndex(E.tday))
E['half'] = np.where(E.index < '2025-01-01', '18-24', '25-26')
E['c2'] = (E.kind == 'C2').astype(int)
for c in ('take2', 'takeC1', 'hold3', 'eq3', 'take2_34', 'hold34', 'cisd_in_c2', 'cisd_any', 'ext_hold'):
    E[c] = E[c].astype(float)
for c in ('p1', 'p2', 'p2.5', 'p4', 'p4.5'):
    if c in E: E[c.replace('.', '_')] = E[c].astype(float)
print('rates by kind (pooled):')
print(E.groupby('kind')[['take2', 'take2_34', 'takeC1', 'hold3', 'hold34', 'eq3']].mean().mul(100).round(1).to_string())
print(E.groupby(['kind', 'half'])[['take2', 'hold3']].mean().mul(100).round(1).unstack().to_string())
print(E.groupby(['kind', 'sym'])[['take2', 'hold3']].mean().mul(100).round(1).unstack().to_string())
rows = []
NB = E[E.kind != 'fail']
rows.append(dict(test='C3 takes C2 extreme: C2 vs other candles', **check(NB, 'take2 ~ c2', 'c2')))
rows.append(dict(test='C3/C4 take C2 extreme: C2 vs other', **check(NB.dropna(subset=['take2_34']), 'take2_34 ~ c2', 'c2')))
rows.append(dict(test='C2 extreme holds through C3: C2 vs other', **check(NB, 'hold3 ~ c2', 'c2')))
rows.append(dict(test='C2 extreme holds C3+C4: C2 vs other', **check(NB.dropna(subset=['hold34']), 'hold34 ~ c2', 'c2')))
SW = E[E.kind != 'base']
rows.append(dict(test='C3 takes C2 extreme: closed back inside vs not', **check(SW, 'take2 ~ c2', 'c2')))
C2 = E[E.kind == 'C2'].copy()
C2['cisd'] = C2.cisd_in_c2.fillna(0)
rows.append(dict(test='C2: CISD by C2 close → C3 takes extreme', **check(C2, 'take2 ~ cisd', 'cisd')))
rows.append(dict(test='C2: CISD by C2 close → C2 holds C3', **check(C2, 'hold3 ~ cisd', 'cisd')))
rows.append(dict(test='C2: C3 retraces to C2 EQ → takes extreme', **check(C2, 'take2 ~ eq3', 'eq3')))
print(table(rows).round(3).to_string())
print('C2 with CISD by C2 close: %.1f%% of C2s' % (100 * C2.cisd.mean()))
print(C2.groupby('cisd')[['take2', 'take2_34', 'hold3', 'hold34']].mean().mul(100).round(1).to_string())
print('C2 and EQ retrace in C3:', C2.groupby('eq3')[['take2']].mean().mul(100).round(1).to_dict())
P = C2[C2.cisd_any == 1]
pc = [c for c in ('p1', 'p2', 'p2_5', 'p4', 'p4_5') if c in P]
print('projections hit (after CISD confirms, through C4):')
print(P[pc + ['ext_hold']].mean().mul(100).round(1).to_string())
print(P.groupby('half')[pc].mean().mul(100).round(1).to_string())
print(P.groupby('sym')[pc].mean().mul(100).round(1).to_string())
E.to_pickle(f'/home/claude/xa/fm/E_all_{HTF}.pkl')
# ── controls: close location (a C2 that closed high in its range is a strong candle anyway)
if 'clv' in E:
    E['clv'] = E.clv.astype(float)
    NB = E[E.kind != 'fail'].dropna(subset=['clv'])
    C2 = E[E.kind == 'C2'].dropna(subset=['clv']).copy()
    C2['cisd'] = C2.cisd_in_c2.fillna(0)
    rows = [dict(test='take extreme: C2 vs other | close location', **check(NB, 'take2 ~ c2 + clv', 'c2')),
            dict(test='C2 holds: C2 vs other | close location', **check(NB, 'hold3 ~ c2 + clv', 'c2')),
            dict(test='C2: CISD → take extreme | close location', **check(C2, 'take2 ~ cisd + clv', 'cisd')),
            dict(test='C2: CISD → holds | close location', **check(C2, 'hold3 ~ cisd + clv', 'cisd'))]
    print(table(rows).round(3).to_string())
    NB['q'] = pd.cut(NB.clv, [-0.01, 0.25, 0.5, 0.75, 1.01], labels=['0-25', '25-50', '50-75', '75-100'])
    print(NB.groupby(['q', 'kind'])[['take2', 'hold3']].mean().mul(100).round(1).unstack().to_string())
# ── the dollar / oil regime of the day
R = pd.read_pickle('/home/claude/xa/P_dx.pkl')
R = R[R.sym == 'ES'][['dAbove', 'shock_l']]
C2 = E[E.kind == 'C2'].join(R, how='left')
C2['reg'] = np.where(C2.shock_l == 1, 'shock', np.where(C2.dAbove == 1, 'strong $', 'weak $'))
C2['cisd'] = C2.cisd_in_c2.fillna(0)
print(C2.groupby(['reg', 'cisd'])[['take2', 'hold3']].agg(['mean', 'size']).round(3).to_string())
for v in ('shock_l', 'dAbove'):
    d = C2.dropna(subset=[v])
    print(table([dict(test=f'C2 take extreme × {v}', **check(d, f'take2 ~ {v}', v))]).round(3).to_string())
