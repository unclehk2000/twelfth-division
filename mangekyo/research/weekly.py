"""Weekly range from the daily chart: at each week's open, the nearest live daily gap above (bearish) and below (bullish),
within a look back of 20 / 40 / 60 trading days.  Does the week reach it more often than any level as far away, and does
the week's high (low) stop inside it more often than inside a same-size band as far away?  Controls: 5 weeks of the same
symbol within ±2 years with a similar prior week and prior 4 weeks (returns in ATR)."""
import numpy as np, pandas as pd
from data import daily, SYMS
from split import clus
Z = pd.read_pickle('zones.pkl')
rows = []
for s in SYMS:
    D = daily(s); O, H, L, C, A = D.bo.values, D.bh.values, D.bl.values, D.bc.values, D.atrB.values
    wk = D.wk.values; starts = np.r_[0, np.where(wk[1:] != wk[:-1])[0] + 1]; ends = np.r_[starts[1:] - 1, len(D) - 1]
    z = Z[(Z.sym == s)]
    for i0, i1 in zip(starts, ends):
        if i0 < 80 or not np.isfinite(A[i0 - 1]): continue
        cp = C[i0 - 1]; a = A[i0 - 1]
        wh = H[i0:i1 + 1].max(); wl = L[i0:i1 + 1].min()
        r5 = (cp - C[i0 - 6]) / a; r20 = (cp - C[i0 - 21]) / a
        rec = dict(sym=s, i0=i0, date=D.index[i0], yr=D.index[i0].year, a=a, cp=cp, up=(wh - cp) / a, dn=(cp - wl) / a, r5=r5, r20=r20, wk=wk[i0])
        for LB in (20, 40, 60):
            live = z[(z.t0 < i0) & (i0 - z.t0 <= LB) & ((z.tX < 0) | (z.tX >= i0))]
            for side, d in (('ab', -1), ('be', 1)):
                g = live[(live.dir == d) & (live.kind.isin(['FVG', 'SB']))]
                if d == -1:
                    g = g[g.bot > cp]; dist = (g.bot - cp) / a
                else:
                    g = g[g.top < cp]; dist = (cp - g.top) / a
                if len(g):
                    j = dist.values.argmin(); rr = g.iloc[j]
                    rec[f'{side}{LB}_d'] = dist.values[j]; rec[f'{side}{LB}_w'] = (rr.top - rr.bot) / a; rec[f'{side}{LB}_k'] = rr.kind
        rows.append(rec)
Wk = pd.DataFrame(rows)
Wk.to_pickle('weeks.pkl')
rng = np.random.default_rng(3)
out = []
for LB in (20, 40, 60):
    for side in ('ab', 'be'):
        mv = 'up' if side == 'ab' else 'dn'
        g = Wk[Wk[f'{side}{LB}_d'].notna()]
        reach = []; reachC = []; insd = []; insdC = []; wkk = []
        for r in g.itertuples():
            d = getattr(r, f'{side}{LB}_d'); w = getattr(r, f'{side}{LB}_w')
            pool = Wk[(Wk.sym == r.sym) & (np.abs(Wk.i0 - r.i0) <= 504) & (Wk.i0 != r.i0)]
            dist = ((pool.r5 - r.r5) / 1.0) ** 2 + ((pool.r20 - r.r20) / 2.0) ** 2
            cc = pool.iloc[np.argsort(dist.values + rng.random(len(pool)) * 1e-9)[:5]]
            m = getattr(r, mv); mc = cc[mv].values
            reach.append(float(m >= d)); reachC.append(np.mean(mc >= d))
            insd.append(float(d <= m <= d + w) if m >= d else np.nan)
            ok = mc >= d
            insdC.append(np.mean((mc[ok] <= d + w)) if ok.any() else np.nan)
            wkk.append(r.wk)
        reach, reachC, insd, insdC = map(np.array, (reach, reachC, insd, insdC))
        m1, se1, t1, n1 = clus(reach - reachC, wkk)
        ok = np.isfinite(insd) & np.isfinite(insdC)
        m2, se2, t2, n2 = clus(insd[ok] - insdC[ok], np.array(wkk)[ok])
        gg = g.assign(rd=reach - reachC, sd=insd - insdC)
        sy = ''.join('+' if v > 0 else '−' for v in gg.groupby('sym').rd.mean())
        sy2 = ''.join('+' if v > 0 else '−' for v in gg.groupby('sym').sd.mean())
        pe = ''.join('+' if v > 0 else '−' for v in gg.groupby(gg.yr >= 2025).rd.mean())
        print(f"LB {LB} {'gap above' if side=='ab' else 'gap below'}: weeks {len(g)} median dist {g[f'{side}{LB}_d'].median():.2f} ATR | "
              f"reached {reach.mean():.3f} vs ctl {reachC.mean():.3f} ({m1:+.3f}, t {t1:+.1f}, {sy}, per {pe}) | "
              f"extreme stops inside | reached {np.nanmean(insd):.3f} vs ctl {np.nanmean(insdC):.3f} ({m2:+.3f}, t {t2:+.1f}, {sy2})")
