"""Eternal Mangekyō mock: NQ daily (back-adjusted front month) to 23 Oct 2026 with the live weekly gaps from the 52-week look back
(the most local 2 each side, default filters), the graded one in octants, the PO3 weekly candles with the countdown, and the card."""
import sys, json, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy.stats import norm
sys.path.insert(0, '/home/claude/mgk')
from data import daily, atr
from gaps import detect, lifecycle
P = json.load(open('/home/claude/mgk/wk_par.json'))
FG, GR, SUB = '#131722', '#eef1f6', '#5d6476'; CB, CS, CSB, CVI, CINV, CCE = '#26a69a', '#ef5350', '#42a5f5', '#9575cd', '#ff9800', '#089981'
D = daily('NQ'); D = D[D.index <= '2026-10-09']
g = D.groupby('wk'); W = pd.DataFrame({'o': g.bo.first(), 'h': g.bh.max(), 'l': g.bl.min(), 'c': g.bc.last(), 'n': g.bc.size()}); W = W[W.n >= 3]
W['atr'] = atr(W.h.values, W.l.values, W.c.values)
cur = W.index[-1]                                   # the week of 19 Oct (incomplete: Mon–Fri all in, but treat as this week)
Wc = W.iloc[:-1]                                    # completed weeks
O, H, L, C, A = (Wc[x].values for x in ['o', 'h', 'l', 'c', 'atr'])
z = detect(O, H, L, C, A); z = lifecycle(z, O, H, L, C, A, horizon=150)
c2 = np.where(z.kind.values == 'VI', z.t0.values, z.t0.values - 1); disp = (C[c2] - O[c2]) * z.dir.values / A[z.t0.values]
z['w'] = (z.top - z.bot) / A[z.t0.values]
keep = ((z.kind == 'FVG') & (z.w >= 0.10) & (disp >= 0.25)) | ((z.kind == 'SB') & (z.w >= 0.10)) | ((z.kind == 'VI') & (z.w >= 0.05))
z = z[keep.values & (len(Wc) - 1 - z.t0.values <= 52)]
tw = W.iloc[-1]; wkH, wkL = tw.h, tw.l
lastC = Wc.c.iloc[-1]; aW = Wc.atr.iloc[-1]; px = D.bc.iloc[-1]
def inv(r): return r.tX >= 0
live = []
for r in z.itertuples():
    if r.tX >= 0 and r.kind != 'FVG': continue
    if r.tX >= 0:
        # inversion: spent once closed beyond the other edge
        later = C[r.tX + 1:]; spent = ((later > r.top) if r.dir == 1 else (later < r.bot)).any()
        if spent or (r.dir == 1 and wkH > r.top and px > r.top) or (r.dir == -1 and wkL < r.bot and px < r.bot): continue
    live.append(r)
above = sorted([r for r in live if r.bot > px], key=lambda r: r.bot)[:2]
below = sorted([r for r in live if r.top < px], key=lambda r: -r.top)[:2]
inside = [r for r in live if r.bot <= px <= r.top]
def reach(d, h, up):
    k, a, b = P['above' if up else 'below']; q = np.clip(2 * norm.cdf(-(d / np.sqrt(h)) / k), 1e-5, 1 - 1e-5); return 1 / (1 + np.exp(-(a + b * np.log(q / (1 - q)))))
def ptouch(kind, w):
    a, b = P[f'{kind}_inside']; return 1 / (1 + np.exp(-(a + b * np.log(max(w, 0.01)))))
def p4(kind, w):
    a, b = P[f'{kind}_hold4']; return 1 / (1 + np.exp(-(a + b * np.log(max(w, 0.01)))))
# chart: last ~260 daily candles
Dd = D.iloc[-260:]; n = len(Dd); xi = {d: i for i, d in enumerate(Dd.index)}
fig = plt.figure(figsize=(15, 8.6), dpi=130); ax = fig.add_axes([0.03, 0.07, 0.80, 0.84])
for i, (o, h, l, c) in enumerate(zip(Dd.bo, Dd.bh, Dd.bl, Dd.bc)):
    col = '#089981' if c >= o else '#f23645'; ax.plot([i, i], [l, h], color=col, lw=0.6); ax.add_patch(Rectangle((i - 0.3, min(o, c)), 0.6, max(abs(c - o), 1), fc=col, ec=col, lw=0.2))
xE = n + 6
def xof(widx):
    d = Wc.index[widx]; k = np.searchsorted(Dd.index, d); return max(k, 0)
def col(r): return CINV if inv(r) else CSB if r.kind == 'SB' else CVI if r.kind == 'VI' else (CB if r.dir == 1 else CS)
def nm(r):
    base = {'FVG': '▲ BISI' if r.dir == 1 else '▼ SIBI', 'SB': '▲ SB' if r.dir == 1 else '▼ SB', 'VI': '▲ VI' if r.dir == 1 else '▼ VI'}[r.kind]
    if inv(r): base = '▼ IFVG' if r.dir == 1 else '▲ IFVG'
    return 'W ' + base + ' · wk ' + Wc.index[r.t1 + 1 if r.kind == 'VI' else r.t0 - 1].strftime('%d %b %y')
