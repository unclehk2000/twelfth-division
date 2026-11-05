"""Python port of Suzumebachi.pine's bar-by-bar logic (no contract resets, as on a continuous chart), compared with the research events."""
import numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/claude/lr'); from lib import load, bars
def run(sym, u, k, td0, full=False):
    m = load(sym); B = bars(m, u); s = np.searchsorted(B['td'], td0 - 30)   # start a month early
    O, H, L, C, ts, td = (B[c][s:] for c in ['O', 'H', 'L', 'C', 'ts', 'td']); n = len(H)
    rel = (((ts % 1440) - 1080) % 1440).astype(int); wk = (td + 3) // 7
    S = {c: np.full(n, np.nan) for c in ['dHb', 'dLb', 'wHb', 'wLb', 'aHb', 'aLb', 'lHb', 'lLb', 'ASH', 'ASL', 'LOH', 'LOL', 'MO', 'pdh', 'pdl', 'pwh', 'pwl']}
    v = dict(dHi=np.nan, dLo=np.nan, wHi=np.nan, wLo=np.nan, pdh=np.nan, pdl=np.nan, pwh=np.nan, pwl=np.nan, asH=np.nan, asL=np.nan, loH=np.nan, loL=np.nan, aHi=np.nan, aLo=np.nan, lHi=np.nan, lLo=np.nan, moO=np.nan)
    mx = lambda a, b: b if np.isnan(a) else max(a, b); mn = lambda a, b: b if np.isnan(a) else min(a, b)
    shv = slv = np.nan; shb = slb = -1; bH = bL = True; trd = 0; HV, HB, HC, LV, LB, LC = [], [], [], [], [], []; ev = []
    for i in range(n):
        r = rel[i]
        if i > 0 and wk[i] != wk[i - 1]: v['pwh'], v['pwl'], v['wHi'], v['wLo'] = v['wHi'], v['wLo'], np.nan, np.nan
        if i > 0 and td[i] != td[i - 1]:
            v['pdh'], v['pdl'] = v['dHi'], v['dLo']
            for c in ['dHi', 'dLo', 'asH', 'asL', 'loH', 'loL', 'aHi', 'aLo', 'lHi', 'lLo', 'moO']: v[c] = np.nan
        S['dHb'][i], S['dLb'][i], S['wHb'][i], S['wLb'][i] = v['dHi'], v['dLo'], v['wHi'], v['wLo']
        S['aHb'][i] = v['aHi'] if r >= 360 else np.nan; S['aLb'][i] = v['aLo'] if r >= 360 else np.nan
        S['lHb'][i] = v['lHi'] if r >= 660 else np.nan; S['lLb'][i] = v['lLo'] if r >= 660 else np.nan
        if r >= 360 and np.isnan(v['moO']): v['moO'] = O[i]
        S['ASH'][i] = v['asH'] if r >= 360 else np.nan; S['ASL'][i] = v['asL'] if r >= 360 else np.nan
        S['LOH'][i] = v['loH'] if r >= 660 else np.nan; S['LOL'][i] = v['loL'] if r >= 660 else np.nan
        S['MO'][i] = v['moO'] if r >= 360 else np.nan; S['pdh'][i], S['pdl'][i], S['pwh'][i], S['pwl'][i] = v['pdh'], v['pdl'], v['pwh'], v['pwl']
        v['dHi'] = mx(v['dHi'], H[i]); v['dLo'] = mn(v['dLo'], L[i]); v['wHi'] = mx(v['wHi'], H[i]); v['wLo'] = mn(v['wLo'], L[i])
        if 120 <= r < 360: v['asH'] = mx(v['asH'], H[i]); v['asL'] = mn(v['asL'], L[i])
        if 480 <= r < 660: v['loH'] = mx(v['loH'], H[i]); v['loL'] = mn(v['loL'], L[i])
        if r >= 360: v['aHi'] = mx(v['aHi'], H[i]); v['aLo'] = mn(v['aLo'], L[i])
        if r >= 660: v['lHi'] = mx(v['lHi'], H[i]); v['lLo'] = mn(v['lLo'], L[i])
        a5 = np.mean(H[i - 14:i] - L[i - 14:i]) if i >= 14 else np.nan
        if i >= 2 * k:
            j = i - k; hi = lo = True
            for q in range(1, k + 1):
                if H[j - q] >= H[j]: hi = False
                if L[j - q] <= L[j]: lo = False
                if H[j + q] > H[j]: hi = False
                if L[j + q] < L[j]: lo = False
            if hi: shv, shb, bH = H[j], j, False; HV.append(shv); HB.append(j); HC.append(i)
            if lo: slv, slb, bL = L[j], j, False; LV.append(slv); LB.append(j); LC.append(i)
        for d in (-1, 1):
            if d == -1 and not (not bL and slb >= 0 and C[i] < slv): continue
            if d == 1 and not (not bH and shb >= 0 and C[i] > shv): continue
            sb = slb if d == -1 else shb; mss = (trd == 1) if d == -1 else (trd == -1)
            seg = H[sb:i + 1] if d == -1 else -L[sb:i + 1]; xb = sb + int(np.argmax(seg)); x = H[xb] if d == -1 else L[xb]
            pv = np.nan
            VV, BB, CC = (HV, HB, HC) if d == -1 else (LV, LB, LC)
            for z in range(len(VV) - 1, max(-1, len(VV) - 61), -1):
                if CC[z] <= xb and BB[z] < xb: pv = VV[z]; break
            sb1 = sb + 1 if sb + 1 <= i and td[sb + 1] == td[sb] else sb
            def fr(lvH, lvL, bH_, bL_):
                lv = S[lvH][xb] if d == -1 else S[lvL][xb]; bf = S[bH_][sb1] if d == -1 else S[bL_][sb1]
                return (not np.isnan(lv)) and ((x > lv and not (bf > lv)) if d == -1 else (x < lv and not (bf < lv)))
            fPW = fr('pwh', 'pwl', 'wHb', 'wLb'); fPD = fr('pdh', 'pdl', 'dHb', 'dLb'); fAS = fr('ASH', 'ASL', 'aHb', 'aLb'); fLO = fr('LOH', 'LOL', 'lHb', 'lLb')
            fDay = (x > S['dHb'][xb]) if d == -1 else (x < S['dLb'][xb]); fSw = (x > pv) if d == -1 else (x < pv)
            raid = fPW or fPD or fAS or fLO or fDay or fSw
            fvg = any((H[jj] < L[jj - 2]) if d == -1 else (L[jj] > H[jj - 2]) for jj in range(max(xb + 2, 2), i + 1))
            risk = (x - C[i]) * (-d); rA = risk / a5 if a5 > 0 else np.nan
            pdr = (C[i] - S['pdl'][i]) / (S['pdh'][i] - S['pdl'][i]) if S['pdh'][i] > S['pdl'][i] else np.nan
            pdx = np.nan if np.isnan(pdr) else (pdr if d == -1 else 1 - pdr)
            loc = 1 if np.isnan(pdx) else (2 if pdx >= 0.75 else 0 if pdx < 0.25 else 1)
            mos = 0 if np.isnan(S['MO'][i]) else (1 if (-d) * (C[i] - S['MO'][i]) > 0 else 2)
            tight = rA < 1.5
            cell = (4 * raid + 2 * fvg + tight) if mss else 8 + 3 * loc + mos
            rn = ('PWH' if d == -1 else 'PWL') if fPW else ('PDH' if d == -1 else 'PDL') if fPD else ('Asia H' if d == -1 else 'Asia L') if fAS else ('London H' if d == -1 else 'London L') if fLO else ('day high' if d == -1 else 'day low') if fDay else 'prior swing' if fSw else ''
            ev.append(dict(ts=int(ts[i]), dir=d, mss=int(mss), cell=int(cell), x=x, risk=risk, rA=rA, td=int(td[i]), i=i, sb=sb, sv=(slv if d == -1 else shv), xb=xb, raid=rn, fvg=int(fvg), pdx=pdx, mos=mos, rel=int(r), entry=C[i]))
            if d == -1: bL = True; trd = -1
            else: bH = True; trd = 1
    E = pd.DataFrame(ev)
    if full: return E, dict(O=O, H=H, L=L, C=C, ts=ts, td=td, rel=rel)
    return E[E.td >= td0]
