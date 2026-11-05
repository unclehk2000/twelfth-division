"""Hōgyoku: port check (formation, readings inputs, reach odds with the script's normal-CDF approximation) against the research
matrix, and the mock (NQ 15 minutes, 22 Oct 2026 as of 11:30 ET, 4H profile)."""
import numpy as np, pandas as pd, json, sys, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy.stats import norm
sys.path.insert(0, '/home/claude/lr'); from lib import load
J = json.load(open('/home/claude/pdm/pine_params.json')); SY = ['NQ', 'ES', 'YM', 'RTY']; TFS = ['15', '60', '240', 'D']; TN = ['15m', '1H', '4H', 'D']
def ncdf(x):
    t = 1 / (1 + 0.2316419 * np.abs(x)); d = 0.3989423 * np.exp(-x * x / 2)
    p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274)))); return np.where(x > 0, 1 - p, p)
lgt = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
def reach(t, k, lv, d): ix = (t * 4 + k) * 4 + lv; return np.where(d <= 0, 1.0, 1 / (1 + np.exp(-(J['RA'][ix] + J['RB'][ix] * lgt(2 * ncdf(-d))))))
def form(h1, l1, h2, l2, c2):
    sh = h2 > h1; sl = l2 < l1
    return np.select([sl & ~sh & (c2 > l1), sh & ~sl & (c2 < h1), c2 > h1, c2 < l1, ~sh & ~sl], ['bullC2', 'bearC2', 'expUp', 'expDn', 'inside'], 'outside')
# port check
print('normal CDF approximation, max error', float(np.max(np.abs(ncdf(np.linspace(-6, 6, 10001)) - norm.cdf(np.linspace(-6, 6, 10001))))))
for t, tf in enumerate(TFS):
    W = pd.read_pickle(f'/home/claude/pdm/mat_{tf}.pkl'); agree = []; dp = []
    for k, s in enumerate(SY):
        A = W[s]; H1 = A.H - A.dh * A.atr; L1 = A.L + A.dl * A.atr
        agree.append(np.mean(form(H1.values, L1.values, A.H.values, A.L.values, A.C.values) == A.form.values))
        d = ((A.H - A.C) / A.atr).values; ok = d > 0; a, b = J['RA'][(t * 4 + k) * 4], J['RB'][(t * 4 + k) * 4]
        ref = 1 / (1 + np.exp(-(a + b * lgt(2 * norm.cdf(-d[ok]))))); dp.append(np.max(np.abs(reach(t, k, 0, d[ok]) - ref)))
    print(f'{TN[t]}: formation agreement {min(agree):.5f}–{max(agree):.5f}, reach max |Δp| vs exact Φ {max(dp):.2e}')
