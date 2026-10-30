"""Python emulation of Mangekyō's daily engine (same rules, same order), to check it against the research detector and
to feed the mock-ups.  Daily candles: back-adjusted settlement closes (SET) and last-trade closes (LST); the newest days
(after the daily table ends) are built from the 1-minute bars (settlement ≈ the 15:59 minute's close)."""
import numpy as np, pandas as pd
from data import daily, atr
def candles(sym, end=None):
    D = daily(sym)[['bo', 'bh', 'bl', 'bc', 'v', 'atrB', 'uc']].copy()
    adj = (D.bc - D.uc)
    import os
    ext = f'/home/claude/kyw/bars_{sym}_ext.pkl'
    b = pd.read_pickle(ext if os.path.exists(ext) else f'/home/claude/kyw/bars_{sym}_all.pkl')
    b = b.sort_values('ts')   # the trading day runs 18:00 (the evening before) → 16:59
    g = b.groupby('tday')
    M = pd.DataFrame({'o': g.Open.first(), 'h': g.High.max(), 'l': g.Low.min(), 'lc': g.Close.last(),
                      's': b[b.hm == 1559].groupby('tday').Close.last(), 'v': g.Volume.sum()})
    M.index = pd.DatetimeIndex(M.index)
    new = M[M.index > D.index[-1]]
    X = pd.DataFrame({'o': D.bo, 'h': D.bh, 'l': D.bl, 's': D.bc, 'v': D.v})
    X['lc'] = (M.lc.reindex(D.index) + adj).values
    N = pd.DataFrame({'o': new.o, 'h': new.h, 'l': new.l, 's': new.s, 'v': new.v, 'lc': new.lc})
    sup = '/home/claude/kyw/nqz26_daily_sup.pkl'      # Barchart's daily NQZ26 table (settlements) for the days after the daily file
    if sym == 'NQ' and os.path.exists(sup):
        S_ = pd.read_pickle(sup); S_ = S_[S_.index.isin(N.index)]
        for k in ('o', 'h', 'l', 's'): N.loc[S_.index, k] = S_[k].astype(float)
    X = pd.concat([X, N]); X['lc'] = X.lc.fillna(X.s)
    if end is not None: X = X[X.index <= end]
    X['atr'] = atr(X.h.values, X.l.values, X.s.values)
    return X
