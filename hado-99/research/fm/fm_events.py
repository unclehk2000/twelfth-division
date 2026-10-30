"""Fractal Model events from 1-minute bars (own definitions, written from the model's description, not from the shared code).
HTF candles: 15 minutes (LTF 1 minute) or the CME trading day 18:00–17:00 (LTF 1 hour). Bullish (bearish mirrored):
  C2   = candle k sweeps C1's low (L2 < L1) and closes back above it (C2 > L1).
  Fail = swept C1's low and closed at or below it.      Base = every other candle.
  CISD = the highest open of the run of down-closing LTF bars that delivered C2's low (up to 10 bars back);
         confirmed by the first LTF close above it after the low. Range r = CISD − C2 low; projections CISD + k·r.
Outcomes on C3 (k+1) and C4 (k+2): take C2's high, take C1's high, C2's low holds, trade back to C2's midpoint (EQ).
python3 fm_events.py SYM HTF   (HTF = 15 or D)"""
import sys, numpy as np, pandas as pd
S, HTF = sys.argv[1], sys.argv[2]
B = pd.read_pickle(f'/home/claude/kyw/bars_{S}_all.pkl')
B = B[B.ts >= '2018-01-02'].reset_index(drop=True)
# contract id: labelled contract, or (continuous segments) the next quarterly expiry
def third_friday(y, m):
    d = pd.Timestamp(y, m, 15); return d + pd.Timedelta(days=(4 - d.weekday()) % 7)
EXP = pd.DatetimeIndex([third_friday(y, m) + pd.Timedelta(hours=9, minutes=30) for y in range(2017, 2028) for m in (3, 6, 9, 12)])
nxt = EXP[np.searchsorted(EXP.values, B.ts.values, side='right')]
B['ctr'] = np.where(B.Contract.values != 'CONT', B.Contract.values, pd.DatetimeIndex(nxt).strftime('EXP%Y%m'))
O, H, L, Cl = (B[k].to_numpy(float) for k in ('Open', 'High', 'Low', 'Close'))
ts = B.ts.to_numpy()
if HTF == '15':
    key = B.ts.dt.floor('15min')
    step = pd.Timedelta(minutes=15)
    # LTF = 1 minute: the bars themselves
    lO, lH, lL, lC, lts = O, H, L, Cl, ts
    lrow = np.arange(len(B))
else:
    key = B.tday
    step = None
    # LTF = 1 hour, built from the minutes (aligned to the clock hour)
    hk = B.ts.dt.floor('60min')
    G = B.groupby([hk, B.ctr], sort=True)
    Hb = G.agg(O=('Open', 'first'), H=('High', 'max'), L=('Low', 'min'), C=('Close', 'last'), ts=('ts', 'first')).reset_index(drop=True)
    Hb = Hb.sort_values('ts').reset_index(drop=True)
    lO, lH, lL, lC, lts = (Hb[k].to_numpy(float) for k in ('O', 'H', 'L', 'C')) + (Hb.ts.to_numpy(),) if False else (Hb.O.to_numpy(float), Hb.H.to_numpy(float), Hb.L.to_numpy(float), Hb.C.to_numpy(float), Hb.ts.to_numpy())
g = B.groupby(key, sort=True)
K = g.agg(O=('Open', 'first'), H=('High', 'max'), L=('Low', 'min'), C=('Close', 'last'), c0=('ctr', 'first'), c1=('ctr', 'last'),
          t0=('ts', 'first'), t1=('ts', 'last'), tday=('tday', 'first'), n=('ts', 'size'))
K['iH'] = g.High.idxmax().values
K['iL'] = g.Low.idxmin().values
K = K[(K.c0 == K.c1)].copy()
K['key'] = K.index
K = K.reset_index(drop=True)
if HTF == '15':
    contig = (K.key - K.key.shift(1) == step) & (K.c0 == K.c0.shift(1))
else:
    K = K[K.n > 600].reset_index(drop=True)            # full trading days only
    contig = (K.c0 == K.c0.shift(1))
K['contig'] = contig.fillna(False)
def sh(c, k):
    return K[c].shift(-k)
