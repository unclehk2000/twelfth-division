"""Getsuga v4 mock-ups (Tenshō + Jūjishō, cards reading Jūjishō): NQ 15-minute chart from real 1-minute data, computed the
way the Pine script does. Light theme. python3 mock_gt4.py OUTDIR 'YYYY-MM-DD HH:MM'"""
import sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plt.rcParams['font.family'] = 'DejaVu Sans'
OUT = sys.argv[1]; NOW = pd.Timestamp(sys.argv[2] if len(sys.argv) > 2 else '2026-10-21 10:15')
BG, CHT, SUB, GRID = '#ffffff', '#131722', '#5d6476', '#eef1f6'
UP, DN = '#089981', '#f23645'
TEN, TEN8, TSD = '#2962ff', '#2962ff80', '#9c27b0'
JJ, JJQ, JSD, JGAP = '#e53935', '#e53935b3', '#ff6d00', '#e539354d'
PWC, WOC, CC = '#787b86', '#c9a227', '#131722'
LT = dict(body='#f4f6f9', txt='#131722', sub='#5d6476', head='#1e88e5', ok='#26a69a', up='#26a69a', dn='#ef5350', form='#f9a825', hl='#dbe7fb')
fmt = lambda v: f'{v:,.2f}'
cl = lambda v, a, b: max(a, min(b, v))
sig = lambda z: 100 / (1 + np.exp(-z))
gauge = lambda f, n: '█' * int(round(cl(0 if f != f else f, 0, 1) * n)) + '░' * (n - int(round(cl(0 if f != f else f, 0, 1) * n)))
# the Pine constants
FX = [-0.326, 0.0, 1.0, 2.0, 3.0]; FI = [4.231, 4.051, 3.615, 3.055, 2.370]; FA, FB = 1.824, -7.685
PWI = [3.657, 3.453, 3.135, 2.587, 1.955]; PA, PB = 0.255, -5.922
DXc = [0, 30, 60, 90, 150, 210, 270, 330, 390]; DIc = [4.292, 4.145, 3.971, 3.827, 3.527, 3.101, 2.815, 2.378, 0.714]; DA, DB = 0.1201, -2.3432
AXc = [0, 30, 60]; AIc = [4.313, 3.746, 2.925]; AA, AB = 0.1823, -2.9349
def pReach(I, a, b, x, d):
    xx = cl(x, -0.326, 4.0); dd = d
    if xx >= 3:
        it = I[4]; dd = d / np.sqrt(max(4 - xx, 0.01))
    else:
        i = 0 if xx < 0 else int(np.floor(xx)) + 1; f = (xx - FX[i]) / (FX[i + 1] - FX[i]); it = I[i] * (1 - f) + I[i + 1] * f
    dc = cl(dd, 0, 3); return sig(it + a * dc + b * np.sqrt(dc))
def pToday(X, I, a, b, m, d, end):
    n = len(X); mm = max(m, 0); dd = d
    if mm >= end: return None
    if mm >= X[-1]:
        it = I[-1]; dd = d / np.sqrt(max((end - mm) / (end - X[-1]), 0.01))
    else:
        i = 0
        while i < n - 2 and mm >= X[i + 1]: i += 1
        f = (mm - X[i]) / (X[i + 1] - X[i]); it = I[i] * (1 - f) + I[i + 1] * f
    dc = cl(dd, 0, 30); return sig(it + a * dc + b * np.sqrt(dc))

# ---------------- data
B = pd.read_pickle('/home/claude/kyw/bars_NQ_all.pkl').query("ts >= '2026-08-15' and ts < '2026-10-24'").set_index('ts')
b = B[B.index < NOW]
wid = (B.index + pd.Timedelta(hours=6)).normalize(); wid = wid - pd.to_timedelta(wid.dayofweek, unit='D'); B['wid'] = wid
wk = B.loc[b.index[-1], 'wid']; cur = B[(B.wid == wk) & (B.index < NOW)]; prev = B[B.wid == wk - pd.Timedelta(days=7)]
wks = sorted(w for w in B.wid.unique() if w < wk)[-4:]
awr = np.mean([B[B.wid == w].High.max() - B[B.wid == w].Low.min() for w in wks])
def fpfvg(day):
    x = B[(B.index.normalize() == day) & (B.hm >= 930) & (B.hm <= 959)]
    h, l, t = x.High.values, x.Low.values, x.index
    for j in range(len(x) - 2):
        if l[j + 2] > h[j]: return 1, h[j], l[j + 2], t[j], t[j + 2], x.Close.values[j + 2]
        if h[j + 2] < l[j]: return -1, h[j + 2], l[j], t[j], t[j + 2], x.Close.values[j + 2]
