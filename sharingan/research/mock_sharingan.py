"""Sharingan mock: a Python port of the Pine daily engine (anchor, structure shift, look back, taken, cast forward with CME holidays,
tested odds) drawn the way the indicator draws it on a daily NQ1! chart, plus the card. Usage: python3 mock_sharingan.py OUT.png [desktop|mobile] [light|dark] [month|shift]"""
import sys, math, numpy as np, pandas as pd
from datetime import date, timedelta
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from scipy.special import ndtr, expit, logit
sys.path.insert(0, '/home/claude/tpf')
from data import daily
OUT = sys.argv[1]; LAY = sys.argv[2] if len(sys.argv) > 2 else 'desktop'; THEME = sys.argv[3] if len(sys.argv) > 3 else 'light'; MODE = sys.argv[4] if len(sys.argv) > 4 else 'month'
SWK = 3
# ── daily NQ: the task-2 table to 9 Oct, then days built from the 1-minute bars to 23 Oct
F = daily('NQ')[['ao', 'ah', 'al', 'ac']].rename(columns={'ao': 'o', 'ah': 'h', 'al': 'l', 'ac': 'c'})
b = pd.read_pickle('/home/claude/kyw/bars_NQ_all.pkl'); g = b.groupby('tday').agg(o=('Open', 'first'), h=('High', 'max'), l=('Low', 'min'), c=('Close', 'last'))
D = pd.concat([F, g[g.index > F.index.max()]]); D = D[D.index >= '2024-01-01']
dts = list(D.index.date); o, h, l, c = (D[k].to_numpy() for k in 'ohlc'); n = len(D)
# ── CME holidays (as the Pine)
def nth_dow(y, m, wd, k):
    d0 = date(y, m, 1); off = (wd - d0.weekday()) % 7; return 1 + off + 7 * (k - 1)
def last_dow(y, m, wd):
    d = date(y, m + 1, 1) - timedelta(days=1) if m < 12 else date(y, 12, 31)
    while d.weekday() != wd: d -= timedelta(days=1)
    return d.day
def easter(y):
    a = y % 19; bb = y // 100; cc = y % 100; d = bb // 4; e = bb % 4; f = (bb + 8) // 25; gg = (bb - f + 1) // 3; hh = (19 * a + bb - d - gg + 15) % 30
    i = cc // 4; k = cc % 4; lw = (32 + 2 * e + 2 * i - hh - k) % 7; mm = (a + 11 * hh + 22 * lw) // 451; mo = (hh + lw - 7 * mm + 114) // 31; dd = (hh + lw - 7 * mm + 114) % 31 + 1
    return date(y, mo, dd)
def is_hol(d):
    y, m, dd, w = d.year, d.month, d.day, d.weekday()
    if w >= 5: return False
    gf = easter(y) - timedelta(days=2); gfo = y in (2010, 2012, 2015, 2023, 2026)
    return ((m == 1 and (dd == 1 or (dd == 2 and w == 0))) or (m == 1 and dd == nth_dow(y, 1, 0, 3)) or (m == 2 and dd == nth_dow(y, 2, 0, 3)) or (not gfo and d == gf)
            or (m == 5 and dd == last_dow(y, 5, 0)) or (y >= 2022 and m == 6 and (dd == 19 or (dd == 18 and w == 4) or (dd == 20 and w == 0)))
            or (m == 7 and (dd == 4 or (dd == 3 and w == 4) or (dd == 5 and w == 0))) or (m == 9 and dd == nth_dow(y, 9, 0, 1)) or (m == 11 and dd == nth_dow(y, 11, 3, 4))
            or (m == 12 and (dd == 25 or (dd == 24 and w == 4) or (dd == 26 and w == 0))))
def is_td(d): return d.weekday() < 5 and not is_hol(d)
def step_td(d, k):
    while k > 0:
        d += timedelta(days=1)
        if is_td(d): k -= 1
    return d
