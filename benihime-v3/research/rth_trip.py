# Triplet head (Zabimaru's sister idea, on the ORG): at each checkpoint, an unfilled gap's odds of filling by 16:14 from its own
# distance and time, and whether 0 / 1 / 2 sisters have already filled (CE likewise). Also: do the three gap the same way?
import numpy as np, pandas as pd
CPS = [30, 60, 90, 150, 210, 270, 330]          # minutes after 09:30: 10:00, 10:30, 11:00, 12:00, 13:00, 14:00, 15:00
per = {}
for sym in ('NQ', 'ES', 'RTY'):
    Z = np.load(f'/home/claude/coc/bars_{sym}.npz'); H, L, C = Z['H'], Z['L'], Z['C']
    D = pd.read_pickle(f'/home/claude/coc/days_{sym}.pkl')
    D = D[D.G.notna() & D.rth_ok & (D.G > 0) & D.avg20.notna()]
    out = {}
    for r in D.itertuples():
        a, z = r.i930, r.i1614
        lv = r.pc; ce = (r.op + r.pc) / 2
        if r.up: tf = np.flatnonzero(L[a:z + 1] <= lv); tc = np.flatnonzero(L[a:z + 1] <= ce)
        else: tf = np.flatnonzero(H[a:z + 1] >= lv); tc = np.flatnonzero(H[a:z + 1] >= ce)
        px = {m: C[a + m - 1] for m in CPS if a + m - 1 <= z}
        out[r.tday] = dict(up=r.up, G=r.G, gR=r.G / r.avg20, pc=r.pc, ce=ce, tf=tf[0] if len(tf) else 9999, tc=tc[0] if len(tc) else 9999, px=px)
    per[sym] = out
rows, agree = [], []
days = set(per['NQ']) & set(per['ES']) & set(per['RTY'])
for td in sorted(days):
    g = {s: per[s][td] for s in per}
    ups = [g[s]['up'] for s in g]
    for s in g:
        x = g[s]; sis = [t for t in g if t != s]
        agree.append((s, td, x['gR'], all(u == ups[0] for u in ups), x['up'] == g[sis[0]]['up'] or x['up'] == g[sis[1]]['up'], x['up'] == g[sis[0]]['up'] and x['up'] == g[sis[1]]['up'], x['tf'] < 9999))
        for m in CPS:
            if m not in x['px']: continue
            for tgt, key, lvl in (('fill', 'tf', x['pc']), ('ce', 'tc', x['ce'])):
                if x[key] < m: continue                      # already done before this checkpoint
                d = abs(x['px'][m] - lvl) / x['G']
                nsis = sum(g[t][key] < m for t in sis)
                rows.append((s, td, tgt, m, d, x['gR'], nsis, x[key] < 9999))
T = pd.DataFrame(rows, columns=['sym', 'tday', 'tgt', 'cp', 'd', 'gR', 'nsis', 'y'])
A = pd.DataFrame(agree, columns=['sym', 'tday', 'gR', 'all3', 'withone', 'withboth', 'fill'])
for X in (T, A): X['tday'] = pd.to_datetime(X.tday); X['half'] = np.where(X.tday.dt.year >= 2025, 'test', 'train')
T.to_pickle('rth_trip.pkl'); A.to_pickle('rth_agree.pkl'); print(len(T), len(A), A.all3.mean().round(3))