def shikai(td):
    o = B[(B.tday == td) & ((B.hm >= 1800) | (B.hm < 930))]
    return (o.High.max() + o.Low.min()) / 2, min(o.High.idxmax(), o.Low.idxmin())
fday = prev.index.normalize().max(); mday = cur[cur.hm == 930].index.normalize().min()
Fd, Fb, Ft, FT1, FT3, _ = fpfvg(fday); Md, Mb, Mt, MT1, MT3, P0 = fpfvg(mday)
jF, jM = (Ft + Fb) / 2, (Mt + Mb) / 2; jR = jF - jM; jSet = MT3 + pd.Timedelta(minutes=1)
tF, tF0 = shikai(prev.tday.max()); tM, _ = shikai(cur.tday.min()); tR = tF - tM; tSet = cur[(cur.tday == cur.tday.min()) & (cur.hm == 930)].index[0]
jl = lambda f: jM + f * jR; tl = lambda f: tM + f * tR
after = cur[cur.index >= jSet]
def hit(y):
    m = (after.Low.values <= y) & (after.High.values >= y)
    return after.index[m][0] if m.any() else None
KEY = (1.5, 1.0, 0.5, 0.0, -0.5)
jt = {f: hit(jl(f)) for f in KEY}
PWH, PWL, wO = prev.High.max(), prev.Low.min(), cur.Open.iloc[0]
tPH = (lambda m: cur.index[m][0] if m.any() else None)(cur.High.values > PWH)
tPL = (lambda m: cur.index[m][0] if m.any() else None)(cur.Low.values < PWL)
px = b.Close.iloc[-1]; td_now = cur.tday.iloc[-1]
x_now = td_now.dayofweek - 1 + cl((NOW - (td_now - pd.Timedelta(hours=6))).total_seconds() / (23 * 3600), 0, 1)
Q = B.resample('15min').agg(dict(Open='first', High='max', Low='min', Close='last', tday='first', hm='first')).dropna()
trr = np.maximum(Q.High - Q.Low, np.maximum((Q.High - Q.Close.shift()).abs(), (Q.Low - Q.Close.shift()).abs()))
atr = trr.ewm(alpha=1 / 14, adjust=False).mean()
today = cur[cur.tday == td_now]; rth = today[(today.hm >= 930) & (today.hm < 1700)]
t930 = rth.index[0]; a15 = atr[atr.index < t930].iloc[-1]; mins = (NOW - t930).total_seconds() / 60
rH, rL, o930 = rth.High.max(), rth.Low.min(), rth.Open.iloc[0]
rr = abs(jR) / awr; coil = rr <= 0.20; down = jF > P0
print(f"Jūjishō F {jF} ({Fb}-{Ft}) M {jM} ({Mb}-{Mt}) R {jR:.2f} AWR4 {awr:.2f} r {rr:.3f} coil {coil} down {down} set {jSet}")
print(f"Tenshō F {tF} M {tM}; px {px} x {x_now:.3f} ATR15 {a15:.2f} mins {mins}")
print('hits', {f: (round(jl(f), 2), str(t)) for f, t in jt.items()})