# ── the engine, bar by bar, exactly as the Pine (state after the previous completed day)
def engine(mode, upto):
    curMS = prvMS = None; trend = 0; shP = shI = slP = slI = sxI = None; sxD = 0; lastA = None; S = {}
    for bi in range(upto + 1):
        newM = bi == 0 or dts[bi].month != dts[bi - 1].month
        if newM: prvMS, curMS = curMS, bi
        if bi > 2 * SWK + 2:
            w = slice(bi - 1 - 2 * SWK, bi)
            if h[bi - 1 - SWK] == h[w].max(): shP, shI = h[bi - 1 - SWK], bi - 1 - SWK
            if l[bi - 1 - SWK] == l[w].min(): slP, slI = l[bi - 1 - SWK], bi - 1 - SWK
        if bi >= 1 and slP is not None and trend >= 0 and c[bi - 1] < slP:
            if trend == 1: seg = h[slI:bi]; sxI = slI + len(seg) - 1 - int(np.argmax(seg[::-1])); sxD = -1
            trend = -1
        elif bi >= 1 and shP is not None and trend <= 0 and c[bi - 1] > shP:
            if trend == -1: seg = l[shI:bi]; sxI = shI + len(seg) - 1 - int(np.argmin(seg[::-1])); sxD = 1
            trend = 1
        A = prvMS if mode == 0 else sxI
        if A is not None and A > 61 and A < bi:
            if A != lastA:
                lastA = A; S = dict(A=A)
                for N in (20, 40, 60):
                    w = slice(A - N, A); S[f'h{N}'] = h[w].max(); S[f'h{N}i'] = A - N + int(np.argmax(h[w][::-1][::-1])) if False else A - N + int(np.argmax(h[w]))
                    # Pine keeps the latest bar on ties when scanning backwards with '>' (first found = most recent); emulate: last occurrence
                    S[f'h{N}i'] = A - N + int(len(h[w]) - 1 - np.argmax(h[w][::-1])); S[f'l{N}'] = l[w].min(); S[f'l{N}i'] = A - N + int(len(l[w]) - 1 - np.argmin(l[w][::-1]))
                    S[f'n{N}'] = c[A - 1] / c[A - 1 - N] - 1
                    S[f'tH{N}'] = next((t for t in range(A, bi) if h[t] >= S[f'h{N}']), None); S[f'tL{N}'] = next((t for t in range(A, bi) if l[t] <= S[f'l{N}']), None)
            else:
                for N in (20, 40, 60):
                    if S[f'tH{N}'] is None and h[bi - 1] >= S[f'h{N}']: S[f'tH{N}'] = bi - 1
                    if S[f'tL{N}'] is None and l[bi - 1] <= S[f'l{N}']: S[f'tL{N}'] = bi - 1
    S['off'] = upto - lastA; S['sxI'] = sxI; S['sxD'] = sxD
    return S
