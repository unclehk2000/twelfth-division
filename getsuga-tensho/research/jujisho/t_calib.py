"""Getsuga Jūjishō research, step 6: do Tenshō's by-Friday odds (distance in AWR4 and time left; fitted on Shikai-mid levels,
NQ + ES + RTY 2018-24) fit the Jūjishō levels on NQ? Checked at the set and at the Monday-Thursday closes."""
import numpy as np, pandas as pd
b = pd.read_pickle('/home/claude/kyw/bars_NQ_all.pkl').reset_index(drop=True)
H, L, C = (b[c].to_numpy() for c in ('High', 'Low', 'Close')); td = b.tday.to_numpy()
tde = np.r_[np.flatnonzero(td[1:] != td[:-1]), len(td) - 1]          # last bar of each trading day
W = pd.read_pickle('weeks_dir.pkl'); D = pd.read_pickle('days.pkl').set_index('date')
FX = np.array([-0.326, 0.0, 1.0, 2.0, 3.0]); FI = np.array([4.231, 4.051, 3.615, 3.055, 2.370]); FA, FB = 1.824, -7.685
def p_reach(x, d):
    x = np.clip(x, -0.326, 4.0)
    if x >= 3:
        it = FI[4]; d = d / np.sqrt(max(4 - x, 0.01))
    else:
        i = 0 if x < 0 else int(np.floor(x)) + 1; f = (x - FX[i]) / (FX[i + 1] - FX[i]); it = FI[i] * (1 - f) + FI[i + 1] * f
    dc = np.clip(d, 0, 3); return 1 / (1 + np.exp(-(it + FA * dc + FB * np.sqrt(dc))))
FS = np.round(np.arange(-1, 2.0001, 0.125), 3)
rows = []
for _, w in W.iterrows():
    Md = D.loc[w.Mday]; a = int(Md.i3) + 1
    endi = a + int(np.searchsorted(b.ts.to_numpy()[a:], np.datetime64(w.wk + pd.Timedelta(days=4, hours=17))))
    h, l = H[a:endi], L[a:endi]
    ends = tde[(tde >= a) & (tde < endi - 1)]
    # checkpoints: the set (x = −0.326 + minutes after 09:30 / 1380), then each day's close before Friday
    cps = [(0, -0.326 + (Md.fpt - 930 + 1) / 1380.0, w.P0)]
    for ei in ends:
        j = int(ei) - a
        if j > 0:
            cps.append((j + 1, float(pd.Timestamp(td[ei]).dayofweek), C[ei]))
    for f in FS:
        y = w.M + f * w.R
        for (j, x, px) in cps:
            if j > 0 and (h[:j].max() >= y >= l[:j].min()):
                continue                                     # already traded
            if j > 0 and ((y > px and h[:j].max() >= y) or (y < px and l[:j].min() <= y)):
                continue
            rest_h, rest_l = h[j:], l[j:]
            if not len(rest_h):
                continue
            hit = (rest_h.max() >= y) if y >= px else (rest_l.min() <= y)
            d_ = abs(y - px) / w.awr
            rows.append(dict(wk=w.wk, yr=w.yr, f=f, x=x, d=d_, hit=int(hit), p=p_reach(x, d_)))
K = pd.DataFrame(rows); K.to_pickle('calib.pkl')
def brier(g): return ((g.p - g.hit) ** 2).mean(), ((g.hit.mean() - g.hit) ** 2).mean()
for nm, g in (('all', K), ('2024-26', K[K.yr >= 2024])):
    b1, b0 = brier(g); print(f"{nm}: n {len(g)}  Brier {b1:.3f} (base rate only {b0:.3f})  mean predicted {g.p.mean():.3f} observed {g.hit.mean():.3f}")
K['bin'] = pd.cut(K.p, [0, .2, .4, .6, .8, .9, .95, 1.0])
print(K.groupby('bin', observed=True).agg(n=('hit', 'size'), pred=('p', 'mean'), obs=('hit', 'mean')).round(3).to_string())
K['cp'] = np.where(K.x < 0, 'set', K.x.map({0.0: 'Mon close', 1.0: 'Tue close', 2.0: 'Wed close', 3.0: 'Thu close'}))
print(K.groupby('cp').agg(n=('hit', 'size'), pred=('p', 'mean'), obs=('hit', 'mean')).round(3).to_string())
