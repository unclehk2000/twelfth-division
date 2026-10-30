"""Protected swings (own definition, from the IC-CISD description), 1m–15m pair.
After the CISD confirms (bullish; bearish mirrored), the first down-closing 1-minute bar arms a level at its open; the
level follows the open of the down-run into each new low. When a later bar closes above the level, the lowest 3-bar
swing low between the arming bar and that close is the protected swing. Outcome: it holds to the end of C4.
Baseline: every 3-bar swing low that forms in C3–C4 after a plain (non-C2) candle, with the same horizon control.
python3 fm_ic.py SYM"""
import sys, numpy as np, pandas as pd
S = sys.argv[1]
B = pd.read_pickle(f'/home/claude/kyw/bars_{S}_all.pkl')
B = B[B.ts >= '2018-01-02'].reset_index(drop=True)
O, H, L, Cl = (B[k].to_numpy(float) for k in ('Open', 'High', 'Low', 'Close'))
ts = B.ts.to_numpy()
E = pd.read_pickle(f'/home/claude/xa/fm/E_{S}_15.pkl')
key = B.ts.dt.floor('15min').to_numpy()
# last 1-minute row of each 15-minute bucket, by bucket start
starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
ends = np.r_[starts[1:], len(B)] - 1
bucket = pd.Series(ends, index=pd.DatetimeIndex(key[starts]))
def end_row(t):            # last 1-minute row of the 15-minute candle starting at t
    return bucket.get(t, -1)
step = pd.Timedelta(minutes=15)
out = []
def protect(jc, jEnd, bull):
    pending = False
    for m in range(jc + 1, jEnd):
        if not pending:
            if (Cl[m] < O[m]) if bull else (Cl[m] > O[m]):
                pending = True; a = m; lvl = O[m]; ex = L[m] if bull else H[m]; exI = m
        else:
            newEx = (L[m] < ex) if bull else (H[m] > ex)
            if newEx:
                ex = L[m] if bull else H[m]; exI = m
                # re-anchor: highest open of the opposite run into the new extreme
                j = m; best = None
                while j > a - 1 and j >= 0 and (((Cl[j] < O[j]) if bull else (Cl[j] > O[j])) or Cl[j] == O[j]):
                    best = O[j] if best is None else (max(best, O[j]) if bull else min(best, O[j])); j -= 1
                if best is not None:
                    lvl = best
            if m > exI and ((Cl[m] > lvl) if bull else (Cl[m] < lvl)):
                sw = [t for t in range(max(a, 1), m) if ((L[t] <= L[t - 1] and L[t] <= L[t + 1]) if bull else (H[t] >= H[t - 1] and H[t] >= H[t + 1]))]
                if sw:
                    t = min(sw, key=lambda t: L[t]) if bull else max(sw, key=lambda t: H[t])
                    return t, m
                pending = False
    return None
# protected swings from C2 setups whose CISD confirmed
C2 = E[(E.kind == 'C2') & (E.jc >= 0)]
for _, e in C2.iterrows():
    bull = e.side == 'bull'
    t0 = pd.Timestamp(e.t0)
    jEnd = end_row(t0 + 3 * step) + 1 if e.ok4 else end_row(t0 + 2 * step) + 1
    if jEnd <= 0:
        continue
    jc = int(e.jc)
    r = protect(jc, jEnd, bull)
    if r is None:
        continue
    t, m = r
    P = L[t] if bull else H[t]
    if m + 1 >= jEnd:
        continue
    held = (L[m + 1:jEnd].min() >= P) if bull else (H[m + 1:jEnd].max() <= P)
    out.append(dict(tday=e.tday, kind='protected', side=e.side, held=held, h=jEnd - m - 1, dist=abs(Cl[m] - P)))
# baseline: 3-bar swings after plain candles (10% sample), during the next two candles
rng = np.random.default_rng(7)
Bs = E[(E.kind == 'base') & E.ok4.astype(bool)]
Bs = Bs.iloc[rng.random(len(Bs)) < 0.10]
for _, e in Bs.iterrows():
    bull = e.side == 'bull'
    t0 = pd.Timestamp(e.t0)
    a = end_row(t0) + 1; jEnd = end_row(t0 + 3 * step) + 1
    if a <= 0 or jEnd <= a + 2:
        continue
    for t in range(a + 1, jEnd - 1):
        if (L[t] <= L[t - 1] and L[t] <= L[t + 1]) if bull else (H[t] >= H[t - 1] and H[t] >= H[t + 1]):
            P = L[t] if bull else H[t]
            m = t + 1
            if m + 1 >= jEnd:
                continue
            held = (L[m + 1:jEnd].min() >= P) if bull else (H[m + 1:jEnd].max() <= P)
            out.append(dict(tday=e.tday, kind='swing', side=e.side, held=held, h=jEnd - m - 1, dist=abs(Cl[m] - P)))
R = pd.DataFrame(out); R['sym'] = S
R.to_pickle(f'/home/claude/xa/fm/IC_{S}.pkl')
print(S, R.groupby('kind').agg(n=('held', 'size'), held=('held', 'mean'), h=('h', 'mean')).round(3).to_string())
