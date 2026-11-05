"""T5: the HTF-FVG → swing sweep → order block → close confirmation with SMT model (studied from the "Forever" scripts, written
from scratch), at 1m–15m, 5m–1H and 15m–4H. NQ with ES as the SMT pair, ES with NQ, RTY with ES. 2018 – 23 Oct 2026.
Bull logic only; bear setups run the same code on negated prices. One trade per FVG (the first confirmed).
Per trade: limit at the OB open, stop at the SMT extreme; no-fill if price reaches the target before the fill; after the fill,
the best excursion in R before the stop (the fill bar counts only its stop), whether the ERL traded before the stop.
Null: the same direction, risk in points and horizon from a random other day at the same minute (market entry), 3 replicates."""
import numpy as np, pandas as pd, sys
from numba import njit
from lay import load


@njit(cache=True)
def sim(O, H, L, C, pH, pL, ts, ct, hk, HO, HH, HL, HC, pHH, pHL, Hst, hmin, maxH, horizon, rnd):
    nL = len(O); nH = len(HO)
    # first LTF bar of each HTF bar
    first = np.full(nH + 1, -1, np.int64)
    for t in range(nL - 1, -1, -1):
        first[hk[t]] = t
    out = []
    stP = np.empty(4096); stI = np.empty(4096, np.int64)
    itP = np.empty(4096); itI = np.empty(4096, np.int64)
    sA = np.empty(4096); iA = np.empty(4096); lA = np.empty(4096)
    for k in range(4, nH - 1):
        if not (HL[k] > HH[k - 2]):
            continue
        s = first[k + 1]; t3 = first[k - 2]
        if s < 2 or t3 < 2:
            continue
        if ct[t3] != ct[s]:
            continue
        top = HL[k]; bot = HH[k - 2]
        erl = max(HH[k], HH[k - 1])
        piv = np.nan
        for j in range(k - 1, 1, -1):
            if HL[j] < HL[j - 1] and HL[j] < HL[j + 1]:
                piv = HL[j]
                break
        if not (piv < bot):
            piv = np.nan
        # seed ST pivot lows from t3 to s-1 (confirmed by s-1)
        nst = 0; nit = 0; ns = 0; ni = 0; nl = 0
        for j in range(t3 + 1, s - 1):
            if L[j] < L[j - 1] and L[j] < L[j + 1]:
                stP[nst] = L[j]; stI[nst] = j; nst += 1
                sA[ns] = L[j]; ns += 1
        # SMT anchors: the three FVG candles
        aN = np.array([HL[k - 2], HL[k - 1], HL[k]]); aE = np.array([pHL[k - 2], pHL[k - 1], pHL[k]])
        aT = np.array([Hst[k - 2], Hst[k - 1], Hst[k]])
        bk = np.full(3, -1, np.int64); bN = np.zeros(3); bE = np.zeros(3)
        fnd = np.zeros(3, np.bool_); y2 = np.full(3, np.nan); win = np.full(3, -1, np.int64); exL = np.full(3, np.nan)
        pend_o = np.empty(64); pend_i = np.empty(64, np.int64); pend_b = np.empty(64); npend = 0
        mitig = False
        tend = first[min(k + 1 + maxH, nH)] if k + 1 + maxH < nH else nL - 1
        if tend < 0:
            tend = nL - 1
        done = False
        for t in range(s, tend):
            if ct[t] != ct[s]:
                break
            # HTF close beyond the FVG at a new HTF bar
            if t > s and hk[t] != hk[t - 1] and HC[hk[t - 1]] < bot:
                break
            if not mitig:
                erl = max(erl, H[t])
                if L[t] < top:
                    mitig = True
            elif H[t] > erl:
                break
            if piv == piv and L[t] < piv:
                break
            # swings: a 3-bar pivot low at t-1, promoted ST -> IT -> LT
            if L[t - 1] < L[t - 2] and L[t - 1] < L[t]:
                stP[nst] = L[t - 1]; stI[nst] = t - 1; nst += 1
                sA[ns] = L[t - 1]; ns += 1
                if nst > 2 and stP[nst - 2] < stP[nst - 3] and stP[nst - 2] < stP[nst - 1]:
                    p = stP[nst - 2]
                    itP[nit] = p; itI[nit] = stI[nst - 2]; nit += 1
                    stP[nst - 2] = stP[nst - 1]; stI[nst - 2] = stI[nst - 1]; nst -= 1
                    for q in range(ns):
                        if sA[q] == p:
                            sA[q] = sA[ns - 1]; ns -= 1
                            iA[ni] = p; ni += 1
                            break
                    if nit > 2 and itP[nit - 2] < itP[nit - 3] and itP[nit - 2] < itP[nit - 1]:
                        p2 = itP[nit - 2]
                        itP[nit - 2] = itP[nit - 1]; itI[nit - 2] = itI[nit - 1]; nit -= 1
                        for q in range(ni):
                            if iA[q] == p2:
                                iA[q] = iA[ni - 1]; ni -= 1
                                lA[nl] = p2; nl += 1
                                break
                if nst > 4000 or nit > 4000:
                    break
            # SMT on each anchor, bucketed by HTF length from the anchor's start
            for a in range(3):
                b = (ts[t] - aT[a]) // hmin
                if b != bk[a]:
                    bk[a] = b; bN[a] = L[t]; bE[a] = pL[t]
                else:
                    bN[a] = min(bN[a], L[t]); bE[a] = min(bE[a], pL[t])
                if not fnd[a]:
                    if (bN[a] - aN[a]) * (bE[a] - aE[a]) < 0:
                        fnd[a] = True; y2[a] = bN[a]; win[a] = t; exL[a] = L[t]
                else:
                    if L[t] < exL[a]:
                        exL[a] = L[t]
                        if (exL[a] - aN[a]) * (pL[t] - aE[a]) < 0:
                            y2[a] = exL[a]; win[a] = t
                        else:
                            win[a] = -1
            # sweeps: LT first, then IT, then ST; a bearish candle (body >= 50% of range) that sweeps makes a pending OB
            rng_ = H[t] - L[t]
            okc = rng_ > 0 and (O[t] - C[t]) >= 0.5 * rng_
            swept = False
            for tier in range(3):
                if swept:
                    break
                best = 1e18; got = False
                if tier == 0:
                    q = 0
                    while q < nl:
                        if L[t] < lA[q]:
                            got = True; best = min(best, lA[q]); lA[q] = lA[nl - 1]; nl -= 1
                        else:
                            q += 1
                elif tier == 1:
                    q = 0
                    while q < ni:
                        if L[t] < iA[q]:
                            got = True; best = min(best, iA[q]); iA[q] = iA[ni - 1]; ni -= 1
                        else:
                            q += 1
                else:
                    q = 0
                    while q < ns:
                        if L[t] < sA[q]:
                            got = True; best = min(best, sA[q]); sA[q] = sA[ns - 1]; ns -= 1
                        else:
                            q += 1
                if got:
                    swept = True
                    if tier == 0:
                        q = 0
                        while q < ni:
                            if L[t] < iA[q]:
                                iA[q] = iA[ni - 1]; ni -= 1
                            else:
                                q += 1
                    if tier <= 1:
                        q = 0
                        while q < ns:
                            if L[t] < sA[q]:
                                sA[q] = sA[ns - 1]; ns -= 1
                            else:
                                q += 1
                    if okc and npend < 64:
                        pend_o[npend] = O[t]; pend_i[npend] = t; pend_b[npend] = best; npend += 1
            # confirmation: the previous bar closed above a pending OB's open, with a live SMT that formed earlier
            if npend > 0 and t > s:
                crossed = -1
                for q in range(npend):
                    if t - 1 > pend_i[q] and C[t - 1] > pend_o[q]:
                        crossed = q
                        break
                if crossed >= 0:
                    bw = -1; by = 1e18
                    for a in range(3):
                        if fnd[a] and win[a] >= 0 and win[a] < t and y2[a] < by:
                            by = y2[a]; bw = win[a]
                    if bw >= 0 and by < pend_o[crossed]:
                        E = pend_o[crossed]; S = by; R = E - S
                        # outcome from t: limit fill, stop, best excursion
                        fill = -1; preM = 0.0
                        tmax = min(t + horizon, nL - 1)
                        for u in range(t, tmax):
                            if ct[u] != ct[s]:
                                break
                            if L[u] <= E:
                                fill = u
                                break
                            preM = max(preM, (H[u] - E) / R)
                        mfe = np.nan; stop = 0; erlH = 0; fstop = 0
                        if fill >= 0:
                            mfe = 0.0
                            if L[fill] <= S:
                                stop = 1; fstop = 1
                            else:
                                for u in range(fill + 1, min(fill + horizon, nL - 1)):
                                    if ct[u] != ct[s]:
                                        break
                                    if L[u] <= S:
                                        stop = 1
                                        break
                                    mfe = max(mfe, (H[u] - E) / R)
                                    if H[u] >= erl:
                                        erlH = 1
                        # null: same risk, random other day at the same minute, market entry
                        nm = np.full(3, np.nan); ns_ = np.zeros(3)
                        if fill >= 0:
                            for r in range(3):
                                off = rnd[(k * 3 + r) % len(rnd)]
                                u0 = fill + off
                                if u0 < 1 or u0 + horizon >= nL:
                                    continue
                                # walk to the same minute of day
                                tgt = ts[fill] % 1440
                                st_ = 0
                                while u0 < nL - horizon - 1 and ts[u0] % 1440 != tgt and st_ < 3000:
                                    u0 += 1; st_ += 1
                                if u0 >= nL - horizon - 1:
                                    continue
                                E2 = O[u0]; S2 = E2 - R; m2 = 0.0; st2 = 0
                                for u in range(u0, u0 + horizon):
                                    if ct[u] != ct[u0]:
                                        break
                                    if L[u] <= S2:
                                        st2 = 1
                                        break
                                    m2 = max(m2, (H[u] - E2) / R)
                                nm[r] = m2; ns_[r] = st2
                        # null 2: the same bars after the fill, each bar's move sign-flipped at random (same volatility, no direction)
                        fm = np.full(3, np.nan)
                        if fill >= 0 and fstop == 0:
                            for r in range(3):
                                c = C[fill]; m3 = 0.0
                                for u in range(fill + 1, min(fill + horizon, nL - 1)):
                                    if ct[u] != ct[s]:
                                        break
                                    dH = H[u] - C[u - 1]; dL = L[u] - C[u - 1]; dC = C[u] - C[u - 1]
                                    if ((u * 2654435761 + r * 40503 + k * 97) >> 9) & 1 == 0:
                                        dH, dL, dC = -dL, -dH, -dC
                                    hh = c + dH; ll = c + dL; c = c + dC
                                    if ll <= S:
                                        break
                                    m3 = max(m3, (hh - E) / R)
                                fm[r] = m3
                        elif fill >= 0:
                            fm[:] = 0.0
                        out.append((float(k), float(ts[t]), float(t - s), E, S, R, R / max(HH[k] - HL[k - 2], 1e-9), (1.0 if fill >= 0 else 0.0), preM,
                                    mfe, float(stop), float(fstop), float(erlH), (erl - E) / R, nm[0], nm[1], nm[2], ns_[0], ns_[1], ns_[2],
                                    fm[0], fm[1], fm[2], float(ts[pend_i[crossed]]), pend_b[crossed], L[pend_i[crossed]]))
                        done = True
                        break
                    else:
                        # confirmation without a live SMT: the OBs that closed through are dropped
                        q2 = 0
                        for q in range(npend):
                            if not (t - 1 > pend_i[q] and C[t - 1] > pend_o[q]):
                                pend_o[q2] = pend_o[q]; pend_i[q2] = pend_i[q]; pend_b[q2] = pend_b[q]; q2 += 1
                        npend = q2
        # end FVG
    return out