# ---------------- chart
Qc = Q[(Q.index >= tF0.floor('15min') - pd.Timedelta(hours=2)) & (Q.index < NOW.floor('15min'))]
N = len(Qc); ix = lambda t: float(np.searchsorted(Qc.index, pd.Timestamp(t).floor('15min')))
def chart(fig, rect, x_from=None, labels=True, mob=False):
    ax = fig.add_axes(rect); ax.set_facecolor(BG)
    x0 = 0 if x_from is None else ix(x_from)
    for i, (t, r) in enumerate(Qc.iterrows()):
        if i < x0: continue
        c = UP if r.Close >= r.Open else DN
        ax.plot([i, i], [r.Low, r.High], color=c, lw=0.7, zorder=3)
        ax.add_patch(Rectangle((i - 0.33, min(r.Open, r.Close)), 0.66, max(abs(r.Close - r.Open), 0.5), color=c, zorder=4))
    # day candles right of price (Mon … Wed and the week)
    dcOff, dcW, dcSp = 15, 4, 6
    x = N - 1 + dcOff; days = sorted(cur.tday.unique())
    def dcand(o, h, l, c, th, tl_, xa, nm):
        bt, bb = max(o, c), min(o, c); xm = xa + dcW / 2
        ax.add_patch(Rectangle((xa, bb), dcW, max(bt - bb, 0.5), facecolor=CC + '26', edgecolor=CC, lw=0.8, zorder=5))
        ax.plot([xm, xm], [bt, h], color=CC, lw=0.8, zorder=5); ax.plot([xm, xm], [l, bb], color=CC, lw=0.8, zorder=5)
        ax.text(xm, h + 6, f'{nm}\n{fmt(h)}', fontsize=5.6, ha='center', va='bottom', color=CC, zorder=6, bbox=dict(boxstyle='round,pad=0.15', fc='#e9ebef', ec='none'))
        ax.text(xm, l - 6, fmt(l), fontsize=5.6, ha='center', va='top', color=CC, zorder=6)
        dnl = th < tl_
        for q, cc in ((0.25, '#1e88e5'), (0.375, '#5c6bc0'), (0.5, '#ab47bc')):
            y = l + q * (h - l) if dnl else h - q * (h - l)
            ax.plot([xa + dcW, xa + dcW + dcSp * 0.6], [y, y], color=cc, lw=0.7, zorder=5)
    for d in days:
        dd = cur[cur.tday == d]
        dcand(dd.Open.iloc[0], dd.High.max(), dd.Low.min(), dd.Close.iloc[-1], dd.High.idxmax(), dd.Low.idxmin(), x, f'{d:%a}'); x += dcW + dcSp
    dcand(cur.Open.iloc[0], cur.High.max(), cur.Low.min(), cur.Close.iloc[-1], cur.High.idxmax(), cur.Low.idxmin(), x, 'Week'); x += dcW + dcSp
    xr = x + 6
    # Tenshō grid (blue, with eighths) and its reference lines
    for k in range(-8, 17):
        f = k / 8; y = tl(f)
        if k in (0, 8): st = dict(color=TEN, lw=2); nm = ' · Fri mid' if k == 8 else ' · Mon mid'
        elif k == 4: st = dict(color=TEN, lw=1, ls='--'); nm = ''
        elif k in (2, 6): st = dict(color=TEN, lw=1); nm = ''
        elif 0 < k < 8: st = dict(color=TEN8, lw=1, ls=':'); nm = ''
        elif k in (12, -4): st = dict(color=TSD, lw=2); nm = ' · SD'
        else: continue
        ax.plot([max(ix(tF0), x0), xr], [y, y], zorder=2, **st)
        if labels: ax.text(xr + 0.5, y, f'{f:g} ({fmt(y)}){nm}', fontsize=6.0, va='center', color=st['color'][:7], alpha=0.85)
    ws = ix(cur.index[0])
    for y, nm, c in ((PWH, 'PWH', PWC), (PWL, 'PWL', PWC), (wO, 'Week open', WOC)):
        ax.plot([max(ws, x0), xr], [y, y], color=c, lw=0.9, ls=':', zorder=1)
        ax.text(max(ws, x0) + 0.5, y + (8 if nm != 'PWL' else -8), f'{nm} ({fmt(y)})', fontsize=6.0, color=c, va='bottom' if nm != 'PWL' else 'top')
    # Jūjishō grid (red, no eighths) and the two gaps
    for k in range(-8, 17):
        f = k / 8; y = jl(f)
        if k in (0, 8): st = dict(color=JJ, lw=2); nm = ' · Fri FVG' if k == 8 else ' · Mon FVG'
        elif k == 4: st = dict(color=JJ, lw=1, ls='--'); nm = ''
        elif k in (2, 6): st = dict(color=JJQ, lw=1); nm = ''
        elif k in (12, -4): st = dict(color=JSD, lw=2); nm = ' · SD'
        else: continue
        ax.plot([max(ix(FT1), x0), xr], [y, y], zorder=2.5, **st)
        if labels: ax.text(xr + 0.5, y, f'{f:g} ({fmt(y)}){nm}', fontsize=6.0, va='center', color=st['color'][:7], weight='bold' if k in (0, 8) else 'normal')
    for t1, lo, hi in ((FT1, Fb, Ft), (MT1, Mb, Mt)):
        if ix(t1) >= x0:
            ax.add_patch(Rectangle((ix(t1) - 0.4, lo), 4, max(hi - lo, 1.5), facecolor=JGAP, edgecolor=JJ, lw=0.6, zorder=6))
    # ✓ markers (the range the cards read: Jūjishō) and PW
    nmk = {1.5: '✓ 1.5 SD', 1.0: '✓ 1 FRI FVG', 0.5: '✓ 0.5 EQ', 0.0: '✓ 0 MON FVG', -0.5: '✓ −0.5 SD'}
    for f, t in jt.items():
        if t is None or ix(t) < x0: continue
        y = jl(f); o = Qc.Open.iloc[int(min(ix(t), N - 1))]; upm = y >= o
        ax.annotate(nmk[f], (ix(t), y), xytext=(0, 10 if upm else -10), textcoords='offset points', ha='center', va='bottom' if upm else 'top', fontsize=6.0, color=CHT,
                    bbox=dict(boxstyle='round,pad=0.22', fc=JSD if abs(f) == 0.5 or f == 1.5 else JJ, alpha=0.2, ec='none'), arrowprops=dict(arrowstyle='-', color=JJ, lw=0.7), zorder=9)
    days_ix = [ix(t) for t in Qc.index if t.hour == 0 and t.minute == 0 and ix(t) >= x0]
    ax.set_xticks(days_ix); ax.set_xticklabels([f'{Qc.index[int(i)] + pd.Timedelta(hours=6):%a %-d}' for i in days_ix], fontsize=7, color='#9aa1b2')
    lo = min(Qc.Low[Qc.index >= Qc.index[int(x0)]].min(), jl(-0.5), PWL) - 60; hi = max(Qc.High[Qc.index >= Qc.index[int(x0)]].max(), tl(1.5) if not mob else jl(1.5)) + 80
    ax.set_xlim(x0 - 2, xr + (34 if labels else 4)); ax.set_ylim(lo, hi)
    ax.yaxis.tick_right(); ax.tick_params(axis='y', labelsize=7, colors='#9aa1b2', length=0); ax.tick_params(axis='x', length=0)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f'{v:,.0f}'))
    ax.grid(color=GRID, lw=0.6); [s_.set_visible(False) for s_ in ax.spines.values()]
    return ax

