"""T1–T3 for the LTF IPDA layers. NQ, ES, RTY 1-minute 2018 – 23 Oct 2026. Fished 2018–24, scored 2025–26.
T1 draw: at the start of the current period, each standing look-back high / low (not traded since the anchor) against its mirror
   (the same distance on the other side of the period's open): traded within 20 units, and by the cast-forward end (anchor + 60).
T2 timing: where the high and low of the anchor's +0…+60 window sit, real vs the same window with each unit's move sign-flipped at
   random (keeps the volatility profile, drops direction): share within ±2 of +20 / +40 and at 58–60.
T3 order flow: 60-unit net change before the anchor; which standing 20-unit level (high or low) trades first after the period opens,
   real vs sign-flipped."""
import numpy as np, pandas as pd, sys
from numba import njit
from lay import load, units

rng0 = np.random.default_rng(13)


@njit(cache=True)
def run(O, H, L, C, ct, td, atr, ps, flips):
    out1 = []      # T1 rows: k, td, N, side(+1 hi / -1 lo), d_atr, hit20, hitE, mhit20, mhitE, dup
    out2 = []      # T2 rows: k, td, posH, posL, nposH(3), nposL(3)
    out3 = []      # T3 rows: k, td, flow, first(+1 hi / -1 lo / 0 none), nfirst(3)
    n = len(O)
    for k in range(1, len(ps)):
        a = ps[k - 1]
        s = ps[k]
        e = a + 60
        if a - 61 < 0 or e >= n:
            continue
        if ct[a - 61] != ct[e]:
            continue
        if s - a < 6:
            continue
        A = atr[s]
        if not (A > 0):
            continue
        P0 = O[s]
        h20 = min(s + 19, e)
        # anchor-period extremes
        hiA = H[a]
        loA = L[a]
        for i in range(a, s):
            hiA = max(hiA, H[i])
            loA = min(loA, L[i])
        lv = np.empty(6)
        for j in range(3):
            N = (20, 40, 60)[j]
            hh = H[a - N]
            ll = L[a - N]
            for i in range(a - N, a):
                hh = max(hh, H[i])
                ll = min(ll, L[i])
            lv[j] = hh
            lv[3 + j] = ll
        # T1
        for j in range(6):
            side = 1 if j < 3 else -1
            N = (20, 40, 60)[j % 3]
            lvl = lv[j]
            dup = 0
            for jj in range(j % 3):
                if lv[(0 if side == 1 else 3) + jj] == lvl:
                    dup = 1
            stand = (hiA < lvl) if side == 1 else (loA > lvl)
            if not stand:
                continue
            d = (lvl - P0) * side
            if d <= 0:
                continue
            m = P0 - side * d
            r20 = 0; rE = 0; m20 = 0; mE = 0
            for i in range(s, e + 1):
                hit = (H[i] >= lvl) if side == 1 else (L[i] <= lvl)
                mh = (L[i] <= m) if side == 1 else (H[i] >= m)
                if hit:
                    rE = 1
                    if i <= h20:
                        r20 = 1
                if mh:
                    mE = 1
                    if i <= h20:
                        m20 = 1
            out1.append((float(k), float(td[s]), float(N), float(side), d / A, float(r20), float(rE), float(m20), float(mE), float(dup)))
        # T2: positions in the anchor's 0..60 window, real and sign-flipped
        bh = a; bl = a
        for i in range(a, e + 1):
            if H[i] > H[bh]:
                bh = i
            if L[i] < L[bl]:
                bl = i
        nposH = np.zeros(3); nposL = np.zeros(3)
        for r in range(3):
            c = C[a - 1]
            mx = -1e18; mn = 1e18; ph = 0; pl = 0
            for i in range(a, e + 1):
                dH = H[i] - C[i - 1]; dL = L[i] - C[i - 1]; dC = C[i] - C[i - 1]
                if flips[r, (k * 61 + i - a) % flips.shape[1]]:
                    dH, dL, dC = -dL, -dH, -dC
                hh = c + dH; ll = c + dL; c = c + dC
                if hh > mx:
                    mx = hh; ph = i - a
                if ll < mn:
                    mn = ll; pl = i - a
            nposH[r] = ph; nposL[r] = pl
        out2.append((float(k), float(td[s]), float(bh - a), float(bl - a), nposH[0], nposH[1], nposH[2], nposL[0], nposL[1], nposL[2]))
        # T3: 60-unit order flow before the anchor; which standing 20-unit side trades first after s
        if hiA < lv[0] and loA > lv[3] and lv[0] > P0 and lv[3] < P0:
            flow = C[a - 1] - C[a - 61]
            first = 0
            for i in range(s, e + 1):
                th = H[i] >= lv[0]; tl = L[i] <= lv[3]
                if th and tl:
                    first = 9
                    break
                if th:
                    first = 1
                    break
                if tl:
                    first = -1
                    break
            nf = np.zeros(3)
            for r in range(3):
                c = C[s - 1]
                f = 0
                for i in range(s, e + 1):
                    dH = H[i] - C[i - 1]; dL = L[i] - C[i - 1]; dC = C[i] - C[i - 1]
                    if flips[r, (k * 61 + i - s + 7) % flips.shape[1]]:
                        dH, dL, dC = -dL, -dH, -dC
                    hh = c + dH; ll = c + dL; c = c + dC
                    th = hh >= lv[0]; tl = ll <= lv[3]
                    if th and tl:
                        f = 9
                        break
                    if th:
                        f = 1
                        break
                    if tl:
                        f = -1
                        break
                nf[r] = f
            out3.append((float(k), float(td[s]), flow, float(first), nf[0], nf[1], nf[2]))
    return out1, out2, out3


if __name__ == '__main__':
    flips = rng0.random((3, 100003)) < 0.5
    R1, R2, R3 = [], [], []
    for sym in ('NQ', 'ES', 'RTY'):
        m = load(sym)
        for layer in ('H', 'M15', 'M5', 'M1'):
            U = units(m, layer)
            o1, o2, o3 = run(U['O'], U['H'], U['L'], U['C'], U['ct'], U['td'], U['atr'], U['ps'], flips)
            for out, R, cols in ((o1, R1, ['k', 'td', 'N', 'side', 'd', 'h20', 'hE', 'm20', 'mE', 'dup']),
                                 (o2, R2, ['k', 'td', 'pH', 'pL', 'nH0', 'nH1', 'nH2', 'nL0', 'nL1', 'nL2']),
                                 (o3, R3, ['k', 'td', 'flow', 'first', 'n0', 'n1', 'n2'])):
                X = pd.DataFrame(out, columns=cols); X['sym'] = sym; X['layer'] = layer; R.append(X)
            print(sym, layer, len(o1), len(o2), len(o3), flush=True)
    for nm, R in (('t1', R1), ('t2', R2), ('t3', R3)):
        X = pd.concat(R, ignore_index=True)
        X['yr'] = pd.to_datetime(X.td.astype('int64'), unit='D').dt.year
        X.to_pickle(f'{nm}_rows.pkl')
