"""Mangekyō research — daily gap detection and lifecycle.
FVG (three candles, known at candle 3's close):  bull  L3 > H1 → zone [H1, L3];  bear  H3 < L1 → zone [H3, L1].
VI (two candles, body gap):  bull  min(O,C)2 > max(O,C)1 → zone [max(O,C)1, min(O,C)2];  bear the mirror.
  'void' = the wicks do not overlap either (a full gap).
SB (suspension block): a candle with a VI on both sides, same direction → zone [body top of the candle before, body
  bottom of the candle after] (bull), ICT's 'volume imbalance at the high and at the low'.
Near edge = the side price left from (top of a bull zone), far edge = the other side.  CE = the midpoint."""
import numpy as np, pandas as pd

def detect(O, H, L, C, A, kinds=('FVG', 'VI', 'SB')):
    n = len(C); bt = np.maximum(O, C); bb = np.minimum(O, C)
    Z = []
    for t in range(2, n):
        if not np.isfinite(A[t]) or A[t] <= 0: continue
        if 'FVG' in kinds:
            if L[t] > H[t - 2]:
                Z.append((t, 1, 'FVG', L[t], H[t - 2], t - 2))
            elif H[t] < L[t - 2]:
                Z.append((t, -1, 'FVG', L[t - 2], H[t], t - 2))
    for t in range(1, n):
        if not np.isfinite(A[t]) or A[t] <= 0: continue
        if 'VI' in kinds:
            if bb[t] > bt[t - 1]:
                Z.append((t, 1, 'VI', bb[t], bt[t - 1], t - 1))
            elif bt[t] < bb[t - 1]:
                Z.append((t, -1, 'VI', bb[t - 1], bt[t], t - 1))
        if 'SB' in kinds and t >= 2:
            if bb[t] > bt[t - 1] and bb[t - 1] > bt[t - 2]:
                Z.append((t, 1, 'SB', bb[t], bt[t - 2], t - 2))
            elif bt[t] < bb[t - 1] and bt[t - 1] < bb[t - 2]:
                Z.append((t, -1, 'SB', bb[t - 2], bt[t], t - 2))
    z = pd.DataFrame(Z, columns=['t0', 'dir', 'kind', 'top', 'bot', 't1'])
    return z

def lifecycle(z, O, H, L, C, A, horizon=250, k_bounce=1.0, race=20):
    """Per zone: first touch of the near edge, CE, far edge (traded through) and the first close beyond the far edge,
    in trading days after formation; the bounce race from the first touch: does price reach k ATR beyond the near edge
    (in the zone's direction) before a close beyond the far edge, within `race` days after the touch day."""
    n = len(C); out = []
    for r in z.itertuples(index=False):
        t0, d, top, bot = r.t0, r.dir, r.top, r.bot
        near = top if d == 1 else bot; far = bot if d == 1 else top; mid = 0.5 * (top + bot)
        tT = tM = tF = tX = -1; bounce = np.nan; bodyMid = np.nan; deep = np.nan; tB = -1
        end = min(n, t0 + 1 + horizon)
        for t in range(t0 + 1, end):
            lo, hi, cl = L[t], H[t], C[t]
            if d == 1:
                if tT < 0 and lo <= near: tT = t
                if tM < 0 and lo <= mid: tM = t
                if tF < 0 and lo <= far: tF = t
                if tX < 0 and cl < far: tX = t
            else:
                if tT < 0 and hi >= near: tT = t
                if tM < 0 and hi >= mid: tM = t
                if tF < 0 and hi >= far: tF = t
                if tX < 0 and cl > far: tX = t
            if tX >= 0: break
        if tT >= 0:
            a = A[tT]
            # where the touch day closed, in zone units (0 = near edge, 1 = far edge), and how deep it reached
            w = abs(top - bot)
            bodyMid = ((near - C[tT]) * d) / w if w > 0 else np.nan
            deep = ((near - (L[tT] if d == 1 else H[tT])) * d) / w if w > 0 else np.nan
            if (C[tT] - far) * d < 0:
                bounce = 0.0
            else:
                tgt = near + d * k_bounce * a
                bounce = 0.0
                for t in range(tT + 1, min(n, tT + 1 + race)):
                    if (C[t] - far) * d < 0: break
                    if (H[t] >= tgt) if d == 1 else (L[t] <= tgt):
                        bounce = 1.0; tB = t; break
        out.append((tT, tM, tF, tX, bounce, tB, bodyMid, deep))
    o = pd.DataFrame(out, columns=['tT', 'tM', 'tF', 'tX', 'bounce', 'tB', 'bodyPos', 'deep'], index=z.index)
    return pd.concat([z, o], axis=1)
