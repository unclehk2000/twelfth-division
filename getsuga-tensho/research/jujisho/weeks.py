"""Getsuga Jūjishō research, step 2: weeks. One row per week with a Friday → Monday FPFVG range, plus per-level frames.
Roll weeks (last week's last day, this week's first day and Friday in different contracts) are left out: the bars are raw
contracts, so a range spanning a roll would mix two price scales."""
import numpy as np, pandas as pd
b = pd.read_pickle('/home/claude/kyw/bars_NQ_all.pkl').reset_index(drop=True)
O, H, L, C = (b[c].to_numpy() for c in ('Open', 'High', 'Low', 'Close'))
hm = b.hm.to_numpy(); td = b.tday.to_numpy(); con = b.Contract.to_numpy()
D = pd.read_pickle('days.pkl').set_index('date')
FS = np.round(np.arange(-1, 2.0001, 0.125), 3)
rng_ = np.random.default_rng(11)
bts = b.ts
# chart weeks: Sunday 18:00 → Friday 17:00 ET (Monday of the week of ts + 6 h)
wkid = (bts + pd.Timedelta(hours=6)).dt.normalize(); wkid = (wkid - pd.to_timedelta(wkid.dt.dayofweek, unit='D')).to_numpy()
ws = np.r_[0, np.flatnonzero(wkid[1:] != wkid[:-1]) + 1]; we = np.r_[ws[1:], len(b)]
WB = {pd.Timestamp(wkid[s]): (s, e) for s, e in zip(ws, we)}
wr = {w: H[s:e].max() - L[s:e].min() for w, (s, e) in WB.items()}
wk = {}
for d in D.index:
    wk.setdefault(D.at[d, 'wk'], []).append(d)
weeks = sorted(wk)
W, LV, HD, PH = [], [], [], []
def first_reach(h, l, y, P0):
    if y >= P0:
        cm = np.maximum.accumulate(h); i = np.searchsorted(cm, y)
    else:
        cm = -np.minimum.accumulate(l); i = np.searchsorted(cm, -y)
    return int(i) if i < len(h) else -1
def hold(h, l, c, t, y, B, came_from_below):
    hh, ll = h[t:], l[t:]
    if came_from_below:          # first reached from below: holds if it drops B under before rising B over
        b1 = np.flatnonzero(ll <= y - B); b2 = np.flatnonzero(hh >= y + B)
    else:
        b1 = np.flatnonzero(hh >= y + B); b2 = np.flatnonzero(ll <= y - B)
    i1 = b1[0] if len(b1) else 10 ** 9; i2 = b2[0] if len(b2) else 10 ** 9
    return np.nan if i1 == i2 else float(i1 < i2)
