"""Sakanade research v2: day and week samples with the pooled intraday volatility profile (NQ + ES + RTY, 2018–24) and
'event still ahead' features. Day: every 15 minutes, outcome = the running day high (low) holds to 16:59.
Week: every hour, outcome = the running week high (low) holds to Friday 16:59. Distances in daily ATR(14)."""
import numpy as np, pandas as pd, sys
from numba import njit
sys.path.insert(0, '/home/claude/lr'); sys.path.insert(0, '/home/claude/hm')
from lib import load, D2025
import events as E
PM = pd.read_pickle('/home/claude/sk/vprof.pkl').mean(axis=1).values          # pooled per-minute (1m range / ATR)^2
np.save('/home/claude/sk/pm_pooled.npy', PM)

def rma(x, n=14):
    out = np.full(len(x), np.nan); a = 1.0 / n; out[n - 1] = np.nanmean(x[:n])
    for i in range(n, len(x)): out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out

@njit(cache=True)
def build(H, L, C, O, rel, gs, ge, atrB, ref1, ref2, PM, step, evRelB, minBars):
    """Generic: groups gs..ge (a day or a week). atrB[k], ref1[k] (PDH or PWH), ref2[k] (PDL or PWL), evRelB[k] = minutes from
    18:00 of the next release still ahead in the group at bar k (−1 none) — per bar arrays. Samples at bars with (rel+1)%step==0."""
    rows = []
    for g in range(len(gs)):
        s = gs[g]; e = ge[g]
        if e - s + 1 < minBars: continue
        n = e - s + 1
        fH = np.empty(n); fL = np.empty(n); Vf = np.empty(n)
        mh = -1e18; ml = 1e18; v = 0.0
        for k in range(e, s - 1, -1):
            fH[k - s] = mh; fL[k - s] = ml; Vf[k - s] = v
            if H[k] > mh: mh = H[k]
            if L[k] < ml: ml = L[k]
            v += PM[rel[k]]
        hi = -1e18; lo = 1e18; tH = s; tL = s; op = O[s]
        for k in range(s, e):
            if H[k] > hi: hi = H[k]; tH = k
            if L[k] < lo: lo = L[k]; tL = k
            if (rel[k] + 1) % step != 0: continue
            a = atrB[k]
            if not (a > 0) or not (ref1[k] > 0) or not (Vf[k - s] > 0): continue
            rg = hi - lo; Vr = Vf[k - s]; lb = float(e - k)
            dH = (hi - C[k]) / a; dL = (C[k] - lo) / a
            rows.append((float(g), 1.0, float(rel[k] + 1), lb, dH / np.sqrt(Vr), rg / a, float(k - tH), (C[k] - lo) / rg if rg > 0 else 0.5,
                         (hi - ref1[k]) / a, (C[k] - op) / a, float(rel[tH]), float(evRelB[k]), Vr, 1.0 if fH[k - s] <= hi else 0.0))
            rows.append((float(g), -1.0, float(rel[k] + 1), lb, dL / np.sqrt(Vr), rg / a, float(k - tL), (hi - C[k]) / rg if rg > 0 else 0.5,
                         (ref2[k] - lo) / a, (op - C[k]) / a, float(rel[tL]), float(evRelB[k]), Vr, 1.0 if fL[k - s] >= lo else 0.0))
    out = np.empty((len(rows), 14))
    for i in range(len(rows)):
        for j in range(14): out[i, j] = rows[i][j]
    return out

COLS = ['g', 'side', 'r', 'barsLeft', 'z', 'ru', 'age', 'pos', 'xRef', 'opn', 'tEx', 'evA', 'V', 'y']
evd = {}
for nm, lst, rr in [('CPI', E.CPI, 870), ('NFP', E.NFP, 870), ('FOMC', E.FOMC, 1200)]:
    for t in lst: evd[int(pd.Timestamp(t).normalize().value // 86400_000_000_000)] = rr
DAYR = []; WKR = []
for sym in ['NQ', 'ES', 'RTY']:
    m = load(sym)
    rel = (((m['ts'] % 1440) - 1080) % 1440).astype(np.int64)
    td = m['td'].astype(np.int64)
    b = np.flatnonzero(np.diff(td) != 0) + 1; ds = np.r_[0, b]; de = np.r_[b - 1, len(td) - 1]
    dH = np.maximum.reduceat(m['H'], ds); dL = np.minimum.reduceat(m['L'], ds); dC = m['C'][de]; nb = de - ds + 1
    pc = np.r_[np.nan, dC[:-1]]
    tr = np.nanmax(np.c_[dH - dL, np.abs(dH - pc), np.abs(dL - pc)], axis=1)
    trF = pd.Series(np.where(nb >= 1200, tr, np.nan)).ffill().values
    atr = np.r_[np.nan, rma(trF)[:-1]]
    days = td[ds]; wk = (days + 3) // 7
    di = np.repeat(np.arange(len(ds)), nb)
    atrB = atr[di]
    pdh = np.r_[np.nan, dH[:-1]][di]; pdl = np.r_[np.nan, dL[:-1]][di]
    ww = pd.DataFrame({'wk': wk, 'h': dH, 'l': dL}).groupby('wk').agg(h=('h', 'max'), l=('l', 'min'))
    pwh = pd.Series(wk).map(ww.h.shift(1)).values[di]; pwl = pd.Series(wk).map(ww.l.shift(1)).values[di]
    # event still ahead: today (day model) / this week (week model): minutes-from-18:00 of the next release, −1 if none ahead today;
    # for the week: the number of releases still ahead this week
    evR = np.array([evd.get(int(d), -1) for d in days])[di]
    evDay = np.where((evR >= 0) & (evR > rel), evR, -1).astype(np.float64)
    wkB = wk[di]
    # releases ahead in the week: count event days later in the week + today's if still ahead
    evFlag = np.array([1 if int(d) in evd else 0 for d in days])
    later = pd.Series(evFlag).groupby(wk).transform(lambda x: x[::-1].cumsum()[::-1] - x).values   # strictly later days in the week
    evWk = (later[di] + (evDay >= 0)).astype(np.float64)
    R = build(m['H'], m['L'], m['C'], m['O'], rel, ds, de, atrB, pdh, pdl, PM, 15, evDay, 1200)
    df = pd.DataFrame(R, columns=COLS); df['td'] = days[df.g.astype(int)]; df['sym'] = sym
    df['dow'] = pd.to_datetime(df.td, unit='D').dt.dayofweek; DAYR.append(df)
    wb = np.flatnonzero(np.diff(wkB) != 0) + 1; ws = np.r_[0, wb]; we = np.r_[wb - 1, len(wkB) - 1]
    R = build(m['H'], m['L'], m['C'], m['O'], rel, ws, we, atrB, pwh, pwl, PM, 60, evWk, 4000)
    dw = pd.DataFrame(R, columns=COLS); dw['td'] = td[ws[dw.g.astype(int)]]; dw['sym'] = sym
    # day of week of the sample: from barsLeft is awkward, so recompute from the sample's position: use rel & bars — store via td of bar
    WKR.append(dw); print(sym, len(df), len(dw), flush=True)
pd.concat(DAYR, ignore_index=True).to_pickle('/home/claude/sk/t13_day.pkl'); pd.concat(WKR, ignore_index=True).to_pickle('/home/claude/sk/t13_wk.pkl')