# mock: candles at a moment from minute data
T = pd.Timestamp('2026-10-22 11:30'); tmin = int((T - pd.Timestamp('1970-01-01')).total_seconds() // 60)
M = {s: load(s) for s in SY}
def ohlc_blocks(m, tf):
    rel = (((m['ts'] % 1440) - 1080) % 1440).astype(np.int64); td = m['td'].astype(np.int64)
    blk = np.zeros_like(rel) if tf == 'D' else rel // {'15': 15, '60': 60, '240': 240}[tf]
    return td * 1000 + blk
def candles_at(s, tf):
    m = M[s]; key = ohlc_blocks(m, tf); i = np.searchsorted(m['ts'], tmin) - 1; kc = key[i]
    ks = np.unique(key[max(0, i - 40000):i + 1]); ks = ks[ks <= kc]
    out = []
    for kk in ks[-16:]:
        mk = (key == kk) & (m['ts'] <= tmin); idx = np.flatnonzero(mk)
        out.append((m['O'][idx[0]], m['H'][idx].max(), m['L'][idx].min(), m['C'][idx[-1]]))
    out = np.array(out); rng = out[:, 1] - out[:, 2]; atr = rng[-16:-2].mean()   # 14 candles before C2
    return out[-3], out[-2], out[-1], atr
data = {(t, s): candles_at(s, tf) for t, tf in enumerate(TFS) for s in SY}
# chart: NQ 15m from 18:00
m = M['NQ']; rel = (((m['ts'] % 1440) - 1080) % 1440); td0 = m['td'][np.searchsorted(m['ts'], tmin) - 1]
sel = np.flatnonzero((m['td'] == td0) & (m['ts'] <= tmin)); key = (m['ts'][sel] // 15)
br = np.r_[0, np.flatnonzero(np.diff(key)) + 1]; en = np.r_[br[1:] - 1, len(key) - 1]
bars = [(m['O'][sel[a]], m['H'][sel[a:b + 1]].max(), m['L'][sel[a:b + 1]].min(), m['C'][sel[b]]) for a, b in zip(br, en)]
fig = plt.figure(figsize=(15, 8.8), dpi=130); ax = fig.add_axes([0.03, 0.07, 0.84, 0.85])
for i, (o, h, l, c) in enumerate(bars):
    col = '#089981' if c >= o else '#f23645'; ax.plot([i, i], [l, h], color=col, lw=0.8); ax.add_patch(Rectangle((i - 0.32, min(o, c)), 0.64, max(abs(c - o), 0.25), fc=col, ec=col))
n = len(bars); x0 = n + 6
C1n, C2n, C3n, _ = data[(2, 'NQ')]; aH, aL = C1n[1], C1n[2]
w, g = 2, 2; gw = 3 * (w + g) - g; topAll = aH; xEnd = x0 + 4 * (gw + 2 * g) - 2 * g
times = ['02:00', '06:00', '10:00']
for k, s in enumerate(SY):
    c1, c2, c3, a = data[(2, s)]; sc = (aH - aL) / (c1[1] - c1[2]); f = lambda p_: aL + (p_ - c1[2]) * sc
    xb = x0 + k * (gw + 2 * g); gTop = None
    for j, (o, h, l, c) in enumerate([c1, c2, c3]):
        up = c >= o; mc = '#26a69a' if up else '#ef5350'; x1 = xb + j * (w + g); xm = x1 + w / 2
        bt, bb = max(f(o), f(c)), min(f(o), f(c))
        ax.plot([xm, xm], [bt, f(h)], color=mc, alpha=0.7, lw=1); ax.plot([xm, xm], [f(l), bb], color=mc, alpha=0.7, lw=1)
        ax.add_patch(Rectangle((x1, bb), w, max(bt - bb, 0.5), fc=mc, alpha=0.3, ec=mc, lw=1.1, ls='--' if j == 2 else '-'))
        ax.text(xm, f(l), times[j] + '\nC' + str(j + 1), ha='center', va='top', fontsize=6.3, color='#5d6476', linespacing=1.2)
        gTop = f(h) if gTop is None else max(gTop, f(h))
    fm = str(form(np.array([c1[1]]), np.array([c1[2]]), np.array([c2[1]]), np.array([c2[2]]), np.array([c2[3]]))[0])
    gl = {'bullC2': '▲ C2', 'bearC2': '▼ C2', 'expUp': '⇧ exp', 'expDn': '⇩ exp', 'inside': '◆ in', 'outside': '✕ out'}[fm]
    ax.text(xb + gw / 2, gTop, f'{s} {gl}', ha='center', va='bottom', fontsize=7.5, color='#ab47bc' if s == 'NQ' else '#5d6476', weight='bold' if s == 'NQ' else None)
    topAll = max(topAll, gTop)
for y, nm in [(aH, 'C1 high'), (aL, 'C1 low')]:
    ax.plot([x0 - 2, xEnd + 2], [y, y], color='#9aa1ad', ls=':', lw=1); ax.text(xEnd + 2.5, y, nm, fontsize=7, color='#5d6476', va='center')
ax.text((x0 + xEnd) / 2, topAll + (aH - aL) * 0.25, '4H · 02h 30m', ha='center', va='bottom', fontsize=7.5, color='#131722')
lo = min(min(b[2] for b in bars), aL - (aH - aL) * 0.9); hi = max(max(b[1] for b in bars), topAll + (aH - aL) * 0.45); pad = (hi - lo) * 0.03
ax.set_ylim(lo - pad, hi + pad); ax.set_xlim(-1, xEnd + 12)
ax.yaxis.tick_right(); ax.grid(color='#eef1f6', lw=0.6); ax.tick_params(colors='#131722', labelsize=8, length=0)
for sp in ax.spines.values(): sp.set_color('#eef1f6')
tk = list(range(0, n, 8)); ax.set_xticks(tk); ax.set_xticklabels([f"{((rel[sel[br[i]]] + 1080) % 1440) // 60:02d}:{(rel[sel[br[i]]] + 1080) % 60:02d}" for i in tk])
fig.text(0.03, 0.955, 'Hōgyoku · NQ 15 min · 22 Oct 2026 as of 11:30 ET · four-market price delivery matrix, C1-aligned 4H profile (Hadō 99 candles), tested reach odds', fontsize=10.5, color='#131722', weight='bold')
# card
G = {'bullC2': ('▲ C2', '#26a69a'), 'bearC2': ('▼ C2', '#ef5350'), 'expUp': ('⇧ exp', '#26a69a'), 'expDn': ('⇩ exp', '#ef5350'), 'inside': ('◆ in', '#8a93a6'), 'outside': ('✕ out', '#8a93a6')}
rows = [('HŌGYOKU', ['15m', '1H', '4H', 'D'], 'h')]
for k, s in enumerate(SY):
    cells = []
    for t in range(4):
        c1, c2, c3, a = data[(t, s)]; fm = str(form(np.array([c1[1]]), np.array([c1[2]]), np.array([c2[1]]), np.array([c2[2]]), np.array([c2[3]]))[0]); cells.append(G[fm])
    rows.append((s + (' ◂' if s == 'NQ' else ''), cells, 'm'))
base = J['BASE']
for t in range(4):
    c1, c2, c3, a = data[(t, 'NQ')]; s_ = []
    for lv, (lvl, up) in enumerate([(c2[1], 1), (c2[2], 0), (c1[1], 1), (c1[2], 0)]):
        d = (lvl - c2[3]) / a if up else (c2[3] - lvl) / a; hit = (c3[1] > lvl) if up else (c3[2] < lvl)
        s_.append(['C2H', 'C2L', 'C1H', 'C1L'][lv] + ' ' + ('thru' if d <= 0 else f'{100 * float(reach(t, 0, lv, np.array(d))):.0f}%') + ('✓' if hit and d > 0 else ''))
    rows.append((f'{TN[t]} C3 reach', ' · '.join(s_), 'r'))
    # readings for NQ on this timeframe
    fNQ = str(form(np.array([c1[1]]), np.array([c1[2]]), np.array([c2[1]]), np.array([c2[2]]), np.array([c2[3]]))[0]); txt = []
    r2 = {s: (data[(t, s)][1][3] - data[(t, s)][0][3]) / data[(t, s)][3] for s in SY}; spr = r2['NQ'] - np.mean([r2[s] for s in SY[1:]])
    swl = {s: data[(t, s)][1][2] < data[(t, s)][0][2] for s in SY}; swh = {s: data[(t, s)][1][1] > data[(t, s)][0][1] for s in SY}
    col = {s: np.sign(data[(t, s)][1][3] - data[(t, s)][1][0]) for s in SY}; psp = any(col[s] != col['NQ'] for s in SY[1:])
    heldHi = (not swh['NQ']) and any(swh[s] for s in SY[1:])
    if t == 0:
        if fNQ == 'expUp': txt.append('⇧ exp → C3 up −1.6')
        if fNQ == 'expDn': txt.append('⇩ exp → C3 up +1.6')
        if psp and col['NQ'] > 0: txt.append('PSP green −0.6')
        if psp and col['NQ'] < 0: txt.append('PSP red +0.7')
        if spr <= J['Q20'][0]: txt.append('laggard +0.3')
        if spr >= J['Q80'][0]: txt.append('leader −0.6')
        if heldHi: txt.append('held high (partner swept) +0.2')
    elif t == 1:
        if fNQ == 'bullC2': txt.append('▲C2 +1.4')
        if fNQ == 'expUp': txt.append('⇧ exp −1.6')
        if heldHi: txt.append('held high (partner swept) +0.8')
        if psp and col['NQ'] < 0: txt.append('PSP red +1.0')
        if spr <= J['Q20'][1]: txt.append('laggard +0.5')
    elif t == 2:
        if fNQ == 'bullC2' and not all(swl[s] for s in SY[1:]): txt.append('▲C2 + SMT +2.0')
    rows.append((f'{TN[t]} C3 up', f'drift {base[t * 4]:.1f}%' + (' · ' + ' · '.join(txt) + ' pts' if txt else ' · no tested reading'), 'u'))
rows.append(('tested', 'reach calibrated · direction ≈ drift · 15 / 72 readings passed', 'r'))
x0c, y0, wd, hh = 0.035, 0.405, 0.36, 0.0235
for i, (a, b, kind) in enumerate(rows):
    yy = y0 - i * hh
    fig.patches.append(Rectangle((x0c, yy - hh), wd, hh, transform=fig.transFigure, fc='#7e57c2' if kind == 'h' else '#f4f6f9', ec='#7e57c2' if kind == 'h' else '#dde1e8', lw=0.6))
    fig.text(x0c + 0.005, yy - hh / 2, a, fontsize=7, color='#ffffff' if kind == 'h' else ('#ab47bc' if '◂' in a else '#5d6476'), va='center', family='monospace')
    if kind in ('h', 'm'):
        for j, c in enumerate(b):
            txt, cc = (c, '#ffffff') if kind == 'h' else c
            fig.text(x0c + 0.105 + j * 0.062, yy - hh / 2, txt, fontsize=7, color=cc, va='center', ha='center', family='monospace')
    else:
        fig.text(x0c + 0.075, yy - hh / 2, b, fontsize=6.6, color='#ab47bc' if (kind == 'u' and 'pts' in b) else '#131722', va='center', family='monospace')
fig.savefig('/home/claude/pdm/Hogyoku_15m.png', facecolor='white')
print('mock rows:'); [print('  ', r[0], r[1]) for r in rows]