ok3 = K.contig & K.contig.shift(-1).fillna(False).astype(bool)          # k-1→k and k→k+1 contiguous
ok4 = ok3 & K.contig.shift(-2).fillna(False).astype(bool)
H1, L1 = K.H.shift(1), K.L.shift(1)
H2, L2, C2 = K.H, K.L, K.C
H3, L3, O3 = sh('H', 1), sh('L', 1), sh('O', 1)
H4, L4 = sh('H', 2), sh('L', 2)
ev = []
for side in ('bull', 'bear'):
    if side == 'bull':
        sweep = L2 < L1; back = C2 > L1
        take2 = H3 > H2; take2_34 = np.maximum(H3, H4) > H2; takeC1 = H3 >= H1; take1_34 = np.maximum(H3, H4) >= H1
        hold3 = L3 >= L2; hold34 = np.minimum(L3, L4) >= L2
        mid = (H2 + L2) / 2; eq3 = L3 <= mid
    else:
        sweep = H2 > H1; back = C2 < H1
        take2 = L3 < L2; take2_34 = np.minimum(L3, L4) < L2; takeC1 = L3 <= L1; take1_34 = np.minimum(L3, L4) <= L1
        hold3 = H3 <= H2; hold34 = np.maximum(H3, H4) <= H2
        mid = (H2 + L2) / 2; eq3 = H3 >= mid
    d = pd.DataFrame({'side': side, 'kind': np.where(sweep & back, 'C2', np.where(sweep, 'fail', 'base')),
                      'take2': take2, 'take2_34': take2_34, 'takeC1': takeC1, 'takeC1_34': take1_34,
                      'hold3': hold3, 'hold34': hold34, 'eq3': eq3, 'ok3': ok3, 'ok4': ok4,
                      't0': K.t0, 'tday': K.tday, 'k': K.index,
                      'clv': ((C2 - L2) / (H2 - L2)) if side == 'bull' else ((H2 - C2) / (H2 - L2)),
                      'rng1': H1 - L1, 'rng2': H2 - L2})
    ev.append(d[ok3])
E = pd.concat(ev, ignore_index=True)
for c in ('take2_34', 'takeC1_34', 'hold34'):
    E[c] = E[c].astype(float).where(E.ok4)
# ── CISD for the C2 events
def ltf_index(t):
    return np.searchsorted(lts, t, side='left')
c2 = E[E.kind == 'C2']
Kt0 = K.t0.to_numpy(); Kt1 = K.t1.to_numpy(); KiL = K.iL.to_numpy(); KiH = K.iH.to_numpy()
ev_idx = c2.index.to_numpy(); ev_k = c2.k.to_numpy().astype(int); ev_bull = (c2.side == 'bull').to_numpy(); ev_ok4 = c2.ok4.to_numpy()
rows = []
for n in range(len(ev_idx)):
    k = ev_k[n]; bull = ev_bull[n]
    jEnd2 = ltf_index(Kt1[k]) + 1
    jEnd4 = ltf_index(Kt1[k + 2]) + 1 if ev_ok4[n] else ltf_index(Kt1[k + 1]) + 1
    if HTF == '15':
        j0 = int(KiL[k] if bull else KiH[k])
    else:
        a, b = ltf_index(Kt0[k]), jEnd2
        seg = lL[a:b] if bull else lH[a:b]
        if len(seg) == 0:
            continue
        j0 = a + int(np.argmin(seg) if bull else np.argmax(seg))
    ext = lL[j0] if bull else lH[j0]
    start = j0 - 1 if ((lC[j0] > lO[j0]) if bull else (lC[j0] < lO[j0])) else j0
    run = []
    j = start
    while j >= 0 and j0 - j <= 10:
        isOpp = lC[j] < lO[j] if bull else lC[j] > lO[j]
        if isOpp or lC[j] == lO[j]:
            if isOpp:
                run.append(j)
            j -= 1
        else:
            break
    if run:
        lvl = max(lO[r] for r in run) if bull else min(lO[r] for r in run)
    else:
        lvl = lO[j0]
    rr = (lvl - ext) if bull else (ext - lvl)
    seg = lC[j0 + 1:jEnd4]
    hit = np.flatnonzero(seg > lvl) if bull else np.flatnonzero(seg < lvl)
    jc = j0 + 1 + int(hit[0]) if len(hit) else -1
    r = dict(idx=ev_idx[n], lvl=lvl, ext=ext, r=rr, jc=jc, cisd_in_c2=bool(jc >= 0 and jc < jEnd2), cisd_any=bool(jc >= 0))
    if jc >= 0 and rr > 0:
        hmax = lH[jc:jEnd4].max(); lmin = lL[jc:jEnd4].min()
        for m in (1, 2, 2.5, 4, 4.5):
            tgt = lvl + m * rr if bull else lvl - m * rr
            r[f'p{m}'] = (hmax >= tgt) if bull else (lmin <= tgt)
        r['ext_hold'] = (lmin >= ext) if bull else (hmax <= ext)
    rows.append(r)
X = pd.DataFrame(rows).set_index('idx')
E = E.join(X, how='left')
E['sym'] = S
E['htf'] = HTF
E.to_pickle(f'/home/claude/xa/fm/E_{S}_{HTF}.pkl')
c = E[E.kind == 'C2']
print(S, HTF, 'events', len(E), 'C2', len(c), 'CISD in C2 %.1f%%' % (100 * c.cisd_in_c2.mean()), 'any %.1f%%' % (100 * c.cisd_any.mean()))
print(E.groupby(['kind'])[['take2', 'takeC1', 'hold3', 'eq3', 'take2_34', 'hold34']].mean().round(3).to_string())