TODAY = n - 1
S = engine(0 if MODE == 'month' else 1, TODAY); SH = engine(1, TODAY)
A = S['A']; off = S['off']
def cf_date(M): return dts[A + M] if A + M <= TODAY else step_td(dts[TODAY], A + M - TODAY)
cf = {M: cf_date(M) for M in (20, 40, 60)}
tr = np.maximum(h, np.r_[c[0], c[:-1]]) - np.minimum(l, np.r_[c[0], c[:-1]]); atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()[TODAY - 1]; lastC = c[TODAY - 1]
def reach(d, hh, k, a, bb): q = np.clip(2 * ndtr(-(d / math.sqrt(hh)) / k), 1e-5, 1 - 1e-5); return expit(a + bb * logit(q))
pH20 = lambda d: reach(d, 20, 0.4906, 0.4378, 0.8583); pL20 = lambda d: reach(d, 20, 1.4948, -1.8160, 1.1503)
pHW = lambda d, hh: reach(d, hh, 0.6481, 0.2346, 1.2171); pLW = lambda d, hh: reach(d, hh, 1.8075, -1.9465, 1.0824)
left = 60 - off + 1
print('anchor', dts[A], 'off', off, 'cf', cf, 'atr', round(atr, 1), {k: (round(v, 2) if isinstance(v, float) else v) for k, v in S.items()})
# ── market structure and the Quarterly Theory true opens, as the Pine's structure() (state after the last completed day)
def structure(upto):
    trend = 0; shP = shT = slP = slT = None; m1 = m2 = None; tyO = tyT = tmO = tmT = None
    for bi in range(upto + 1):
        if bi > 2 * SWK + 2:
            w = slice(bi - 1 - 2 * SWK, bi); cc_ = bi - 1 - SWK
            if h[cc_] == h[w].max(): shP, shT = h[cc_], cc_
            if l[cc_] == l[w].min(): slP, slT = l[cc_], cc_
        if bi >= 1 and slP is not None and trend >= 0 and c[bi - 1] < slP:
            if trend == 1: m2 = m1; m1 = (slP, slT, bi - 1, -1)
            trend = -1
        elif bi >= 1 and shP is not None and trend <= 0 and c[bi - 1] > shP:
            if trend == -1: m2 = m1; m1 = (shP, shT, bi - 1, 1)
            trend = 1
        if bi > 1:
            d1 = dts[bi - 1]
            if d1.weekday() == 0:
                if d1.month == 4 and d1.day <= 7: tyO, tyT = o[bi - 1], bi - 1
                if 8 <= d1.day <= 14: tmO, tmT = o[bi - 1], bi - 1
    return dict(trend=trend, shP=shP, shT=shT, slP=slP, slT=slT, m1=m1, m2=m2, tyO=tyO, tyT=tyT, tmO=tmO, tmT=tmT)
