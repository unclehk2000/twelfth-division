"""T1: fadi 'ICT Dealing Range Pro' claims, written from scratch.
Bull range: a swing low that sweeps the previous swing low (100) → the next confirmed swing high (0 = highest high of the leg).
One range per sweep low, formed when that swing high is confirmed. Bear = same code on mirrored prices.
Forward (horizon units): 0 broken before the 50% touch = 'direct'; after the 50% touch, 0 broken first = 'complete' (fadi),
100 taken first = 'invalid'. Tip 1: no bull FVG reaching the discount half inside the leg → 100 fails more often.
Tip 2: narrow (consolidation) ranges get both sides swept. Null: per-bar sign flip from the confirmation close, 4 replicates."""
import numpy as np, pandas as pd, sys
from numba import njit
sys.path.insert(0, '/home/claude/lr')
from lib import load, bars, neg, flipbar, cse, fmt, D2025

NREP = 4


@njit(cache=True)
def walk(H, L, C, ct, t, hz, top, mid, bot, rep):
    """rep < 0: real path. Returns (outcome, both)."""
    n = len(H)
    end = min(t + hz, n - 1)
    touched = False; out = 4; upB = False; dnB = False; done = False
    cp = C[t]
    for k in range(t + 1, end + 1):
        if ct[k] != ct[t]:
            break
        if rep < 0:
            h = H[k]; l = L[k]
        else:
            h, l, cp = flipbar(H, L, C, k, cp, rep)
        if h > top:
            upB = True
        if l < bot:
            dnB = True
        if not done:
            if not touched:
                if h > top and l <= mid:
                    out = 5; done = True
                elif h > top:
                    out = 0; done = True
                elif l <= mid:
                    touched = True; out = 3
                    if l < bot:
                        out = 2; done = True
            else:
                if h > top and l < bot:
                    out = 5; done = True
                elif h > top:
                    out = 1; done = True
                elif l < bot:
                    out = 2; done = True
        if done and upB and dnB:
            break
    return out, (upB and dnB)


@njit(cache=True)
def scan(H, L, C, ct, atr, layer, hz, nrep):
    n = len(H)
    sLp = np.empty(n); sLi = np.empty(n, np.int64); nsl = 0
    sHp = np.empty(n); sHi = np.empty(n, np.int64); nsh = 0
    iLp = np.empty(n); iLi = np.empty(n, np.int64); nil = 0
    iHp = np.empty(n); iHi = np.empty(n, np.int64); nih = 0
    usedLow = -1
    rows = []
    for t in range(2, n - 1):
        j = t - 1
        newHigh = False; hiIdx = -1
        if L[j] < L[j - 1] and L[j] < L[t]:
            sLp[nsl] = L[j]; sLi[nsl] = j; nsl += 1
            if nsl >= 3 and sLp[nsl - 2] < sLp[nsl - 3] and sLp[nsl - 2] < sLp[nsl - 1]:
                iLp[nil] = sLp[nsl - 2]; iLi[nil] = sLi[nsl - 2]; nil += 1
        if H[j] > H[j - 1] and H[j] > H[t]:
            sHp[nsh] = H[j]; sHi[nsh] = j; nsh += 1
            if layer == 0:
                newHigh = True; hiIdx = j
            if nsh >= 3 and sHp[nsh - 2] > sHp[nsh - 3] and sHp[nsh - 2] > sHp[nsh - 1]:
                iHp[nih] = sHp[nsh - 2]; iHi[nih] = sHi[nsh - 2]; nih += 1
                if layer == 1:
                    newHigh = True; hiIdx = sHi[nsh - 2]
        if not newHigh:
            continue
        # the latest swing low before the swing high, and the one before it
        if layer == 0:
            q = nsl - 1
            while q >= 0 and sLi[q] >= hiIdx:
                q -= 1
            if q < 1:
                continue
            i = sLi[q]; pl = sLp[q]; pl2 = sLp[q - 1]
        else:
            q = nil - 1
            while q >= 0 and iLi[q] >= hiIdx:
                q -= 1
            if q < 1:
                continue
            i = iLi[q]; pl = iLp[q]; pl2 = iLp[q - 1]
        if i == usedLow or not (pl < pl2):
            continue
        if ct[i] != ct[t] or not (atr[t] > 0):
            continue
        top = -1e18; bot = 1e18
        for k in range(i, t + 1):
            if H[k] > top:
                top = H[k]
            if L[k] < bot:
                bot = L[k]
        if bot < pl:
            continue
        usedLow = i
        w = (top - bot) / atr[t]
        if w < 0.25:
            continue
        mid = 0.5 * (top + bot)
        fvg = 0
        for m in range(i + 2, t + 1):
            if L[m] > H[m - 2] and H[m - 2] < mid:
                fvg = 1
                break
        o, b = walk(H, L, C, ct, t, hz, top, mid, bot, -1)
        r = [float(t), w, float(fvg), float(o), 1.0 if b else 0.0]
        for rep in range(nrep):
            o2, b2 = walk(H, L, C, ct, t, hz, top, mid, bot, rep)
            r.append(float(o2)); r.append(1.0 if b2 else 0.0)
        rows.append(r)
    out = np.empty((len(rows), 5 + 2 * nrep))
    for a in range(len(rows)):
        for c in range(5 + 2 * nrep):
            out[a, c] = rows[a][c]
    return out


if __name__ == '__main__':
    res = []
    for sym in ['NQ', 'ES', 'RTY']:
        m = load(sym)
        for u in [5, 15, 60]:
            B = bars(m, u)
            for layer, hz in [(0, 60), (1, 120)]:
                for side, BB in [(1, B), (-1, neg(B))]:
                    R = scan(BB['H'], BB['L'], BB['C'], BB['ct'], BB['atr'], layer, hz, NREP)
                    df = pd.DataFrame(R[:, :5], columns=['t', 'w', 'fvg', 'o', 'both'])
                    for rep in range(NREP):
                        df[f'o{rep}'] = R[:, 5 + 2 * rep]; df[f'b{rep}'] = R[:, 6 + 2 * rep]
                    df['td'] = B['td'][df.t.astype(int)]
                    df['sym'] = sym; df['u'] = u; df['layer'] = 'ST' if layer == 0 else 'IT'; df['side'] = side
                    res.append(df)
            print(sym, u, flush=True)
    D = pd.concat(res, ignore_index=True)
    D.to_pickle('/home/claude/lr/t1_rows.pkl')
    print(len(D))
