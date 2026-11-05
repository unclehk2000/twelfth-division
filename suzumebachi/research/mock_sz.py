"""Suzumebachi mock: ES 5 minutes, sensitivity 3, 21 Oct 2026 from 18:00 to 10:30 ET, drawn by the Python port."""
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from port_sz import run
td0 = int(np.datetime64('2026-10-21', 'D').astype(np.int64)); CUT = 990
E, A = run('ES', 5, 3, td0, full=True)
CH = [54.4, 54.8, 55.0, 55.6, 55.6, 55.2]; WK = [51.6, 52.2, 51.3]; cfg = 1
d0 = np.flatnonzero((A['td'] == td0) & (A['rel'] <= CUT)); i0, i1 = d0[0], d0[-1]
E = E[(E.i >= i0) & (E.i <= i1)].copy()
def passed(e):
    tested = 0.5 <= e.rA <= 12
    chase = (not e.mss) and e.dir == -1 and e.cell in (14, 16)
    weak = e.mss and e.raid == '' and ((not e.fvg) or e.rA < 1.5)
    if not tested or not (chase or weak): return None
    if chase: return 55.9 if 120 <= e.rel < 660 else 57.9 if 1050 <= e.rel < 1170 else CH[cfg]
    if e.dir == -1: return 53.8 if (360 <= e.rel < 480 or 1170 <= e.rel < 1320) else 52.6
    return 50.9
O, H, L, C, rel = A['O'], A['H'], A['L'], A['C'], A['rel']
fig = plt.figure(figsize=(15, 8.8), dpi=130); ax = fig.add_axes([0.03, 0.07, 0.84, 0.85])
X = lambda i: i - i0
for i in range(i0, i1 + 1):
    col = '#089981' if C[i] >= O[i] else '#f23645'; ax.plot([X(i)] * 2, [L[i], H[i]], color=col, lw=0.6); ax.add_patch(Rectangle((X(i) - 0.3, min(O[i], C[i])), 0.6, max(abs(C[i] - O[i]), 0.05), fc=col, ec=col, lw=0.2))
GOLD = '#ffb300'; last = None
for e in E.itertuples():
    f = passed(e); cc = GOLD if f else ('#ef5350' if e.dir == -1 else '#26a69a'); nm = 'MSS' if e.mss else 'BOS'
    sx = max(X(e.sb), -1)
    ax.plot([sx, X(e.i)], [e.sv, e.sv], color=cc, lw=1.1 if f else 0.9, ls='-' if e.mss else '--')
    ax.text((sx + X(e.i)) / 2, e.sv, f"{nm} {'▼' if e.dir == -1 else '▲'}" + (f' · fails {f:.0f}%' if f else ''), color=cc, fontsize=7.4 if f else 6.8, ha='center', va='top' if e.dir == -1 else 'bottom', weight='bold' if f else None, clip_on=True)
    if f:
        oneR = e.entry + e.dir * e.risk; j = e.i + 1; res = None
        while j <= i1:
            hx = H[j] >= e.x if e.dir == -1 else L[j] <= e.x; h1 = L[j] <= oneR if e.dir == -1 else H[j] >= oneR
            if hx or h1: res = 'x' if hx and not h1 else '1' if h1 and not hx else 'b'; break
            j += 1
        end = X(min(j, i1))
        ax.plot([X(e.i), end], [e.x, e.x], color=GOLD, ls=':', lw=1.8); ax.plot([X(e.i), end], [oneR, oneR], color=cc if False else ('#ef5350' if e.dir == -1 else '#26a69a'), ls=':', lw=1)
        ax.text(end + 0.5, e.x, f"extreme · {f:.0f}% first" + (' ✓' if res == 'x' else ''), color=GOLD, fontsize=7, va='center', clip_on=True)
        ax.text(end + 0.5, oneR, f"1R · {100 - f:.0f}%" + (' ✓' if res == '1' else ''), color='#ef5350' if e.dir == -1 else '#26a69a', fontsize=7, va='center', clip_on=True)
    last = (e, f)
