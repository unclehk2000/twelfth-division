"""Wabisuke tests before claims (6 Nov 2026).

T1 Release pulse: on CPI / NFP days the 08:30-08:44 range. After 08:45, the first break of its high or low: does price go a
   further 1 x the pulse range before coming back to the pulse's midpoint (continuation vs failure)? Null: compared with the
   same rule on ordinary days' 08:30-08:44 range, and with 50%.
T2 ZN shadow gap: at 10:00 / 12:00 / 14:00 ET, gap = index % move since 18:00 minus beta60 x ZN % move since 18:00. Does the
   index's next 2 hours move against the gap (converge to the shadow)? Hit = sign(next 2h) = -sign(gap); null 50%.
T3 Next-60-session correlation forecast: today's rho60 alone vs rho60 + ZN 60-session % + VIX3M, fitted on 2018-24 and scored
   on 2025-26 (R2 out of sample). The coefficients go into the card.
T4 1H ZN-weighted candle: the hour's ZN move x beta60 gives a ZN-implied candle; when its direction disagrees with the index's
   own 1H candle, does the next 1H candle follow ZN more than when they agree? Hit = next hour's sign = ZN-implied sign.
"""
import numpy as np, pandas as pd, hydra, lib
P = pd.read_pickle('cache/panel.pkl')
ZN_OK = set(P.index[P['ZN_ok'].astype(bool)])

def minutes(mk):
    m = lib.load(mk)
    return pd.DataFrame({'O': m['O'], 'H': m['H'], 'L': m['L'], 'C': m['C'], 'td': m['td']}, index=pd.to_datetime(m['ts'], unit='m'))

def t1(mk, M):
    rows = []
    ev = set(P.index[P.CPI | P.NFP]); fomc = set(P.index[P.FOMC])
    for td, g in M.groupby('td'):
        d = pd.Timestamp(str(td))
        if d in fomc:
            continue
        day = g.index[0].normalize() + pd.Timedelta(days=1) if g.index[0].hour >= 18 else g.index[0].normalize()
        p = g.between_time('08:30', '08:44')
        p = p[p.index.normalize() == d]
        if len(p) < 10:
            continue
        hi, lo = p.H.max(), p.L.min(); rg = hi - lo
        if rg <= 0:
            continue
        a = g[(g.index > d + pd.Timedelta(hours=8, minutes=44)) & (g.index < d + pd.Timedelta(hours=16))]
        if len(a) < 30:
            continue
        H, L = a.H.values, a.L.values
        bu = np.flatnonzero(H > hi); bd = np.flatnonzero(L < lo)
        iu = bu[0] if len(bu) else 10 ** 9; idn = bd[0] if len(bd) else 10 ** 9
        if iu == idn:
            continue
        up = iu < idn; i = min(iu, idn)
        tgt = hi + rg if up else lo - rg; mid = (hi + lo) / 2
        Hs, Ls = H[i:], L[i:]
        ht = np.flatnonzero(Hs >= tgt) if up else np.flatnonzero(Ls <= tgt)
        hm = np.flatnonzero(Ls <= mid) if up else np.flatnonzero(Hs >= mid)
        x = ht[0] if len(ht) else 10 ** 9; y = hm[0] if len(hm) else 10 ** 9
        if x == y:
            continue
        rows.append(dict(day=d, mk=mk, rel=d in ev, up=up, hit=float(x < y), rg_pct=rg / p.O.iloc[0], brk_min=i))
    return pd.DataFrame(rows)

def path_since_18(M, d, t):
    """% move from the session's 18:00 open to the close of the minute before t (ET)"""
    g = M[M.td == int(d.strftime('%Y%m%d'))]
    if len(g) < 500:
        return np.nan, g
    o = g.O.iloc[0]
    w = g[g.index < d + t]
    return (w.C.iloc[-1] / o - 1) if len(w) else np.nan, g

def t2(mk, Mi, Mz):
    rows = []
    beta = P[f'{mk}_beta60'].shift(1); rho = P[f'{mk}_rho60'].shift(1)
    for d in P.index[(P.index >= '2018-03-01')]:
        if d not in ZN_OK or np.isnan(beta.get(d, np.nan)):
            continue
        for hh in (10, 12, 14):
            t = pd.Timedelta(hours=hh)
            ri, gi = path_since_18(Mi, d, t); rz, gz = path_since_18(Mz, d, t)
            if np.isnan(ri) or np.isnan(rz):
                continue
            gap = ri - beta[d] * rz
            w = gi[(gi.index >= d + t) & (gi.index < d + t + pd.Timedelta(hours=2))]
            if len(w) < 60:
                continue
            nxt = w.C.iloc[-1] / w.O.iloc[0] - 1
            if gap == 0 or nxt == 0:
                continue
            rows.append(dict(day=d, mk=mk, hh=hh, reg='pos' if rho[d] > 0.2 else 'neg' if rho[d] < -0.2 else 'flat',
                             hit=float(np.sign(nxt) == -np.sign(gap)), gapz=abs(gap)))
    return pd.DataFrame(rows)

