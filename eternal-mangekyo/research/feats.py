"""Mangekyō research — the zone table with features and matched controls (back-adjusted daily, all four symbols).
Controls: the same three-candle geometry with no gap. For each real gap, 5 windows of the same symbol and direction, within
±2 years, whose candle 2 moved as far (body in ATR) and whose candle 3 closed as far from its own extreme (d0 in ATR); the
pseudo-zone hangs from candle 3's low (bull) / high (bear) with the real gap's width.  Same lifecycle on both."""
import numpy as np, pandas as pd
from data import daily, SYMS
from gaps import detect, lifecycle

def swings(H, L, k=3):
    """Last confirmed swing high / low known at each bar's close (centre k bars back, the extreme of 2k+1 bars)."""
    n = len(H); sh = np.full(n, np.nan); sl = np.full(n, np.nan); ch = cl = np.nan
    for t in range(2 * k, n):
        c = t - k
        if H[c] == H[t - 2 * k:t + 1].max(): ch = H[c]
        if L[c] == L[t - 2 * k:t + 1].min(): cl = L[c]
        sh[t] = ch; sl[t] = cl
    return sh, sl

def features(D, z, ser='b'):
    O, H, L, C = (D[ser + x].values for x in 'ohlc'); A = D.atrB.values; V = D.v.values; VM = D.v_eth.values
    t0 = z.t0.values; d = z.dir.values; c2 = np.where(z.kind.values == 'VI', t0, t0 - 1)
    z = z.copy()
    z['w'] = (z.top - z.bot).values / A[t0]
    near = np.where(d == 1, z.top.values, z.bot.values)
    z['d0'] = (C[t0] - near) * d / A[t0]
    z['c2body'] = (C[c2] - O[c2]) * d / A[t0]
    z['c2rng'] = (H[c2] - L[c2]) / A[t0]
    v20 = pd.Series(V).rolling(20, min_periods=15).mean().shift(1).values
    m20 = pd.Series(VM).rolling(20, min_periods=15).mean().shift(1).values
    z['rv2'] = V[c2] / v20[c2]; z['rv3'] = V[t0] / v20[t0]
    z['rvm2'] = VM[c2] / m20[c2]
    z['rvmax'] = np.fmax(np.fmax(V[np.maximum(t0 - 2, 0)] / v20[np.maximum(t0 - 2, 0)], V[c2] / v20[c2]), V[t0] / v20[t0])
    sh, sl = swings(H, L, 3)
    pre = np.maximum(t0 - 3, 0)                  # structure known before the three candles
    z['brk'] = np.where(d == 1, np.fmax(C[c2], C[t0]) > sh[pre], np.fmin(C[c2], C[t0]) < sl[pre])
    lo3 = np.fmin(L[np.maximum(t0 - 2, 0)], L[c2]); hi3 = np.fmax(H[np.maximum(t0 - 2, 0)], H[c2])
    z['swp'] = np.where(d == 1, lo3 < sl[pre], hi3 > sh[pre])
    r20 = C / pd.Series(C).shift(20).values - 1
    z['trend'] = np.sign(r20[t0]) * d                    # +1 = with the 20-day move
    # weekly context: last week's range and where the near edge sits in it (0 = PWL, 1 = PWH)
    wk = D.wk.values
    W = D.groupby('wk').agg(h=(ser + 'h', 'max'), l=(ser + 'l', 'min'))
    pw = W.shift(1)
    pwh = pw.h.reindex(wk).values; pwl = pw.l.reindex(wk).values
    z['pwpos'] = (near - pwl[t0]) / (pwh[t0] - pwl[t0])
    z['dow'] = D.dow.values[t0]
    z['date'] = D.index[t0]; z['yr'] = D.index[t0].year
    return z

def controls(D, z, ser='b', M=5, seed=7):
    O, H, L, C = (D[ser + x].values for x in 'ohlc'); A = D.atrB.values
    n = len(C); t = np.arange(2, n)
    rng = np.random.default_rng(seed)
    body = (C[t - 1] - O[t - 1]) / A[t]
    out = []
    for dd in (1, -1):
        gap = (L[t] > H[t - 2]) if dd == 1 else (H[t] < L[t - 2])
        ok = (~gap) & np.isfinite(A[t]) & (body * dd > 0)
        ct = t[ok]; cb = body[ok] * dd
        ext = L[ct] if dd == 1 else H[ct]
        cd0 = (C[ct] - ext) * dd / A[ct]
        zz = z[(z.dir == dd) & (z.kind == 'FVG')]
        for r in zz.itertuples():
            m = np.abs(ct - r.t0) <= 504
            m &= np.abs(ct - r.t0) > 3
            if m.sum() < 20: continue
            dist = ((cb[m] - r.c2body) / 0.35) ** 2 + ((cd0[m] - r.d0) / 0.25) ** 2
            pick = np.argsort(dist + rng.random(m.sum()) * 1e-9)[:M]
            for j in ct[m][pick]:
                a = A[j]; e = L[j] if dd == 1 else H[j]
                top, bot = (e, e - r.w * a) if dd == 1 else (e + r.w * a, e)
                out.append((j, dd, 'CTL', top, bot, j - 2, r.Index))
    return pd.DataFrame(out, columns=['t0', 'dir', 'kind', 'top', 'bot', 't1', 'of'])

if __name__ == '__main__':
    R = []; Q = []
    for s in SYMS:
        D = daily(s)
        O, H, L, C = (D['b' + x].values for x in 'ohlc'); A = D.atrB.values
        z = detect(O, H, L, C, A)
        z = lifecycle(z, O, H, L, C, A)
        z = features(D, z)
        z['sym'] = s; z.index = [f'{s}{i}' for i in range(len(z))]
        q = controls(D, z)
        q = lifecycle(q, O, H, L, C, A)
        q = features(D, q); q['sym'] = s
        R.append(z); Q.append(q)
        print(s, len(z), (z.kind == 'FVG').sum(), 'controls', len(q))
    R = pd.concat(R); Q = pd.concat(Q, ignore_index=True)
    R.to_pickle('/home/claude/mgk/zones.pkl'); Q.to_pickle('/home/claude/mgk/ctl.pkl')