lo, hi = L[i0:i1 + 1].min(), H[i0:i1 + 1].max(); pad = (hi - lo) * 0.06; ax.set_ylim(lo - pad, hi + pad * 6.5); ax.set_xlim(-1, X(i1) + 30)
ax.yaxis.tick_right(); ax.grid(color='#eef1f6', lw=0.6); ax.tick_params(colors='#131722', labelsize=8, length=0)
for sp in ax.spines.values(): sp.set_color('#eef1f6')
tk = [X(i) for i in range(i0, i1 + 1) if rel[i] % 120 == 0]; ax.set_xticks(tk); ax.set_xticklabels([f"{((rel[i0 + t] + 1080) % 1440) // 60:02d}:00" for t in tk])
fig.text(0.03, 0.955, 'Suzumebachi · ES 5 min · sensitivity 3 · 21 Oct 2026 as of 10:30 ET · structure breaks with tested odds (gold = fails more often than not)', fontsize=10.5, color='#131722', weight='bold')
e, f = last; tt = lambda r: f"{((r + 1080) % 1440) // 60:02d}:{(r + 1080) % 60:02d}"
cn = {0: 'MSS · no raid · no FVG', 1: 'MSS · no raid · no FVG · tight stop', 2: 'MSS · no raid · FVG', 3: 'MSS · no raid · FVG · tight stop', 4: 'MSS · raid · no FVG', 5: 'MSS · raid · no FVG · tight', 6: 'MSS · raid · FVG (textbook)', 7: 'MSS · raid · FVG · tight'}
nmC = cn.get(e.cell, 'BOS · ' + ('PD low quarter' if e.cell < 11 else 'PD middle' if e.cell < 14 else 'PD top quarter+') + ' · ' + ['before 00:00', 'ICT side of 00:00 open', 'wrong side of 00:00 open'][(e.cell - 8) % 3])
rows = [('SUZUMEBACHI', 'STRUCTURE BREAK ODDS', '5m · k3'),
        ('last break', f"{'MSS' if e.mss else 'BOS'} {'▼' if e.dir == -1 else '▲'} {tt(e.rel)}", 'live'),
        ('scenario', nmC, ''),
        ('fails' if f else 'odds', f'extreme first {f:.1f}%' if f else '1R first ≈ coin flip', f'1R {100 - f:.1f}%' if f else ''),
        ('levels', f'extreme {e.x:,.2f}', f'1R {e.entry + e.dir * e.risk:,.2f}'),
        ('leg', f"raid: {e.raid or 'none'} · {'FVG' if e.fvg else 'no FVG'}", f'stop {e.rA:.1f} ATR'),
        ('location', f'prior day {100 * e.pdx:.0f}% to its side', ['before 00:00', 'ICT side of 00:00', 'wrong side of 00:00'][e.mos]),
        ('PASSED', 'setups at this setting', 'extreme first'),
        ('', 'sell BOS chasing PD top ¼', '54.8% · 25–26 54.9%'),
        ('', '  … 20:00–05:00', '55.9%'),
        ('', 'weak MSS (no raid; no FVG / tight)', '52.2% · 25–26 53.1%'),
        ('textbook', 'MSS · raid · FVG · normal stop', '1R 50.5%')]
x0, y0, wd, hh = 0.515, 0.92, 0.34, 0.025
for k_, (a, b, c) in enumerate(rows):
    yy = y0 - k_ * hh; hdr = k_ == 0
    fig.patches.append(Rectangle((x0, yy - hh), wd, hh, transform=fig.transFigure, fc='#f9a825' if hdr else '#f4f6f9', ec='#f9a825' if hdr else '#dde1e8', lw=0.6))
    fig.text(x0 + 0.005, yy - hh / 2, a, fontsize=7.2, color='#131722' if hdr else ('#f9a825' if a == 'PASSED' else '#5d6476'), va='center', family='monospace')
    vc = '#131722' if hdr else (GOLD if (k_ in (1, 3) and f) or k_ in (8, 9, 10) else '#131722')
    fig.text(x0 + 0.075, yy - hh / 2, b, fontsize=7.2, color=vc, va='center', family='monospace')
    fig.text(x0 + wd - 0.005, yy - hh / 2, c, fontsize=7.2, color='#131722' if hdr else '#5d6476', va='center', ha='right', family='monospace')
fig.savefig('/home/claude/sz/Suzumebachi_5m.png', facecolor='white')
print(E[['rel', 'dir', 'mss', 'cell', 'raid', 'fvg', 'rA']].assign(p=[passed(e) for e in E.itertuples()]).to_string())