def t4(mk, Mi, Mz):
    bi = Mi.resample('60min').agg({'O': 'first', 'C': 'last', 'td': 'first'}).dropna()
    bz = Mz.resample('60min').agg({'O': 'first', 'C': 'last'}).dropna()
    b = bi.join(bz, rsuffix='z', how='inner')
    b['day'] = pd.to_datetime(b['td'].astype(int).astype(str))
    beta = P[f'{mk}_beta60'].shift(1)
    b['beta'] = b['day'].map(lambda d: beta.get(d, np.nan))
    b = b[b['day'].isin(ZN_OK)].dropna()
    b['ri'] = b.C / b.O - 1; b['rz'] = (b.Cz / b.Oz - 1) * b['beta']
    b['nxt'] = b['ri'].shift(-1); b = b[(b['td'] == b['td'].shift(-1))]
    b = b[(b.ri != 0) & (b.rz != 0) & (b.nxt != 0)]
    b['dis'] = np.sign(b.ri) != np.sign(b.rz)
    b['hit_zn'] = (np.sign(b.nxt) == np.sign(b.rz)).astype(float)
    b['mk'] = mk
    return b[['day', 'mk', 'dis', 'hit_zn']]

if __name__ == '__main__':
    pd.set_option('display.width', 220)
    Mz = minutes('ZN')
    out1, out2, out4 = [], [], []
    for mk in ('NQ', 'ES'):
        Mi = minutes(mk)
        out1.append(t1(mk, Mi)); out2.append(t2(mk, Mi, Mz)); out4.append(t4(mk, Mi, Mz))
    A = pd.concat(out1); A['per'] = hydra.period(A['day'])
    print('=== T1: first break of the 08:30-08:44 range, 1 x range further before back to its midpoint ===')
    for p in ('fish', 'test'):
        r = A[A.rel & (A.per == p)]; o = A[~A.rel & (A.per == p)]
        d = hydra.diff(r.hit.values, (r.day.astype(str) + r.mk).values, o.hit.values, (o.day.astype(str) + o.mk).values)
        rr = hydra.rate(r.hit.values, r.day.values)
        print(f"{p}: release {rr['r']*100:.1f}% (n {rr['n']}, p vs 50 {rr['p']:.3f}) vs ordinary {d['rb']*100:.1f}% (n {d['nb']}) Δ {d['d']*100:+.1f} (p {d['p']:.3f}) | NQ {r[r.mk=='NQ'].hit.mean()*100:.1f}% ES {r[r.mk=='ES'].hit.mean()*100:.1f}% | release pulse median {r.rg_pct.median()*100:.2f}% vs ordinary {o.rg_pct.median()*100:.2f}%")
    B = pd.concat(out2); B['per'] = hydra.period(B['day'])
    print('=== T2: shadow gap convergence over the next 2 hours (hit = moves against the gap) ===')
    for reg in ('pos', 'neg', 'flat', 'all'):
        res = {}
        for p in ('fish', 'test'):
            g = B[(B.per == p) & ((B.reg == reg) if reg != 'all' else True)]
            big = g[g.gapz > g.gapz.quantile(0.67)] if len(g) else g
            res[p] = (hydra.rate(g.hit.values, g.day.values), hydra.rate(big.hit.values, big.day.values))
        v = hydra.verdict(res['fish'][0], res['test'][0], key='r')
        print(f"{reg:4s}: fish {hydra.fmt(res['fish'][0])} (top third gap {res['fish'][1]['r']*100:.1f}%) | test {hydra.fmt(res['test'][0])} (top third {res['test'][1]['r']*100:.1f}%) | {v}")
    C = pd.concat(out4); C['per'] = hydra.period(C['day'])
    print('=== T4: next 1H candle follows the ZN-weighted candle: when it disagrees with the index candle vs when it agrees ===')
    for p in ('fish', 'test'):
        g = C[C.per == p]
        d = hydra.diff(g[g.dis].hit_zn.values, g[g.dis].day.values, g[~g.dis].hit_zn.values, g[~g.dis].day.values)
        print(f"{p}: disagree → next hour follows ZN {d['ra']*100:.1f}% (n {d['na']}) vs agree {d['rb']*100:.1f}% (n {d['nb']}) Δ {d['d']*100:+.1f} (p {d['p']:.3f}) | disagree share {g.dis.mean()*100:.0f}%")
    print('=== T3: next-60-session ZN-index correlation forecast ===')
    import s_regime as sr
    coefs = {}
    for mk in ('NQ', 'ES'):
        F = sr.features(mk).dropna(subset=['rho60', 'zn60', 'vix3m', 'fwdrho'])
        F['per'] = hydra.period(F.index)
        f, t = F[F.per == 'fish'], F[F.per == 'test']
        for cols in (['rho60'], ['rho60', 'zn60', 'vix3m']):
            X = np.c_[np.ones(len(f)), f[cols].values]; b, *_ = np.linalg.lstsq(X, f['fwdrho'].values, rcond=None)
            pr = np.c_[np.ones(len(t)), t[cols].values] @ b
            r2 = 1 - ((t.fwdrho - pr) ** 2).sum() / ((t.fwdrho - t.fwdrho.mean()) ** 2).sum()
            mae = np.abs(t.fwdrho - pr).mean()
            print(f"{mk} {cols}: coef {np.round(b, 4)} | test R2 {r2:.3f}, MAE {mae:.3f}")
            coefs[(mk, tuple(cols))] = b
    pd.to_pickle(coefs, 'cache/wabisuke_coefs.pkl')
