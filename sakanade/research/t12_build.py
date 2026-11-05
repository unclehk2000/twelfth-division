"""Sakanade research: is the day's high (low) in? Samples at the close of every 15-minute block of the trading day (18:00–17:00 ET),
NQ / ES / RTY 1-minute 2018 – 23 Oct 2026. Outcome: the running high (low) is not exceeded before 16:59.
Features (high; the low mirrored): minutes left, distance from the close to the high in daily ATR(14), the Brownian z with the
intraday volatility profile, range used, age of the high, position in the range, the high vs PDH / PWH, move since the open,
day of week, CPI / NFP / FOMC day, the minute the high was set."""
import numpy as np, pandas as pd, sys
from numba import njit
sys.path.insert(0, '/home/claude/lr'); sys.path.insert(0, '/home/claude/hm')
from lib import load, D2025
import events as E

def rma(x, n=14):
    out = np.full(len(x), np.nan); a = 1.0 / n
    s = np.nanmean(x[:n]); out[n - 1] = s
    for i in range(n, len(x)): out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out

@njit(cache=True)
def samples(H, L, C, O, rel, ds, de, atr, pdh, pdl, pwh, pwl, V, step):
    rows = []
    for d in range(len(ds)):
        a = atr[d]
        if not (a > 0) or not (pdh[d] > 0) or not (pwh[d] > 0): continue
        s = ds[d]; e = de[d]
        if rel[s] > 5 or rel[e] < 1370: continue
        # future max/min from each bar to the end of the day
        n = e - s + 1
        fH = np.empty(n); fL = np.empty(n)
        mh = -1e18; ml = 1e18
        for k in range(e, s - 1, -1):
            fH[k - s] = mh; fL[k - s] = ml       # max/min strictly after k
            if H[k] > mh: mh = H[k]
            if L[k] < ml: ml = L[k]
        hi = -1e18; lo = 1e18; tH = s; tL = s; op = O[s]
        for k in range(s, e):
            if H[k] > hi: hi = H[k]; tH = k
            if L[k] < lo: lo = L[k]; tL = k
            if (rel[k] + 1) % step != 0: continue
            r = rel[k] + 1
            if r >= 1380: continue
            Vr = V[r]
            if not (Vr > 0): continue
            rg = hi - lo
            # high
            dH = (hi - C[k]) / a
            rows.append((float(d), 1.0, float(r), dH, dH / np.sqrt(Vr), rg / a, float(rel[k] - rel[tH]), (C[k] - lo) / rg if rg > 0 else 0.5,
                         (hi - pdh[d]) / a, (hi - pwh[d]) / a, (C[k] - op) / a, float(rel[tH]), 1.0 if fH[k - s] <= hi else 0.0))
            dL = (C[k] - lo) / a
            rows.append((float(d), -1.0, float(r), dL, dL / np.sqrt(Vr), rg / a, float(rel[k] - rel[tL]), (hi - C[k]) / rg if rg > 0 else 0.5,
                         (pdl[d] - lo) / a, (pwl[d] - lo) / a, (op - C[k]) / a, float(rel[tL]), 1.0 if fL[k - s] >= lo else 0.0))
    out = np.empty((len(rows), 13))
    for i in range(len(rows)):
        for j in range(13): out[i, j] = rows[i][j]
    return out

COLS = ['d', 'side', 'r', 'dist', 'z', 'ru', 'age', 'pos', 'xPD', 'xPW', 'opn', 'tEx', 'y']
ev = {}
for nm, lst in [('CPI', E.CPI), ('NFP', E.NFP), ('FOMC', E.FOMC)]:
    for t in lst: ev[int(pd.Timestamp(t).normalize().value // 86400_000_000_000)] = {'CPI': 1, 'NFP': 2, 'FOMC': 3}[nm]
allr = []; prof = {}
for sym in ['NQ', 'ES', 'RTY']:
    m = load(sym)
    rel = (((m['ts'] % 1440) - 1080) % 1440).astype(np.int64)
    td = m['td'].astype(np.int64)
    b = np.flatnonzero(np.diff(td) != 0) + 1; ds = np.r_[0, b]; de = np.r_[b - 1, len(td) - 1]
    dH = np.maximum.reduceat(m['H'], ds); dL = np.minimum.reduceat(m['L'], ds); dC = m['C'][de]; nb = de - ds + 1
    full = nb >= 1200
    pc = np.r_[np.nan, dC[:-1]]
    tr = np.nanmax(np.c_[dH - dL, np.abs(dH - pc), np.abs(dL - pc)], axis=1)
    trF = np.where(full, tr, np.nan); trF = pd.Series(trF).ffill().values
    atr = np.r_[np.nan, rma(trF)[:-1]]                                    # prior days only
    pdh = np.r_[np.nan, dH[:-1]]; pdl = np.r_[np.nan, dL[:-1]]
    days = td[ds]; wk = (days + 3) // 7                                    # weeks (Thu-based epoch → Monday groups)
    dfw = pd.DataFrame({'wk': wk, 'h': dH, 'l': dL}); ww = dfw.groupby('wk').agg(h=('h', 'max'), l=('l', 'min'))
    pwh = pd.Series(wk).map(ww.h.shift(1)).values; pwl = pd.Series(wk).map(ww.l.shift(1)).values
    # intraday volatility profile (fish years): mean (1m range / daily ATR)^2 by minute from 18:00, cumulative to the close
    di = np.repeat(np.arange(len(ds)), nb); a1 = atr[di]
    fish = days[di] < D2025
    q = ((m['H'] - m['L']) / a1) ** 2
    ok = fish & np.isfinite(q)
    pm = np.bincount(rel[ok], weights=q[ok], minlength=1380)[:1380] / np.maximum(np.bincount(rel[ok], minlength=1380)[:1380], 1)
    prof[sym] = pm
    V = np.r_[np.cumsum(pm[::-1])[::-1], 0.0]                             # V[r] = expected variance from minute r to the close
    R = samples(m['H'], m['L'], m['C'], m['O'], rel, ds, de, atr, pdh, pdl, pwh, pwl, V, 15)
    df = pd.DataFrame(R, columns=COLS)
    df['td'] = days[df.d.astype(int)]; df['sym'] = sym
    df['dow'] = pd.to_datetime(df.td, unit='D').dt.dayofweek
    df['ev'] = df.td.map(ev).fillna(0).astype(int)
    allr.append(df); print(sym, len(df), flush=True)
D = pd.concat(allr, ignore_index=True); D.to_pickle('/home/claude/sk/t12_rows.pkl')
pd.DataFrame(prof).to_pickle('/home/claude/sk/vprof.pkl')
print(D.groupby('side').y.mean())