focus = inside[0] if inside else (above[0] if above and (not below or above[0].bot - px < px - below[0].top) else (below[0] if below else None))
for r in above + below + inside:
    x1 = xof(r.t1); c = col(r)
    ax.add_patch(Rectangle((x1, r.bot), xE - x1, r.top - r.bot, fc=c, alpha=0.16, ec=c, lw=0.8))
    if r is focus:
        for k in range(9):
            y = r.bot + (r.top - r.bot) * k / 8
            ax.plot([x1, xE], [y, y], color=CCE if k == 4 else FG, lw=1.6 if k == 4 else 0.6, alpha=1 if k in (0, 4, 8) else 0.35)
            fr = (8 - k) / 8 if r.dir == 1 else k / 8
            if k in (0, 4, 8): ax.text(xE, y, f' {fr:g} ({y:,.2f})', fontsize=7, color=CCE if k == 4 else SUB, va='center')
    else:
        ax.plot([x1, xE], [(r.top + r.bot) / 2] * 2, color=c, lw=0.8, ls='--')
    ax.text(x1, r.top if r.dir == 1 or inv(r) else r.top, ' ' + nm(r), fontsize=7.4, color=c, va='bottom')
# PO3 of the focus gap with the countdown
if focus is not None:
    x0 = n + 14; step = 4
    idx = [focus.t1, focus.t1 + 1, focus.t0] if focus.kind != 'VI' else [focus.t1, focus.t0]
    ax.add_patch(Rectangle((x0 - 1, focus.bot), len(idx) * step + 1, focus.top - focus.bot, fc=col(focus), alpha=0.2, ec=col(focus)))
    for j, t in enumerate(idx):
        o, h, l, c = O[t], H[t], L[t], C[t]; xm = x0 + j * step + 1.5
        ax.plot([xm, xm], [l, h], color='#787b86', lw=0.9); ax.add_patch(Rectangle((xm - 1.4, min(o, c)), 2.8, abs(c - o), fc='#787b86', alpha=0.25 if c >= o else 0.8, ec='#787b86'))
        ax.text(xm, l, Wc.index[t].strftime('%d %b'), fontsize=6.5, color=SUB, ha='center', va='top')
    yT = max(focus.top, H[idx].max())
    ax.text(x0 - 1, yT, ' W closes in 0d 00h 00m · this week ' + f'{wkL:,.2f}–{wkH:,.2f}', fontsize=7, color=SUB, va='bottom')
lo = min(Dd.bl.min(), *(r.bot for r in below)) if below else Dd.bl.min(); hi = max(Dd.bh.max(), *(r.top for r in above)) if above else Dd.bh.max()
pad = (hi - lo) * 0.04; ax.set_ylim(lo - pad, hi + pad); ax.set_xlim(-1, n + 34)
ax.yaxis.tick_right(); ax.grid(color=GR, lw=0.6); ax.tick_params(colors=FG, labelsize=8, length=0)
for sp in ax.spines.values(): sp.set_color(GR)
tk = [i for i, d in enumerate(Dd.index) if d.day <= 7 and d.dayofweek == 0][::2]; ax.set_xticks(tk); ax.set_xticklabels([Dd.index[i].strftime('%b %y') for i in tk])
fig.text(0.03, 0.955, 'Eternal Mangekyō · NQ daily (back-adjusted) to 9 Oct 2026 · weekly gaps from the 52-week look back, the nearest graded in octants, PO3 weekly candles right of price', fontsize=10.2, color=FG, weight='bold')
rows = [('◆ ETERNAL MANGEKYŌ  NQ1!  1! back-adj · SET · 52w look back', '', '', '', '', '')]
rows.append(('WEEKLY GAP', 'RANGE', 'ATR · DIST', 'STATUS', '4W · 12W', 'HOLDS · 4W'))
def row(r, up):
    w = (r.top - r.bot) / A[r.t0]; d = ((r.bot - lastC) if up else (lastC - r.top)) / aW
    hit = (r.tT >= 0 and not inv(r))
    st = 'inverted' if inv(r) else ('touched' if hit else 'untouched')
    return (nm(r)[2:], f'{r.bot:,.0f}–{r.top:,.0f}', f'{w:.2f} · {"✓" if hit else f"{d:.1f}"}', st,
            'reached' if hit else f'{100*reach(max(d,0),4,up):.0f}% · {100*reach(max(d,0),12,up):.0f}%', '—' if (inv(r) or hit) else f'{100*ptouch(r.kind, w):.0f}% · {100*p4(r.kind, w):.0f}%')
for r in above[::-1]: rows.append(row(r, True))
rows.append((f'— price {px:,.2f}', '', '', '', '', ''))
for r in inside: rows.append(row(r, False))
for r in below: rows.append(row(r, False))
x0, y0, hh = 0.035, 0.30, 0.026; cw = [0.0, 0.17, 0.25, 0.32, 0.40, 0.475, 0.55]
for k, rr in enumerate(rows):
    yy = y0 - k * hh
    fig.patches.append(Rectangle((x0, yy - hh), cw[-1], hh, transform=fig.transFigure, fc='#eef1f6' if k in (0, 1) or rr[0].startswith('—') else '#ffffff', ec='#d5dae4', lw=0.5))
    if k == 0 or rr[0].startswith('—'):
        fig.text(x0 + 0.004, yy - hh / 2, rr[0], fontsize=7.2, color=FG, va='center', family='monospace'); continue
    for j, t in enumerate(rr): fig.text(x0 + cw[j] + 0.004, yy - hh / 2, t, fontsize=7.0, color=SUB if k == 1 else FG, va='center', family='monospace')
fig.savefig('/home/claude/em/EternalMangekyo_daily.png', facecolor='white'); print('above', [(r.kind, r.bot, r.top) for r in above], 'below', [(r.kind, r.bot, r.top) for r in below], 'inside', len(inside))
