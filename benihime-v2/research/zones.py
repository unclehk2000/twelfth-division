"""Confluence test. Each RTH day, the staircase = the last 5 RTH gaps (today's included). Levels per gap: the edges,
quarters (25 / 50 / 75%) and ±1 / ±2 SD. A level is 'stacked' when a level of a DIFFERENT gap lies within
tol = 0.10 × the 20-session average gap. Placebo: each real level shifted by u × avg gap, u ~ U(-1, 1).
First RTH touch after 09:31 (levels inside the 09:30 bar's range skipped). Hold = price moves R = 0.5 × avg gap back
the way it came before it moves R through the level, by 16:14 (else 'none'). Writes zones.pkl"""
import numpy as np, pandas as pd
rng = np.random.default_rng(7)
R = pd.read_pickle('feat.pkl'); R = R[R.ratio.notna()]
rows = []
for sym in ('NQ', 'ES', 'RTY'):
    b = pd.read_pickle(f'/home/claude/kyw/bars_{sym}_all.pkl')[['High', 'Low', 'Close', 'tday', 'hm']].reset_index(drop=True)
    H, L, C = b.High.to_numpy(), b.Low.to_numpy(), b.Close.to_numpy(); hm = b.hm.to_numpy(); td = b.tday.to_numpy()
    i930 = np.flatnonzero(hm == 930); first = pd.Series(i930, index=td[i930]); first = first[~first.index.duplicated()]
    g = R[R.sym == sym].sort_values('tday').reset_index(drop=True)
    for k in range(4, len(g)):
        d = g.loc[k, 'tday']
        if d not in first.index:
            continue
        io = first[d]
        if io + 405 > len(H) or td[io + 404] != d:
            continue
        a = g.loc[k, 'avg20']; tol = 0.10 * a; Rr = 0.5 * a
        lv = []
        for j in range(k - 4, k + 1):
            pc, op, gg = g.loc[j, 'pc'], g.loc[j, 'op'], g.loc[j, 'g']
            top, bot = max(pc, op), min(pc, op)
            for nm, x in (('edge', top), ('edge', bot), ('q', bot + 0.25 * gg), ('ce', bot + 0.5 * gg), ('q', bot + 0.75 * gg),
                          ('sd1', top + gg), ('sd1', bot - gg), ('sd2', top + 2 * gg), ('sd2', bot - 2 * gg)):
                lv.append((j, nm, x))
        X = np.array([x for _, _, x in lv]); J = np.array([j for j, _, _ in lv])
        h, l, c = H[io:io + 405], L[io:io + 405], C[io:io + 405]
        op0 = c[0]
        def test(x):
            if l[0] <= x <= h[0]:
                return None
            m = (l[1:] <= x) & (h[1:] >= x)
            if not m.any():
                return None
            t = int(np.argmax(m)) + 1
            above = c[t - 1] > x                    # came down to it
            hh, ll = h[t:], l[t:]
            if above:
                b1 = np.flatnonzero(hh >= x + Rr); b2 = np.flatnonzero(ll <= x - Rr)
            else:
                b1 = np.flatnonzero(ll <= x - Rr); b2 = np.flatnonzero(hh >= x + Rr)
            i1 = b1[0] if len(b1) else 10 ** 6; i2 = b2[0] if len(b2) else 10 ** 6
            res = np.nan if i1 == i2 == 10 ** 6 else float(i1 < i2) if i1 != i2 else np.nan
            return t, res
        for (j, nm, x) in lv:
            st = int(((np.abs(X - x) <= tol) & (J != j)).sum())
            r = test(x)
            if r is not None:
                rows.append(dict(sym=sym, tday=d, kind=nm, own=(j == k), stack=st, real=1, t=r[0], hold=r[1], dist=abs(x - op0) / a))
            xp = x + rng.uniform(-1, 1) * a
            r = test(xp)
            if r is not None:
                stp = int((np.abs(X - xp) <= tol).sum())
                rows.append(dict(sym=sym, tday=d, kind='placebo', own=False, stack=stp, real=0, t=r[0], hold=r[1], dist=abs(xp - op0) / a))
Z = pd.DataFrame(rows); Z.to_pickle('zones.pkl')
Z['half'] = np.where(Z.tday.dt.year >= 2025, '25-26', '18-24')
z = Z[Z.hold.notna()]
print(len(Z), len(z))
z['stk'] = z.stack.clip(0, 3)
print(z.pivot_table(index='kind', columns='stk', values='hold', aggfunc='mean').round(3))
print(z.pivot_table(index='kind', columns='stk', values='hold', aggfunc='size'))