for k, w in enumerate(weeks):
    if k < 5 or (w - weeks[k - 1]).days != 7:
        continue
    prevW = [x for x in sorted(WB) if x < w][-4:]
    if len(prevW) < 4 or w not in WB:
        continue
    awr = np.mean([wr[x] for x in prevW])
    pdd, dd = wk[weeks[k - 1]], wk[w]
    pf = [x for x in pdd if not pd.isna(D.at[x, 'fp'])]; mf = [x for x in dd if not pd.isna(D.at[x, 'fp'])]
    if not pf or not mf or len(dd) < 3:
        continue
    Fd, Md = D.loc[pf[-1]], D.loc[mf[0]]
    if mf[0] != dd[0] and mf[0].dayofweek > 1:
        continue
    endi = WB[w][1]
    roll = len({Fd.con, Md.con, con[endi - 1]}) > 1
    F, M = Fd.ce, Md.ce; R = F - M
    if abs(R) < 1e-9 or roll:
        W.append(dict(wk=w, roll=roll, zero=abs(R) < 1e-9)); continue
    a = int(Md.i3) + 1; P0 = Md.P0
    h, l, c = H[a:endi], L[a:endi], C[a:endi]; tdr = td[a:endi]
    dows = pd.DatetimeIndex(tdr).dayofweek.to_numpy()
    r = dict(wk=w, roll=False, zero=False, F=F, M=M, R=R, aR=abs(R), awr=awr, P0=P0, x0=(P0 - M) / R,
             Fday=pf[-1], Mday=mf[0], Ffri=pf[-1].dayofweek == 4, Mmon=mf[0].dayofweek == 0, ndays=len(dd),
             Fdir=Fd.fp, Mdir=Md.fp, Fgap=Fd.gap, Mgap=Md.gap, Ftop=Fd.top, Fbot=Fd.bot, Mtop=Md.top, Mbot=Md.bot,
             Mfpt=Md.fpt, Fhalf=bool(Fd.half), Mhalf=bool(Md.half),
             Fradr=Fd.radr5, Mradr=Md.radr5, Mpre=Md.pre_rng, Mrest=Md.rest_rng, Mam=Md.am_rng,
             wO=O[WB[w][0]], Hr=h.max(), Lr=l.min(), Cw=c[-1], wH=H[WB[w][0]:endi].max(), wL=L[WB[w][0]:endi].min(),
             pwH=H[slice(*WB[prevW[-1]])].max(), pwL=L[slice(*WB[prevW[-1]])].min(), Fclose=Fd.c_end)
    r['xH'], r['xL'], r['xC'] = (r['Hr'] - M) / R, (r['Lr'] - M) / R, (r['Cw'] - M) / R
    r['overlap'] = min(Fd.top, Md.top) >= max(Fd.bot, Md.bot)
    # next week's range (for "does Friday's gap / this range predict next week")
    r['wk_rest_rng'] = r['Hr'] - r['Lr']
    W.append(r)
    # levels: real grid, a grid shifted by a random fraction of an eighth, and the mirror of each real level
    u = rng_.uniform(0, 1)
    for kind, fs in (('real', FS), ('shift', FS + u / 8)):
        for f in fs:
            y = M + f * R
            t = first_reach(h, l, y, P0)
            rec = dict(wk=w, kind=kind, f=round(float(f), 4) if kind == 'real' else np.nan, y=y, d=abs(y - P0) / awr,
                       up=y >= P0, hit=t >= 0, hday=int(dows[t]) if t >= 0 else -1, t=t, aR=abs(R) / awr)
            if kind == 'real':
                pl = 2 * P0 - y; tp = first_reach(h, l, pl, P0); rec['mir'] = tp >= 0
            # first-touch hold test, brackets 0.05 and 0.1 AWR4 (level must not be reached on the first bar)
            if t > 0:
                for B in (0.05, 0.10):
                    rec[f'hold{int(B * 100)}'] = hold(h, l, c, t, y, B * awr, y >= P0)
            LV.append(rec)
    # day highs / lows / closes after the set, on the grid (phase in eighths) and on the shifted grid
    for dw in np.unique(dows):
        m = dows == dw
        for nm, v in (('high', h[m].max()), ('low', l[m].min()), ('close', c[m][-1])):
            fr = (v - M) / R * 8
            PH.append(dict(wk=w, dow=int(dw), what=nm, ph=fr - np.round(fr), phs=(fr - u) - np.round(fr - u), aR=abs(R) / awr))
Wd = pd.DataFrame(W); LVd = pd.DataFrame(LV); PHd = pd.DataFrame(PH)
Wd.to_pickle('weeks.pkl'); LVd.to_pickle('levels.pkl'); PHd.to_pickle('phases.pkl')
G = Wd[~Wd.roll & ~Wd.zero]
print('weeks total', len(Wd), 'roll', Wd.roll.sum(), 'zero R', Wd.zero.sum(), 'usable', len(G))
print('F is Friday', G.Ffri.mean().round(3), 'M is Monday', G.Mmon.mean().round(3))
print('|R|/AWR4 quantiles', (G.aR / G.awr).quantile([.1, .25, .5, .75, .9]).round(3).tolist())
print('Mon FPFVG presented (third candle) quantiles', G.Mfpt.quantile([.25, .5, .75, .9]).tolist())
print('overlap share', G.overlap.mean().round(3))
