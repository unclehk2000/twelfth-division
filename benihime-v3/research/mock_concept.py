"""Benihime v3 concept: the RTH-only 'jigsaw' on a 1-hour chart, each day's ORG between the pieces, the week's ORG CEs carried
through Friday (last week's Monday and Friday dashed), RTH-only swings and structure shifts, today's ORG graded like Zabimaru's
opening range, and a Zabimaru-style card with the triplet. NQ data, real; layout is a proposal."""
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plt.rcParams['font.family'] = 'DejaVu Sans'
NOW = pd.Timestamp('2026-10-23 13:00'); D0 = pd.Timestamp('2026-10-12')
BG, MU, GRD, CHT = '#ffffff', '#9aa1b2', '#eef1f6', '#131722'
UPC, DNC, CEC, ORG_UP, ORG_DN = '#089981', '#f23645', '#7b1fa2', '#26a69a', '#ef5350'
fmt = lambda v: f'{np.floor(v / 0.25 + 0.5) * 0.25:,.2f}'
WD = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
def days(sym):
    return pd.read_pickle(f'/home/claude/coc/days_{sym}.pkl').set_index('tday')
b = pd.read_pickle('/home/claude/kyw/bars_NQ_all.pkl')
b = b[(b.tday >= D0) & (b.tday <= NOW.normalize()) & (b.hm >= 930) & (b.hm <= 1614) & (b.ts < NOW)]
# RTH-only 1h candles
b['h'] = ((b.hm // 100) * 60 + b.hm % 100 - 570) // 60
c = b.groupby(['tday', 'h']).agg(o=('Open', 'first'), hh=('High', 'max'), ll=('Low', 'min'), cl=('Close', 'last'), t=('ts', 'first')).reset_index()
n = len(c); c['x'] = np.arange(n)
fig = plt.figure(figsize=(19, 10.2), dpi=100, facecolor=BG); ax = fig.add_axes([0.01, 0.05, 0.60, 0.85])
for sp in ax.spines.values(): sp.set_visible(False)
ax.set_facecolor(BG); ax.yaxis.tick_right(); ax.tick_params(axis='y', colors=MU, labelsize=8); ax.tick_params(axis='x', length=0); ax.grid(color=GRD, lw=0.7, zorder=0)
for r in c.itertuples():
    col = UPC if r.cl >= r.o else DNC
    ax.plot([r.x, r.x], [r.ll, r.hh], color=col, lw=0.9, zorder=4)
    ax.add_patch(Rectangle((r.x - 0.32, min(r.o, r.cl)), 0.64, max(abs(r.cl - r.o), 1), fc=col, ec=col, lw=0.3, zorder=5))
starts = c.groupby('tday').x.min(); ends = c.groupby('tday').x.max(); dlist = list(starts.index)
for d in dlist[1:]: ax.axvline(starts[d] - 0.5, color='#90caf9', lw=0.8, alpha=0.7, zorder=1)
DN = days('NQ'); xr = n - 1 + 0.6; LBL = []
# each ORG between the pieces; this week's CEs carried to Friday, last week's Monday and Friday dashed
wk = NOW.normalize() - pd.Timedelta(days=NOW.dayofweek)
for d in dlist:
    if d == dlist[0]: continue
    r = DN.loc[d]; x0 = starts[d] - 0.5; col = ORG_UP if r.up else ORG_DN
    ax.add_patch(Rectangle((x0 - 0.35, min(r.pc, r.op)), 0.7, abs(r.op - r.pc), fc=col, alpha=0.35, ec=col, lw=0.8, zorder=3))
    ce = (r.op + r.pc) / 2; thisw = d >= wk; lastMF = (d < wk) and (d >= wk - pd.Timedelta(days=7)) and d.dayofweek in (0, 4)
    if thisw or lastMF:
        after = c[(c.x > starts[d]) | ((c.x == starts[d]))]
        hit = after[(after.ll <= ce) & (after.hh >= ce)]
        xt = hit.x.iloc[0] if len(hit) else None
        ls = '-' if thisw else (0, (5, 3))
        ax.plot([x0, xr], [ce, ce], color=CEC, lw=1.4 if thisw else 1.0, ls=ls, alpha=0.95 if thisw else 0.7, zorder=3)
        tag = (WD[d.dayofweek] if thisw else 'last ' + WD[d.dayofweek]) + ' ORG CE ' + fmt(ce) + (f' ✓ {c.loc[c.x == xt, "t"].iloc[0]:%a %H:%M}' if xt is not None else '')
        LBL.append((ce, tag, CEC))
# yesterday's RTH high / low
y = dlist[-2]; LBL += [(DN.loc[y].rH, f'RTH PDH {fmt(DN.loc[y].rH)}', '#1e88e5'), (DN.loc[y].rL, f'RTH PDL {fmt(DN.loc[y].rL)}', '#1e88e5')]
for v in (DN.loc[y].rH, DN.loc[y].rL): ax.plot([starts[y], xr], [v, v], color='#1e88e5', lw=0.9, ls=':', zorder=3)
# RTH-only swings (2 either side) and structure shifts by a 1h close
hh, ll, cl = c.hh.values, c.ll.values, c.cl.values; lastH = lastL = None; state = 0
for i in range(n):
    j = i - 2
    if j >= 2 and hh[j] > hh[j - 2:j].max() and hh[j] > hh[j + 1:i + 1].max():
        lastH = (j, hh[j]); ax.annotate('▼', (j, hh[j]), xytext=(0, 3), textcoords='offset points', ha='center', fontsize=7, color=DNC, zorder=7)
    if j >= 2 and ll[j] < ll[j - 2:j].min() and ll[j] < ll[j + 1:i + 1].min():
        lastL = (j, ll[j]); ax.annotate('▲', (j, ll[j]), xytext=(0, -10), textcoords='offset points', ha='center', fontsize=7, color=UPC, zorder=7)
    if lastH and cl[i] > lastH[1] and state != 1:
        state = 1; ax.plot([lastH[0], i], [lastH[1]] * 2, color=UPC, lw=1.1, ls='--', zorder=6)
        ax.text((lastH[0] + i) / 2, lastH[1], 'MSS ▲', color=UPC, fontsize=7.5, ha='center', va='bottom', zorder=7, weight='bold'); flip = lastL; lastH = None
    elif lastL and cl[i] < lastL[1] and state != -1:
        state = -1; ax.plot([lastL[0], i], [lastL[1]] * 2, color=DNC, lw=1.1, ls='--', zorder=6)
        ax.text((lastL[0] + i) / 2, lastL[1], 'MSS ▼', color=DNC, fontsize=7.5, ha='center', va='top', zorder=7, weight='bold'); flip = lastH; lastL = None
    if state == 1: mssT, mssD = c.t.iloc[i] if False else None, None
# today's ORG graded (octants, CE, ±0.5 / ±1 SD), from today's first candle
t = dlist[-1]; r = DN.loc[t]; G = r.G; x0 = starts[t] - 0.5; s = 1 if r.up else -1
for q in (0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1):
    v = r.pc + q * (r.op - r.pc); w = 1.6 if q in (0, 0.5, 1) else 1.0 if q in (0.25, 0.75) else 0.6
    ax.plot([x0, xr], [v, v], color=ORG_UP if r.up else ORG_DN, lw=w, alpha=0.9 if q in (0, 0.5, 1) else 0.55, ls='-' if q != 0.5 else '--', zorder=3)
for k, nm in ((0.5, '+0.5 SD'), (1.0, '+1 SD')):
    v = r.op + s * k * G; ax.plot([x0, xr], [v, v], color='#ff9800', lw=0.9, ls=':', zorder=3); LBL.append((v, f'ORG {nm} {fmt(v)}', '#ff9800'))
    v = r.pc - s * k * G; ax.plot([x0, xr], [v, v], color='#ff9800', lw=0.9, ls=':', zorder=3); LBL.append((v, f'ORG −{nm[1:]} {fmt(v)}', '#ff9800'))
LBL += [(r.op, f'Fri ORG open {fmt(r.op)}', ORG_DN), (r.pc, f'Fri ORG close (Thu 16:14) {fmt(r.pc)}', ORG_DN)]
# labels (merge within 0.5% of ADR-ish 5 pts)
grp = []
for yv, tx, col in sorted(LBL, key=lambda z: -z[0]):
    if grp and abs(grp[-1][3] - yv) <= 6: grp[-1][0].append(yv); grp[-1][1].append(tx); grp[-1][3] = yv
    else: grp.append([[yv], [tx], col, yv])
for ys, txs, col, _ in grp: ax.text(xr + 0.4, float(np.mean(ys)), '\n'.join(txs), color=col, fontsize=7, va='center', zorder=8)
ax.set_xticks([starts[d] for d in dlist]); ax.set_xticklabels([f'{d:%a %d}' for d in dlist], color=MU, fontsize=8)
ax.set_xlim(-1, n + 14); lo, hi = c.ll.min(), c.hh.max(); ax.set_ylim(lo - 60, hi + 60)
# ── card (Zabimaru style)
def times(sym):
    Dd = days(sym).loc[t]; bb = pd.read_pickle(f'/home/claude/kyw/bars_{sym}_all.pkl'); bb = bb[(bb.tday == t) & (bb.hm >= 930) & (bb.hm <= 1614) & (bb.ts < NOW)]
    ce = (Dd.op + Dd.pc) / 2
    f = bb[(bb.Low <= Dd.pc)] if Dd.up else bb[(bb.High >= Dd.pc)]; e = bb[(bb.Low <= ce)] if Dd.up else bb[(bb.High >= ce)]
    return Dd, (f.ts.iloc[0] if len(f) else None), (e.ts.iloc[0] if len(e) else None)
rowsC = []
for sym in ('NQ', 'ES', 'RTY'):
    Dd, tf, tc = times(sym)
    rowsC.append((sym, f"{'▲' if Dd.up else '▼'} {Dd.G:,.2f} · {Dd.G / Dd.avg20:.2f}× avg", f'CE ✓ {tc:%H:%M}' if tc is not None else 'CE —', f'fill ✓ {tf:%H:%M}' if tf is not None else 'open'))
cx = fig.add_axes([0.665, 0.40, 0.325, 0.50]); cx.axis('off'); cx.set_xlim(0, 1); cx.set_ylim(0, 1)
cx.add_patch(Rectangle((0, 0), 1, 1, fc='#161a25', ec='#ef5350', lw=1.2))
cx.add_patch(Rectangle((0, 0.925), 1, 0.075, fc='#ef5350', ec='none'))
cx.text(0.03, 0.965, 'BENIHIME   RTH ORG', color='white', fontsize=9.5, weight='bold', va='center', family='DejaVu Sans Mono')
cx.text(0.50, 0.965, '10/23 · 13:00 ET', color='white', fontsize=9, va='center', family='DejaVu Sans Mono')
cx.add_patch(Rectangle((0.80, 0.94), 0.17, 0.05, fc='white', ec='none')); cx.text(0.885, 0.965, '▼ FILLED', color='#ef5350', fontsize=8.5, ha='center', va='center', weight='bold', family='DejaVu Sans Mono')
Dn, tfn, tcn = times('NQ')
L1 = [('GAP', f'▼ {Dn.G:,.2f} pts · {100 * Dn.G / Dn.op:.2f}%', f'{Dn.G / Dn.avg20:.2f}× avg'),
      ('CE', fmt((Dn.op + Dn.pc) / 2), f'✓ {tcn:%H:%M}'), ('FILL', fmt(Dn.pc), f'✓ {tfn:%H:%M}'),
      ('−1 SD', f'{fmt(Dn.pc + Dn.G)} (past the close)', 'odds after the fill'),
      ('TRIPLET', 'gap · × avg', 'CE / fill')] + [(f'  {a}', b_, f'{c_} · {d_}') for a, b_, c_, d_ in rowsC] + [
      ('SISTERS', 'ES ✓ · RTY ✓ filled first?', 'tested: +4 pts each (borderline)'),
      ('WEEK CE', 'nearest Mon 29,571.25 · +0.62× ATR', '4 above · 0 below'),
      ('RTH 1H', 'structure from RTH candles only', 'MSS ▼ / ▲ · flip level'),
      ('PD RTH', f'H {fmt(DN.loc[y].rH)} · L {fmt(DN.loc[y].rL)}', 'yesterday, RTH only')]
yy = 0.87
for a, b_, c_ in L1:
    hdr = a in ('TRIPLET',)
    cx.text(0.03, yy, a, color='#ef5350' if hdr else '#8a8f9c', fontsize=8.3, va='center', family='DejaVu Sans Mono', weight='bold' if hdr else 'normal')
    cx.text(0.24, yy, b_, color='#d1d4dc', fontsize=8.3, va='center', family='DejaVu Sans Mono')
    cx.text(0.97, yy, c_, color='#d1d4dc', fontsize=8.3, va='center', ha='right', family='DejaVu Sans Mono')
    yy -= 0.077
fig.text(0.01, 0.955, 'Benihime v3 concept · NQ 1-hour, RTH candles only (the "jigsaw"), Fri 23 Oct 2026 13:00 ET', color=CHT, fontsize=13, weight='bold')
fig.text(0.01, 0.928, "Each ORG between the pieces (shaded), this week's ORG CEs carried to Friday (solid, ✓ when traded), last week's Monday and Friday (dashed), RTH-only swings ▼▲ and shifts, today's ORG graded with ±SD, and a Zabimaru-style card. A proposal to weigh, from real data.", color='#5d6476', fontsize=9)
plt.savefig('Benihime_v3_concept_NQ_1h_RTH.png', dpi=100, facecolor=BG); print('saved')
