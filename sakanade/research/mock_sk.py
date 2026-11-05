"""Sakanade: Python port of the Pine logic (features bar by bar, the exported trees via sklearn, the week Brownian model),
a port check against the training samples, and the mock (NQ 5 minutes, 22–23 Oct 2026, with the pane)."""
import sys, pickle, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy.stats import norm
sys.path.insert(0, '/home/claude/lr'); sys.path.insert(0, '/home/claude/hm')
from lib import load
import events as E
M = pickle.load(open('/home/claude/sk/t13_models.pkl', 'rb')); MD = M['day']; GB = MD['gb']
PM = np.load('/home/claude/sk/pm_pooled.npy'); CUM = np.r_[np.cumsum(PM[::-1])[::-1], 0.0]; C5 = CUM[::5]
def vrem(r):
    r = min(max(r, 0), 1380); b = min(int(r // 5), 275); f = (r - 5 * b) / 5; return C5[b] + f * (C5[b + 1] - C5[b])
def lgt(p): p = np.clip(p, 1e-6, 1 - 1e-6); return np.log(p / (1 - p))
evd = {}
for lst, rr in [(E.CPI, 870), (E.NFP, 870), (E.FOMC, 1200)]:
    for t in lst: evd.setdefault(int(pd.Timestamp(t).normalize().value // 86400_000_000_000), []).append(rr)
def rma(x, n=14):
    out = np.full(len(x), np.nan); a = 1.0 / n; out[n - 1] = np.nanmean(x[:n])
    for i in range(n, len(x)): out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out
m = load('NQ'); rel = (((m['ts'] % 1440) - 1080) % 1440).astype(int); td = m['td'].astype(int)
b = np.flatnonzero(np.diff(td) != 0) + 1; ds = np.r_[0, b]; de = np.r_[b - 1, len(td) - 1]
dH = np.maximum.reduceat(m['H'], ds); dL = np.minimum.reduceat(m['L'], ds); dC = m['C'][de]; nb = de - ds + 1
pc = np.r_[np.nan, dC[:-1]]; tr = np.nanmax(np.c_[dH - dL, np.abs(dH - pc), np.abs(dL - pc)], axis=1)
atr = np.r_[np.nan, rma(pd.Series(np.where(nb >= 1200, tr, np.nan)).ffill().values)[:-1]]
days = td[ds]; wk = (days + 3) // 7
ww = pd.DataFrame({'wk': wk, 'h': dH, 'l': dL}).groupby('wk').agg(h=('h', 'max'), l=('l', 'min'))
pwh = pd.Series(wk).map(ww.h.shift(1)).values; pwl = pd.Series(wk).map(ww.l.shift(1)).values
def run_day(di, tf=1):
    """Pine port over day di on tf-minute bars; returns per-bar dict list."""
    s, e = ds[di], de[di]; a = atr[di]; out = []
    O, H, L, C, R = m['O'][s:e + 1], m['H'][s:e + 1], m['L'][s:e + 1], m['C'][s:e + 1], rel[s:e + 1]
    key = R // tf; brk = np.r_[0, np.flatnonzero(np.diff(key)) + 1]; en = np.r_[brk[1:] - 1, len(key) - 1]
    dO = O[0]; hi = -1e18; lo = 1e18; hr = lr_ = 0
    dow0 = pd.Timestamp(days[di], unit='D').dayofweek
    for i0, i1 in zip(brk, en):
        bh, bl, bc, br = H[i0:i1 + 1].max(), L[i0:i1 + 1].min(), C[i1], R[i0]
        if bh > hi: hi, hr = bh, br
        if bl < lo: lo, lr_ = bl, br
        rN = br + tf
        if rN >= 1380: break
        v = max(vrem(rN), 1e-6); rg = hi - lo
        evs = [x for x in evd.get(days[di], []) if x > rN - 1]; ev = min(evs) if evs else -1
        zH = (hi - bc) / a / np.sqrt(v); zL = (bc - lo) / a / np.sqrt(v)
        fH = [lgt(2 * norm.cdf(MD['k0'] * zH) - 1), 1, rN, rg / a, br - hr, (bc - lo) / rg if rg > 0 else .5, (hi - dH[di - 1]) / a, (bc - dO) / a, hr, ev, dow0]
        fL = [lgt(2 * norm.cdf(MD['k0'] * zL) - 1), -1, rN, rg / a, br - lr_, (hi - bc) / rg if rg > 0 else .5, (dL[di - 1] - lo) / a, (dO - bc) / a, lr_, ev, dow0]
        out.append(dict(r=rN, rel=br, c=bc, hi=hi, lo=lo, hr=hr, lr=lr_, fH=fH, fL=fL, v=v))
    if out:
        P = GB.predict_proba(np.array([o['fH'] for o in out] + [o['fL'] for o in out]))[:, 1]
        for i, o in enumerate(out): o['pH'] = P[i]; o['pL'] = P[len(out) + i]
    return out
# port check against the training rows (1-minute, at the 15-minute marks)
T = pd.read_pickle('/home/claude/sk/t13_day.pkl'); T = T[T.sym == 'NQ']
FE = MD['FE']; T['lz'] = lgt(np.clip(2 * norm.cdf(MD['k0'] * T.z) - 1, 1e-6, 1 - 1e-6))
rng = np.random.default_rng(5); diffs = []; pdiff = []
for di in rng.choice(np.flatnonzero((days >= 20089) & (nb >= 1200) & (nb <= 1440)), 25, replace=False):
    out = {o['r']: o for o in run_day(di, 1)}
    tt = T[T.td == days[di]]
    for row in tt.itertuples():
        o = out.get(int(row.r));
        if o is None: continue
        f = o['fH'] if row.side == 1 else o['fL']
        ref = [getattr(row, k) for k in FE]
        diffs.append(np.abs(np.array(f, float) - np.array(ref, float)).max())
        pdiff.append(abs((o['pH'] if row.side == 1 else o['pL']) - GB.predict_proba(np.array([ref]))[0, 1]))
print(f'port check: {len(diffs)} samples, max |prob diff| {np.max(pdiff):.4f}, mean {np.mean(pdiff):.5f}, share within 0.01: {np.mean(np.array(pdiff) < 0.01):.3f} (age counts minutes in Pine, bars in the test: a few 1-minute bars are missing)')
# mock: 5-minute chart, 22–23 Oct 2026
d1 = int(np.searchsorted(days, int(pd.Timestamp('2026-10-23').value // 86400e9)))
bars = []
for di in (d1 - 1, d1):
    out = run_day(di, 5); s = ds[di]
    O, H, L, C, R = m['O'][s:de[di] + 1], m['H'][s:de[di] + 1], m['L'][s:de[di] + 1], m['C'][s:de[di] + 1], rel[s:de[di] + 1]
    key = R // 5; brk = np.r_[0, np.flatnonzero(np.diff(key)) + 1]; en = np.r_[brk[1:] - 1, len(key) - 1]
    for j, (i0, i1) in enumerate(zip(brk, en)):
        o = out[j] if j < len(out) else None
        bars.append(dict(di=di, o=O[i0], h=H[i0:i1 + 1].max(), l=L[i0:i1 + 1].min(), c=C[i1], rel=R[i0], pH=o['pH'] if o else np.nan, pL=o['pL'] if o else np.nan, hi=o['hi'] if o else np.nan, lo=o['lo'] if o else np.nan, v=o['v'] if o else np.nan))
B = pd.DataFrame(bars)
# week: running week high/low (Mon 18:00 = start of the week's first trading day) and the Brownian week odds
wk0 = int(np.flatnonzero(wk == wk[d1])[0]); s0 = ds[wk0]
WH = m['H'][s0:ds[d1 - 1]].max(); WL = m['L'][s0:ds[d1 - 1]].min()
pw = []; whs = []; wls = []
for r in B.itertuples():
    WH = max(WH, r.h); WL = min(WL, r.l); whs.append(WH); wls.append(WL)
    dow0 = pd.Timestamp(days[r.di], unit='D').dayofweek; vw = r.v + max(4 - dow0, 0) * CUM[0]
    pwH = 1 / (1 + np.exp(-(M['week']['a0'] + M['week']['b0'] * lgt(2 * norm.cdf(M['week']['k0'] * (WH - r.c) / atr[r.di] / np.sqrt(vw)) - 1))))
    pwL = 1 / (1 + np.exp(-(M['week']['a0'] + M['week']['b0'] * lgt(2 * norm.cdf(M['week']['k0'] * (r.c - WL) / atr[r.di] / np.sqrt(vw)) - 1))))
    pw.append((pwH, pwL))
B['pwH'] = [a for a, b in pw]; B['pwL'] = [b for a, b in pw]; B['WH'] = whs; B['WL'] = wls
B = B.iloc[:-1]  # last bar of the day is 16:55
cut = int(np.flatnonzero((B.di == d1) & (B.rel == 1170))[0])   # mock as of 13:30 on 23 Oct
V = B.iloc[:cut + 1].reset_index(drop=True); n = len(V)
fig = plt.figure(figsize=(15, 9.4), dpi=130)
ax = fig.add_axes([0.03, 0.36, 0.86, 0.57]); ax2 = fig.add_axes([0.03, 0.06, 0.86, 0.26], sharex=ax)
for i, r in V.iterrows():
    c = '#089981' if r.c >= r.o else '#f23645'; ax.plot([i, i], [r.l, r.h], color=c, lw=0.6); ax.add_patch(Rectangle((i - 0.3, min(r.o, r.c)), 0.6, max(abs(r.c - r.o), 0.25), fc=c, ec=c, lw=0.2))
last = V.iloc[-1]; xr = n + 10
iH = int(V[(V.di == d1) & (V.h == last.hi)].index[0]); iL = int(V[(V.di == d1) & (V.l == last.lo)].index[0])
ax.plot([iH, xr], [last.hi] * 2, color='#ef5350', lw=1); ax.text(xr, last.hi, f' Day high {last.hi:,.2f} · holds {100*last.pH:.0f}%', color='#ef5350', fontsize=8, va='bottom')
ax.plot([iL, xr], [last.lo] * 2, color='#26a69a', lw=1); ax.text(xr, last.lo, f' Day low {last.lo:,.2f} · holds {100*last.pL:.0f}%', color='#26a69a', fontsize=8, va='top')
iWH = int(V[V.h == last.WH].index[0]) if (V.h == last.WH).any() else 0; iWL = int(V[V.l == last.WL].index[0]) if (V.l == last.WL).any() else 0
ax.plot([iWH, xr], [last.WH] * 2, color='#ef5350', lw=1, ls='--', alpha=0.7); ax.text(xr, last.WH, f' Week high {last.WH:,.2f} · holds {100*last.pwH:.0f}%', color='#ef5350', fontsize=8, va='bottom', alpha=0.85)
ax.plot([iWL, xr], [last.WL] * 2, color='#26a69a', lw=1, ls='--', alpha=0.7); ax.text(xr, last.WL, (f'   = week low · holds {100*last.pwL:.0f}%' if last.WL == last.lo else f' Week low {last.WL:,.2f} · holds {100*last.pwL:.0f}%'), color='#26a69a', fontsize=8, va='bottom' if last.WL == last.lo else 'top', alpha=0.85)
lo, hi = min(V.l.min(), last.WL), max(V.h.max(), last.WH); pad = (hi - lo) * 0.05; ax.set_ylim(lo - pad, hi + pad); ax.set_xlim(-1, n + 40)
for a_ in (ax, ax2):
    a_.yaxis.tick_right(); a_.grid(color='#eef1f6', lw=0.6); a_.tick_params(colors='#131722', labelsize=8, length=0)
    for sp in a_.spines.values(): sp.set_color('#eef1f6')
ax2.plot(V.index, 100 * V.pH, color='#ef5350', lw=1.6, label='day high holds'); ax2.plot(V.index, 100 * V.pL, color='#26a69a', lw=1.6, label='day low holds')
ax2.scatter(V.index[::3], 100 * V.pwH[::3], color='#ef5350', s=3, alpha=0.6); ax2.scatter(V.index[::3], 100 * V.pwL[::3], color='#26a69a', s=3, alpha=0.6)
ax2.axhline(50, color='#9aa1b2', lw=0.6, ls=':'); ax2.axhline(80, color='#c9ced8', lw=0.6, ls=':'); ax2.set_ylim(0, 100)
ax2.text(1, 92, 'Sakanade · day high (red) / low (green) holds to 16:59 · week odds dotted', fontsize=8, color='#5d6476')
tk = [i for i in range(n) if V.rel[i] % 240 == 0]; ax2.set_xticks(tk); ax2.set_xticklabels([f"{((V.rel[i] + 1080) % 1440) // 60:02d}:00" for i in tk]); plt.setp(ax.get_xticklabels(), visible=False)
fig.text(0.03, 0.965, 'Sakanade · NQ 5 min · 22–23 Oct 2026, as of 13:30 ET · is the day\'s / week\'s high or low in?', fontsize=10.5, color='#131722', weight='bold')
gauge = lambda f, k: '█' * int(round(f * k)) + '░' * (k - int(round(f * k)))
hmf = lambda r: f"{((r + 1080) % 1440) // 60:02d}:{(r + 1080) % 60:02d}"
rows = [('SAKANADE', 'IS IT IN?', 'holds', '13:30'), ('DAY HIGH', gauge(last.pH, 10), f'{100*last.pH:.0f}%', f'{last.hi:,.2f} · {hmf(int(last.hr if "hr" in last else V[V.h==last.hi].rel.iloc[0]))}'),
        ('DAY LOW', gauge(last.pL, 10), f'{100*last.pL:.0f}%', f'{last.lo:,.2f} · {hmf(int(V[(V.di==d1)&(V.l==last.lo)].rel.iloc[0]))}'), ('WEEK HIGH', gauge(last.pwH, 10), f'{100*last.pwH:.0f}%', f'{last.WH:,.2f}'),
        ('WEEK LOW', gauge(last.pwL, 10), f'{100*last.pwL:.0f}%', f'{last.WL:,.2f}'), ('release ahead', '', 'none today', ''), ('day H forms', '', 'NY PM 35%', 'AM 27 · Asia 17'), ('week H forms', '', 'Fri 34%', 'Mon 18'), ('tested', '', 'Brier 0.135', 'flat 0.239')]
cols = ['#ffffff', None, None, None]; x0, y0, wd, hh = 0.615, 0.925, 0.275, 0.024
for k, (a, b2, c3, d4) in enumerate(rows):
    yy = y0 - k * hh
    fig.patches.append(Rectangle((x0, yy - hh), wd, hh, transform=fig.transFigure, fc='#6d4c41' if k == 0 else '#f4f6f9', ec='#6d4c41' if k == 0 else '#dde1e8', lw=0.6))
    tc = '#ffffff' if k == 0 else '#131722'; gc = '#ef5350' if 'HIGH' in a else '#26a69a' if 'LOW' in a else '#5d6476'
    fig.text(x0 + 0.005, yy - hh / 2, a, fontsize=7.4, color=tc if k == 0 else '#5d6476', va='center', family='monospace')
    fig.text(x0 + 0.065, yy - hh / 2, b2, fontsize=7.4, color=tc if k == 0 else gc, va='center', family='monospace')
    fig.text(x0 + 0.14, yy - hh / 2, c3, fontsize=7.4, color=tc, va='center', family='monospace')
    fig.text(x0 + wd - 0.005, yy - hh / 2, d4, fontsize=7.4, color=tc if k == 0 else '#5d6476', va='center', ha='right', family='monospace')
fig.savefig('/home/claude/sk/Sakanade_5m.png', facecolor='white'); print('mock: day high', last.hi, f'{last.pH:.2f}', 'low', last.lo, f'{last.pL:.2f}', 'week', last.WH, f'{last.pwH:.2f}', last.WL, f'{last.pwL:.2f}')
