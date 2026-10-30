"""Getsuga NY AM heads. For every trading day of a set week (Monday 09:30 onward), at the 09:30 open: the Friday -> Monday
Shikai-mid fib, the nearest level above and below price (full grid: eighths -1..2; key grid: 0, 0.5, 1, 1.5, -0.5), what the
RTH session (09:30 -> 16:59) and the NY AM (09:30 -> 10:59) did with them, and a placebo grid shifted by a random fraction of
an eighth. Units: ADR20 (mean daily high-low of the 20 days before), ATR15 (RMA-14 true range of 15-minute bars, finished at
09:30), AWR4. Also checkpoints through the day for a same-day reach model. Writes ny.pkl, nyck.pkl."""
import numpy as np, pandas as pd
FW = pd.read_pickle('/home/claude/gt/fw.pkl')
FULL = np.round(np.arange(-1, 2.0001, 0.125), 3)
KEY = np.array([-0.5, 0.0, 0.5, 1.0, 1.5])
CKS = [930, 1000, 1030, 1100, 1200, 1300, 1400, 1500, 1600]
rng_ = np.random.default_rng(11)
OUT, CK = [], []


def nearest(levels, P):
    up = levels[levels > P]; dn = levels[levels < P]
    return (up.min() if len(up) else np.nan), (dn.max() if len(dn) else np.nan)


def first_touch(h, l, U, D):
    """1 if U is touched first, 0 if D first, nan if neither or both on the same bar."""
    iu = np.flatnonzero(h >= U) if U == U else np.array([], int)
    idn = np.flatnonzero(l <= D) if D == D else np.array([], int)
    a = iu[0] if len(iu) else 10 ** 9; b = idn[0] if len(idn) else 10 ** 9
    if a == b:
        return np.nan, a
    return float(a < b), min(a, b)


