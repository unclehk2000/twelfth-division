import sys, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude/gh2/stats-kit')
from stats_kit import check, table
P = pd.read_pickle('path.pkl'); P['date'] = P.tday; P = P.set_index('date')
P['distc'] = P.dist.clip(0, 3); P['retrc'] = P.retr.clip(0, 1)
P['onl'] = P.on_loc.clip(0, 1.5)
P['ce_hit'] = (P.retr >= 0.5).astype(float)
ctl = ' + C(bk) + lr + C(ck)'
rows = [check(P, f'fill ~ distc{ctl}', 'distc', test='live fill: distance now'),
        check(P, f'fill ~ distc + retrc{ctl}', 'retrc', test='live fill: retracement so far | dist'),
        check(P, f'fill ~ distc + ce_hit{ctl}', 'ce_hit', test='live fill: CE touched | dist'),
        check(P, f'fill ~ distc + onl{ctl}', 'onl', test='live fill: ON location | dist'),
        check(P, f'fill ~ distc{ctl}', 'distc', test='live fill: distance (strict)', period_p=0.10)]
T = table(rows); print(T[['coef', 'p', 'n', '18-24', 'p_18-24', '25-26', 'p_25-26', 'ES', 'NQ', 'RTY', 'ok']].to_string())
# how much does distance add over size+time? compare out-of-sample Brier, fit 18-24, test 25-26 (logit)
import statsmodels.formula.api as smf
tr, te = P[P.half == '18-24'], P[P.half == '25-26']
for f in ('fill ~ C(bk):C(ck)', 'fill ~ C(bk) + lr + C(ck)', 'fill ~ C(ck) + lr + distc', 'fill ~ C(ck) + lr + distc + onl', 'fill ~ C(ck) * distc + lr'):
    m = smf.logit(f, tr).fit(disp=0); p = m.predict(te)
    print(f'{f:40s} Brier OOS {np.mean((p - te.fill) ** 2):.4f}  logloss {-np.mean(te.fill*np.log(p)+(1-te.fill)*np.log(1-p)):.4f}')
