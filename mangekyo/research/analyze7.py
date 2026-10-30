"""ICT's body rule on the touch day, and inversion: after a close beyond the far edge, the zone flips; its next touch from
the other side."""
import numpy as np, pandas as pd
from split import show, clus, wkof
from data import daily
from gaps import lifecycle
Z = pd.read_pickle('zones.pkl'); Q = pd.read_pickle('ctl.pkl')
for o in (Z, Q):
    o['hold10'] = np.where(o.tT >= 0, ~((o.tX >= 0) & (o.tX - o.tT <= 10)), np.nan).astype(float)
    o['bp'] = pd.cut(o.bodyPos, [-99, 0, 0.5, 1.0, 99], labels=['closed back outside', 'near half (CE held)', 'far half (past CE)', 'closed beyond'])
F = Z[Z.kind == 'FVG']
print('hold10 after the touch day, by where the touch day closed (FVG, real; controls in brackets)')
for b in ['closed back outside', 'near half (CE held)', 'far half (past CE)']:
    g = F[F.bp == b]; c = Q[Q.bp == b]
    # survive the next 10 days excluding the touch day itself
    hz = (~((g.tX >= 0) & (g.tX - g.tT <= 10))).mean(); hc = (~((c.tX >= 0) & (c.tX - c.tT <= 10))).mean()
    bz = g.bounce.mean(); bc = c.bounce.mean()
    print(f"  {b:22s} real n {len(g):5d} hold10 {hz:.3f} bounce {bz:.3f} | ctl n {len(c):5d} hold10 {hc:.3f} bounce {bc:.3f}")
# inversion
def inv(z, D):
    O, H, L, C, A = D.bo.values, D.bh.values, D.bl.values, D.bc.values, D.atrB.values
    g = z[z.tX >= 0].copy()
    g2 = pd.DataFrame({'t0': g.tX.values, 'dir': -g.dir.values, 'kind': g.kind.values, 'top': g.top.values, 'bot': g.bot.values, 't1': g.t0.values}, index=g.index)
    return lifecycle(g2, O, H, L, C, A)
R = []; RC = []
for s in ['NQ', 'ES', 'RTY', 'YM']:
    D = daily(s)
    a = inv(F[F.sym == s], D); a['sym'] = s; a['date'] = D.index[a.t0.values]; R.append(a)
    c = inv(Q[Q.sym == s], D); c['sym'] = s; c['of'] = Q[Q.sym == s].loc[c.index, 'of'] if len(c) else []; RC.append(c)
R = pd.concat(R); RC = pd.concat(RC)
for o in (R, RC):
    o['inside'] = np.where(o.tT >= 0, o.deep <= 1, np.nan).astype(float)
    o['hold10'] = np.where(o.tT >= 0, ~((o.tX >= 0) & (o.tX - o.tT <= 10)), np.nan).astype(float)
    o['T20'] = ((o.tT >= 0) & (o.tT - o.t0 <= 20)).astype(float)
q = RC.groupby('of')[['inside', 'hold10', 'bounce', 'T20']].mean()
R = R.join(q, rsuffix='_c'); R['yr'] = R.date.dt.year
print('inverted FVGs (after a close beyond): retest within 20 days, then the touch day and the next 10')
for v in ['T20', 'inside', 'hold10', 'bounce']:
    g = R[R[v].notna() & R[v + '_c'].notna()]
    m, se, t, n = clus(g[v] - g[v + '_c'], wkof(g.date))
    sy = ''.join('+' if (gg[v] - gg[v + '_c']).mean() > 0 else '−' for _, gg in g.groupby('sym'))
    print(f"  {v:7s} n {n:5d} real {g[v].mean():.3f} ctl {g[v+'_c'].mean():.3f} diff {m:+.3f} t {t:+.1f} {sy}")