# ---------------- cards
def draw_table(ax, x0, y0, rows, title, pill, lh=0.031, fs=7.6, cw=0.0108):
    txt = lambda c: (c[0] if isinstance(c, tuple) else c) or ''
    ncol = len(title)
    widths = [max([len(txt(r[i])) for r in rows if i < len(r)] + [len(title[i]), len(pill[0]) if i == ncol - 1 else 0]) * cw + 0.012 for i in range(ncol)]
    W = sum(widths); xs = np.cumsum([0] + widths[:-1]) + x0
    ax.add_patch(Rectangle((x0, y0 - lh), W, lh, fc=LT['head'], ec='none'))
    for i, tx in enumerate(title[:-1]):
        ax.text(xs[i] + 0.005, y0 - lh / 2, tx, color='#ffffff', fontsize=fs, family='DejaVu Sans Mono', va='center', weight='bold' if i == 0 else 'normal')
    ax.add_patch(Rectangle((xs[-1], y0 - lh), widths[-1], lh, fc='#ffffff', ec='none'))
    ax.text(xs[-1] + widths[-1] / 2, y0 - lh / 2, pill[0], color=pill[1], fontsize=fs, family='DejaVu Sans Mono', va='center', ha='center')
    for r, row in enumerate(rows):
        yy = y0 - lh * (r + 2)
        for i, cell in enumerate(row):
            c5 = list(cell) if isinstance(cell, tuple) else [cell]
            tx, fg, bg, al = (c5 + ['', None, None, 'left'][len(c5):])[:4]
            ax.add_patch(Rectangle((xs[i], yy), widths[i], lh, fc=bg or LT['body'], ec='none'))
            ax.text(xs[i] + (widths[i] - 0.005 if al == 'right' else 0.005), yy + lh / 2, tx, color=fg or LT['txt'], fontsize=fs, family='DejaVu Sans Mono', va='center', ha=al)
    ax.add_patch(Rectangle((x0, y0 - lh * (len(rows) + 1)), W, lh * (len(rows) + 1), fc='none', ec=LT['head'], lw=1.2))
    return x0 + W
