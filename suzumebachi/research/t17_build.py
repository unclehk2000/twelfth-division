"""Suzumebachi research: market-structure breaks at several sensitivities and the 1R / 2R race after each.
Swings: pivot of strength k (k bars each side), confirmed k bars later. A break is a close beyond the last confirmed swing low
(high). It is an MSS (CHoCH) if the last break was the other way, a BOS if the same way. The leg extreme between the broken swing
and the break is the stop; entry is the break candle's close; targets 1R and 2R, raced on 1-minute bars to 16:59 ET.
Under any driftless price process the 1R race is 50% and the 2R race 33.3%, whatever the volatility (the variance-free null).
Context recorded at the break: what the leg extreme swept (the prior swing, the day's high/low so far, PDH/PDL, Asia, London, PWH/PWL),
SMT (the partner market failed to sweep its own swing), displacement, an FVG in the break leg, the 1H and daily trend, the entry's
octant in the prior day's range and in the 1H dealing range, time, risk in ATR."""
import numpy as np, pandas as pd, sys
from numba import njit
sys.path.insert(0, '/home/claude/lr'); from lib import load, bars
PART = {'ES': 'YM', 'YM': 'ES', 'NQ': 'ES', 'RTY': 'ES'}

@njit(cache=True)
def pivots(H, L, ct, k):
    n = len(H); ph = np.zeros(n, np.bool_); pl = np.zeros(n, np.bool_)
    for j in range(k, n - k):
        ok = True
        for q in range(j - k, j + k + 1):
            if ct[q] != ct[j]: ok = False; break
        if not ok: continue
        hi = True; lo = True
        for q in range(j - k, j):
            if H[q] >= H[j]: hi = False
            if L[q] <= L[j]: lo = False
        for q in range(j + 1, j + k + 1):
            if H[q] > H[j]: hi = False
            if L[q] < L[j]: lo = False
        ph[j] = hi; pl[j] = lo
    return ph, pl

@njit(cache=True)
def engine(O, H, L, C, ct, k, ph, pl):
    """returns per-event arrays and the trend after each bar"""
    n = len(H); trend = np.zeros(n, np.int8)
    ev_i = []; ev_d = []; ev_t = []; ev_x = []; ev_xb = []; ev_sb = []; ev_pv = []; ev_pvb = []
    shv = np.nan; shb = -1; slv = np.nan; slb = -1; bH = True; bL = True; tr = 0
    # history of confirmed swings for the "prior swing" lookup
    HV = np.full(n, np.nan); HB = np.full(n, -1); HC = np.full(n, -1); nh = 0
    LV = np.full(n, np.nan); LB = np.full(n, -1); LC = np.full(n, -1); nl = 0
    for i in range(n):
        if i > 0 and ct[i] != ct[i - 1]:
            shv = np.nan; shb = -1; slv = np.nan; slb = -1; bH = True; bL = True; tr = 0
        j = i - k
        if j >= 0 and ct[j] == ct[i]:
            if ph[j]:
                shv = H[j]; shb = j; bH = False; HV[nh] = H[j]; HB[nh] = j; HC[nh] = i; nh += 1
            if pl[j]:
                slv = L[j]; slb = j; bL = False; LV[nl] = L[j]; LB[nl] = j; LC[nl] = i; nl += 1
        if not bL and slb >= 0 and C[i] < slv:
            bL = True
            xb = slb
            for q in range(slb, i + 1):
                if H[q] > H[xb]: xb = q
            # prior swing high confirmed before the leg extreme
            pv = np.nan; pvb = -1
            for z in range(nh - 1, -1, -1):
                if HC[z] <= xb and HB[z] < xb:
                    pv = HV[z]; pvb = HB[z]; break
            ev_i.append(i); ev_d.append(-1); ev_t.append(1 if tr == 1 else 0); ev_x.append(H[xb]); ev_xb.append(xb); ev_sb.append(slb); ev_pv.append(pv); ev_pvb.append(pvb)
            tr = -1
        if not bH and shb >= 0 and C[i] > shv:
            bH = True
            xb = shb
            for q in range(shb, i + 1):
                if L[q] < L[xb]: xb = q
            pv = np.nan; pvb = -1
            for z in range(nl - 1, -1, -1):
                if LC[z] <= xb and LB[z] < xb:
                    pv = LV[z]; pvb = LB[z]; break
            ev_i.append(i); ev_d.append(1); ev_t.append(1 if tr == -1 else 0); ev_x.append(L[xb]); ev_xb.append(xb); ev_sb.append(shb); ev_pv.append(pv); ev_pvb.append(pvb)
            tr = 1
        trend[i] = tr
    return (np.array(ev_i), np.array(ev_d), np.array(ev_t), np.array(ev_x), np.array(ev_xb), np.array(ev_sb), np.array(ev_pv), np.array(ev_pvb), trend)