if __name__ == '__main__':
    X = pd.read_pickle('/home/claude/sz/t17_evx3.pkl')
    X['raidY'] = (X.raid != 'no raid').astype(int); X['tight'] = (X.rA < 1.5).astype(int)
    X['loc'] = np.where(X.pdx >= 0.75, 2, np.where(X.pdx < 0.25, 0, 1)); X.loc[X.pdx.isna(), 'loc'] = 1
    X['mos'] = np.where(X.xMO.isna(), 0, np.where(X.xMO > 0, 1, 2)); X['cell'] = np.where(X.mss == 1, X.raidY * 4 + X.fvg * 2 + X.tight, 8 + X['loc'] * 3 + X.mos)
    td0 = int(np.datetime64('2025-01-01', 'D').astype(np.int64))
    for sym, u, k in [('ES', 5, 3), ('YM', 5, 2), ('NQ', 15, 2)]:
        E = run(sym, u, k, td0); R = X[(X.sym == sym) & (X.u == u) & (X.k == k) & (X.td >= td0)]
        M = R.merge(E, on=['ts', 'dir'], suffixes=('', '_p'))
        print(f'{sym} {u}m k{k}: research {len(R)}, port {len(E[(E.rA >= 0.5) & (E.rA <= 12)])} (tested range), matched {len(M)} | same MSS/BOS {np.mean(M.mss == M.mss_p):.4f}, same cell {np.mean(M.cell == M.cell_p):.4f}, same extreme {np.mean(np.isclose(M.risk, M.risk_p)):.4f}')
        bad = M[M.cell != M.cell_p]; print('   cell mismatches by (research → port):', bad.groupby(['cell', 'cell_p']).size().sort_values(ascending=False).head(6).to_dict())
