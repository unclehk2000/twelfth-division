import numpy as np, pandas as pd
from split import clus, wkof
Z = pd.read_pickle('zones_var.pkl'); Q = pd.read_pickle('ctl_var.pkl')
exec(open('analyze1.py').read().split('Z = add(Z)')[0].split("Z['key']")[1].join(['', '']) if False else '')
def add(o):
    o = o.copy()
    o['T20'] = ((o.tT >= 0) & (o.tT - o.t0 <= 20)).astype(float)
    o['hold10'] = np.where(o.tT >= 0, ~((o.tX >= 0) & (o.tX - o.tT <= 10)), np.nan).astype(float)
    return o
Z = add(Z); Q = add(Q)
q = Q.groupby('of')[['T20', 'hold10', 'bounce']].mean()
Z = Z.join(q, rsuffix='_c')
for (v, k), g in Z.groupby(['var', 'kind']):
    s = []
    for m in ['T20', 'hold10', 'bounce']:
        mm, se, t, n = clus(g[m] - g[m + '_c'], wkof(g.date))
        sy = ''.join('+' if (gg[m] - gg[m + '_c']).mean() > 0 else '−' for _, gg in g.groupby('sym'))
        pe = ''.join('+' if (gg[m] - gg[m + '_c']).mean() > 0 else '−' for _, gg in g.groupby(g.yr >= 2025))
        s.append(f"{m} {g[m].mean():.3f}/{g[m+'_c'].mean():.3f} {mm:+.3f} t{t:+.1f} {sy} {pe}")
    print(f"{v:4s} {k:3s} n{len(g):5d} w {g.w.median():.2f} | " + ' | '.join(s))
# WIDE: zones that exist only under one setting
W = Z[Z['var'] == 'WIDE']
S = Z[Z['var'] == 'SET']; L = Z[Z['var'] == 'LST']
key = lambda d: set(zip(d.sym, d.t0, d.dir, d.kind))
ks, kl = key(S), key(L)
W = W.copy(); W['both'] = [((a, b, c, d) in ks) and ((a, b, c, d) in kl) for a, b, c, d in zip(W.sym, W.t0, W.dir, W.kind)]
for (k, b), g in W.groupby(['kind', 'both']):
    s = []
    for m in ['hold10', 'bounce']:
        mm, se, t, n = clus(g[m] - g[m + '_c'], wkof(g.date))
        s.append(f"{m} {g[m].mean():.3f}/{g[m+'_c'].mean():.3f} {mm:+.3f} t{t:+.1f}")
    print(f"WIDE {k} {'in both settings' if b else 'one setting only':17s} n{len(g):4d} w {g.w.median():.3f} | " + ' | '.join(s) + f" | src {g.src.value_counts().to_dict()}")
Z.to_pickle('zones_var_j.pkl')
