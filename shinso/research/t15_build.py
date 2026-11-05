"""Shinsō research: draw on liquidity. Pools: PDH/PDL, PWH/PWL, PMH/PML (previous day / week / month), the Asia range
(20:00–00:00 ET, live from 00:00) and the London range (02:00–05:00, live from 05:00). NQ / ES / RTY 1-minute 2018 – 23 Oct 2026.
Samples every 15 minutes for every live untouched pool: is it traded before 16:59? Plus the race between the nearest pool above
(buy-side) and below (sell-side): which trades first."""
import numpy as np, pandas as pd, sys
from numba import njit
sys.path.insert(0, '/home/claude/lr'); sys.path.insert(0, '/home/claude/hm')
from lib import load, D2025
import events as E
PM = np.load('/home/claude/sk/pm_pooled.npy')

def rma(x, n=14):
    out = np.full(len(x), np.nan); a = 1.0 / n; out[n - 1] = np.nanmean(x[:n])
    for i in range(n, len(x)): out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out

@njit(cache=True)
def run(H, L, C, O, rel, ds, de, atr, P0, evr, PM, step):
    """P0[d, 0:6] = PDH, PDL, PWH, PWL, PMH, PML. Pool order: 0 PDH 1 PDL 2 PWH 3 PWL 4 PMH 5 PML 6 AsiaH 7 AsiaL 8 LonH 9 LonL."""
    rows = []; race = []
    sideOf = np.array([1, -1, 1, -1, 1, -1, 1, -1, 1, -1]); typOf = np.array([0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
    for d in range(len(ds)):
        s = ds[d]; e = de[d]; a = atr[d]
        if e - s < 1200 or e - s > 1440 or not (a > 0) or not (P0[d, 0] > 0) or not (P0[d, 2] > 0) or not (P0[d, 4] > 0): continue
        n = e - s + 1
        V = np.empty(n); v = 0.0
        for k in range(e, s - 1, -1):
            V[k - s] = v; v += PM[rel[k]]
        lvl = np.full(10, np.nan); act = np.full(10, 1 << 30); tch = np.full(10, 1 << 30)
        for j in range(6):
            lvl[j] = P0[d, j]; act[j] = s
        aH = -1e18; aL = 1e18; lH = -1e18; lL = 1e18
        # pass 1: when each pool goes live and when it is first traded
        for k in range(s, e + 1):
            r = rel[k]
            if r >= 120 and r < 360:
                aH = max(aH, H[k]); aL = min(aL, L[k])
            if r >= 480 and r < 660:
                lH = max(lH, H[k]); lL = min(lL, L[k])
            if r >= 360 and act[6] == (1 << 30) and aH > -1e17:
                lvl[6] = aH; lvl[7] = aL; act[6] = k; act[7] = k
            if r >= 660 and act[8] == (1 << 30) and lH > -1e17:
                lvl[8] = lH; lvl[9] = lL; act[8] = k; act[9] = k
            for j in range(10):
                if act[j] <= k and tch[j] == (1 << 30):
                    if (sideOf[j] == 1 and H[k] >= lvl[j]) or (sideOf[j] == -1 and L[k] <= lvl[j]):
                        tch[j] = k
        # pass 2: samples
        for k in range(s, e + 1):
            r = rel[k]
            if (r + 1) % step != 0 or r + 1 >= 1380: continue
            Vr = V[k - s]
            if not (Vr > 0): continue
            # per-pool samples
            nTakB = 0; nTakS = 0
            for j in range(10):
                if tch[j] <= k:
                    if sideOf[j] == 1: nTakB += 1
                    else: nTakS += 1
            dayO = O[s]
            for j in range(10):
                if act[j] > k or tch[j] <= k: continue
                sd = sideOf[j]
                dist = (lvl[j] - C[k]) * sd / a
                if dist <= 0: continue
                nb = 0; cf = 0
                for i in range(10):
                    if i == j or act[i] > k or tch[i] <= k or sideOf[i] != sd: continue
                    di = (lvl[i] - C[k]) * sd / a
                    if di > 0 and di < dist: nb += 1
                    if abs(lvl[i] - lvl[j]) / a < 0.15: cf += 1
                opp = nTakS if sd == 1 else nTakB; same = nTakB if sd == 1 else nTakS
                ev = 1.0 if evr[d] > r else 0.0
                y = 1.0 if (tch[j] > k and tch[j] <= e) else 0.0
                rows.append((float(d), float(j), float(typOf[j]), float(sd), float(r + 1), dist, dist / np.sqrt(Vr), float(nb), float(cf), float(opp), float(same), sd * (C[k] - dayO) / a, ev, Vr, y))
            # race: nearest live untouched pool above and below
            jb = -1; js = -1; db = 1e18; dsl = 1e18
            for j in range(10):
                if act[j] > k or tch[j] <= k: continue
                dd = (lvl[j] - C[k]) * sideOf[j] / a
                if dd <= 0: continue
                if sideOf[j] == 1 and dd < db: db = dd; jb = j
                if sideOf[j] == -1 and dd < dsl: dsl = dd; js = j
            if jb >= 0 and js >= 0:
                tb = tch[jb]; ts_ = tch[js]
                if (tb > k and tb <= e) or (ts_ > k and ts_ <= e):
                    if tb != ts_:
                        race.append((float(d), float(r + 1), db, dsl, float(typOf[jb]), float(typOf[js]), float(nTakB), float(nTakS), (C[k] - dayO) / a, 1.0 if tb < ts_ else 0.0))
    A = np.empty((len(rows), 15)); B = np.empty((len(race), 10))
    for i in range(len(rows)):
        for c in range(15): A[i, c] = rows[i][c]
    for i in range(len(race)):
        for c in range(10): B[i, c] = race[i][c]
    return A, B

evd = {}
for lst, rr in [(E.CPI, 870), (E.NFP, 870), (E.FOMC, 1200)]:
    for t in lst: evd[int(pd.Timestamp(t).normalize().value // 86400_000_000_000)] = rr
R1 = []; R2 = []
for sym in ['NQ', 'ES', 'RTY']:
    m = load(sym); rel = (((m['ts'] % 1440) - 1080) % 1440).astype(np.int64); td = m['td'].astype(np.int64)
    b = np.flatnonzero(np.diff(td) != 0) + 1; ds = np.r_[0, b]; de = np.r_[b - 1, len(td) - 1]
    dH = np.maximum.reduceat(m['H'], ds); dL = np.minimum.reduceat(m['L'], ds); dC = m['C'][de]; nb = de - ds + 1
    pc = np.r_[np.nan, dC[:-1]]; tr = np.nanmax(np.c_[dH - dL, np.abs(dH - pc), np.abs(dL - pc)], axis=1)
    atr = np.r_[np.nan, rma(pd.Series(np.where(nb >= 1200, tr, np.nan)).ffill().values)[:-1]]
    days = td[ds]; wk = (days + 3) // 7; dts = pd.to_datetime(days, unit='D'); mo = dts.year * 12 + dts.month
    W = pd.DataFrame({'wk': wk, 'h': dH, 'l': dL}).groupby('wk').agg(h=('h', 'max'), l=('l', 'min'))
    Mo = pd.DataFrame({'mo': mo, 'h': dH, 'l': dL}).groupby('mo').agg(h=('h', 'max'), l=('l', 'min'))
    P0 = np.c_[np.r_[np.nan, dH[:-1]], np.r_[np.nan, dL[:-1]], pd.Series(wk).map(W.h.shift(1)).values, pd.Series(wk).map(W.l.shift(1)).values,
               pd.Series(mo).map(Mo.h.shift(1)).values, pd.Series(mo).map(Mo.l.shift(1)).values]
    evr = np.array([evd.get(int(x), -1) for x in days]).astype(np.int64)
    A, B = run(m['H'], m['L'], m['C'], m['O'], rel, ds, de, atr, P0, evr, PM, 15)
    a = pd.DataFrame(A, columns=['d', 'pool', 'typ', 'side', 'r', 'dist', 'z', 'nb', 'cf', 'opp', 'same', 'tow', 'ev', 'V', 'y'])
    a['td'] = days[a.d.astype(int)]; a['sym'] = sym; a['dow'] = pd.to_datetime(a.td, unit='D').dt.dayofweek; R1.append(a)
    bb = pd.DataFrame(B, columns=['d', 'r', 'dB', 'dS', 'tB', 'tS', 'nTB', 'nTS', 'opn', 'y']); bb['td'] = days[bb.d.astype(int)]; bb['sym'] = sym; R2.append(bb)
    print(sym, len(a), len(bb), flush=True)
pd.concat(R1, ignore_index=True).to_pickle('/home/claude/sn/t15_pools.pkl'); pd.concat(R2, ignore_index=True).to_pickle('/home/claude/sn/t15_race.pkl')
