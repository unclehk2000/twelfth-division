"""Getsuga v3 mock-ups: the chart (range, reference lines, day candles, fixed markers where levels traded) with the week ladder
card and the NY · 15M card, light theme, computed the way the Pine script does. python3 mock_gt3.py OUTDIR 'YYYY-MM-DD HH:MM'"""
import sys
OUT = sys.argv[1]; T = sys.argv[2] if len(sys.argv) > 2 else '2026-09-16 10:15'
src = open('/home/claude/gt/mock_gt2.py').read().split("NOW = pd.Timestamp(")[0]
sys.argv = ['mock_gt2.py', OUT, T]; exec(src)                       # state(), chart(), colours from the v2 mock
import cards as C                                                   # card state and tables (light theme)
import numpy as np, pandas as pd, matplotlib.pyplot as plt

NOW = pd.Timestamp(T)
s2 = state(NOW); s = C.state(NOW)


def markers(ax, s2, start):
    x = Q[(Q.index >= start) & (Q.index < NOW)]
    ix = lambda t: float(np.searchsorted(x.index, t.floor('15min')))
    cols = {1.0: FIB, 0.5: FIB, 0.0: FIB, 1.5: SDC, -0.5: SDC}
    nm = {1.0: '1 FRI', 0.5: '0.5 EQ', 0.0: '0 MON', 1.5: '1.5 SD', -0.5: '−0.5 SD'}
    ev = [(f'✓ {nm[f]}', y, t, cols[f]) for f, (y, t) in s2['lv'].items() if t is not None]
    ev += [('✓ PWH', s2['PWH'], s2['tPH'], PWC), ('✓ PWL', s2['PWL'], s2['tPL'], PWC)]
    for tx, y, t, c in ev:
        if t is None or t < start:
            continue
        xx = ix(t); o = x.Open.iloc[int(min(xx, len(x) - 1))]
        up = y >= o
        ax.annotate(tx, (xx, y), xytext=(0, 9 if up else -9), textcoords='offset points', ha='center', va='bottom' if up else 'top', fontsize=6.3, color=CHT,
                    bbox=dict(boxstyle='round,pad=0.25', fc=c, alpha=0.22, ec='none'), arrowprops=dict(arrowstyle='-', color=c, lw=0.8), zorder=9)


fig = plt.figure(figsize=(18, 10.4), dpi=100, facecolor=BG)
start = s2['fT0'] - pd.Timedelta(hours=8)
ax = chart(fig, [0.02, 0.05, 0.6, 0.85], s2, NOW, start)
markers(ax, s2, start)
cax = fig.add_axes([0.655, 0.0, 0.345, 1.0]); cax.set_xlim(0, 1); cax.set_ylim(0, 1); cax.axis('off')
fp = s['fpos']; abv = s['px'] > max(s['F'], s['M'])
pos = 'INSIDE' if 0 <= fp <= 1 else ('▲ ' if abv else '▼ ') + 'PAST ' + ('1.5' if fp > 1.5 else '−0.5' if fp < -0.5 else '1' if fp > 1 else '0')
r1, w1, t1 = C.week_B2(s)
C.draw_table(cax, 0.02, 0.89, r1, w1, t1, (pos, C.LT['head'] if pos == 'INSIDE' else C.LT['up'] if abv else C.LT['dn']), fs=8.0, lh=0.031, cw=0.0145)
r2, w2, t2 = C.ny_A2(s)
st = 'AM' if 0 <= s['mins'] < 90 else 'PM' if 90 <= s['mins'] < 450 else 'PRE'
C.draw_table(cax, 0.02, 0.89 - 0.031 * (len(r1) + 1) - 0.05, r2, w2, ['GETSUGA', 'NY · 15M', f"{NOW:%H:%M} ET", ''], (st, C.LT['head']), fs=8.0, lh=0.031, cw=0.0145)
fig.text(0.02, 0.955, f"Getsuga Tenshō · NQ1! 15-minute, {NOW:%a %-d %b %Y %H:%M} ET · week ladder + NY · 15M card", color=CHT, fontsize=13, weight='bold')
fig.text(0.02, 0.928, f"{s2['prev'].tday.max():%a %-d %b} Shikai mid (1) → {s2['cur'].tday.min():%a %-d %b} (0) in eighths, SDs at 1.5 / −0.5, fixed ✓ markers where levels first traded, day candles in the Session Map's style. Mock-up from NQ data; TradingView will differ.", color='#5d6476', fontsize=9)
plt.savefig(f'{OUT}/Getsuga_Desktop_15m.png', dpi=100, facecolor=BG); plt.close(fig)