def bars(ts, O, H, L, C, ct, key):
    brk = np.flatnonzero((np.diff(key) != 0) | (np.diff(ct) != 0)) + 1
    st = np.r_[0, brk]; en = np.r_[brk - 1, len(key) - 1]
    return st, en, O[st], np.maximum.reduceat(H, st), np.minimum.reduceat(L, st), C[en], ts[st], ct[st].astype(np.int64)


if __name__ == '__main__':
    rs = np.random.default_rng(41)
    rnd = (rs.choice([-1, 1], 50000) * rs.integers(5, 250, 50000) * 1380).astype(np.int64)
    pairs = {'NQ': 'ES', 'ES': 'NQ', 'RTY': 'ES'}
    TF = [(1, 15), (5, 60), (15, 240)]
    rows = []
    for sym, pr in pairs.items():
        a = load(sym); b = load(pr)
        common, ia, ib = np.intersect1d(a['ts'], b['ts'], return_indices=True)
        ts = common; O, H, L, C, ct = a['O'][ia], a['H'][ia], a['L'][ia], a['C'][ia], a['ct'][ia]
        bH, bL = b['H'][ib], b['L'][ib]
        for lt, ht in TF:
            for side in (1, -1):
                Os, Hs, Ls, Cs = (O, H, L, C) if side == 1 else (-O, -L, -H, -C)
                pHs, pLs = (bH, bL) if side == 1 else (-bL, -bH)
                lk = ts // lt
                st, en, lO, lH, lL, lC, lts, lct = bars(ts, Os, Hs, Ls, Cs, ct, lk)
                pH_ = np.maximum.reduceat(pHs, st); pL_ = np.minimum.reduceat(pLs, st)
                hkey = (lts - 1080) // ht if ht == 240 else lts // ht
                hb = np.r_[0, np.flatnonzero(np.diff(hkey) != 0) + 1]
                hk = np.zeros(len(lts), np.int64); hk[hb[1:]] = 1; hk = np.cumsum(hk)
                HO = lO[hb]; HH = np.maximum.reduceat(lH, hb); HL = np.minimum.reduceat(lL, hb)
                HC = lC[np.r_[hb[1:] - 1, len(lts) - 1]]
                pHH = np.maximum.reduceat(pH_, hb); pHL = np.minimum.reduceat(pL_, hb)
                Hst = (hkey[hb] * ht + (1080 if ht == 240 else 0)).astype(np.int64)
                horizon = int(2 * 1380 / lt)
                o = sim(lO, lH, lL, lC, pH_, pL_, lts, lct, hk, HO, HH, HL, HC, pHH, pHL, Hst, ht, 48, horizon, (rnd // lt).astype(np.int64))
                X = pd.DataFrame(o, columns=['k', 'tsC', 'wait', 'E', 'S', 'R', 'Rfvg', 'filled', 'preM', 'mfe', 'stop', 'fstop', 'erlHit', 'erlR',
                                             'n0', 'n1', 'n2', 's0', 's1', 's2', 'f0', 'f1', 'f2', 'tsSw', 'swP', 'swL'])
                X['sym'] = sym; X['tf'] = f'{lt}-{ht}'; X['side'] = side
                rows.append(X)
                print(sym, lt, ht, side, len(X), int(X.filled.sum()), flush=True)
    X = pd.concat(rows, ignore_index=True)
    X['yr'] = pd.to_datetime(X.tsC.astype('int64'), unit='m').dt.year
    X.to_pickle('t5_rows.pkl')