dA = lambda y: abs(y - px) / awr
NAMES = {1.5: '1.5 SD', 1.0: '1 FRI', 0.5: '0.5 EQ', 0.0: '0 MON', -0.5: '-0.5 SD'}
fpos = (px - jM) / jR
posTx = 'inside' if 0 <= fpos <= 1 else ('past ' + ('1.5' if fpos > 1.5 else '−0.5' if fpos < -0.5 else '1' if fpos > 1 else '0'))
pill = ('INSIDE', LT['head']) if posTx == 'inside' else (('▲ ' if px > max(jF, jM) else '▼ ') + posTx.upper(), LT['up'] if px > max(jF, jM) else LT['dn'])
wt = lambda t: f'{t:%a %H:%M}'
items = [(NAMES[f], jl(f), jt[f], None if jt[f] is not None else pReach(FI, FA, FB, x_now, dA(jl(f))), False) for f in KEY]
items += [('PWH', PWH, tPH, None if tPH is not None else pReach(PWI, PA, PB, x_now, max(PWH - px, 0) / awr), True),
          ('PWL', PWL, tPL, None if tPL is not None else pReach(PWI, PA, PB, x_now, max(px - PWL, 0) / awr), True)]
items.sort(key=lambda z: -z[1])
rows = [[('RANGE', LT['sub']), (gauge(rr, 8), JJ), f'{fmt(jF)} → {fmt(jM)}', (f'{fmt(abs(jR))} · {rr:.2f}× AWR4', None, None, 'right')],
        [('STATE', LT['sub']), ('COILED' if coil else 'UNCOILED', LT['form'] if coil else LT['head']), '≤ 0.20× · both SDs 76%' if coil else '> 0.20× · both SDs 26%', ('past an SD 90%' if coil else 'past an SD 63%', None, None, 'right')],
        [('SHIFT', LT['sub']), ('▼ MON < FRI' if down else '▲ MON > FRI', LT['dn'] if down else LT['up']), 'week up 62% · +78 bp' if down else 'week up 56% · −3 bp', ('all 58% · +33 bp', None, None, 'right')],
        [('GAPS', LT['sub']), '', f"FRI {'▲' if Fd > 0 else '▼'} {fmt(Ft - Fb)} · MON {'▲' if Md > 0 else '▼'} {fmt(Mt - Mb)} pts", (f'set {wt(jSet)}', None, None, 'right')]]
