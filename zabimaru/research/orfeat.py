"""Zabimaru research data: the 09:30-10:00 ET opening range (OR) on NQ, ES and RTY 1-minute 2018-26, one row per symbol
and trading day (18:00 -> 17:00). ATR10 = mean true range of the 10 prior trading days (18:00 -> 17:00 bars).
Writes or.pkl"""
import numpy as np, pandas as pd
rows = []
for sym in ('NQ', 'ES', 'RTY'):
    b = pd.read_pickle(f'/home/claude/kyw/bars_{sym}_all.pkl')[['Open', 'High', 'Low', 'Close', 'tday', 'hm', 'Contract']].reset_index(drop=True)
    O, H, L, C = (b[c].to_numpy() for c in ('Open', 'High', 'Low', 'Close'))
    hm = b.hm.to_numpy(); td = b.tday.to_numpy(); ct = b.Contract.to_numpy()
    st = np.r_[0, np.flatnonzero(td[1:] != td[:-1]) + 1]; en = np.r_[st[1:], len(b)]
    prevC = np.nan; trs = []; prevCt = None
    for s, e in zip(st, en):
        d = td[s]; h = hm[s:e]
        dH, dL, dC = H[s:e].max(), L[s:e].min(), C[e - 1]
        tr = dH - dL if np.isnan(prevC) else max(dH, prevC) - min(dL, prevC)
        atr10 = np.mean(trs[-10:]) if len(trs) >= 10 else np.nan
        atr10_5 = np.mean(trs[-15:-5]) if len(trs) >= 15 else np.nan
        atr5 = np.mean(trs[-5:]) if len(trs) >= 5 else np.nan
        trs.append(tr); pc = prevC; prevC = dC
        i930 = np.flatnonzero(h == 930); i1614 = np.flatnonzero(h == 1614); i0 = np.flatnonzero(h == 0)
        if not len(i930) or not len(i1614):
            continue
        a = s + i930[0]; z = s + i1614[0]
        orr = np.flatnonzero((h >= 930) & (h <= 959)) + s
        if len(orr) < 25 or ct[a] != ct[z]:
            continue
        o930 = O[a]; orh = H[orr].max(); orl = L[orr].min(); c959 = C[orr[-1]]; rng = orh - orl
        if rng <= 0:
            continue
        aft = np.arange(orr[-1] + 1, z + 1)
        hh, ll = H[aft], L[aft]
        bh = np.flatnonzero(hh > orh); bl = np.flatnonzero(ll < orl)
        th = bh[0] if len(bh) else 10 ** 6; tl = bl[0] if len(bl) else 10 ** 6
        side = 0 if th == tl == 10 ** 6 else (1 if th < tl else -1 if tl < th else 2)
        t_break = min(th, tl)
        rth = np.arange(a, z + 1)
        r = dict(sym=sym, tday=d, o930=o930, orh=orh, orl=orl, c959=c959, rng=rng, orpct=100 * rng / o930,
                 atr10=atr10, atr10_5=atr10_5, atr5=atr5, tr=tr, pc=pc,
                 side=side, tbrk=np.nan if t_break == 10 ** 6 else int(t_break) + 30,     # minutes after 09:30 of the break bar
                 th=np.nan if th == 10 ** 6 else int(th) + 30, tl=np.nan if tl == 10 ** 6 else int(tl) + 30,
                 took_h=len(bh) > 0, took_l=len(bl) > 0,
                 ext_h=(hh.max() - orh) / rng, ext_l=(orl - ll.min()) / rng,
                 c1614=C[z], rthH=H[rth].max(), rthL=L[rth].min(),
                 loc959=(c959 - orl) / rng,
                 mid00=O[s + i0[0]] if len(i0) else np.nan, o18=O[s] if h[0] == 1800 else np.nan)
        # midnight / 18:00 open: touched in RTH (09:30-16:14)? placebo = same distance from the 09:30 open, other side
        for nm in ('mid00', 'o18'):
            lv = r[nm]
            if lv == lv:
                pl = 2 * o930 - lv
                r[nm + '_hit'] = bool(L[rth].min() <= lv <= H[rth].max())
                r[nm + '_plc'] = bool(L[rth].min() <= pl <= H[rth].max())
                r[nm + '_dist'] = abs(lv - o930)
        rows.append(r)
D = pd.DataFrame(rows)
D['half'] = np.where(D.tday.dt.year >= 2025, '25-26', '18-24')
D['or_atr'] = D.rng / D.atr10
D['vol_up'] = D.atr10 > D.atr10_5
D['volr'] = np.log(D.atr5 / D.atr10)
D.to_pickle('/home/claude/zb/or.pkl')
print(D.shape); print(D.groupby('sym').agg(n=('tday', 'size'), orpct=('orpct', 'median'), or_atr=('or_atr', 'median'), took_h=('took_h', 'mean'), took_l=('took_l', 'mean')).round(3))
print(D.groupby('sym').orpct.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).unstack().round(3))