# mobile: narrow cards over a short chart
fig = plt.figure(figsize=(7, 10.4), dpi=100, facecolor=BG)
chart(fig, [0.04, 0.05, 0.8, 0.62], s2, NOW, s2['set_t'] - pd.Timedelta(hours=4), lbl=False)
cax = fig.add_axes([0, 0.68, 1, 0.32]); cax.set_xlim(0, 1); cax.set_ylim(0, 1); cax.axis('off')
items = [(C.NAMES[f], y, t) for f, (y, t) in s['key'].items()]
ab = min([z for z in items if z[1] > s['px']], key=lambda z: z[1], default=None); be = max([z for z in items if z[1] < s['px']], key=lambda z: z[1], default=None)
rr = abs(s['R']) / s['awr']
rows = [[('RANGE', C.LT['sub']), (C.gauge(rr, 5), C.LT['head']), (f"{C.fmt(abs(s['R']))} · {rr:.2f}×", None, None, 'right')]]
for tag, z in (('▲ ', ab), (None, None), ('▼ ', be)):
    if tag is None:
        rows.append([('▸ PRICE', C.LT['head'], C.LT['hl']), ('', None, C.LT['hl']), (f"{s['fpos']:.2f}", C.LT['txt'], C.LT['hl'], 'right')])
    elif z:
        rows.append([(tag + z[0], C.LT['sub']), '', (f"✓ {z[2]:%a %H:%M}", '#ffffff', C.LT['ok'], 'right') if z[2] is not None else (f"{round(C.wk_odds(s, z[1], z[2]))}%", None, None, 'right')])
x_end = C.draw_table(cax, 0.02, 0.97, rows, [0] * 3, ['GETSUGA', 'WEEK'], (pos, C.LT['head']), fs=8.2, lh=0.11, cw=0.0125)
L = C.ny_levels(s); rows = []
for nm, f, y, d, am, dy, trd, above in L:
    if (above and f == min([z for z in L if z[7]], key=lambda z: z[2])[1]) or (not above and f == max([z for z in L if not z[7]], key=lambda z: z[2])[1]):
        rows.append([(('▲ ' if above else '▼ ') + nm, C.LT['sub']), C.fmt(y), ('✓ today', '#ffffff', C.LT['ok'], 'right') if trd else (f"{round(am) if am is not None else '—'}% · {round(dy)}%", None, None, 'right')])
KEYF = (1.5, 1.0, 0.5, 0.0, -0.5)
ku = [z for z in L if z[7] and z[1] in KEYF]; kd = [z for z in L if not z[7] and z[1] in KEYF]
if ku and kd:
    pu = 100 * (s['px'] - kd[0][2]) / (ku[-1][2] - kd[0][2]); rows.append([('FIRST', C.LT['sub']), (f'▲ {round(pu)}%', C.LT['up']), (f'▼ {round(100 - pu)}%', C.LT['dn'], None, 'right')])
C.draw_table(cax, x_end + 0.03, 0.97, rows, [0] * 3, ['GETSUGA', 'NY · 15M'], (st, C.LT['head']), fs=8.2, lh=0.11, cw=0.0125)
plt.savefig(f'{OUT}/Getsuga_Mobile.png', dpi=100, facecolor=BG); plt.close(fig)
print('done', s['px'], s['mins'])
