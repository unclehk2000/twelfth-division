"""T11: TheMas7er / bmistiaen "DR/IDR" claims, written from scratch. Sessions (ET): RDR 09:30–10:30 → lines to 16:00,
ODR 03:00–04:00 → 08:30, ADR 19:30–20:30 → 02:00. DR = the hour's wick high/low (1m); IDR = the high/low of its 5-minute
bodies. Confirmation = the first 5-minute close beyond the DR after the hour (long above, short below).
From the confirmation candle's close to the session end:
  A  the opposite DR side traded (or closed beyond on 5m)  — "the DR rule: the other side holds";
  B  price back into the IDR (long: low ≤ IDR high);
  C  furthest extension beyond the IDR in IDR widths (the 0.5 'STD' steps);
  D  the session's last close beyond the IDR mid the confirmed way.
E: the hour's colour (close vs open) and the side confirmed.
Null: per-bar sign flip from the confirmation close (4 replicates); for E, from the hour's last close."""
import numpy as np, pandas as pd, sys
from numba import njit
sys.path.insert(0, '/home/claude/lr')
from lib import load, coin, D2025
NREP = 4
SESS = {'RDR': (930, 990, 1320), 'ODR': (540, 600, 870), 'ADR': (90, 150, 480)}   # minutes after 18:00: start, end, lines end
STEPS = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0])


@njit(cache=True)
def path(O, H, L, C, rel, a, e, rep, dr, dH, dL, iH, iL, conf):
    """Walk bars a..e (inclusive) from the close of bar a-1 (real if rep < 0). dr = +1 long / −1 short.
    Returns (oppTraded, oppClosed5, idrBack, maxExtIDR, lastClose, firstSide) — firstSide for conf == 0 (E test)."""
    cp = C[a - 1]
    opT = 0; opC = 0; back = 0; ext = 0.0; w = iH - iL; side = 0
    for j in range(a, e + 1):
        if rep < 0:
            h = H[j]; l = L[j]; c = C[j]
        else:
            ee = coin(j, rep)
            if ee > 0:
                h = cp + (H[j] - C[j - 1]); l = cp + (L[j] - C[j - 1]); c = cp + (C[j] - C[j - 1])
            else:
                h = cp - (L[j] - C[j - 1]); l = cp - (H[j] - C[j - 1]); c = cp - (C[j] - C[j - 1])
        cp = c
        five = (rel[j] + 1) % 5 == 0          # last minute of a 5-minute candle (5m candles aligned to 18:00)
        if conf == 0:
            if five and side == 0:
                if c > dH: side = 1
                elif c < dL: side = -1
            if side != 0: break
            continue
        if dr == 1:
            if l <= dL: opT = 1
            if five and c < dL: opC = 1
            if l <= iH: back = 1
            x = (h - iH) / w
        else:
            if h >= dH: opT = 1
            if five and c > dH: opC = 1
            if h >= iL: back = 1
            x = (iL - l) / w
        if x > ext: ext = x
    return opT, opC, back, ext, cp, side


@njit(cache=True)
def run(O, H, L, C, rel, td, s0, s1, s2, nrep):
    n = len(O); rows = []
    i = 0
    while i < n:
        d = td[i]; j = i
        while j < n and td[j] == d: j += 1
        # bars of this trading day: i..j-1
        a = -1; b = -1; e = -1
        for k in range(i, j):
            if rel[k] >= s0 and a < 0: a = k
            if rel[k] < s1: b = k
            if rel[k] < s2: e = k
        if a >= 0 and b > a and e > b and rel[a] - s0 < 3 and s1 - rel[b] < 3 and s2 - rel[e] < 15:
            dH = -1e18; dL = 1e18; iH = -1e18; iL = 1e18; o5 = O[a]
            for k in range(a, b + 1):
                if H[k] > dH: dH = H[k]
                if L[k] < dL: dL = L[k]
                if (rel[k] - s0) % 5 == 0: o5 = O[k]
                if (rel[k] + 1) % 5 == 0 or k == b:
                    if max(o5, C[k]) > iH: iH = max(o5, C[k])
                    if min(o5, C[k]) < iL: iL = min(o5, C[k])
            if iH > iL and dH > dL:
                up = 1 if C[b] > O[a] else -1
                posC = (C[b] - dL) / (dH - dL)
                # E: side confirmed first, real and flipped, from the hour's last close
                _, _, _, _, _, sR = path(O, H, L, C, rel, b + 1, e, -1, 0, dH, dL, iH, iL, 0)
                sF = np.zeros(nrep)
                for r in range(nrep):
                    _, _, _, _, _, sx = path(O, H, L, C, rel, b + 1, e, r, 0, dH, dL, iH, iL, 0)
                    sF[r] = sx
                # find the real confirmation candle
                cf = -1; dr = 0
                for k in range(b + 1, e + 1):
                    if (rel[k] + 1) % 5 == 0:
                        if C[k] > dH: cf = k; dr = 1; break
                        if C[k] < dL: cf = k; dr = -1; break
                r0 = [float(d), float(up), posC, float(sR)] + [sF[r] for r in range(nrep)]
                r0 += [float(dr), float(rel[cf]) if cf >= 0 else -1.0, (dH - dL), (iH - iL), dH, dL, iH, iL]
                if cf >= 0 and cf < e:
                    oT, oC, bk, ex, lc, _ = path(O, H, L, C, rel, cf + 1, e, -1, dr, dH, dL, iH, iL, 1)
                    mid = 0.5 * (iH + iL)
                    r0 += [float(oT), float(oC), float(bk), ex, 1.0 if (lc - mid) * dr > 0 else 0.0]
                    for r in range(nrep):
                        oT, oC, bk, ex, lc, _ = path(O, H, L, C, rel, cf + 1, e, r, dr, dH, dL, iH, iL, 1)
                        r0 += [float(oT), float(oC), float(bk), ex, 1.0 if (lc - mid) * dr > 0 else 0.0]
                else:
                    r0 += [np.nan] * (5 * (nrep + 1))
                rows.append(r0)
        i = j
    out = np.full((len(rows), len(rows[0]) if rows else 1), np.nan)
    for q in range(len(rows)):
        for c in range(len(rows[q])): out[q, c] = rows[q][c]
    return out


if __name__ == '__main__':
    cols = ['td', 'up', 'posC', 'sR'] + [f'sF{r}' for r in range(NREP)] + ['dr', 'cfRel', 'drW', 'idrW', 'dH', 'dL', 'iH', 'iL']
    for p in [''] + [f'_{r}' for r in range(NREP)]:
        cols += [f'oT{p}', f'oC{p}', f'bk{p}', f'ex{p}', f'cl{p}']
    res = []
    for sym in ['NQ', 'ES', 'RTY']:
        m = load(sym)
        rel = ((m['ts'] % 1440) - 1080) % 1440
        for nm, (s0, s1, s2) in SESS.items():
            R = run(m['O'], m['H'], m['L'], m['C'], rel.astype(np.int64), m['td'].astype(np.int64), s0, s1, s2, NREP)
            df = pd.DataFrame(R, columns=cols); df['sym'] = sym; df['sess'] = nm
            res.append(df); print(sym, nm, len(df), flush=True)
    pd.concat(res, ignore_index=True).to_pickle('/home/claude/lr/t11_rows.pkl')