@njit(cache=True)
def race(H1, L1, C1, td1, ct1, s0, entry, risk, d):
    """from 1-minute index s0: +1R / +2R before -1R, to the day's end. returns w1 (1/0/0.5/nan), w2, mtm R at the end, minutes"""
    n = len(H1); stop = entry - d * risk; t1 = entry + d * risk; t2 = entry + 2 * d * risk
    r1 = np.nan; r2 = np.nan; m1 = -1
    if s0 >= n: return r1, r2, np.nan, -1
    td0 = td1[s0]; c0 = ct1[s0]; last = s0
    for q in range(s0, n):
        if td1[q] != td0 or ct1[q] != c0: break
        last = q
        hs = (L1[q] <= stop) if d == 1 else (H1[q] >= stop)
        h1 = (H1[q] >= t1) if d == 1 else (L1[q] <= t1)
        h2 = (H1[q] >= t2) if d == 1 else (L1[q] <= t2)
        if np.isnan(r1) and (hs or h1):
            r1 = 0.5 if (hs and h1) else (1.0 if h1 else 0.0); m1 = q - s0
        if np.isnan(r2) and (hs or h2):
            r2 = 0.5 if (hs and h2) else (1.0 if h2 else 0.0)
        if not np.isnan(r1) and not np.isnan(r2): break
    mtm = d * (C1[last] - entry) / risk
    return r1, r2, mtm, m1

def day_levels(B):
    """per bar: the day's high/low before the bar, PDH/PDL, PWH/PWL, Asia (20–00) and London (02–05) H/L once each has ended"""
    rel = (((B['ts'] % 1440) - 1080) % 1440).astype(int); td = B['td']
    df = pd.DataFrame({'td': td, 'rel': rel, 'H': B['H'], 'L': B['L'], 'C': B['C']})
    g = df.groupby('td')
    df['dHb'] = g.H.transform(lambda x: x.cummax().shift(1)); df['dLb'] = g.L.transform(lambda x: x.cummin().shift(1))
    D = g.agg(H=('H', 'max'), L=('L', 'min'), C=('C', 'last'))
    D['PDH'] = D.H.shift(1); D['PDL'] = D.L.shift(1); D['PDC'] = D.C.shift(1)
    wk = (D.index.values + 3) // 7; W = D.groupby(wk).agg(H=('H', 'max'), L=('L', 'min'))
    D['PWH'] = pd.Series(wk, index=D.index).map(W.H.shift(1)); D['PWL'] = pd.Series(wk, index=D.index).map(W.L.shift(1))
    pc = D.C.shift(1); trr = np.maximum(D.H - D.L, np.maximum((D.H - pc).abs(), (D.L - pc).abs()))
    D['ATR'] = trr.ewm(alpha=1 / 14, adjust=False).mean().shift(1)
    for nm, (a, b) in {'AS': (120, 360), 'LO': (480, 660)}.items():
        x = df[(df.rel >= a) & (df.rel < b)].groupby('td'); D[nm + 'H'] = x.H.max(); D[nm + 'L'] = x.L.min(); D[nm + 'end'] = b
    out = {c: df.td.map(D[c]).values for c in ['PDH', 'PDL', 'PDC', 'PWH', 'PWL', 'ATR', 'ASH', 'ASL', 'LOH', 'LOL']}
    out['ASok'] = rel >= 360; out['LOok'] = rel >= 660
    out['dHb'] = df.dHb.values; out['dLb'] = df.dLb.values; out['rel'] = rel
    return out

