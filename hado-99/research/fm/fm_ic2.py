"""Protected swings, retest matched to the Pine module (1m chart, 15m candles). Bullish; bearish mirrored.
Fixes over fm_ic.py: the horizon ends with C4 (fm_ic ran to the end of C5); tracking starts at the later of the bar after
the CISD and C3's first bar; the setup stops if C2's low breaks first (the module marks it XC2 and stops), and a CISD in
C3/C4 only counts if C2's low held until it. Baseline: every 3-bar swing low marked in the two candles after a plain candle.
python3 -I fm_ic2.py SYM"""
import sys, numpy as np, pandas as pd
S = sys.argv[1]
B = pd.read_pickle(f'/home/claude/kyw/bars_{S}_all.pkl')
B = B[B.ts >= '2018-01-02'].reset_index(drop=True)
O, H, L, Cl = (B[k].to_numpy(float) for k in ('Open', 'High', 'Low', 'Close'))
E = pd.read_pickle(f'/home/claude/xa/fm/E_{S}_15.pkl')
key = B.ts.dt.floor('15min').to_numpy()
starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
ends = np.r_[starts[1:], len(B)] - 1
endOf = dict(zip(pd.DatetimeIndex(key[starts]), ends))
step = pd.Timedelta(minutes=15)
def win(t0):
    """rows of C3 start and C4 end (exclusive) for the candle starting at t0, or None when C3/C4 are missing"""
    e2, e3, e4 = endOf.get(t0), endOf.get(t0 + step), endOf.get(t0 + 2 * step)
    if e2 is None or e3 is None or e4 is None:
        return None
    return e2 + 1, e4 + 1
def protect(s0, jEnd, bull, ext):
    pending = False
    for m in range(s0, jEnd):
        if (L[m] < ext) if bull else (H[m] > ext):
            return None                                   # C2's extreme broke first: XC2
        if not pending:
            if (Cl[m] < O[m]) if bull else (Cl[m] > O[m]):
                pending = True; a = m; lvl = O[m]; ex = L[m] if bull else H[m]; exI = m
        else:
            if (L[m] < ex) if bull else (H[m] > ex):
                ex = L[m] if bull else H[m]; exI = m
                j = m; best = None
                while j >= a:
                    isOpp = (Cl[j] < O[j]) if bull else (Cl[j] > O[j])
                    if not (isOpp or Cl[j] == O[j]):
                        break
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
out = []
C2 = E[(E.kind == 'C2') & (E.jc >= 0) & E.ok4.astype(bool)]
for e in C2.itertuples():
    bull = e.side == 'bull'
    w = win(pd.Timestamp(e.t0))
    if w is None:
        continue
    c3, jEnd = w
    jc = int(e.jc)
    if jc >= jEnd:
        continue
    if jc >= c3:                                          # CISD in C3/C4: C2's extreme must hold until it
        if (L[c3:jc + 1].min() < e.ext) if bull else (H[c3:jc + 1].max() > e.ext):
            continue
    r = protect(max(jc + 1, c3), jEnd, bull, e.ext)
    if r is None:
        continue
    t, m = r
    if m + 1 >= jEnd:
        continue
    P = L[t] if bull else H[t]
    held = (L[m + 1:jEnd].min() >= P) if bull else (H[m + 1:jEnd].max() <= P)
    out.append(dict(tday=e.tday, kind='protected', side=e.side, held=held, h=jEnd - m - 1, dist=abs(Cl[m] - P) / e.rng2, early=e.cisd_in_c2))
rng = np.random.default_rng(7)
Bs = E[(E.kind == 'base') & E.ok4.astype(bool) & (E.rng2 > 0)]
Bs = Bs.iloc[rng.random(len(Bs)) < 0.10]
for e in Bs.itertuples():
    bull = e.side == 'bull'
    w = win(pd.Timestamp(e.t0))
    if w is None:
        continue
    a, jEnd = w
    for t in range(a + 1, jEnd - 2):
        if (L[t] <= L[t - 1] and L[t] <= L[t + 1]) if bull else (H[t] >= H[t - 1] and H[t] >= H[t + 1]):
            P = L[t] if bull else H[t]; m = t + 1
            held = (L[m + 1:jEnd].min() >= P) if bull else (H[m + 1:jEnd].max() <= P)
            out.append(dict(tday=e.tday, kind='swing', side=e.side, held=held, h=jEnd - m - 1, dist=abs(Cl[m] - P) / e.rng2, early=False))
R = pd.DataFrame(out); R['sym'] = S
R.to_pickle(f'/home/claude/xa/fm/IC2_{S}.pkl')
print(S, R.groupby('kind').agg(n=('held', 'size'), held=('held', 'mean'), h=('h', 'mean'), dist=('dist', 'median')).round(3).to_string())