placed = False
for nm, y, t, p, pw in items:
    if not placed and y < px:
        rows.append([('▸ PRICE', LT['head'], LT['hl']), ('', None, LT['hl']), (f'{fmt(px)} · at {fpos:.2f}', LT['txt'], LT['hl']), (posTx, LT['txt'], LT['hl'], 'right')]); placed = True
    d = dA(y)
    rows.append([(nm, '#5d647699' if pw else LT['sub']), ('' if t is not None else gauge(1 - d / 0.5, 8), LT['up'] if y > px else LT['dn']),
                 fmt(y) + ('' if t is not None else f' · {d:.2f}×'), (f'✓ {wt(t)}', '#ffffff', LT['ok'], 'right') if t is not None else (f'{round(p)}% by Fri', None, None, 'right')])
if not placed:
    rows.append([('▸ PRICE', LT['head'], LT['hl']), ('', None, LT['hl']), (f'{fmt(px)} · at {fpos:.2f}', LT['txt'], LT['hl']), (posTx, LT['txt'], LT['hl'], 'right')])
wH, wL = cur.High.max(), cur.Low.min()
rows.append([('WEEK', LT['sub']), (gauge((wH - wL) / awr, 8), LT['head']), f'{fmt(wH - wL)} pts so far', (f'{(wH - wL) / awr:.2f}× AWR4', None, None, 'right')])
week_rows = rows
# NY · 15M
grid = [(k / 8, jl(k / 8), k in (-4, 0, 4, 8, 12)) for k in range(-8, 17)]
upl = [g for g in grid if g[1] > px]; dnl = [g for g in grid if g[1] < px]
u8 = min(upl, key=lambda g: g[1]); d8 = max(dnl, key=lambda g: g[1])
uK = min([g for g in upl if g[2]], key=lambda g: g[1]); dK = max([g for g in dnl if g[2]], key=lambda g: g[1])
nmf = lambda f: NAMES.get(f, f'{f:g}')
def nyrow(g, upr):
    y = g[1]; trd = rL <= y <= rH; d = abs(y - px) / a15
    pa = None if trd else pToday(AXc, AIc, AA, AB, mins, d, 90); pd_ = None if trd else pToday(DXc, DIc, DA, DB, mins, d, 450)
    return [(('▲ ' if upr else '▼ ') + nmf(g[0]), LT['sub']), fmt(y), (f'{d:.1f}', None, None, 'right'),
            ('✓ today', '#ffffff', LT['ok'], 'right') if trd else (f'{round(pa)}%', None, None, 'right'), ('', None, LT['ok']) if trd else (f'{round(pd_)}%', None, None, 'right')]
ny = [[('', None), ('PRICE', LT['sub']), ('×ATR15', LT['sub'], None, 'right'), ('11:00', LT['sub'], None, 'right'), ('16:59', LT['sub'], None, 'right')]]
if uK != u8: ny.append(nyrow(uK, True))
ny.append(nyrow(u8, True))
ny.append([('▸ NOW', LT['head'], LT['hl']), (fmt(px), LT['txt'], LT['hl']), ('', None, LT['hl']), ('', None, LT['hl']), ('', None, LT['hl'])])
ny.append(nyrow(d8, False))
if dK != d8: ny.append(nyrow(dK, False))
pu = 100 * (px - dK[1]) / (uK[1] - dK[1])
ny.append([('FIRST', LT['sub']), ('▲ ' + nmf(uK[0]), LT['up']), (f'{round(pu)}%', LT['up'], None, 'right'), ('▼ ' + nmf(dK[0]), LT['dn'], None, 'right'), (f'{round(100 - pu)}%', LT['dn'], None, 'right')])
ny.append([('OPEN', LT['sub']), fmt(o930), (f'at {(o930 - jM) / jR:.2f}', None, None, 'right'), ('ATR15', LT['sub'], None, 'right'), (fmt(a15), None, None, 'right')])
st = 'AM' if 0 <= mins < 90 else 'PM' if mins < 450 else 'CLOSED'

