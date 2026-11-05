# Benihime v3 · HYDRA pass on the RTH / ORG lecture claims. Per (symbol, day): the ORG (prior 16:14 close -> 09:30 open), its CE,
# mirror placebo levels, the overnight range, the week's carried ORG CEs, RTH-only 1h structure, sessions, and shuffled-RTH nulls.
# NQ / ES / RTY 1-minute, 2018 -> 23 Oct 2026 (coc/bars_*.npz, coc/days_*.pkl).
import numpy as np, pandas as pd
rng = np.random.default_rng(11)
NSH = 3
rows, voids, mss, H1all = [], [], [], []
for sym in ('NQ', 'ES', 'RTY'):
    Z = np.load(f'/home/claude/coc/bars_{sym}.npz'); O, H, L, C, hm, ct = Z['O'], Z['H'], Z['L'], Z['C'], Z['hm'], Z['ct']
    D = pd.read_pickle(f'/home/claude/coc/days_{sym}.pkl').reset_index(drop=True)
    ok = D.G.notna() & D.rth_ok & (D.G > 0)
    # RTH-only 1h candles (09:30-10:29 ... 15:30-16:14) for every rth_ok day: the "jigsaw" series
    H1 = []
    for k in np.flatnonzero(D.rth_ok.values):
        a, z = D.i930[k], D.i1614[k]
        for h0 in range(7):
            lo_, hi_ = a + 60 * h0, min(a + 60 * (h0 + 1), z + 1)
            if lo_ > z: break
            H1.append((k, h0, O[lo_], H[lo_:hi_].max(), L[lo_:hi_].min(), C[hi_ - 1]))
    H1 = pd.DataFrame(H1, columns=['k', 'h', 'o', 'hh', 'll', 'c'])
    # RTH-only 1h swings (fractal 2-2 on the RTH-only sequence) and break-of-structure by 1h close
    hh_, ll_, cc_, kk_ = H1.hh.values, H1.ll.values, H1.c.values, H1.k.values
    n1 = len(H1); lastSH = np.nan; lastSL = np.nan; state = 0
    sw_hi = np.full(n1, np.nan); sw_lo = np.full(n1, np.nan)
    for i in range(n1):
        j = i - 2                                              # a swing at j is confirmed at i (two candles after)
        if j >= 2 and hh_[j] > hh_[j - 2:j].max() and hh_[j] > hh_[j + 1:i + 1].max(): lastSH = hh_[j]
        if j >= 2 and ll_[j] < ll_[j - 2:j].min() and ll_[j] < ll_[j + 1:i + 1].min(): lastSL = ll_[j]
        sw_hi[i], sw_lo[i] = lastSH, lastSL
        if not np.isnan(lastSH) and cc_[i] > lastSH and state != 1:
            state = 1; mss.append((sym, kk_[i], H1.h.values[i], 1, cc_[i])); lastSH = np.nan
        elif not np.isnan(lastSL) and cc_[i] < lastSL and state != -1:
            state = -1; mss.append((sym, kk_[i], H1.h.values[i], -1, cc_[i])); lastSL = np.nan
    H1['swH'] = sw_hi; H1['swL'] = sw_lo
    H1['sym'] = sym; H1['tday'] = D.tday.values[H1.k.values]; H1all.append(H1)
    last_by_day = H1.groupby('k').tail(1).set_index('k')         # structure known at the day's 16:14
    # carried CEs: this week's earlier ORG CEs, last week's Monday and Friday
    D['CE'] = np.where(ok, (D.op + D.pc) / 2, np.nan)
    for k in np.flatnonzero(ok.values):
        a, z, s = D.i930[k], D.i1614[k], D.s[k]
        op, pc, G, up, atr = D.op[k], D.pc[k], D.G[k], bool(D.up[k]), D.atr10[k]
        if not np.isfinite(atr): continue
        CE = (op + pc) / 2
        rH_, rL_ = H[a:z + 1], L[a:z + 1]
        sgn = -1 if up else 1                                  # direction toward the fill
        f10 = slice(a, a + 30)
        reach = lambda lv, sl: (L[sl].min() <= lv) if lv <= op else (H[sl].max() >= lv)
        rr = slice(a, z + 1)
        mirCE = op - (CE - op); mirF = op - (pc - op)
        # first touch of the fill and the extension beyond the close / beyond the open (gap units)
        if up:
            t_f = np.flatnonzero(rL_ <= pc); ext_beyond_open = (rH_[:t_f[0]].max() - op) / G if len(t_f) and t_f[0] > 0 else ((rH_.max() - op) / G if not len(t_f) else 0.0)
            ext_after_fill = (pc - rL_[t_f[0]:].min()) / G if len(t_f) else np.nan
        else:
            t_f = np.flatnonzero(rH_ >= pc); ext_beyond_open = (op - rL_[:t_f[0]].min()) / G if len(t_f) and t_f[0] > 0 else ((op - rL_.min()) / G if not len(t_f) else 0.0)
            ext_after_fill = (rH_[t_f[0]:].max() - pc) / G if len(t_f) else np.nan
        # shuffled-RTH null for the extensions and the overnight extremes (returns permuted within 30-minute blocks)
        prevC = np.r_[op, C[a:z]]
        dH, dL, dC = H[a:z + 1] - prevC, L[a:z + 1] - prevC, C[a:z + 1] - prevC
        blk = (np.arange(z - a + 1)) // 30
        onH, onL = H[s:a].max(), L[s:a].min()
        sh = []
        for _ in range(NSH):
            idx = np.arange(len(dC))
            for u in np.unique(blk):
                w = np.flatnonzero(blk == u); idx[w] = rng.permutation(w)
            cc = op + np.cumsum(dC[idx]); pcc = np.r_[op, cc[:-1]]; hh = pcc + dH[idx]; ll = pcc + dL[idx]
            if up:
                tf = np.flatnonzero(ll <= pc); eo = (hh[:tf[0]].max() - op) / G if len(tf) and tf[0] > 0 else ((hh.max() - op) / G if not len(tf) else 0.0)
                ef = (pc - ll[tf[0]:].min()) / G if len(tf) else np.nan
            else:
                tf = np.flatnonzero(hh >= pc); eo = (op - ll[:tf[0]].min()) / G if len(tf) and tf[0] > 0 else ((op - ll.min()) / G if not len(tf) else 0.0)
                ef = (hh[tf[0]:].max() - pc) / G if len(tf) else np.nan
            sh.append((eo, ef, hh.max() > onH, ll.min() < onL, (ll[:30].min() <= CE) if up else (hh[:30].max() >= CE), len(tf) > 0))
        sh = np.array(sh, dtype=float)
        # sessions: London 02:00-04:59, 7-9 07:00-08:59, RTH
        def sess(t0, t1):
            m = np.flatnonzero((hm[s:a] >= t0) & (hm[s:a] < t1)) + s
            if len(m) < 30: return np.nan
            o_, c_, h_, l_ = O[m[0]], C[m[-1]], H[m].max(), L[m].min()
            return (c_ - o_) / (h_ - l_) if h_ > l_ else 0.0
        lon, s79 = sess(200, 500), sess(700, 900)
        rth_tr = (C[z] - op) / (rH_.max() - rL_.min())
        # the week's carried CEs (earlier days this week) + last week's Monday and Friday
        wk = D.wk[k]
        prior = D[(D.wk == wk) & (D.index < k) & ok]
        lastwk = D[(D.wk == wk - pd.Timedelta(days=7)) & ok & D.dow.isin([0, 4])]
        cw = prior.CE.values; cl = lastwk.CE.values
        allc = np.r_[cw, cl]
        near = allc[np.argmin(np.abs(allc - op))] if len(allc) else np.nan
        dn = abs(near - op) if len(allc) else np.nan
        nearR = reach(near, rr) if len(allc) else np.nan
        nearM = reach(op - (near - op), rr) if len(allc) else np.nan
        # yesterday's RTH high / low and ETH high / low (magnet vs mirror)
        y = k - 1
        rpd = {}
        if y >= 0 and D.rth_ok[y]:
            for nm, lv in (('rPDH', D.rH[y]), ('rPDL', D.rL[y]), ('ePDH', D.dH[y]), ('ePDL', D.dL[y])):
                d_ = abs(lv - op)
                if (nm.endswith('H') and lv > op) or (nm.endswith('L') and lv < op):
                    rpd[nm + '_d'] = d_ / atr; rpd[nm + '_r'] = reach(lv, rr); rpd[nm + '_m'] = reach(op - (lv - op), rr)
        # RTH-only structure at yesterday's close: last swing high above / below the open, and state
        st = {}
        if y in last_by_day.index:
            lb = last_by_day.loc[y]
            for nm, lv in (('rsH', lb.swH), ('rsL', lb.swL)):
                if np.isfinite(lv) and ((nm == 'rsH' and lv > op) or (nm == 'rsL' and lv < op)):
                    st[nm + '_d'] = abs(lv - op) / atr; st[nm + '_r'] = reach(lv, rr); st[nm + '_m'] = reach(op - (lv - op), rr)
        rows.append(dict(sym=sym, k=k, tday=D.tday[k], dow=D.dow[k], up=up, G=G, atr=atr, gA=G / atr, gR=G / D.avg20[k] if D.avg20[k] > 0 else np.nan,
                         ce10=reach(CE, f10), ce10m=reach(mirCE, f10), ce16=reach(CE, rr), ce16m=reach(mirCE, rr),
                         fill=reach(pc, rr), fillm=reach(mirF, rr), eo=ext_beyond_open, ef=ext_after_fill,
                         eo_n=sh[:, 0], ef_n=sh[:, 1], onH_r=rH_.max() > onH, onL_r=rL_.min() < onL,
                         onH_n=sh[:, 2].mean(), onL_n=sh[:, 3].mean(), ce10_n=sh[:, 4].mean(), fill_n=sh[:, 5].mean(),
                         onW=(onH - onL) / atr, lon=lon, s79=s79, rth_tr=rth_tr, ret=(C[z] - op) / atr, rng=(rH_.max() - rL_.min()) / atr,
                         nC=len(cw), cwmin=cw.min() if len(cw) else np.nan, cwmax=cw.max() if len(cw) else np.nan, op=op,
                         near_d=dn / atr if len(allc) else np.nan, near_r=nearR, near_m=nearM, **rpd, **st))
    # RTH voids: each ORG followed up to 10 sessions; the void's CE untouched by RTH so far; was it traded in ETH since?
    idx = np.flatnonzero(ok.values)
    for k in idx:
        CE = D.CE[k]; atr = D.atr10[k]
        if not np.isfinite(atr): continue
        rth_hit = (L[D.i930[k]:D.i1614[k] + 1].min() <= CE <= H[D.i930[k]:D.i1614[k] + 1].max())
        eth_hit = False
        for j in range(k + 1, min(k + 11, len(D))):
            if rth_hit or not D.rth_ok[j]: break
            # ETH between the previous RTH close and this 09:30 (both the 16:15-17:00 tail and 18:00-09:29)
            e0 = D.i1614[j - 1] + 1 if D.rth_ok[j - 1] else D.s[j]
            seg = slice(e0, D.i930[j])
            if seg.stop > seg.start and L[seg].min() <= CE <= H[seg].max(): eth_hit = True
            opj = O[D.i930[j]]; rj = slice(D.i930[j], D.i1614[j] + 1)
            hit = L[rj].min() <= CE <= H[rj].max()
            voids.append((sym, D.tday[j], j - k, abs(opj - CE) / D.atr10[j], eth_hit, hit))
            rth_hit = hit
R = pd.DataFrame(rows)
for c in ('ef_n',):
    R[c] = R[c].apply(lambda v: np.array(v, dtype=float))
R['yr'] = R.tday.dt.year; R['half'] = np.where(R.yr >= 2025, 'test', 'train')
V = pd.DataFrame(voids, columns=['sym', 'tday', 'age', 'dA', 'eth', 'hit']); V['half'] = np.where(V.tday.dt.year >= 2025, 'test', 'train')
M = pd.DataFrame(mss, columns=['sym', 'k', 'h', 'dir', 'c'])
R.to_pickle('rth_rows.pkl'); V.to_pickle('rth_voids.pkl'); M.to_pickle('rth_mss.pkl'); pd.concat(H1all).to_pickle('rth_h1.pkl')
print(len(R), R.groupby('sym').size().to_dict(), 'voids', len(V), 'mss', len(M))
