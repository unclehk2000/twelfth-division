import sys, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude/gh2/stats-kit'); from stats_kit import check, table
exec(open('model.py').read().split("tr, te = P[P.half")[0])
Q = P[(P.retr < 0.5) & ((P.ce_min.isna()) | (P.ce_min >= P.ck))].copy(); Q['dce'] = (Q.dist - 0.5).clip(0, 3)
Q['date'] = Q.tday; Q = Q.set_index('date'); P2 = P.copy(); P2['date'] = P2.tday; P2 = P2.set_index('date')
ctl = ' + C(bk) + lr + C(ck)'
T = table([check(Q, f'ce ~ dce + onl{ctl}', 'dce', test='CE live: distance to CE'),
           check(Q, f'ce ~ dce + onl{ctl}', 'onl', test='CE live: ON location'),
           check(P2, f'fill ~ distc + retrc + onl{ctl}', 'distc', test='fill live: distance'),
           check(P2, f'fill ~ distc + retrc + onl{ctl}', 'retrc', test='fill live: retracement'),
           check(P2, f'fill ~ distc + retrc + onl{ctl}', 'onl', test='fill live: ON location')])
print(T[['coef', 'p', 'n', '18-24', 'p_18-24', '25-26', 'p_25-26', 'ES', 'NQ', 'RTY', 'ok']].to_string())