def htf_trend(m, B, u, k):
    """trend of u-minute structure (pivot k), as of each bar's close in B (only completed HTF bars)"""
    T = bars(m, u); ph, pl = pivots(T['H'], T['L'], T['ct'], k)
    r = engine(T['O'], T['H'], T['L'], T['C'], T['ct'], k, ph, pl); tr = r[8]
    # last confirmed swing high/low of the HTF (its dealing range) after each HTF bar
    shv = np.full(len(tr), np.nan); slv = np.full(len(tr), np.nan); a = np.nan; b = np.nan
    for i in range(len(tr)):
        j = i - k
        if j >= 0:
            if ph[j]: a = T['H'][j]
            if pl[j]: b = T['L'][j]
        shv[i] = a; slv[i] = b
    close_t = T['ts'] + u
    idx = np.searchsorted(close_t, B['ts'] + (B['ts'][1] - B['ts'][0] if False else 0), side='right') - 1
    return idx, tr, shv, slv, close_t

def build(sym, u, k):
    m = load(sym); B = bars(m, u); n = len(B['H'])
    ph, pl = pivots(B['H'], B['L'], B['ct'], k)
    ei, ed, et, ex, exb, esb, epv, epvb, trend = engine(B['O'], B['H'], B['L'], B['C'], B['ct'], k, ph, pl)
    DL = day_levels(B)
    # bar close times (ET minutes) of B for HTF mapping
    bclose = B['ts'] + u
    T1 = bars(m, 60); ph1, pl1 = pivots(T1['H'], T1['L'], T1['ct'], 2); r1 = engine(T1['O'], T1['H'], T1['L'], T1['C'], T1['ct'], 2, ph1, pl1)
    sh1 = np.full(len(T1['H']), np.nan); sl1 = np.full(len(T1['H']), np.nan); a = b = np.nan
    for i in range(len(T1['H'])):
        j = i - 2
        if j >= 0 and ph1[j]: a = T1['H'][j]
        if j >= 0 and pl1[j]: b = T1['L'][j]
        sh1[i] = a; sl1[i] = b
    i1 = np.searchsorted(T1['ts'] + 60, bclose, side='right') - 1
    # daily structure (k=2) on day bars
    D = pd.DataFrame({'td': B['td'], 'H': B['H'], 'L': B['L'], 'C': B['C'], 'O': B['O']}).groupby('td').agg(O=('O', 'first'), H=('H', 'max'), L=('L', 'min'), C=('C', 'last'))
    phd, pld = pivots(D.H.values, D.L.values, np.zeros(len(D), np.int64), 2)
    rd = engine(D.O.values, D.H.values, D.L.values, D.C.values, np.zeros(len(D), np.int64), 2, phd, pld)
    dtr = pd.Series(np.r_[0, rd[8][:-1]], index=D.index)     # as of the prior day's close
    # partner for SMT
    P = bars(load(PART[sym]), u); php, plp = pivots(P['H'], P['L'], P['ct'], k)
    pidx = {t: q for q, t in enumerate(P['ts'])}
    # partner swing highs/lows confirmed: arrays of (confirm ts, value)
    pH_c = P['ts'][np.flatnonzero(php) + k] if php.sum() else np.array([]); pH_v = P['H'][php]
    pL_c = P['ts'][np.flatnonzero(plp) + k] if plp.sum() else np.array([]); pL_v = P['L'][plp]
    okh = np.flatnonzero(php) + k < len(P['ts']); okl = np.flatnonzero(plp) + k < len(P['ts'])
    pH_c = P['ts'][(np.flatnonzero(php) + k)[okh]]; pH_v = P['H'][php][okh]; pL_c = P['ts'][(np.flatnonzero(plp) + k)[okl]]; pL_v = P['L'][plp][okl]
    Pcum = P  # partner leg extremes are computed by a time window
    rows = []
    H1, L1, C1, td1, ct1 = m['H'], m['L'], m['C'], m['td'].astype(np.int64), m['ct'].astype(np.int64)
    for q in range(len(ei)):
        i = ei[q]; d = ed[q]; x = ex[q]; xb = exb[q]; entry = B['C'][i]; risk = (x - entry) * (-d)
        if not (risk > 0) or np.isnan(B['atr'][i]): continue
        s0 = B['i1'][i] + 1
        w1, w2, mtm, mins = race(H1, L1, C1, td1, ct1, s0, entry, risk, d)
        a5 = B['atr'][i]; atrD = DL['ATR'][i]
        # what the leg extreme swept (levels known before the extreme's bar)
        lv = lambda arr: arr[xb]
        sw = lambda level: (not np.isnan(level)) and ((x > level) if d == -1 else (x < level))
        f = dict(sym=sym, u=u, k=k, i=i, td=int(B['td'][i]), ts=int(B['ts'][i]), rel=int(DL['rel'][i]), dir=d, mss=int(et[q]),
                 entry=entry, risk=risk, rA=risk / a5, rD=risk / atrD if atrD > 0 else np.nan, w1=w1, w2=w2, mtm=mtm, mins=mins,
                 bars_leg=i - esb[q], bars_x=i - xb,
                 sw_sw=int(sw(epv[q])), sw_day=int(sw(DL['dHb'][xb] if d == -1 else DL['dLb'][xb])),
                 sw_pd=int(sw(DL['PDH'][xb] if d == -1 else DL['PDL'][xb])), sw_pw=int(sw(DL['PWH'][xb] if d == -1 else DL['PWL'][xb])),
                 sw_as=int(DL['ASok'][xb] and sw(DL['ASH'][xb] if d == -1 else DL['ASL'][xb])), sw_lo=int(DL['LOok'][xb] and sw(DL['LOH'][xb] if d == -1 else DL['LOL'][xb])),
                 depth=((x - epv[q]) * (-d) / a5) if not np.isnan(epv[q]) else np.nan,
                 body=abs(B['C'][i] - B['O'][i]) / a5, brk=((entry - B['C'][esb[q]] if False else (B['C'][i] - (B['L'][esb[q]] if d == -1 else B['H'][esb[q]])) * d) / a5),
                 tr1=int(r1[8][i1[i]]) * d if i1[i] >= 0 else 0, trd=int(dtr.get(B['td'][i], 0)) * d,
                 pdr=((entry - DL['PDL'][i]) / (DL['PDH'][i] - DL['PDL'][i])) if DL['PDH'][i] > DL['PDL'][i] else np.nan,
                 hdr=((entry - sl1[i1[i]]) / (sh1[i1[i]] - sl1[i1[i]])) if i1[i] >= 0 and sh1[i1[i]] > sl1[i1[i]] else np.nan,
                 dayR=((max(DL['dHb'][i], B['H'][i]) - min(DL['dLb'][i], B['L'][i])) / atrD) if atrD > 0 and not np.isnan(DL['dHb'][i]) else np.nan,
                 atrD=atrD, a5=a5)
        # FVG in the break leg (from the extreme to the break): bearish = H[j] < L[j-2]
        fv = 0
        for j in range(max(xb + 2, 2), i + 1):
            if (d == -1 and B['H'][j] < B['L'][j - 2]) or (d == 1 and B['L'][j] > B['H'][j - 2]): fv = 1; break
        f['fvg'] = fv
        # SMT: did the partner exceed its own prior swing (confirmed before the extreme's time) during the leg window?
        t0 = B['ts'][esb[q]]; tx = B['ts'][xb]
        if d == -1:
            z = np.searchsorted(pH_c, tx, side='right') - 1; pv = pH_v[z] if z >= 0 else np.nan
        else:
            z = np.searchsorted(pL_c, tx, side='right') - 1; pv = pL_v[z] if z >= 0 else np.nan
        a_ = pidx.get(t0, -1); b_ = pidx.get(int(B['ts'][i]), -1)
        if a_ >= 0 and b_ > a_ and not np.isnan(pv):
            pe = P['H'][a_:b_ + 1].max() if d == -1 else P['L'][a_:b_ + 1].min()
            f['p_sw'] = int(pe > pv) if d == -1 else int(pe < pv)
        else:
            f['p_sw'] = -1
        rows.append(f)
    return pd.DataFrame(rows)

if __name__ == '__main__':
    out = []
    for sym in ['ES', 'YM', 'NQ', 'RTY']:
        for u, ks in [(5, [2, 3, 5, 8]), (15, [2, 3])]:
            for k in ks:
                df = build(sym, u, k); out.append(df)
                print(sym, u, k, len(df), f"w1 {df.w1.mean():.4f}", flush=True)
    X = pd.concat(out, ignore_index=True); X.to_pickle('/home/claude/sz/t17_ev.pkl'); print(len(X))