class G(dict): __getattr__ = dict.get
def engine(X, close_col, srcId, minF=0.25, dispF=0.5, minS=0.25, minVI=0.10, useF=True, useS=True, useVI=True, showInv=True):
    O, H, L, V = X.o.values, X.h.values, X.l.values, X.v.values; C = X[close_col].values
    # ATR as Pine: ta.atr(14) on the requested series (its own closes)
    A = atr(H, L, C); T = X.index
    vAvg = pd.Series(V).rolling(20).mean().values
    gs = []; shP = slP = np.nan; out = []
    for i in range(len(C)):
        # i is the daily bar; [k] = i-k
        a1 = A[i - 1] if i >= 1 else np.nan
        if i > 8:
            if H[i - 4] == H[i - 7:i].max(): shP = H[i - 4]
            if L[i - 4] == L[i - 7:i].min(): slP = L[i - 4]
        if i > 25 and np.isfinite(a1) and a1 > 0:
            gs = [g for g in gs if not (g['age'] >= 60 or (g['tX'] is not None and (g['kind'] != 0 or not showInv)) or g.get('tY') is not None)]
            for g in gs:
                g['age'] += 1
                if g['tX'] is None:
                    w = g['top'] - g['bot']
                    if g['dir'] == 1:
                        if g['tT'] is None and L[i - 1] <= g['top']: g['tT'] = T[i - 1]
                        if g['tM'] is None and L[i - 1] <= (g['top'] + g['bot']) / 2: g['tM'] = T[i - 1]
                        if g['tF'] is None and L[i - 1] <= g['bot']: g['tF'] = T[i - 1]
                        if g['tT'] is not None and w > 0: g['dp'] = max(g['dp'] or 0.0, (g['top'] - L[i - 1]) / w)
                        if C[i - 1] < g['bot']: g['tX'] = T[i - 1]
                    else:
                        if g['tT'] is None and H[i - 1] >= g['bot']: g['tT'] = T[i - 1]
                        if g['tM'] is None and H[i - 1] >= (g['top'] + g['bot']) / 2: g['tM'] = T[i - 1]
                        if g['tF'] is None and H[i - 1] >= g['top']: g['tF'] = T[i - 1]
                        if g['tT'] is not None and w > 0: g['dp'] = max(g['dp'] or 0.0, (H[i - 1] - g['bot']) / w)
                        if C[i - 1] > g['top']: g['tX'] = T[i - 1]
                elif g.get('tY') is None and ((g['dir'] == 1 and C[i - 1] > g['top']) or (g['dir'] == -1 and C[i - 1] < g['bot'])):
                    g['tY'] = T[i - 1]
            bt = lambda k: max(O[i - k], C[i - k]); bb = lambda k: min(O[i - k], C[i - k])
            rv2 = V[i - 2] / vAvg[i - 3] if np.isfinite(vAvg[i - 3]) and vAvg[i - 3] > 0 else np.nan
            rv1 = V[i - 1] / vAvg[i - 2] if np.isfinite(vAvg[i - 2]) and vAvg[i - 2] > 0 else np.nan
            brU = np.isfinite(shP) and max(C[i - 1], C[i - 2]) > shP
            brD = np.isfinite(slP) and min(C[i - 1], C[i - 2]) < slP
            def add(kind, d, top, bot, rv, brk, nc):
                k = [3, 2, 1] if nc == 3 else [2, 1]
                g = dict(kind=kind, dir=d, top=top, bot=bot, rv=rv, brk=brk, src=srcId, nc=nc, atr=a1, age=0, tT=None, tM=None, tF=None, tX=None, dp=None,
                         t1=T[i - k[0]], t2=T[i - k[1]], t0=T[i - 1], v2=V[i - k[1]],
                         cand=[(T[i - j], O[i - j], H[i - j], L[i - j], C[i - j]) for j in k])
                mid = k[1]; g['disp'] = (C[i - mid] - O[i - mid]) * d / a1
                gs.append(g)
            if useF:
                if L[i - 1] > H[i - 3] and (L[i - 1] - H[i - 3]) / a1 >= minF and (C[i - 2] - O[i - 2]) / a1 >= dispF: add(0, 1, L[i - 1], H[i - 3], rv2, brU, 3)
                elif H[i - 1] < L[i - 3] and (L[i - 3] - H[i - 1]) / a1 >= minF and (O[i - 2] - C[i - 2]) / a1 >= dispF: add(0, -1, L[i - 3], H[i - 1], rv2, brD, 3)
            if useS:
                if bb(1) > bt(2) and bb(2) > bt(3) and (bb(1) - bt(3)) / a1 >= minS: add(1, 1, bb(1), bt(3), rv2, brU, 3)
                elif bt(1) < bb(2) and bt(2) < bb(3) and (bb(3) - bt(1)) / a1 >= minS: add(1, -1, bb(3), bt(1), rv2, brD, 3)
            if useVI:
                if bb(1) > bt(2) and (bb(1) - bt(2)) / a1 >= minVI: add(2, 1, bb(1), bt(2), rv1, brU, 2)
                elif bt(1) < bb(2) and (bb(2) - bt(1)) / a1 >= minVI: add(2, -1, bb(2), bt(1), rv1, brD, 2)
            gs = gs[-60:]
    return gs, A
def pick(gS, gL, setM):
    if setM in (0, 3): return list(gS)
    if setM == 1: return list(gL)
    out = list(gS)
    for g in gL:
        if g['kind'] == 0: continue
        at = next((j for j, o in enumerate(out) if o['t0'] == g['t0'] and o['dir'] == g['dir'] and o['kind'] == g['kind']), -1)
        if at < 0: out.append(g)
        elif g['top'] - g['bot'] > out[at]['top'] - out[at]['bot']: out[at] = g
    return out
if __name__ == '__main__':
    from gaps import detect
    X = candles('NQ')
    print('NQ daily candles to', X.index[-1].date(), len(X))
    gS, A = engine(X, 's', 0); gL, _ = engine(X, 'lc', 1)
    al = pick(gS, gL, 2)
    print('engine gaps (SET):', len(gS), ' (LST):', len(gL), ' widest union:', len(al))
    for g in sorted(al, key=lambda g: g['t0']):
        print(f"  {['FVG','SB','VI'][g['kind']]} {'bull' if g['dir']==1 else 'bear'} {g['t0'].date()} {g['bot']:.2f}–{g['top']:.2f} w {(g['top']-g['bot'])/g['atr']:.2f} age {g['age']} src {g['src']} tT {g['tT'].date() if g['tT'] is not None else '-'} tX {g['tX'].date() if g['tX'] is not None else '-'} rv {g['rv']:.2f} brk {g['brk']}")
    # cross-check FVG detection against the research detector over the full history (no filters)

def swing_day(X, close_col='s'):
    O, H, L, C = X.o.values, X.h.values, X.l.values, X[close_col].values; out = None
    i = len(X) - 1
    for j in range(3, i + 1):
        swL = L[j - 2] < L[j - 1] and L[j - 2] < L[j - 3]; swH = H[j - 2] > H[j - 1] and H[j - 2] > H[j - 3]
        if swL or swH: out = (O[j - 2], H[j - 2], L[j - 2], C[j - 2], X.index[j - 2], 0 if (swL and swH) else 1 if swL else -1)
    return out
