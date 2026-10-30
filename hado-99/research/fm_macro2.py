import numpy as np, pandas as pd
from tests import check, table, cfit
pd.set_option('display.width', 220)
E = pd.read_pickle('fm/E15_macro.pkl')
P = pd.read_pickle('P_rng.pkl')[['sym', 'reg']].reset_index()
E = E.reset_index().merge(P, on=['date', 'sym'], how='left').set_index('date')
rows = []
for y in ('take2', 'hold3'):
    for g in ('weak', 'strong'):
        G = E[E.reg == g]
        r = check(G, f'{y} ~ w + a + C(q)', 'w'); r['test'] = f'{y} with, {g} $ (n {len(G)})'; rows.append(r)
    r = check(E, f'{y} ~ w + a + C(q)', 'w'); r['test'] = f'{y} with, all'; rows.append(r)
T = pd.DataFrame(rows).set_index('test')
print(T[['coef', 'p', '23-24', 'p_23-24', '25-26', 'p_25-26', 'NQ', 'ES', 'RTY', 'ok']].round(4).to_string())
print(E.reg.value_counts(normalize=True).round(3).to_dict())