ST = structure(TODAY)
flipP, flipT = (ST['shP'], ST['shT']) if ST['trend'] == -1 else (ST['slP'], ST['slT']) if ST['trend'] == 1 else (None, None)
print('structure', ST)
# ── calendar positions: trading-day index, extended into the future with stepped dates
fut = [dts[-1]]
for _ in range(70): fut.append(step_td(fut[-1], 1))
alld = dts + fut[1:]; pos = {d: i for i, d in enumerate(alld)}
x0 = max(0, A - 75) if LAY == 'desktop' else max(0, A - 45)
dark = THEME == 'dark'
bg = '#131722' if dark else '#ffffff'; fg = '#d1d4dc' if dark else '#131722'; grid = '#1f2433' if dark else '#f0f3fa'
cBg = '#0e1117' if dark else '#ffffff'; cHd = '#171c28' if dark else '#eef1f6'; cBd = '#262c3a' if dark else '#d5dae4'; cTx = '#e6e9ef' if dark else '#131722'; cSub = '#9aa3b5' if dark else '#4a5163'; cMu = '#5d6476' if dark else '#9aa1b2'
COL = dict(H60='#d32f2f', H40='#ef5350', H20='#f48484', L60='#00897b', L40='#26a69a', L20='#5cc4b8', A='#e53935', Q='#7e57c2', U='#26a69a', D='#ef5350', TO='#787b86')
mono = fm.FontProperties(fname='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'); sans = fm.FontProperties(fname='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
sansB = fm.FontProperties(fname='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'); monoB = fm.FontProperties(fname='/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf')
W, H = (19.2, 10.8) if LAY == 'desktop' else (10.8, 19.2)
fig = plt.figure(figsize=(W, H), dpi=100, facecolor=bg)
ax = fig.add_axes([0.03, 0.06, 0.86, 0.88] if LAY == 'desktop' else [0.02, 0.04, 0.80, 0.78]); ax.set_facecolor(bg)
for i in range(x0, n):
    col = ('#089981' if c[i] >= o[i] else '#f23645')
    ax.plot([i, i], [l[i], h[i]], color=col, lw=1, zorder=3); ax.add_patch(plt.Rectangle((i - 0.35, min(o[i], c[i])), 0.7, max(abs(c[i] - o[i]), 1e-6), color=col, zorder=3))
top = max(S['h60'], h[x0:].max()); bot = min(S['l60'], l[x0:].min()); u = atr
fs = 8 if LAY == 'desktop' else 9
def vline(x, colr, ls, lw, a=1.0): ax.axvline(x, color=colr, ls=ls, lw=lw, alpha=a, zorder=2)
vline(A, COL['A'], '-', 1); ax.text(A + 0.5, top + 1.6 * u, f"ANCHOR {dts[A]:%d %b %Y} · " + ('last closed month' if MODE == 'month' else f"the {'high' if ST['m1'] and ST['m1'][3] == -1 else 'low'} before the {dts[ST['m1'][2]]:%d %b} MSS"), color=COL['A'], fontsize=fs, fontproperties=sans, va='bottom')
for N, yy in ((60, 1.2), (40, 0.9), (20, 0.6)):
    ax.plot([A - N, A], [top + yy * u] * 2, color=cSub, lw=1, alpha=0.6); ax.text(A - N, top + yy * u, f'{N}', color=cSub, fontsize=fs, va='bottom', fontproperties=sans)
    ax.plot([A, pos[cf[N]]], [top + yy * u] * 2, color=COL['A'], lw=1, alpha=0.6)
ax.text(A - 60, top + 1.6 * u, 'look back 60 / 40 / 20', color=cSub, fontsize=fs, va='bottom', fontproperties=sans)
ax.text(pos[cf[60]], top + 1.2 * u, 'cast forward', color=COL['A'], fontsize=fs, va='bottom', ha='right', fontproperties=sans)
ax.add_patch(plt.Rectangle((pos[cf[20]], bot - 0.3 * u), pos[cf[60]] - pos[cf[20]], top - bot + 0.6 * u, color=COL['A'], alpha=0.04, zorder=1))
for M in (20, 40, 60):
    vline(pos[cf[M]], COL['A'], '--', 1, 0.4 if M < 60 else 0.6); ax.text(pos[cf[M]] + 0.4, bot - 0.5 * u, f'+{M} {cf[M]:%d %b}', color=COL['A'], fontsize=fs, va='top', fontproperties=sans)
# liquidity: BSL (highs) and SSL (lows), merged names as the Pine
def same(a, b): return S[a] == S[b] and S[a + 'i'] == S[b + 'i']
nm = {'h40': '' if same('h40', 'h60') else '40d', 'l40': '' if same('l40', 'l60') else '40d'}
nm['h20'] = '' if (same('h20', 'h40') or same('h20', 'h60')) else '20d'; nm['l20'] = '' if (same('l20', 'l40') or same('l20', 'l60')) else '20d'
nm['h60'] = ('60/40/20d' if nm['h20'] == '' else '60/40d') if nm['h40'] == '' else '60d'; nm['l60'] = ('60/40/20d' if nm['l20'] == '' else '60/40d') if nm['l40'] == '' else '60d'
if nm['h40'] and not nm['h20'] and same('h20', 'h40'): nm['h40'] = '40/20d'
if nm['l40'] and not nm['l20'] and same('l20', 'l40'): nm['l40'] = '40/20d'
tE = max(pos[cf[60]], TODAY)
def tk(key):
    t = S['tH' + key[1:]] if key[0] == 'h' else S['tL' + key[1:]]
    if t is None and ((key[0] == 'h' and h[TODAY] >= S[key]) or (key[0] == 'l' and l[TODAY] <= S[key])): t = TODAY
    return t
for key in ('h60', 'h40', 'h20', 'l20', 'l40', 'l60'):
    if not nm[key]: continue
    t0 = S[key + 'i']; t1 = tk(key); colr = COL[key[0].upper() + key[1:]]; side = 'BSL ' if key[0] == 'h' else 'SSL '
    if t1 is not None:
        ax.plot([t0, t1], [S[key]] * 2, color=colr, lw=2, zorder=4)
        tW = A - int(key[1:]); rt = (t1 - t0) >= (t0 - tW)
        ax.text(t0 + (0.3 if rt else -0.3), S[key], f"{side}{nm[key]} · swept {dts[t1]:%d %b}", color=colr, fontsize=fs, va='bottom' if key[0] == 'h' else 'top', ha='left' if rt else 'right', fontproperties=sansB, zorder=6, clip_on=True)
        ax.text(t1, S[key], '✕', color=colr, fontsize=fs + 2, ha='center', va='center', fontproperties=sansB, zorder=7)
    else:
        ax.plot([t0, tE], [S[key]] * 2, color=colr, lw=1, zorder=4)
        ax.text(tE + 0.4, S[key], f"{side}{nm[key]} {S[key]:,.2f}", color=colr, fontsize=fs, va='center', fontproperties=sans, zorder=6)
# market structure: the last two shifts and the flip level
for m_, last in ((ST['m2'], False), (ST['m1'], True)):
    if m_ is None or m_[1] is None or m_[1] < x0 - 5: continue
    lv, tf, ta, d = m_; colr = COL['U'] if d == 1 else COL['D']; a_ = 1.0 if last else 0.6
    ax.plot([tf, ta], [lv, lv], color=colr, ls='--', lw=1, alpha=a_, zorder=4)
    ax.text(tf + 0.3, lv, 'MSS ▲' if d == 1 else 'MSS ▼', color=colr, alpha=a_, fontsize=fs, va='bottom' if d == 1 else 'top', fontproperties=sans, zorder=6)
if flipP is not None:
    colr = COL['U'] if ST['trend'] == -1 else COL['D']
    ax.plot([flipT, tE], [flipP, flipP], color=colr, ls=':', lw=1, alpha=0.8, zorder=4)
    ax.text(tE + 0.4, flipP, ('flip ▲ ' if ST['trend'] == -1 else 'flip ▼ ') + f'{flipP:,.2f}', color=colr, fontsize=fs, va='center', fontproperties=sans, zorder=6)
# true opens
for key, tkey, nmm, a_ in (('tyO', 'tyT', 'true year open', 1.0), ('tmO', 'tmT', 'true month open', 0.7)):
    if ST[key] is None: continue
    ax.plot([ST[tkey], tE], [ST[key]] * 2, color=COL['TO'], ls='--', lw=1, alpha=a_, zorder=4)
    ax.text(tE + 0.4, ST[key], f'{nmm} {ST[key]:,.2f}', color=COL['TO'], alpha=a_, fontsize=fs, va='center', fontproperties=sans, zorder=6)
# quarter dividers (Q1–Q4) and the next one
def qname(d): return f'Q{(d.month - 1) // 3 + 1} {d.year}'
for i in range(max(1, x0), n):
    if dts[i].month != dts[i - 1].month and dts[i].month in (1, 4, 7, 10):
        vline(i, COL['Q'], ':', 1, 0.7); ax.text(i + 0.3, top + 0.15 * u, qname(dts[i]), color=COL['Q'], fontsize=fs - 1, fontproperties=sans)
from datetime import date as _date
d0 = _date(2027, 1, 1)
while not is_td(d0): d0 += timedelta(days=1)
if d0 in pos: vline(pos[d0], COL['Q'], '--', 1, 0.8); ax.text(pos[d0] + 0.3, top + 1.9 * u, f'next: {qname(d0)} · {d0:%d %b}', color=COL['Q'], fontsize=fs, fontproperties=sans, clip_on=True)
# axes (the price scale reaches the true year open only if it is near)
ylo = bot - 1.3 * u; yhi = top + 2.3 * u
xmax = (pos[d0] + 14) if (LAY == 'desktop' and d0 in pos) else pos[cf[60]] + 10
ax.set_xlim(x0 - 1, xmax); ax.set_ylim(ylo, yhi)
ticks = [i for i in range(x0, len(alld)) if i < xmax and (i == 0 or alld[i].month != alld[i - 1].month)]
ax.set_xticks(ticks); ax.set_xticklabels([alld[i].strftime('%b') for i in ticks], color=fg, fontsize=9, fontproperties=sans)
ax.yaxis.tick_right(); ax.tick_params(axis='y', colors=fg, labelsize=9); ax.grid(color=grid, lw=0.6, zorder=0)
for sp in ax.spines.values(): sp.set_visible(False)
ax.text(0.005, 0.995, f'NQ1! · 1D · CME · B-ADJ   ·   Sharingan   (mock: {dts[TODAY]:%a %d %b %Y}, NQ daily, back-adjusted)', transform=ax.transAxes, va='top', color=fg, fontsize=10, fontproperties=sans)
# ── card
def px(v): return f'{v:,.2f}'
def pc1(v): return f'{100 * v:+.1f}%'
def arw(v): return '▲' if v >= 0 else '▼'
B = 'bold'
rows = [[(f"◆ SHARINGAN   NQ1!   {qname(dts[TODAY])} · anchor {dts[A]:%d %b %Y} · day {off} of 60", cTx, cHd, B)]]
if LAY == 'desktop':
    rows.append([('ORDER FLOW', cSub, cBg)] + [(f"{N}d {arw(S[f'n{N}'])} {pc1(S[f'n{N}'])}", COL['L40'] if S[f'n{N}'] >= 0 else COL['H40'], cBg) for N in (60, 40, 20)])
else:
    rows.append([('ORDER FLOW', cSub, cBg), (''.join(arw(S[f'n{N}']) for N in (60, 40, 20)) + ' 60/40/20', COL['L40'] if S['n60'] >= 0 else COL['H40'], cBg)])
tr_ = ST['trend']; stTxt = '▲ bullish' if tr_ == 1 else '▼ bearish' if tr_ == -1 else '—'; stCol = COL['U'] if tr_ == 1 else COL['D'] if tr_ == -1 else cMu
m1 = ST['m1']; ago = (TODAY - m1[2]) if m1 else None
flipTxt = '—' if flipP is None else ('flip > ' if tr_ == -1 else 'flip < ') + px(flipP)
if LAY == 'desktop':
    rows.append([('STRUCTURE', cSub, cBg), (stTxt + (f' · MSS {dts[m1[2]]:%d %b}' if m1 else ''), stCol, cBg, B), (flipTxt, cTx, cBg), (f'{ago} d ago' if ago is not None else '', cSub, cBg)])
    rows.append([('LIQUIDITY', cSub, cHd), ('PRICE · ATR', cSub, cHd), ('≤ 20 DAYS', cSub, cHd), ('BY +60', cSub, cHd)])
else:
    rows.append([('STRUCTURE', cSub, cBg), (stTxt + (f' · MSS {dts[m1[2]]:%d %b}' if m1 else ''), stCol, cBg, B), ('' if flipP is None else ('flip > ' if tr_ == -1 else 'flip < ') + px(flipP), cTx, cBg)])
def lvrow(key):
    t1 = tk(key); colr = COL[key[0].upper() + key[1:]]; v = S[key]; side = 'BSL ' if key[0] == 'h' else 'SSL '
    if t1 is not None: return [('✕ ' + side + nm[key], colr, cBg, B), (px(v), cSub, cBg), (f'swept {dts[t1]:%d %b}', colr, cBg, B), ('', cMu, cBg)]
    d = ((v - lastC) if key[0] == 'h' else (lastC - v)) / atr
    p1 = pH20(d) if key[0] == 'h' else pL20(d); p2 = (pHW(d, left) if key[0] == 'h' else pLW(d, left)) if left > 0 else None
    return [(side + nm[key], colr, cBg), (f'{px(v)} · {d:.1f}', cTx, cBg), (f'{100 * p1:.0f}%', cTx, cBg), (f'{100 * p2:.0f}%' if p2 is not None else '—', cTx, cBg)]
if LAY == 'desktop':
    for k_ in ('h60', 'h40', 'h20'):
        if nm[k_]: rows.append(lvrow(k_))
    rows.append([(f'— price {px(c[TODAY])}', cTx, cHd)])
    for k_ in ('l20', 'l40', 'l60'):
        if nm[k_]: rows.append(lvrow(k_))
else:
    hk = next((k for k in ('h20', 'h40', 'h60') if nm[k] and tk(k) is None), None); lk = next((k for k in ('l20', 'l40', 'l60') if nm[k] and tk(k) is None), None)
    rows.append(lvrow(hk) if hk else [('BSL', cSub, cBg), ('all swept', cMu, cBg)]); rows.append(lvrow(lk) if lk else [('SSL', cSub, cBg), ('all swept', cMu, cBg)])
rows.append([('WINDOW', cSub, cBg)] + [((f'+{M} ✓ ' if off >= M else f'+{M} ') + f'{cf[M]:%d %b}', cMu if off >= M else COL['A'], cBg) for M in (20, 40, 60)])
if LAY == 'desktop':
    posw = lambda v: 'above' if lastC >= v else 'below'
    rows.append([('QUARTER', cSub, cBg), (f'{qname(dts[TODAY])} · next {d0:%d %b}', cTx, cBg),
                 (f"year TO {px(ST['tyO'])} · {posw(ST['tyO'])}" if ST['tyO'] is not None else 'year TO —', cTx, cBg),
                 (f"month TO {px(ST['tmO'])} · {posw(ST['tmO'])}" if ST['tmO'] is not None else 'month TO —', cTx, cBg)])
ncol = 4; chw = (0.0044 if LAY == 'desktop' else 0.0094)
cw = [0.0] * ncol
def spanof(k): return {1: [(0, 4)], 2: [(0, 1), (1, 4)], 3: [(0, 1), (1, 2), (2, 4)], 4: [(0, 1), (1, 2), (2, 3), (3, 4)]}[k]
for row in rows:
    for cell, (a_, b_) in zip(row, spanof(len(row))):
        if b_ - a_ == 1: cw[a_] = max(cw[a_], (len(cell[0]) + 2) * chw)
cw = [max(x, 0.03) for x in cw]
for row in rows:
    for cell, (a_, b_) in zip(row, spanof(len(row))):
        need = (len(cell[0]) + 2) * chw
        if b_ - a_ > 1 and sum(cw[a_:b_]) < need: cw[b_ - 1] += need - sum(cw[a_:b_])
rh = 0.023 if LAY == 'desktop' else 0.017; fsz = 8 if LAY == 'desktop' else 11
x0c = 0.035 if LAY == 'desktop' else 0.04; y0c = (0.065 + len(rows) * rh) if LAY == 'desktop' else 0.975
for ri, row in enumerate(rows):
    xx = x0c
    if len(row) == 1: spans = [sum(cw)]
    elif len(row) == 2: spans = [cw[0], sum(cw[1:])]
    elif len(row) == 3: spans = [cw[0], cw[1], sum(cw[2:])]
    else: spans = cw
    for cell, wdt in zip(row, spans):
        txt, col, bgc = cell[:3]; bold = len(cell) > 3
        fig.patches.append(plt.Rectangle((xx, y0c - (ri + 1) * rh), wdt, rh, transform=fig.transFigure, fc=bgc, ec=cBd, lw=0.8, zorder=10))
        fig.text(xx + 0.004, y0c - (ri + 0.5) * rh, txt, color=col, fontsize=fsz, va='center', fontproperties=monoB if bold else mono, zorder=11); xx += wdt
if LAY == 'desktop':
    bb = ax.get_position(); f = (y0c - bb.y0) / bb.height + 0.015
    yl0, yl1 = ax.get_ylim(); ax.set_ylim(yl1 - (yl1 - yl0) / (1 - f), yl1)
if LAY == 'mobile':
    fig.text(0.04, y0c - (len(rows) + 0.8) * rh, 'Phone: the card sits bottom left on a full chart; shown here above the chart so it can be read.', color=cSub, fontsize=10, fontproperties=sans)
fig.savefig(OUT, facecolor=bg); print(OUT)
