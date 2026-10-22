import sys, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude/gh2/stats-kit')
from stats_kit import check, table
D = pd.read_pickle('feat.pkl')
D = D[D.ratio.notna()].copy()
D['date'] = D.tday
D = D.set_index('date')
for c in ('fill_rth', 'ce_rth', 'o1_rth', 'c1_rth', 'fill_w5', 'ce_w5'):
    D[c] = D[c].astype(float)
for c in ('out_pdr', 'on_thru', 'pd_with', 'f15_hit', 'f15_ce'):
    D[c] = D[c].astype(float)
up = np.where(D.up, 1, -1)
# overnight excursion past the prior close, against the gap, in gap units (0 = never got back to the close)
D['on_loc'] = D.on_loc.clip(0, 1.5)
D['f15_avg'] = (D.f15_away * D.g / D.avg20).clip(-3, 3)          # first 15-min move in average-gap units, + = away
D['pd_cloc'] = D.pd_cloc
D['dx_ag'] = (D.dx_z > 0.5).astype(float)
D['dx_z_c'] = D.dx_z.clip(-3, 3)
D['mon'] = (D.dow == 0).astype(float)
ctl = ' + C(bk) + lr'
rows = []
for y in ('fill_rth', 'ce_rth'):
    for x in ('out_pdr', 'on_loc', 'pd_with', 'pd_cloc', 'mon'):
        rows.append(check(D, f'{y} ~ {x}{ctl}', x, test=f'{y}: {x}'))
dd = D[D.dx_z.notna()]
for y in ('fill_rth', 'ce_rth'):
    for x in ('dx_z_c', 'dx_ag'):
        rows.append(check(dd, f'{y} ~ {x}{ctl}', x, test=f'{y}: {x} (2023-26)'))
# first 15 minutes: gaps not filled by 09:45
u = D[D.f15_hit == 0]
for x in ('f15_avg', 'f15_ce'):
    rows.append(check(u, f'fill_rth ~ {x}{ctl}', x, test=f'fill after 09:45: {x}'))
u2 = D[D.f15_ce == 0]
rows.append(check(u2, f'ce_rth ~ f15_avg{ctl}', 'f15_avg', test='CE after 09:45: f15_avg'))
pd.set_option('display.width', 250)
T = table(rows)
print(T[['coef', 'p', 'n', '18-24', 'p_18-24', '25-26', 'p_25-26', 'ES', 'NQ', 'RTY', 'ok']].to_string())