for sym in ('NQ', 'ES', 'RTY'):
    b = pd.read_pickle(f'/home/claude/kyw/bars_{sym}_all.pkl')[['ts', 'Open', 'High', 'Low', 'Close', 'tday', 'hm']].reset_index(drop=True)
    O, H, L, C = (b[c].to_numpy() for c in ('Open', 'High', 'Low', 'Close'))
    hm = b.hm.to_numpy(); td = b.tday.to_numpy(); ts = b.ts.to_numpy()
    # ATR15: 15-minute bars, RMA-14 of the true range
    q = b.set_index('ts')[['Open', 'High', 'Low', 'Close']].resample('15min').agg(dict(Open='first', High='max', Low='min', Close='last')).dropna()
    tr = np.maximum(q.High - q.Low, np.maximum((q.High - q.Close.shift()).abs(), (q.Low - q.Close.shift()).abs()))
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
    atr_end = pd.Series(atr.values, index=q.index + pd.Timedelta(minutes=15))      # value known at the bar's close
    # days
    ds = np.r_[0, np.flatnonzero(td[1:] != td[:-1]) + 1]; de = np.r_[ds[1:], len(b)]
    drng = [H[s:e].max() - L[s:e].min() for s, e in zip(ds, de)]
    days = [pd.Timestamp(td[s]) for s in ds]
    fw = FW[FW.sym == sym].set_index('wk')
    for k, (s, e) in enumerate(zip(ds, de)):
        d = days[k]; wk = d - pd.Timedelta(days=d.dayofweek)
        if wk not in fw.index or k < 20:
            continue
        r = fw.loc[wk]
        rth = np.flatnonzero((hm[s:e] >= 930) & (hm[s:e] < 1700)) + s
        if len(rth) < 300:
            continue
        a, z = rth[0], rth[-1] + 1
        t930 = pd.Timestamp(ts[a])
        a15 = atr_end.asof(t930) if t930 >= atr_end.index[0] else np.nan
        adr = np.mean(drng[k - 20:k]); P = O[a]
        h, l, c = H[a:z], L[a:z], C[a:z]; hmr = hm[a:z]; am = hmr < 1100
        M, R = r.M, r.R
        row = dict(sym=sym, wk=wk, day=d, dow=d.dayofweek, P=P, adr=adr, atr15=a15, awr=r.awr, aR=abs(R), R=R, M=M, F=r.F,
                   fpos=(P - M) / R, ndays_left=4 - d.dayofweek, Cam=c[am][-1] if am.any() else np.nan, Cday=c[-1],
                   Ham=h[am].max(), Lam=l[am].min(), Hd=h.max(), Ld=l.min())
        u = rng_.uniform(0, 1)
        for nm, grid in (('f', M + FULL * R), ('k', M + KEY * R), ('pf', M + (FULL + u / 8) * R), ('pk', M + (KEY + u / 8) * R)):
            U, D = nearest(np.sort(grid), P)
            row[nm + 'U'], row[nm + 'D'] = U, D
            row[nm + 'first'], row[nm + 'tf'] = first_touch(h, l, U, D)
            for side, y in (('U', U), ('D', D)):
                hit = (h >= y) if side == 'U' else (l <= y)
                i = np.flatnonzero(hit) if y == y else np.array([], int)
                row[f'{nm}{side}am'] = bool(len(i) and am[i[0]]); row[f'{nm}{side}day'] = bool(len(i)); row[f'{nm}{side}t'] = int(i[0]) if len(i) else -1
            # the nearer of the two and its mirror (same distance, other side of the open)
            if U == U or D == D:
                near_up = D != D or (U == U and (U - P) <= (P - D)); yn = U if near_up else D; dn_ = abs(yn - P); mir = P - dn_ if near_up else P + dn_
                row[nm + 'two'] = U == U and D == D
                row[nm + 'near_up'] = near_up; row[nm + 'dn'] = dn_
                row[nm + 'near_am'] = bool(((h[am] >= yn) if near_up else (l[am] <= yn)).any())
                row[nm + 'mir_am'] = bool(((l[am] <= mir) if near_up else (h[am] >= mir)).any())
                row[nm + 'near_day'] = bool(((h >= yn) if near_up else (l <= yn)).any())
                row[nm + 'mir_day'] = bool(((l <= mir) if near_up else (h >= mir)).any())
        OUT.append(row)
        # same-day checkpoints for the key levels: reach by 16:59 from the checkpoint
        for ckm in CKS:
            j = np.flatnonzero(hmr == ckm)
            if not len(j):
                continue
            j = j[0]; px = O[a + j] if ckm == 930 else C[a + j - 1]
            for f in FULL:
                y = M + f * R
                if f not in KEY and abs(y - px) > 3 * a15:
                    continue
                if j > 0 and ((l[:j] <= y) & (h[:j] >= y)).any():
                    continue
                hit = ((l[j:] <= y) & (h[j:] >= y)).any()
                amj = am[j:]
                yam = float(((l[j:][amj] <= y) & (h[j:][amj] >= y)).any()) if amj.any() else np.nan
                CK.append(dict(sym=sym, wk=wk, day=d, dow=d.dayofweek, ck=ckm, f=f, y=float(hit), yam=yam, d=abs(y - px), adr=adr, atr15=a15, awr=r.awr,
                               side=float(y > px), inside=float(min(r.M, r.F) <= px <= max(r.M, r.F)), aR=abs(R)))
D = pd.DataFrame(OUT); D['half'] = np.where(D.day.dt.year >= 2025, '25-26', '18-24')
K = pd.DataFrame(CK); K['half'] = np.where(K.day.dt.year >= 2025, '25-26', '18-24')
D.to_pickle('/home/claude/gt/ny.pkl'); K.to_pickle('/home/claude/gt/nyck.pkl')
print(D.shape, K.shape, D.groupby('sym').size().to_dict())
print('ADR20 / AWR4 median', (D.adr / D.awr).median().round(3), ' ATR15 / ADR20 median', (D.atr15 / D.adr).median().round(3))
for nm in ('f', 'k'):
    g = D.dropna(subset=[nm + 'U', nm + 'D'])
    print(nm, 'nearest above / below at 09:30 in ATR15, median', ((g[nm + 'U'] - g.P) / g.atr15).median().round(2), ((g.P - g[nm + 'D']) / g.atr15).median().round(2), 'n', len(g))
