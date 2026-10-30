"""Getsuga Jūjishō research, step 7: the two-state version for the card (coiled = |R| ≤ 0.20 × AWR4, about the median), the
direction effect within each state, and the numbers for the week of 26 Oct 2026."""
import numpy as np, pandas as pd
from scipy import stats
W = pd.read_pickle('weeks_dir.pkl'); D = pd.read_pickle('days.pkl').set_index('date')
LV = pd.read_pickle('levels.pkl'); LV = LV[(LV.kind == 'real') & LV.wk.isin(W.wk)]
W['coil'] = W.r <= 0.20
lo, hi = np.minimum(W.xH, W.xL), np.maximum(W.xH, W.xL)
W['up_x'], W['dn_x'] = hi, lo
def pct(v): return f"{100 * np.mean(v):.0f}%"
def wil(v):
    v = np.asarray(v, float); k, n = v.sum(), len(v); z = 1.96; p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return f"{100 * p:.0f}% [{100 * (c - h):.0f}–{100 * (c + h):.0f}]"
for s, g in W.groupby('coil'):
    nm = 'COILED (≤ 0.20×)' if s else 'UNCOILED (> 0.20×)'
    hits = LV[LV.wk.isin(g.wk)].pivot_table(index='wk', columns='f', values='hit', aggfunc='first')
    print(f"{nm}: n {len(g)}  |R| median {g.aR.median():.0f} pts ({g.r.median():.2f}× AWR4)")
    print(f"   rest-of-week range {g.vol.mean():.2f}× AWR4 (median {g.vol.median():.2f})")
    print(f"   close between the anchors {wil(((g.xC >= 0) & (g.xC <= 1)))}  beyond an SD {wil(((g.xC > 1.5) | (g.xC < -0.5)))}  beyond 2 / −1 {wil(((g.xC > 2) | (g.xC < -1)))}")
    print("   reached by Friday: " + '  '.join(f"{f:+g} {pct(hits[f])}" for f in (2.0, 1.5, 1.0, 0.5, -0.5, -1.0)))
    print(f"   both SDs (1.5 and −0.5) {pct(hits[1.5].astype(bool) & hits[-0.5].astype(bool))}")
    a, b_ = g[g.dn == 1].bp, g[g.dn == 0].bp; t = stats.ttest_ind(a, b_, equal_var=False)
    print(f"   direction: after a down shift {a.mean():+.0f} bp (up {pct(g[g.dn == 1].upw)}, n {len(a)}), up shift {b_.mean():+.0f} bp (up {pct(g[g.dn == 0].upw)}, n {len(b_)}) p {t.pvalue:.3f}")
print(f"\nall weeks: up from the set {pct(W.upw)}  mean {W.bp.mean():+.0f} bp; down shift up {pct(W[W.dn == 1].upw)} {W[W.dn == 1].bp.mean():+.0f} bp; up shift up {pct(W[W.dn == 0].upw)} {W[W.dn == 0].bp.mean():+.0f} bp")
print('share coiled', W.coil.mean().round(3))
# the week of 26 Oct 2026: Friday 23 Oct's FPFVG, AWR4 from the four chart weeks before
b = pd.read_pickle('/home/claude/kyw/bars_NQ_all.pkl')
wid = (b.ts + pd.Timedelta(hours=6)).dt.normalize(); wid = wid - pd.to_timedelta(wid.dt.dayofweek, unit='D')
WR = b.groupby(wid).agg(H=('High', 'max'), L=('Low', 'min')); WR['r'] = WR.H - WR.L
last4 = WR.tail(4); awr = last4.r.mean(); F = D.loc[pd.Timestamp('2026-10-23')]
print('\nWEEK OF 26 OCT: last four chart weeks', [(str(i.date()), round(v, 2)) for i, v in last4.r.items()], 'AWR4', round(awr, 2))
print(f"Friday 23 Oct FPFVG: {'bull' if F.fp > 0 else 'bear'} {F.bot} – {F.top}, CE {F.ce}, gap {F.gap} pts, third candle {int(F.fpt)}; set price {F.P0}; RTH close {F.c_end}; RTH H {F.rthH} L {F.rthL}")
print(f"coiled if Monday's CE within ±{0.20 * awr:.2f} pts of {F.ce}: {F.ce - 0.2 * awr:.2f} – {F.ce + 0.2 * awr:.2f}")
print('last week H/L', WR.iloc[-1].H, WR.iloc[-1].L, 'contract', F.con)
W.to_pickle('weeks_final.pkl')
