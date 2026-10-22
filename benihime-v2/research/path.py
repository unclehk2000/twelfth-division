"""Live state of each unfilled gap at checkpoints after 09:30: distance now and retracement so far, in gap units.
dist  = (price now − prior close) oriented ÷ gap  (1 = at the open, 0.5 = at the CE, >1 = beyond the open)
retr  = deepest retracement toward the fill so far ÷ gap (0 = never came back, 0.5 = CE touched)
Writes path.pkl"""
import numpy as np, pandas as pd
R = pd.read_pickle('feat.pkl')
CK = [15, 30, 45, 60, 90, 120, 180, 240, 300, 360]
out = []
for sym in ('NQ', 'ES', 'RTY'):
    b = pd.read_pickle(f'/home/claude/kyw/bars_{sym}_all.pkl')[['High', 'Low', 'Close', 'tday', 'hm']].reset_index(drop=True)
    H, L, C = b.High.to_numpy(), b.Low.to_numpy(), b.Close.to_numpy()
    hm = b.hm.to_numpy(); td = b.tday.to_numpy()
    i930 = np.flatnonzero(hm == 930)
    first = pd.Series(i930, index=td[i930]); first = first[~first.index.duplicated()]
    for i, r in R[R.sym == sym].iterrows():
        if r.tday not in first.index:
            continue
        io = first[r.tday]
        s = 1 if r.up else -1
        n = 405
        seg = slice(io, io + n)
        if not (hm[io + n - 1] == 1614 or (io + n - 1 < len(hm) and td[io + n - 1] == r.tday)):
            continue
        h, l, c = H[seg], L[seg], C[seg]
        # oriented excursion toward the fill: for an up gap, lows
        tow = (r.op - l) / r.g if s == 1 else (h - r.op) / r.g     # 1 = reached the prior close
        retr = np.maximum.accumulate(tow)
        dist = s * (c - r.pc) / r.g
        fm = r.fill_min
        for m in CK:
            if not np.isnan(fm) and fm < m:
                continue
            out.append(dict(idx=i, ck=m, dist=dist[m - 1], retr=retr[m - 1], fill=float(not np.isnan(fm))))
P = pd.DataFrame(out)
P = P.join(R[['sym', 'tday', 'half', 'bk', 'lr', 'ratio', 'on_loc', 'fill_rth', 'o1_rth']], on='idx')
P.to_pickle('path.pkl'); print(P.shape); print(P.groupby('ck').fill.agg(['mean', 'size']))
