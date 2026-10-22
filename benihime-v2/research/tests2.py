import sys, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude/gh2/stats-kit')
from stats_kit import check, table
D = pd.read_pickle('feat.pkl'); D = D[D.ratio.notna()].copy(); D['date'] = D.tday; D = D.set_index('date')
for c in ('fill_rth', 'ce_rth', 'o1_rth', 'c1_rth', 'out_pdr'):
    D[c] = D[c].astype(float)
D['on_loc'] = D.on_loc.clip(0, 1.5)
D['ont'] = pd.cut(D.on_loc, [-1, 0.5, 0.85, 9], labels=['<0.5', '0.5-0.85', '>=0.85'])
ctl = ' + C(bk) + lr'
rows = [check(D, f'fill_rth ~ on_loc + out_pdr{ctl}', 'on_loc', test='fill: on_loc | out_pdr'),
        check(D, f'fill_rth ~ on_loc + out_pdr{ctl}', 'out_pdr', test='fill: out_pdr | on_loc'),
        check(D, f'fill_rth ~ on_loc{ctl}', 'on_loc', test='fill: on_loc strict', period_p=0.10),
        check(D, f'ce_rth ~ on_loc{ctl}', 'on_loc', test='ce: on_loc strict', period_p=0.10),
        check(D, f'o1_rth ~ on_loc{ctl}', 'on_loc', test='-1SD: on_loc'),
        check(D, f'c1_rth ~ on_loc{ctl}', 'on_loc', test='+1SD: on_loc')]
T = table(rows); print(T[['coef', 'p', 'n', '18-24', 'p_18-24', '25-26', 'p_25-26', 'ES', 'NQ', 'RTY', 'ok']].to_string())
print(D.ont.value_counts())
order = ['<0.5', '0.5', '0.5-1', '1-1.5', '1.5-2.5', '>=2.5']
print(D.bk.unique())
for y in ('fill_rth', 'ce_rth'):
    t = D.pivot_table(index='bk', columns='ont', values=y, aggfunc='mean') * 100
    n = D.pivot_table(index='bk', columns='ont', values=y, aggfunc='size')
    print(y); print(t.round(0)); print(n)
    # by half
    for h in ('18-24', '25-26'):
        print(h, (D[D.half == h].pivot_table(index='bk', columns='ont', values=y, aggfunc='mean') * 100).round(0).to_string())
