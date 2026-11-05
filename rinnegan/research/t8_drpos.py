"""T8: live dealing-range odds by position. Same ranges as T1 (sweep swing → expansion swing, ST and IT, 5m/15m/60m, NQ/ES/RTY).
From the confirmation bar, at every bar until 0 or 100 trades (cap 120 units): p = (close − 100) / (0 − 100) in the range
(0 at the sweep extreme, 1 at the expansion extreme) and whether 0 traded before 100. Calibration by p decile; the
random-walk answer is P = p."""
import numpy as np, pandas as pd, sys
from numba import njit
sys.path.insert(0, '/home/claude/lr')
from lib import load, bars, neg, D2025
import t1_dr


@njit(cache=True)
def pos_rows(H, L, C, ct, idx, tops, bots, cap):
    out = []
    for r in range(len(idx)):
        t = idx[r]; top = tops[r]; bot = bots[r]
        res = -1; endk = -1
        for k in range(t + 1, min(t + cap, len(H))):
            if ct[k] != ct[t]: break
            up = H[k] > top; dn = L[k] < bot
            if up and dn: res = -1; endk = k; break
            if up: res = 1; endk = k; break
            if dn: res = 0; endk = k; break
        if res < 0: continue
        for k in range(t, endk):
            p = (C[k] - bot) / (top - bot)
            if p >= 0 and p <= 1:
                out.append((float(r), float(k - t), p, float(res)))
    a = np.empty((len(out), 4))
    for i in range(len(out)):
        for j in range(4): a[i, j] = out[i][j]
    return a


@njit(cache=True)
def ranges(H, L, C, ct, atr, layer):
    """Re-derive T1's ranges (index, top, bottom) without walking them."""
    n = len(H)
    sLp = np.empty(n); sLi = np.empty(n, np.int64); nsl = 0
    sHp = np.empty(n); sHi = np.empty(n, np.int64); nsh = 0
    iLp = np.empty(n); iLi = np.empty(n, np.int64); nil = 0
    usedLow = -1
    I = []; T = []; Bv = []
    for t in range(2, n - 1):
        j = t - 1; newHigh = False; hiIdx = -1
        if L[j] < L[j - 1] and L[j] < L[t]:
            sLp[nsl] = L[j]; sLi[nsl] = j; nsl += 1
            if nsl >= 3 and sLp[nsl - 2] < sLp[nsl - 3] and sLp[nsl - 2] < sLp[nsl - 1]:
                iLp[nil] = sLp[nsl - 2]; iLi[nil] = sLi[nsl - 2]; nil += 1
        if H[j] > H[j - 1] and H[j] > H[t]:
            sHp[nsh] = H[j]; sHi[nsh] = j; nsh += 1
            if layer == 0: newHigh = True; hiIdx = j
            if nsh >= 3 and sHp[nsh - 2] > sHp[nsh - 3] and sHp[nsh - 2] > sHp[nsh - 1]:
                if layer == 1: newHigh = True; hiIdx = sHi[nsh - 2]
        if not newHigh: continue
        if layer == 0:
            q = nsl - 1
            while q >= 0 and sLi[q] >= hiIdx: q -= 1
            if q < 1: continue
            i = sLi[q]; pl = sLp[q]; pl2 = sLp[q - 1]
        else:
            q = nil - 1
            while q >= 0 and iLi[q] >= hiIdx: q -= 1
            if q < 1: continue
            i = iLi[q]; pl = iLp[q]; pl2 = iLp[q - 1]
        if i == usedLow or not (pl < pl2): continue
        if ct[i] != ct[t] or not (atr[t] > 0): continue
        top = -1e18; bot = 1e18
        for k in range(i, t + 1):
            if H[k] > top: top = H[k]
            if L[k] < bot: bot = L[k]
        if bot < pl: continue
        usedLow = i
        if (top - bot) / atr[t] < 0.25: continue
        I.append(t); T.append(top); Bv.append(bot)
    return np.array(I), np.array(T), np.array(Bv)


res = []
for sym in ['NQ', 'ES', 'RTY']:
    m = load(sym)
    for u in [5, 15, 60]:
        B = bars(m, u)
        for layer in [0, 1]:
            for side, BB in [(1, B), (-1, neg(B))]:
                I, T, Bv = ranges(BB['H'], BB['L'], BB['C'], BB['ct'], BB['atr'], layer)
                A = pos_rows(BB['H'], BB['L'], BB['C'], BB['ct'], I, T, Bv, 120)
                df = pd.DataFrame(A, columns=['r', 'age', 'p', 'y'])
                df['td'] = B['td'][I[df.r.astype(int)]]; df['sym'] = sym; df['u'] = u; df['lay'] = layer; df['side'] = side
                res.append(df.sample(frac=0.25, random_state=1) if len(df) > 400000 else df)
    print(sym, flush=True)
D = pd.concat(res, ignore_index=True)
D['era'] = np.where(D.td >= D2025, 'score', 'fish')
D['pb'] = np.minimum((D.p * 10).astype(int), 9)
t = D.groupby(['era', 'pb']).y.mean().unstack(0) * 100
t['mid'] = (t.index + 0.5) * 10
print(t.round(1))
print(D.groupby(['era', 'lay', 'u']).apply(lambda d: np.mean(d.y - d.p)).round(3))
D[['era', 'pb', 'y', 'lay', 'u', 'sym', 'td']].to_pickle('/home/claude/lr/t8_rows.pkl')
