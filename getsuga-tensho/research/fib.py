"""Getsuga Tenshō v2 research: the Friday → Monday Shikai-mid fib as this week's dealing range. NQ, ES, RTY 1-minute 2018-26.
Shikai mid of a trading day = (overnight high + overnight low) / 2, overnight = 18:00 -> 09:29 ET (as in the Shikai / Bankai
Session Map). F = the mid of last week's last trading day (Friday), M = the mid of this week's first (Monday). Fib: 1 = F,
0 = M, level(f) = M + f (F - M); 1.5 and -0.5 are the range's SDs. The fib is set at Monday 09:30; the rest of the week runs
from that bar to Friday 17:00. Roll weeks (F and the week in different contracts) are dropped: the data are raw contracts.
Writes fw.pkl (weeks, levels reached), fck.pkl (checkpoints for live odds), fz.pkl (first touches for the hold test)."""
import numpy as np, pandas as pd
FS = np.round(np.arange(-1, 2.0001, 0.125), 3)          # fib levels -1 .. 2 in eighths
W, CK, Z = [], [], []
rng_ = np.random.default_rng(7)
for sym in ('NQ', 'ES', 'RTY'):
    b = pd.read_pickle(f'/home/claude/kyw/bars_{sym}_all.pkl')[['ts', 'Open', 'High', 'Low', 'Close', 'tday', 'hm', 'Contract']].reset_index(drop=True)
    O, H, L, C = (b[c].to_numpy() for c in ('Open', 'High', 'Low', 'Close'))
    hm = b.hm.to_numpy(); td = b.tday.to_numpy(); con = b.Contract.to_numpy(); ts = b.ts.to_numpy()
    on = (hm >= 1800) | (hm < 930)
    # per trading day: overnight mid, the time its line starts (earlier extreme), the 09:30 bar
    ds = np.r_[0, np.flatnonzero(td[1:] != td[:-1]) + 1]; de = np.r_[ds[1:], len(b)]
    day = {}
    for s, e in zip(ds, de):
        m = on[s:e]
        if m.sum() < 60:
            continue
        ii = np.flatnonzero(m) + s
        ih, il = ii[np.argmax(H[ii])], ii[np.argmin(L[ii])]
        r = np.flatnonzero((hm[s:e] >= 930) & (hm[s:e] < 1700))      # the 09:30 bar (the day's bars start at 18:00)
        if not len(r):
            continue
        day[pd.Timestamp(td[s])] = dict(s=s, e=e, mid=(H[ih] + L[il]) / 2, onh=H[ih], onl=L[il], t0=min(ts[ih], ts[il]), i930=s + r[0], con=con[ii[-1]])
    days = sorted(day)
    wk = {}
    for d in days:
        wk.setdefault(d - pd.Timedelta(days=d.dayofweek), []).append(d)
    weeks = sorted(wk); ranges = []
    for k, w in enumerate(weeks):
        dd = wk[w]; s, e = day[dd[0]]['s'], day[dd[-1]]['e']
        wr = H[s:e].max() - L[s:e].min()
        awr = np.mean(ranges[-4:]) if len(ranges) >= 4 else np.nan
        ranges.append(wr)
        if k == 0 or (w - weeks[k - 1]).days != 7 or len(dd) < 4 or np.isnan(awr):
            continue
        pdd = wk[weeks[k - 1]]; Fd, Md = day[pdd[-1]], day[dd[0]]
        ps, pe = day[pdd[0]]['s'], day[pdd[-1]]['e']
        if len({Fd['con'], Md['con'], con[e - 1], con[ps]}) > 1:
            continue                                       # roll week
        F, M = Fd['mid'], Md['mid']; R = F - M
        a = Md['i930']; h, l, c = H[a:e], L[a:e], C[a:e]; P0 = O[a]
        tdr = td[a:e]
        if abs(R) < 1e-9:
            continue
        r = dict(sym=sym, wk=w, F=F, M=M, R=R, aR=abs(R), awr=awr, P0=P0, x0=(P0 - M) / R, wO=O[s], ndays=len(dd),
                 PWH=H[ps:pe].max(), PWL=L[ps:pe].min(), Hr=h.max(), Lr=l.min(), Cw=c[-1], onR=Md['onh'] - Md['onl'])
        r['xH'], r['xL'], r['xC'] = (r['Hr'] - M) / R, (r['Lr'] - M) / R, (c[-1] - M) / R
        for f in FS:
            y = M + f * R; pl = 2 * P0 - y
            hit = (l <= y) & (h >= y); i = np.flatnonzero(hit)
            r[f'h{f}'] = len(i) > 0; r[f't{f}'] = int(i[0]) if len(i) else -1
            r[f'p{f}'] = bool(((l <= pl) & (h >= pl)).any())
            # first touch hold test (R = 0.1 AWR4), level must not sit in the first bar
            if len(i) and i[0] > 0 and abs(f) <= 2:
                t = int(i[0]); above = c[t - 1] > y; RR = 0.1 * awr
                for kind, yy, tt in (('real', y, t),):
                    hh, ll = h[tt:], l[tt:]
                    b1 = np.flatnonzero(hh >= yy + RR) if above else np.flatnonzero(ll <= yy - RR)
                    b2 = np.flatnonzero(ll <= yy - RR) if above else np.flatnonzero(hh >= yy + RR)
                    i1 = b1[0] if len(b1) else 10 ** 9; i2 = b2[0] if len(b2) else 10 ** 9
                    if i1 != i2:
                        Z.append(dict(sym=sym, wk=w, f=f, real=1.0, hold=float(i1 < i2), dist=abs(yy - P0) / awr, aR=abs(R) / awr))
        # placebo first touches: random levels within the same span of the fib (-1 .. 2), one per real level
        for _ in range(6):
            y = M + rng_.uniform(-1, 2) * R
            hit = (l <= y) & (h >= y); i = np.flatnonzero(hit)
            if len(i) and i[0] > 0:
                t = int(i[0]); above = c[t - 1] > y; RR = 0.1 * awr; hh, ll = h[t:], l[t:]
                b1 = np.flatnonzero(hh >= y + RR) if above else np.flatnonzero(ll <= y - RR)
                b2 = np.flatnonzero(ll <= y - RR) if above else np.flatnonzero(hh >= y + RR)
                i1 = b1[0] if len(b1) else 10 ** 9; i2 = b2[0] if len(b2) else 10 ** 9
                if i1 != i2:
                    Z.append(dict(sym=sym, wk=w, f=np.nan, real=0.0, hold=float(i1 < i2), dist=abs(y - P0) / awr, aR=abs(R) / awr))
        # extremes of the rest of the week on the grid vs a grid shifted by a random fraction of an eighth
        u = rng_.uniform(0, 1)
        for nm, x in (('H', r['xH']), ('L', r['xL'])):
            r['d8' + nm] = abs(8 * x - np.round(8 * x)); xs = 8 * x + u
            r['q8' + nm] = abs(xs - np.round(xs))
        r['PWHt'] = bool(r['Hr'] > r['PWH']); r['PWLt'] = bool(r['Lr'] < r['PWL'])
        W.append(r)
        # checkpoints: Monday 09:30 (before its bar) and each day's close Mon..Thu
        uday = pd.unique(tdr)
        cks = [(-1, -1)] + [(j, int(np.flatnonzero(tdr == uday[j])[-1])) for j in range(min(4, len(uday) - 1))]
        for ck, j in cks:
            px = P0 if j < 0 else c[j]
            for f in (-0.5, 0.0, 0.5, 1.0, 1.5, 'PWH', 'PWL'):
                y = r['PWH'] if f == 'PWH' else r['PWL'] if f == 'PWL' else M + f * R
                done = j >= 0 and (l[:j + 1] <= y).any() and (h[:j + 1] >= y).any() and ((l[:j + 1] <= y) & (h[:j + 1] >= y)).any()
                if f == 'PWH':
                    done = j >= 0 and h[:j + 1].max() > y
                if f == 'PWL':
                    done = j >= 0 and l[:j + 1].min() < y
                if done:
                    continue
                rest_h, rest_l = h[j + 1:], l[j + 1:]
                if f == 'PWH':
                    y_ = bool((rest_h > y).any()); dist = (y - px) / awr
                elif f == 'PWL':
                    y_ = bool((rest_l < y).any()); dist = (px - y) / awr
                else:
                    y_ = bool(((rest_l <= y) & (rest_h >= y)).any()); dist = abs(y - px) / awr
                if dist <= 0:
                    continue
                CK.append(dict(sym=sym, wk=w, ck=ck, lvl=str(f), y=float(y_), d=dist, aR=abs(R) / awr))
D = pd.DataFrame(W); D['half'] = np.where(D.wk.dt.year >= 2025, '25-26', '18-24')
K = pd.DataFrame(CK); K['half'] = np.where(K.wk.dt.year >= 2025, '25-26', '18-24')
Zf = pd.DataFrame(Z); Zf['half'] = np.where(Zf.wk.dt.year >= 2025, '25-26', '18-24')
D.to_pickle('/home/claude/gt/fw.pkl'); K.to_pickle('/home/claude/gt/fck.pkl'); Zf.to_pickle('/home/claude/gt/fz.pkl')
print(D.shape, K.shape, Zf.shape, D.groupby('sym').size().to_dict())
print('|R| / AWR4 quantiles', (D.aR / D.awr).quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round(3).tolist())
print('x0 (Mon 09:30 on the fib) quantiles', D.x0.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round(2).tolist())
