"""T6: SMT at the LTF IPDA look-back sweeps. When the primary first trades through a standing 20- or 60-unit look-back high (low)
after the period opens, did its pair take its own matching level in the same unit (no SMT) or not (SMT)? Outcome from the sweep
unit's close: down 1 unit-ATR (a reversal) before up 1 unit-ATR beyond the sweep unit's extreme, within 40 units.
NQ/ES, ES/NQ, RTY/ES, layers H, M15, M5. Lows run on negated prices. Fished 2018–24, scored 2025–26."""
import numpy as np, pandas as pd
from numba import njit
from lay import load, period_key


@njit(cache=True)
def run(O, H, L, C, pH, pL, ct, atr, ps, td):
    out = []
    n = len(O)
    for k in range(1, len(ps)):
        a = ps[k - 1]; s = ps[k]; e = a + 60
        if a - 61 < 0 or e + 41 >= n or ct[a - 61] != ct[e + 41] or s - a < 6:
            continue
        A = atr[s]
        if not (A > 0):
            continue
        hiA = -1e18; phA = -1e18
        for i in range(a, s):
            hiA = max(hiA, H[i]); phA = max(phA, pH[i])
        for N in (20, 60):
            lv = -1e18; plv = -1e18
            for i in range(a - N, a):
                lv = max(lv, H[i]); plv = max(plv, pH[i])
            if not (hiA < lv and phA < plv and lv > O[s]):
                continue
            u = -1
            for i in range(s, e + 1):
                if H[i] >= lv:
                    u = i
                    break
            if u < 0:
                continue
            smt = 0.0 if pH[u] >= plv else 1.0
            # pair already through earlier in the period?
            for i in range(s, u):
                if pH[i] >= plv:
                    smt = -1.0
                    break
            ref = C[u]; ext = H[u]; res = 0.0
            for i in range(u + 1, min(u + 41, n)):
                dn = L[i] <= ref - A; up = H[i] >= ext + A
                if dn and up:
                    res = 0.5
                    break
                if dn:
                    res = 1.0
                    break
                if up:
                    res = -1.0
                    break
            out.append((float(k), float(td[s]), float(N), smt, res))
    return out


if __name__ == '__main__':
    rows = []
    for sym, pr in (('NQ', 'ES'), ('ES', 'NQ'), ('RTY', 'ES')):
        A_ = load(sym); B_ = load(pr)
        ts, ia, ib = np.intersect1d(A_['ts'], B_['ts'], return_indices=True)
        for layer, u in (('H', 60), ('M15', 15), ('M5', 5)):
            for side in (1, -1):
                O, H, L, C = (A_['O'][ia], A_['H'][ia], A_['L'][ia], A_['C'][ia]) if side == 1 else (-A_['O'][ia], -A_['L'][ia], -A_['H'][ia], -A_['C'][ia])
                bH, bL = (B_['H'][ib], B_['L'][ib]) if side == 1 else (-B_['L'][ib], -B_['H'][ib])
                ct = A_['ct'][ia]; td = A_['td'][ia]
                key = ts // u
                brk = np.flatnonzero((np.diff(key) != 0) | (np.diff(ct) != 0)) + 1; st = np.r_[0, brk]; en = np.r_[brk - 1, len(key) - 1]
                uO, uH, uL, uC = O[st], np.maximum.reduceat(H, st), np.minimum.reduceat(L, st), C[en]
                upH, upL = np.maximum.reduceat(bH, st), np.minimum.reduceat(bL, st)
                uts, uct, utd = ts[st], ct[st].astype(np.int64), td[st].astype(np.int64)
                P = period_key(layer, uts, utd); ps = np.r_[0, np.flatnonzero(np.diff(P) != 0) + 1]
                rg = uH - uL; c = np.cumsum(np.r_[0, rg]); atr = np.full(len(rg), np.nan); atr[14:] = (c[14:-1] - c[:-15]) / 14
                o = run(uO, uH, uL, uC, upH, upL, uct, atr, ps, utd)
                X = pd.DataFrame(o, columns=['k', 'td', 'N', 'smt', 'res']); X['sym'] = sym; X['layer'] = layer; X['side'] = side
                rows.append(X)
                print(sym, layer, side, len(X), flush=True)
    X = pd.concat(rows, ignore_index=True)
    X['yr'] = pd.to_datetime(X.td.astype('int64'), unit='D').dt.year
    X.to_pickle('t6_rows.pkl')
