"""T2: does CL's move lead the index? CL settle-to-settle return (day t, to 14:30 ET) against
(a) the index's 14:30→16:00 on the same day, (b) the next session's overnight (16:00→09:30) and RTH (09:30→16:00),
(c) the next 5 sessions (14:30→14:30). Pooled, normal regime and shock regime."""
import sys; sys.path.insert(0, '/home/claude/xa')
import pandas as pd, numpy as np
from tests import check, table
P = pd.read_pickle('/home/claude/xa/P_cl.pkl')
g = P.groupby('sym')
same = lambda a, b: P[a + '_c'] == P[b + '_c']
P['a_1430_1600'] = np.log(P.p1600 / P.p1430).where(same('p1600', 'p1430')) * 100
P['rth'] = np.log(P.p1600 / P.o0930).where(P.p1600_c == P.o0930_c) * 100
P['on'] = np.log(P.o0930 / g.p1600.shift(1)).where(P.o0930_c == g.p1600_c.shift(1)) * 100
g = P.groupby('sym')
P['n_rth'] = g.rth.shift(-1)
P['n_on'] = g.on.shift(-1)
P['n5'] = g.rI.transform(lambda s: s[::-1].rolling(5).sum()[::-1].shift(-1)) * 100
P['shockN'] = 1 - P.shock
rows = []
for y in ('a_1430_1600', 'n_on', 'n_rth', 'n5'):
    rows.append(dict(test=f'{y} ~ x', **check(P, f'{y} ~ x', 'x')))
    rows.append(dict(test=f'{y} ~ x × shock', **check(P, f'{y} ~ x * shock', 'x:shock')))
    d = P[P.shock == 1]
    if len(d) > 100:
        rows.append(dict(test=f'{y} ~ x | shock only', **check(d, f'{y} ~ x', 'x')))
print(table(rows).round(3).to_string())
P.to_pickle('/home/claude/xa/P_cl.pkl')
