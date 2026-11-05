"""Shinsō: Python port of the Pine logic (pools, live/taken, features, both tree models via sklearn), a port check against the
training rows, and the mock (NQ 5 minutes, 23 Oct 2026 as of 10:30 ET)."""
import sys, pickle, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy.stats import norm
sys.path.insert(0, '/home/claude/lr'); sys.path.insert(0, '/home/claude/hm')
from lib import load
import events as E
M = pickle.load(open('/home/claude/sn/t15_models.pkl', 'rb')); PMd, RMd = M['pool'], M['race']
PM = np.load('/home/claude/sk/pm_pooled.npy'); CUM = np.r_[np.cumsum(PM[::-1])[::-1], 0.0]; C5 = CUM[::5]
def vrem(r):
    r = min(max(r, 0), 1380); b = min(int(r // 5), 275); f = (r - 5 * b) / 5; return C5[b] + f * (C5[b + 1] - C5[b])
def lgt(p): p = np.clip(p, 1e-6, 1 - 1e-6); return np.log(p / (1 - p))
evd = {}
for lst, rr in [(E.CPI, 870), (E.NFP, 870), (E.FOMC, 1200)]:
    for t in lst: evd[int(pd.Timestamp(t).normalize().value // 86400_000_000_000)] = rr
def rma(x, n=14):
    out = np.full(len(x), np.nan); a = 1.0 / n; out[n - 1] = np.nanmean(x[:n])
    for i in range(n, len(x)): out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out
PN = ['PDH', 'PDL', 'PWH', 'PWL', 'PMH', 'PML', 'Asia H', 'Asia L', 'London H', 'London L']
m = load('NQ'); rel = (((m['ts'] % 1440) - 1080) % 1440).astype(int); td = m['td'].astype(int)
b = np.flatnonzero(np.diff(td) != 0) + 1; ds = np.r_[0, b]; de = np.r_[b - 1, len(td) - 1]
dH = np.maximum.reduceat(m['H'], ds); dL = np.minimum.reduceat(m['L'], ds); dC = m['C'][de]; nb_ = de - ds + 1
pc = np.r_[np.nan, dC[:-1]]; tr = np.nanmax(np.c_[dH - dL, np.abs(dH - pc), np.abs(dL - pc)], axis=1)
atr = np.r_[np.nan, rma(pd.Series(np.where(nb_ >= 1200, tr, np.nan)).ffill().values)[:-1]]
days = td[ds]; wk = (days + 3) // 7; dts = pd.to_datetime(days, unit='D'); mo = dts.year * 12 + dts.month
W = pd.DataFrame({'wk': wk, 'h': dH, 'l': dL}).groupby('wk').agg(h=('h', 'max'), l=('l', 'min'))
Mo = pd.DataFrame({'mo': mo, 'h': dH, 'l': dL}).groupby('mo').agg(h=('h', 'max'), l=('l', 'min'))
P0 = np.c_[np.r_[np.nan, dH[:-1]], np.r_[np.nan, dL[:-1]], pd.Series(wk).map(W.h.shift(1)).values, pd.Series(wk).map(W.l.shift(1)).values, pd.Series(mo).map(Mo.h.shift(1)).values, pd.Series(mo).map(Mo.l.shift(1)).values]
side = lambda j: 1 if j % 2 == 0 else -1
def run_day(di, tf=1, until=None):
    s, e = ds[di], de[di]; a = atr[di]; dow0 = pd.Timestamp(days[di], unit='D').dayofweek
    O, H, L, C, R = m['O'][s:e + 1], m['H'][s:e + 1], m['L'][s:e + 1], m['C'][s:e + 1], rel[s:e + 1]
    key = R // tf; brk = np.r_[0, np.flatnonzero(np.diff(key)) + 1]; en = np.r_[brk[1:] - 1, len(key) - 1]
    LV = list(P0[di]) + [np.nan] * 4; LIV = [0] * 6 + [None] * 4; TK = [None] * 10
    aH = aL = lH = lL = None; dO = O[0]; snaps = {}
    for bi, (i0, i1) in enumerate(zip(brk, en)):
        bh, bl, bc, br = H[i0:i1 + 1].max(), L[i0:i1 + 1].min(), C[i1], R[i0]
        if 120 <= br < 360: aH = bh if aH is None else max(aH, bh); aL = bl if aL is None else min(aL, bl)
        if 480 <= br < 660: lH = bh if lH is None else max(lH, bh); lL = bl if lL is None else min(lL, bl)
        if br >= 360 and LIV[6] is None and aH is not None: LV[6], LV[7] = aH, aL; LIV[6] = LIV[7] = bi
        if br >= 660 and LIV[8] is None and lH is not None: LV[8], LV[9] = lH, lL; LIV[8] = LIV[9] = bi
        for j in range(10):
            if LIV[j] is not None and TK[j] is None and (bh >= LV[j] if side(j) == 1 else bl <= LV[j]): TK[j] = bi
        rN = br + tf
        if rN >= 1380: break
        if until is not None and br > until: break
        v = max(vrem(rN), 1e-6); ev = 1.0 if evd.get(days[di], -1) > rN - 1 else 0.0
        nTB = sum(1 for j in range(10) if TK[j] is not None and side(j) == 1); nTS = sum(1 for j in range(10) if TK[j] is not None and side(j) == -1)
        live = [j for j in range(10) if LIV[j] is not None and TK[j] is None]
        feats = {}; dB = dS = 1e18; jB = jS = -1
        for j in live:
            sd = side(j); d = (LV[j] - bc) * sd / a
            if d <= 0: continue
            nb = sum(1 for i in live if i != j and side(i) == sd and 0 < (LV[i] - bc) * sd / a < d)
            cf = sum(1 for i in live if i != j and side(i) == sd and abs(LV[i] - LV[j]) / a < 0.15)
            feats[j] = [lgt(2 * norm.cdf(-PMd['k0'] * d / np.sqrt(v))), j // 2, sd, rN, nb, cf, nTS if sd == 1 else nTB, nTB if sd == 1 else nTS, sd * (bc - dO) / a, ev, dow0]
            if sd == 1 and d < dB: dB, jB = d, j
            if sd == -1 and d < dS: dS, jS = d, j
        race = [lgt(dS / (dB + dS)), jB // 2, jS // 2, nTB, nTS, (bc - dO) / a, rN] if jB >= 0 and jS >= 0 else None
        snaps[rN] = dict(feats=feats, race=race, jB=jB, jS=jS, LV=list(LV), TK=list(TK), LIV=list(LIV), c=bc, bi=bi)
    return snaps
# port check vs training rows (1-minute, 15-minute marks)
T = pd.read_pickle('/home/claude/sn/t15_pools.pkl'); T = T[T.sym == 'NQ']
T['lz'] = lgt(2 * norm.cdf(-PMd['k0'] * T.z.values))
rng = np.random.default_rng(7); pd_ = []; fmax = []
for di in rng.choice(np.flatnonzero((days >= 20089) & (nb_ >= 1200) & (nb_ <= 1440)), 20, replace=False):
    sn = run_day(di, 1); tt = T[T.td == days[di]]
    for row in tt.itertuples():
        snap = sn.get(int(row.r)); 
        if snap is None or int(row.pool) not in snap['feats']: continue
        f = np.array(snap['feats'][int(row.pool)], float); ref = np.array([getattr(row, k) for k in PMd['FE']], float)
        fmax.append(np.abs(f - ref).max())
        pd_.append(abs(PMd['gb'].predict_proba([f])[0, 1] - PMd['gb'].predict_proba([ref])[0, 1]))
print(f'port check: {len(pd_)} pool samples, max |prob diff| {np.max(pd_):.4f}, share within 0.01 {np.mean(np.array(pd_) < 0.01):.3f}')
# mock
d1 = int(np.searchsorted(days, int(pd.Timestamp('2026-10-23').value // 86400e9)))
sn = run_day(d1, 5, until=990); last = sn[max(sn)]
s, e = ds[d1], de[d1]; R = rel[s:e + 1]; key = R // 5; brk = np.r_[0, np.flatnonzero(np.diff(key)) + 1]; en = np.r_[brk[1:] - 1, len(key) - 1]
bars = [(m['O'][s + i0], m['H'][s + i0:s + i1 + 1].max(), m['L'][s + i0:s + i1 + 1].min(), m['C'][s + i1], R[i0]) for i0, i1 in zip(brk, en)][:last['bi'] + 1]
n = len(bars); xr = n + 12
P = {j: PMd['gb'].predict_proba([f])[0, 1] for j, f in last['feats'].items()}
pr = RMd['gb'].predict_proba([last['race']])[0, 1] if last['race'] else None
fig = plt.figure(figsize=(15, 8.8), dpi=130); ax = fig.add_axes([0.03, 0.07, 0.84, 0.85])
for i, (o, h, l, c, r) in enumerate(bars):
    col = '#089981' if c >= o else '#f23645'; ax.plot([i, i], [l, h], color=col, lw=0.6); ax.add_patch(Rectangle((i - 0.3, min(o, c)), 0.6, max(abs(c - o), 0.25), fc=col, ec=col, lw=0.2))
ys = []
for j in range(10):
    lv = last['LV'][j]
    if lv != lv or last['LIV'][j] is None: continue
    tk = last['TK'][j]; c = '#ef5350' if side(j) == 1 else '#26a69a'; x1 = 0 if j < 6 else last['LIV'][j]
    top = j in (last['jB'], last['jS'])
    ax.plot([x1, tk if tk is not None else xr], [lv, lv], color=c, lw=2 if top else 1, ls='-' if j < 6 else '--', alpha=0.35 if tk is not None else 1)
    tx = f"{PN[j]} {lv:,.2f}" + (f" ✓ {((bars[tk][4] + 1080) % 1440) // 60:02d}:{(bars[tk][4] + 1080) % 60:02d}" if tk is not None else (f" · {100*P[j]:.0f}% today" if j in P else ''))
    ax.text(tk if tk is not None else xr, lv, ' ' + tx, color=c, alpha=0.55 if tk is not None else 1, fontsize=7.6, va='bottom' if side(j) == 1 else 'top', clip_on=True)
    ys.append(lv)
lo = min(min(b_[2] for b_ in bars), *[y for y in ys if abs(y - last['c']) < 900]); hi = max(max(b_[1] for b_ in bars), *[y for y in ys if abs(y - last['c']) < 900])
pad = (hi - lo) * 0.05; ax.set_ylim(lo - pad, hi + pad); ax.set_xlim(-1, n + 46)
ax.yaxis.tick_right(); ax.grid(color='#eef1f6', lw=0.6); ax.tick_params(colors='#131722', labelsize=8, length=0)
for sp in ax.spines.values(): sp.set_color('#eef1f6')
tk_ = [i for i in range(n) if bars[i][4] % 120 == 0]; ax.set_xticks(tk_); ax.set_xticklabels([f"{((bars[i][4] + 1080) % 1440) // 60:02d}:00" for i in tk_])
fig.text(0.03, 0.955, 'Shinsō · NQ 5 min · 23 Oct 2026 as of 10:30 ET · ICT liquidity pools with machine-learned odds of being taken today', fontsize=10.5, color='#131722', weight='bold')
gauge = lambda f, k: '█' * int(round(f * k)) + '░' * (k - int(round(f * k)))
rows = [('SHINSŌ', 'DRAW ON LIQUIDITY', 'today', '10:30')]
if pr is not None: rows.append(('FIRST', '▲ ' + PN[last['jB']], f'{100*pr:.0f}%', f"{PN[last['jS']]} ▼ {100*(1-pr):.0f}%"))
order = sorted(P, key=lambda j: -last['LV'][j]); done = False
for j in order:
    if not done and side(j) == -1: rows.append(('— price', '', f"{last['c']:,.2f}", '')); done = True
    rows.append((PN[j], gauge(P[j], 10), f'{100*P[j]:.0f}%', f"{last['LV'][j]:,.2f} · {(last['LV'][j] - last['c']) * side(j) / atr[d1]:.1f} ATR"))
if not done: rows.append(('— price', '', f"{last['c']:,.2f}", ''))
rows += [('taken today', '', f"{sum(1 for t in last['TK'] if t is not None)} pools", ''), ('draw rules', '', '≤ 1 pt', 'beyond distance'), ('tested', '', 'Brier 0.088', 'flat 0.167')]
x0, y0, wd, hh = 0.60, 0.92, 0.27, 0.024
for k, (a, b2, c3, d4) in enumerate(rows):
    yy = y0 - k * hh
    fig.patches.append(Rectangle((x0, yy - hh), wd, hh, transform=fig.transFigure, fc='#ad1457' if k == 0 else '#f4f6f9', ec='#ad1457' if k == 0 else '#dde1e8', lw=0.6))
    tc = '#ffffff' if k == 0 else '#131722'; gc = '#ef5350' if ('H' in a and a not in ('— price',)) or a == 'FIRST' else '#26a69a'
    fig.text(x0 + 0.005, yy - hh / 2, a, fontsize=7.3, color=tc if k == 0 else '#5d6476', va='center', family='monospace')
    fig.text(x0 + 0.062, yy - hh / 2, b2, fontsize=7.3, color=tc if k == 0 else gc, va='center', family='monospace')
    fig.text(x0 + 0.145, yy - hh / 2, c3, fontsize=7.3, color=tc, va='center', family='monospace')
    fig.text(x0 + wd - 0.005, yy - hh / 2, d4, fontsize=7.3, color=tc if k == 0 else '#5d6476', va='center', ha='right', family='monospace')
fig.savefig('/home/claude/sn/Shinso_5m.png', facecolor='white'); print('pools', {PN[j]: round(P[j], 2) for j in P}, 'race', pr)