# ---------------- desktop
fig = plt.figure(figsize=(18, 10.4), dpi=100, facecolor=BG)
chart(fig, [0.015, 0.05, 0.62, 0.85])
cax = fig.add_axes([0.655, 0.0, 0.345, 1.0]); cax.set_xlim(0, 1); cax.set_ylim(0, 1); cax.axis('off')
draw_table(cax, 0.02, 0.89, week_rows, ['GETSUGA', 'JŪJISHŌ', f'{NOW:%m/%d} · {NOW:%H:%M} ET', ''], pill)
draw_table(cax, 0.02, 0.89 - 0.031 * (len(week_rows) + 1) - 0.05, ny, ['GETSUGA', 'NY · 15M', f'{NOW:%H:%M} ET', '', ''], (st, LT['head']))
fig.text(0.015, 0.955, f"Getsuga · Tenshō (blue) + Jūjishō (red) · NQ1! 15-minute, {NOW:%a %-d %b %Y %H:%M} ET · cards reading Jūjishō", color=CHT, fontsize=13, weight='bold')
fig.text(0.015, 0.928, f"Jūjishō: the CE of Fri {fday:%-d %b}'s first presented FVG (1) → Mon {mday:%-d %b}'s (0), set {jSet:%H:%M}; the two gaps as small boxes. Tenshō: Shikai mids. Mock-up from NQ 1-minute data; TradingView will differ.", color=SUB, fontsize=9)
plt.savefig(f'{OUT}/Getsuga_Desktop_15m.png', dpi=100, facecolor=BG); plt.close(fig)

# ---------------- mobile: Jūjishō only on the chart for space; narrow cards
fig = plt.figure(figsize=(7, 10.4), dpi=100, facecolor=BG)
chart(fig, [0.04, 0.04, 0.84, 0.70], x_from=jSet - pd.Timedelta(hours=10), labels=False, mob=True)
cax = fig.add_axes([0, 0.765, 1, 0.235]); cax.set_xlim(0, 1); cax.set_ylim(0, 1); cax.axis('off')
keyit = [(NAMES[f], jl(f), jt[f]) for f in KEY]
ab = min([z for z in keyit if z[1] > px], key=lambda z: z[1], default=None); be = max([z for z in keyit if z[1] < px], key=lambda z: z[1], default=None)
mrows = [[('RANGE', LT['sub']), (gauge(rr, 5), JJ), (f'{fmt(abs(jR))} · {rr:.2f}×', None, None, 'right')],
         [('COILED' if coil else 'UNCOILED', LT['form'] if coil else LT['head']), '', ('past SD 90%' if coil else 'past SD 63%', None, None, 'right')],
         [('▼ SHIFT' if down else '▲ SHIFT', LT['dn'] if down else LT['up']), '', ('up 62%' if down else 'up 56%', None, None, 'right')]]
for tag, z in (('▲ ', ab), (None, None), ('▼ ', be)):
    if tag is None:
        mrows.append([('▸ PRICE', LT['head'], LT['hl']), ('', None, LT['hl']), (f'{fpos:.2f}', LT['txt'], LT['hl'], 'right')])
    elif z:
        mrows.append([(tag + z[0], LT['sub']), '', (f'✓ {wt(z[2])}', '#ffffff', LT['ok'], 'right') if z[2] is not None else (f'{round(pReach(FI, FA, FB, x_now, dA(z[1])))}%', None, None, 'right')])
xe = draw_table(cax, 0.02, 0.97, mrows, ['GETSUGA', 'JŪJISHŌ', ''], (pill[0], pill[1]), lh=0.122, fs=7.4, cw=0.0094)
nym = []
for g, upr in ((u8, True), (d8, False)):
    rw = nyrow(g, upr); nym.append([rw[0], rw[1], ('✓ today', '#ffffff', LT['ok'], 'right') if rw[3][0] == '✓ today' else (f"{rw[3][0]} · {rw[4][0]}", None, None, 'right')])
nym.append([('FIRST', LT['sub']), (f'▲ {round(pu)}%', LT['up']), (f'▼ {round(100 - pu)}%', LT['dn'], None, 'right')])
draw_table(cax, xe + 0.03, 0.97, nym, ['GETSUGA', 'NY · 15M', ''], (st, LT['head']), lh=0.122, fs=7.4, cw=0.0094)
plt.savefig(f'{OUT}/Getsuga_Mobile.png', dpi=100, facecolor=BG); plt.close(fig)
print('done')
