"""Mangekyō mock: the Pine engine's Python port (emu.py) on NQ daily (back-adjusted, settlement and last-trade closes), the chart side
(above / inside / below price, the most local gaps, inversion FVGs, the forming FVG, the PO3 candles, the wick CEs of the last daily
swing candle) and the card, drawn as the indicator draws them.
Usage: python3 mock_mangekyo.py OUT.png [desktop|mobile] [light|dark] [D|60|15|5|1] [ASOF e.g. '2026-10-23 15:30'] [SETM 3 chart SET | 2 widest] [SCOPE lb|both|last|this]"""
import sys, math, numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from scipy.special import ndtr, expit, logit
sys.path.insert(0, '/home/claude/mgk')
from emu import candles, engine, pick, swing_day
OUT = sys.argv[1]; LAY = sys.argv[2] if len(sys.argv) > 2 else 'desktop'; THEME = sys.argv[3] if len(sys.argv) > 3 else 'light'
TF = sys.argv[4] if len(sys.argv) > 4 else 'D'; ASOF = pd.Timestamp(sys.argv[5] if len(sys.argv) > 5 else '2026-10-23 15:30')
SETM = int(sys.argv[6]) if len(sys.argv) > 6 else 3          # 3 = as the chart (a SET chart: settlement closes), 2 = widest
SCOPE = sys.argv[7] if len(sys.argv) > 7 else 'lb'          # gaps from: the look back, this + last week, last week, this week
LB = 60; NEACH = 2; MINF, DISPF = 0.25, 0.5
isD = TF == 'D'; tfK = 0 if isD else 3 if TF == '1' else 2 if TF == '5' else 1
XB = {0: 14, 3: 110, 2: 70, 1: 40}[tfK]; PO, PW, PS = {0: (3, 2, 1), 3: (25, 16, 8), 2: (15, 10, 5), 1: (10, 5, 3)}[tfK]
# ── daily candles; today's candle from the 1-minute bars up to ASOF
b = pd.read_pickle('/home/claude/kyw/bars_NQ_ext.pkl').sort_values('ts')
tday = pd.Timestamp(ASOF.date()) if ASOF.hour < 18 else pd.Timestamp(ASOF.date()) + pd.Timedelta(days=1)
X = candles('NQ', end=tday)                      # includes today's full day; the engine reads [1] and older only
from data import daily as _daily
_D = _daily('NQ'); OFF = float((_D.bc - _D.uc).asof(tday)) if tday <= _D.index[-1] else 0.0
for k in ('o', 'h', 'l', 's', 'lc'): X[k] = X[k] - OFF
CON = _D.con.asof(tday).upper() if tday <= _D.index[-1] else 'NQZ26'
gS, A = engine(X, 's', 0); gL, _ = engine(X, 'lc', 1)
al = pick(gS, gL, SETM)
T = X.index; i_today = len(X) - 1
atr = A[i_today - 1]; lastC = X.s.values[i_today - 1]; lastO = X.o.values[i_today - 1]
h2, l2 = X.h.values[i_today - 2], X.l.values[i_today - 2]
today = b[(b.tday == tday) & (b.ts <= ASOF)]
tdO, tdH, tdL, close = today.Open.iloc[0], today.High.max(), today.Low.min(), today.Close.iloc[-1]
SW = swing_day(X.iloc[:i_today + 1], 's')
yL_, yH_, l2_, h2_ = X.l.values[i_today - 1], X.h.values[i_today - 1], X.l.values[i_today - 2], X.h.values[i_today - 2]
pD = 1 if (yL_ < l2_ and not yH_ > h2_) else -1 if (yH_ > h2_ and not yL_ < l2_) else 0
if pD != 0 and ((pD == 1 and tdL >= yL_) or (pD == -1 and tdH <= yH_)):     # yesterday as the pending swing
    SW = (X.o.values[i_today - 1], yH_, yL_, X.s.values[i_today - 1], X.index[i_today - 1], pD)
print('as of', ASOF, 'today', tday.date(), 'O/H/L/C', tdO, tdH, tdL, close, 'ATR', round(atr, 1), 'last settle', lastC, 'swing', SW)
def rtm(v, tick=0.25): return math.floor(v / tick + 0.5) * tick       # math.round_to_mintick (half up)
# ── chart side, as the Pine
inv = lambda g: g['tX'] is not None
role = lambda g: -g['dir'] if inv(g) else g['dir']
def dayNm(t): return (pd.Timestamp(t)).strftime('%a %d %b')
def baseNm(g): return ('▲ BISI' if g['dir'] == 1 else '▼ SIBI') if g['kind'] == 0 else ('▲ SB' if g['dir'] == 1 else '▼ SB') if g['kind'] == 1 else ('▲ VI' if g['dir'] == 1 else '▼ VI')
def kindNm(g): return ('▼ IFVG' if g['dir'] == 1 else '▲ IFVG') if inv(g) else baseNm(g)
dark = THEME == 'dark'
cBull, cBear, cSBc, cVIc, cInv, cWick = '#26a69a', '#ef5350', '#42a5f5', '#9575cd', '#ff9800', '#7e57c2'
def colOf(g): return cInv if inv(g) else cSBc if g['kind'] == 1 else cVIc if g['kind'] == 2 else (cBull if g['dir'] == 1 else cBear)
def anchorT(g): return g['t2'] if g['kind'] == 1 else g['t1']
def todayIn(g): return tdL <= g['top'] if role(g) == 1 else tdH >= g['bot']
def inZ(g, p): w = g['top'] - g['bot']; return ((g['top'] - p) / w if role(g) == 1 else (p - g['bot']) / w) if w > 0 else np.nan
def dmy(t): return pd.Timestamp(t).strftime('%d %b')
insideNow = lambda g: g['bot'] <= close <= g['top']
def statusOf(g):
    dpT = inZ(g, tdL if role(g) == 1 else tdH) if todayIn(g) else -1
    dpA = max(g['dp'] if g['dp'] is not None else -1, dpT); tch = g['tT'] is not None or todayIn(g)
    if inv(g): return 'inverted ' + dmy(g['tX']) + (' · inside now' if insideNow(g) else '')
    if insideNow(g): return 'inside now'
    if not tch: return 'untouched'
    if dpA >= 1: return 'traded through' + (' today' if g['tT'] is None else '')
    if dpA >= 0.5: return 'past CE' + (' today' if g['tT'] is None else '')
    return 'touched today' if g['tT'] is None else 'touched ' + dmy(g['tT'])
wk0 = tday - pd.Timedelta(days=tday.dayofweek)          # this week's Monday
def wkAgo(g):
    t = pd.Timestamp(g['t0']); w = t - pd.Timedelta(days=t.dayofweek)
    return 0 if w >= wk0 else 1 if w >= wk0 - pd.Timedelta(days=7) else 2
def inScope(g): return g['age'] <= LB if SCOPE == 'lb' else wkAgo(g) <= 1 if SCOPE == 'both' else wkAgo(g) == 1 if SCOPE == 'last' else wkAgo(g) == 0
def wkTag(g): return ' · this week' if wkAgo(g) == 0 else ' · last week' if wkAgo(g) == 1 else ''
keep = []
for g in sorted(al, key=lambda g: (g['kind'] * 10 + (1 if inv(g) else 0), -(g['top'] - g['bot']))):
    if not inScope(g) or (inv(g) and g['kind'] != 0) or g.get('tY') is not None: continue
    if any(role(k) == role(g) and min(g['top'], k['top']) - max(g['bot'], k['bot']) >= 0.5 * min(g['top'] - g['bot'], k['top'] - k['bot']) for k in keep): continue
    keep.append(g)
shA, shB, shI = [], [], []
for g in keep: (shA if g['bot'] > close else shB if g['top'] < close else shI).append(g)
shA = sorted(shA, key=lambda g: g['bot'])[:NEACH]; shB = sorted(shB, key=lambda g: -g['top'])[:NEACH]
focus = min(shI, key=lambda g: (g['kind'], -pd.Timestamp(g['t0']).value), default=None)
if focus is None and SCOPE != 'lb' and (shA or shB):
    dA_ = shA[0]['bot'] - close if shA else None; dB_ = close - shB[0]['top'] if shB else None
    focus = shA[0] if dB_ is None or (dA_ is not None and dA_ < dB_) else shB[0]
fm_ = None
if tdL > h2 and (tdL - h2) / atr >= MINF and (lastC - lastO) / atr >= DISPF: fm_ = (1, tdL, h2)
elif tdH < l2 and (l2 - tdH) / atr >= MINF and (lastO - lastC) / atr >= DISPF: fm_ = (-1, l2, tdH)
if SCOPE == 'last': fm_ = None
for nm, L_ in (('above', shA), ('inside', shI), ('below', shB)): print(nm, [(kindNm(g), dayNm(g['t2']), g['bot'], g['top'], g['src']) for g in L_])
print('forming', fm_)
def reachP(d, h, above):
    k, a, bb = (0.625, 0.2108, 0.9973) if above else (1.05, -1.0257, 1.0638)
    q = np.clip(2 * ndtr(-(d / math.sqrt(max(h, 0.25))) / k), 1e-5, 1 - 1e-5); return expit(a + bb * logit(q))
PT = {0: (1.9063, 1.4383), 1: (1.8216, 1.5525), 2: (1.1063, 1.0892)}; P10 = {0: (-0.3164, 0.4153), 1: (-0.0963, 0.6071), 2: (-0.8334, 0.2189)}
PB = {0: (0.439, 0.342, 0.161), 1: (0.508, 0.448, 0.198), 2: (0.324, 0.241, 0.159)}
def pT(g, w): a, bb = PT[g['kind']]; return expit(a + bb * math.log(max(w, 0.01)))
def p10(g, w): a, bb = P10[g['kind']]; return expit(a + bb * math.log(max(w, 0.01)))
dLeft = 5 - tday.dayofweek if tday.dayofweek <= 4 else 1
# ── the chart's bars
if isD:
    bars = X[X.index <= tday].copy().rename(columns={'s': 'c'})
    bars.loc[tday, ['o', 'h', 'l', 'c']] = [tdO, tdH, tdL, close]
    bars = bars[bars.index >= (pd.Timestamp('2026-07-27') if LAY == 'desktop' else pd.Timestamp('2026-08-24'))]
    bt = list(bars.index); O, H, L, C = (bars[k].values for k in 'ohlc')
    def xof(t):
        t = pd.Timestamp(t).normalize(); return bt.index(t) if t in bt else (-1 if t < bt[0] else len(bt))
else:
    m = b[(b.tday >= tday - pd.Timedelta(days={'60': 10, '15': 3, '5': 2, '1': 0}[TF])) & (b.ts <= ASOF)].set_index('ts')
    rs = m.resample(f'{TF}min', origin='start_day', offset='0min').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
    bt = list(rs.index); O, H, L, C = (rs[k].values for k in ['Open', 'High', 'Low', 'Close'])
    def xof(t):
        t = pd.Timestamp(t) - pd.Timedelta(hours=6)
        return 0 if t <= bt[0] else next((i for i, x in enumerate(bt) if x >= t), len(bt))
n = len(bt); xEnd = n - 1 + XB
mono = fm.FontProperties(fname='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'); sans = fm.FontProperties(fname='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
sansB = fm.FontProperties(fname='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'); cCE = '#089981'
bg = '#131722' if dark else '#ffffff'; fg = '#d1d4dc' if dark else '#131722'; grid = '#1f2433' if dark else '#f0f3fa'
cBg = '#0e1117' if dark else '#ffffff'; cHd = '#171c28' if dark else '#eef1f6'; cBd = '#262c3a' if dark else '#d5dae4'; cTx = '#e6e9ef' if dark else '#131722'; cSub = '#9aa3b5' if dark else '#4a5163'; cMu = '#5d6476' if dark else '#9aa1b2'
pCol = '#787b86'
W, Hh = (19.2, 10.8) if LAY == 'desktop' else (10.8, 19.2)
fig = plt.figure(figsize=(W, Hh), dpi=100, facecolor=bg)
ax = fig.add_axes([0.03, 0.06, 0.88, 0.88] if LAY == 'desktop' else [0.02, 0.04, 0.80, 0.60]); ax.set_facecolor(bg)
up, dn = ('#089981', '#f23645')
cw_ = 0.35 if isD else 0.33 if TF in ('60', '15') else 0.3
for i in range(n):
    col = up if C[i] >= O[i] else dn
    ax.plot([i, i], [L[i], H[i]], color=col, lw=1, zorder=3); ax.add_patch(plt.Rectangle((i - cw_, min(O[i], C[i])), 2 * cw_, max(abs(C[i] - O[i]), 0.5), color=col, zorder=3))
fs = 8 if LAY == 'desktop' else 9
def rgba(hexc, tr):
    h = hexc.lstrip('#'); return tuple(int(h[k:k + 2], 16) / 255 for k in (0, 2, 4)) + ((100 - tr) / 100,)
def grades(x1, x2, g, lvl, lab):
    step = 1 if lvl == 3 else 2 if lvl == 2 else 4; c = colOf(g)
    for k in range(0, 9):
        if k % step: continue
        y = rtm(g['bot'] + (g['top'] - g['bot']) * k / 8); ce = k == 4
        if 0 < k < 8: ax.plot([x1, x2], [y, y], color=rgba(c, 10 if ce else 55), ls='--' if ce else ':', lw=1, zorder=4)
        if lab == 2 or (lab == 1 and ce):
            fr = (8 - k) / 8 if g['dir'] == 1 else k / 8
            ax.text(x2 + 0.4, y, f"{fr:g} ({y:,.2f})", color=rgba(c, 0 if ce else 30), fontsize=fs - 1, va='center', fontproperties=sans, zorder=6, clip_on=True)
# the wick CEs, known before the gaps: one on a graded line joins that line's label
WK = [None, None, None]; WKU = [False, False, False]
if SW is not None:
    _wO, _wH, _wL, _wC, _wT, _wD = SW; _bt, _bb = max(_wO, _wC), min(_wO, _wC)
    _pw, _dw = rtm((_wH + _bt) / 2), rtm((_bb + _wL) / 2)
    WK = [_pw if _wH > _bt else None, _dw if _wL < _bb else None, rtm((_pw + _dw) / 2) if (_wH > _bt and _wL < _bb) else None]
def gradeF(x1, x2, g, nmT=''):
    wA = (g['top'] - g['bot']) / atr; lv = 3 if (not isD or wA >= 1.5) else 2 if wA >= 0.75 else 1
    for k in range(9):
        y = rtm(g['bot'] + (g['top'] - g['bot']) * k / 8); ce = k == 4; tr = 25 if k in (0, 8) else 40 if k % 2 == 0 else 58
        ax.plot([x1, x2], [y, y], color=cCE if ce else rgba(cTx, tr), lw=2 if ce else 1, zorder=4)
        fr = (8 - k) / 8 if g['dir'] == 1 else k / 8
        top_ = k == 8 and nmT
        if not (k % 8 == 0 or ce or lv == 3 or (lv == 2 and k % 2 == 0)): continue
        wx = ''
        for j in range(3):
            if WK[j] is not None and not WKU[j] and abs(WK[j] - y) <= (g['top'] - g['bot']) / 16: WKU[j] = True; wx += f" · wick CE {WK[j]:,.2f}"
        ax.text(x2 + 0.4, y, f"{fr:g} ({y:,.2f})" + wx + (f"   {nmT}" if top_ else ''), color=colOf(g) if top_ else cCE if ce else rgba(cTx, tr - 20), fontsize=fs - (1 if isD else 0), va='center', fontproperties=sansB if top_ else sans, zorder=6, clip_on=True)
def drawGap(g, focusOn):
    c = colOf(g); x1 = max(xof(anchorT(g)) - 0.4, -0.5); alt = SETM == 2 and g['src'] == 1
    tr = 74 if focusOn else 84
    ax.add_patch(plt.Rectangle((x1, g['bot']), xEnd - x1, g['top'] - g['bot'], fc=rgba(c, tr), ec=rgba(c, 45), lw=1, ls='--' if alt else '-', zorder=2))
    nm = f"D {kindNm(g)} · {dayNm(g['t2'])}" + wkTag(g) + (' · last trade' if alt else '')
    if focusOn: gradeF(x1, xEnd, g, '' if isD else nm)
    else: grades(x1, xEnd, g, 1, 0)
    up_ = role(g) == 1
    if focusOn:
        if isD: ax.text(max(x1, 0) + 0.3, g['top'], nm, color=c, fontsize=fs - 1, va='bottom', fontproperties=sans, zorder=6, clip_on=True)
    elif isD: ax.text(max(x1, 0) + 0.3, g['top'] if up_ else g['bot'], nm, color=c, fontsize=fs - 1, va='bottom' if up_ else 'top', fontproperties=sans, zorder=6, clip_on=True)
    else: ax.text(xEnd + 0.4, g['top'] if up_ else g['bot'], nm, color=c, fontsize=fs - 1, va='bottom' if up_ else 'top', fontproperties=sans, zorder=6, clip_on=True)
for g in shA + shB: drawGap(g, focus is not None and g is focus)
for g in shI: drawGap(g, focus is not None and g is focus)
if fm_:
    d_, ft, fb = fm_; fc = cBull if d_ == 1 else cBear; x1 = xof(T[i_today - 2]) - 0.4
    ax.add_patch(plt.Rectangle((x1, fb), xEnd - x1, ft - fb, fc=rgba(fc, 92), ec=rgba(fc, 30), lw=1, ls='--', zorder=2))
    ax.plot([x1, xEnd], [rtm((ft + fb) / 2)] * 2, color=rgba(fc, 40), ls='--', lw=1, zorder=4)
    ax.text(xEnd + 0.4, fb if d_ == -1 else ft, f"D {'▲ BISI' if d_ == 1 else '▼ SIBI'} forming · {dayNm(T[i_today - 1])} · {(ft - fb) / atr:.2f} ATR", color=fc, fontsize=fs - 1, va='top' if d_ == -1 else 'bottom', fontproperties=sans, zorder=6, clip_on=True)
# wick CEs of the last daily swing candle
if SW is not None:
    wO, wH, wL, wC, wT, wD = SW; btw, bbw = max(wO, wC), min(wO, wC)
    pw, dw = rtm((wH + btw) / 2), rtm((bbw + wL) / 2); mw = rtm((pw + dw) / 2); x1 = xof(wT) - 0.4
    for j_, (y, ls_, tr_) in enumerate(((pw, ':', 0), (dw, ':', 0), (mw, '--', 20))):
        if WK[j_] is None: continue
        ax.plot([x1, xEnd], [y, y], color=rgba(cWick, tr_), ls=ls_, lw=1, zorder=4)
        if not WKU[j_]: ax.text(xEnd + 0.4, y, f"0.5 ({y:,.2f})", color=rgba(cWick, tr_), fontsize=fs - 1, va='center', fontproperties=sans, zorder=6, clip_on=True)
    print('wick CE of', pd.Timestamp(wT).date(), pw, dw, mw)
# PO3: the focus gap's candles right of price
if focus is not None and shI:
    step = PW + PS; x = n - 1 + PO; xE = x + focus['nc'] * step; c = colOf(focus)
    ax.add_patch(plt.Rectangle((x - 1, focus['bot']), xE - x + 1, focus['top'] - focus['bot'], fc=rgba(c, 80), ec=rgba(c, 40), lw=1, zorder=2))
    for j, (t_, o_, h_, l_, c_) in enumerate(focus['cand']):
        x1_ = x + j * step; x2_ = x1_ + PW; xm = (x1_ + x2_) / 2
        bt_, bb_ = max(o_, c_), min(o_, c_)
        ax.add_patch(plt.Rectangle((x1_, bb_), PW, max(bt_ - bb_, 0.5), fc=rgba(pCol, 85 if c_ >= o_ else 30), ec=pCol, lw=1, zorder=5))
        ax.plot([xm, xm], [bt_, h_], color=pCol, lw=1, zorder=5); ax.plot([xm, xm], [l_, bb_], color=pCol, lw=1, zorder=5)
        ax.text(xm, l_, pd.Timestamp(t_).strftime('%a %d'), color=cSub, fontsize=fs - 1, ha='center', va='top', fontproperties=sans, zorder=6, clip_on=True)
    ax.plot([x - 1, xE], [close, close], color=cTx, lw=1, ls=':', zorder=6)
xmax = xEnd + (17 if isD else int(0.27 * n) + 10)
ys = [L.min(), H.max()] + [g['bot'] for g in shA + shB + shI] + [g['top'] for g in shA + shB + shI]
if LAY == 'mobile': ys = [L.min(), H.max(), *(g['top'] for g in shI), *(g['bot'] for g in shI)] + ([shA[0]['top']] if shA else []) + ([shB[0]['bot']] if shB else []) + ([max(c[2] for c in focus['cand']), min(c[3] for c in focus['cand'])] if focus is not None else [])
lo_, hi_ = min(ys), max(ys); pad = (hi_ - lo_) * 0.06
ax.set_xlim(-1, xmax); ax.set_ylim(lo_ - (hi_ - lo_) * (0.55 if LAY == 'desktop' else 0.06), hi_ + pad)
if isD:
    ticks = [i for i in range(n) if i == 0 or bt[i].month != bt[i - 1].month or (bt[i].day >= 15 and bt[i - 1].day < 15)]
    ax.set_xticks(ticks); ax.set_xticklabels([bt[i].strftime('%d %b') for i in ticks], color=fg, fontsize=9, fontproperties=sans)
elif TF in ('1', '5'):
    stp = 2 if TF == '1' else 6
    ticks = [i for i in range(n) if bt[i].minute == 0 and bt[i].hour % stp == 0]
    ax.set_xticks(ticks); ax.set_xticklabels([bt[i].strftime('%a %d') if bt[i].hour == 0 else bt[i].strftime('%H:%M') for i in ticks], color=fg, fontsize=9, fontproperties=sans)
else:
    td_ = [(x_ + pd.Timedelta(hours=6)).date() for x_ in bt]
    ticks = [i for i in range(1, n) if td_[i] != td_[i - 1]]
    ax.set_xticks(ticks); ax.set_xticklabels([td_[i].strftime('%a %d') for i in ticks], color=fg, fontsize=9, fontproperties=sans)
ax.yaxis.tick_right(); ax.tick_params(axis='y', colors=fg, labelsize=9); ax.grid(color=grid, lw=0.6, zorder=0)
for sp in ax.spines.values(): sp.set_visible(False)
tfn = {'D': '1D', '60': '1h', '15': '15', '5': '5', '1': '1'}[TF]
ax.text(0.005, 0.995, f'NQ1! · {tfn} · CME · B-ADJ · SET   ·   Mangekyō   (mock: {ASOF:%a %d %b %Y %H:%M} ET, NQ data, {CON} prices)', transform=ax.transAxes, va='top', color=fg, fontsize=10, fontproperties=sans)
# ── card
def px(v): return f'{v:,.2f}'
def pc0(p): return f'{100 * p:.0f}%'
def gapRow(g, above):
    w = (g['top'] - g['bot']) / g['atr']; d = (g['bot'] - lastC) / atr if above else (lastC - g['top']) / atr
    iv = inv(g); hit = (not iv and g['tT'] is not None) or todayIn(g)
    pF = 1.0 if hit or d <= 0 else reachP(d, dLeft, above); p20 = 1.0 if hit or d <= 0 else reachP(d, 20, above)
    vm = (f"{g['rv']:.1f}×" if g['rv'] == g['rv'] else '—') + (' · BOS' if g['brk'] else '')
    c = colOf(g); nm = kindNm(g) + ' ' + dayNm(g['t2'])
    if LAY == 'mobile':
        return [(nm, c, cBg), (f"{px(g['bot'])}–{px(g['top'])} · " + ('✓' if hit else f'{d:.1f} ATR'), cTx, cBg), (statusOf(g) if hit else f'{pc0(pF)} by Fri', cTx, cBg)]
    holds = '—' if iv or g['tT'] is not None else f'{pc0(pT(g, w))} · {pc0(p10(g, w))}'
    return [(nm, c, cBg), (f"{px(g['bot'])}–{px(g['top'])}", cTx, cBg), (f"{w:.2f} · " + ('✓' if hit else f'{d:.1f}'), cTx, cBg), (statusOf(g), cTx if hit else cSub, cBg),
            ('reached' if hit else f'{pc0(pF)} · {pc0(p20)}', cTx, cBg), (holds, cTx, cBg), (vm, cSub, cBg)]
scT = {'lb': f'{LB}d look back', 'both': 'this + last week', 'last': 'last week', 'this': 'this week'}[SCOPE]
noneT = {'lb': 'in the look back', 'both': 'this or last week', 'last': 'from last week', 'this': 'this week'}[SCOPE]
rows = [[(f"◆ MANGEKYŌ   NQ1!   chart · {'chart SET' if SETM == 3 else 'widest'} · {scT}", cTx, cHd)]]
if LAY == 'desktop':
    rows.append([(t, cSub, cHd) for t in ('DAILY GAP', 'RANGE', 'ATR · DIST', 'STATUS', 'BY FRI · 20D', 'HOLDS · 10D', 'VOL · MS')])
for g in reversed(shA): rows.append(gapRow(g, True))
if not shA: rows.append([('ABOVE', cSub, cBg), (f'no live gap {noneT}', cMu, cBg)])
rows.append([(f'— price {px(close)}', cTx, cHd)])
for g in shI[:3]: rows.append(gapRow(g, False))
for g in shB: rows.append(gapRow(g, False))
if not shB: rows.append([('BELOW', cSub, cBg), (f'no live gap {noneT}', cMu, cBg)])
if fm_:
    d_, ft, fb = fm_
    rows.append([(('▲ BISI' if d_ == 1 else '▼ SIBI') + ' forming', cBull if d_ == 1 else cBear, cBg), (f"{px(fb)}–{px(ft)} · {(ft - fb) / atr:.2f} ATR · while today's " + (f'low > {px(fb)}' if d_ == 1 else f'high < {px(ft)}'), cTx, cBg)])
okW = lambda g: inv(g) or g['tT'] is None or pd.Timestamp(g['tT']) >= wk0
pA = next((g for g in shA if role(g) == -1 and okW(g)), None); pB = next((g for g in shB if role(g) == 1 and okW(g)), None)
def wtxt(g, above):
    if g is None: return ('premium draw —' if above else 'discount draw —')
    d = (g['bot'] - lastC) / atr if above else (lastC - g['top']) / atr; hit = (not inv(g) and g['tT'] is not None) or todayIn(g)
    return ('premium ' if above else 'discount ') + kindNm(g) + ' ' + px(g['bot'] if above else g['top']) + (' ✓' if hit else ' ' + pc0(1.0 if d <= 0 else reachP(d, dLeft, above)) + ' by Fri')
rows.append([('WEEK', cSub, cBg), (wtxt(pA, True), cBear, cBg), (wtxt(pB, False), cBull, cBg)])
if focus is not None and shI:
    pos = inZ(focus, close); hf = 0 if pos <= 0 else 1 if pos <= 0.5 else 2
    side = ['back outside', 'near half, CE held', 'past CE'][hf]
    rows.append([('TODAY', cSub, cBg), (f"in {kindNm(focus)} {dayNm(focus['t2'])} · {side}" + ('' if inv(focus) else f" · if today closes here, 10 more days {pc0(PB[focus['kind']][hf])}"), cTx, cBg)])
cw = [0.085, 0.105, 0.06, 0.11, 0.075, 0.07, 0.07] if LAY == 'desktop' else [0.30, 0.40, 0.25]
rh = 0.024 if LAY == 'desktop' else 0.0165; fsz = 8.5 if LAY == 'desktop' else 10.5
x0c = 0.035 if LAY == 'desktop' else 0.03; y0c = (0.07 + len(rows) * rh) if LAY == 'desktop' else 0.985
for ri, row in enumerate(rows):
    xx = x0c
    if len(row) == 1: spans = [sum(cw)]
    elif len(row) == 2: spans = [cw[0], sum(cw[1:])]
    elif len(row) == 3 and LAY == 'desktop': spans = [cw[0], sum(cw[1:4]), sum(cw[4:])]
    else: spans = cw
    for (txt, col, bgc), wdt in zip(row, spans):
        fig.patches.append(plt.Rectangle((xx, y0c - (ri + 1) * rh), wdt, rh, transform=fig.transFigure, fc=bgc, ec=cBd, lw=0.8, zorder=10))
        fig.text(xx + 0.003, y0c - (ri + 0.5) * rh, txt, color=col, fontsize=fsz, va='center', fontproperties=mono, zorder=11); xx += wdt
if LAY == 'mobile':
    fig.text(0.03, y0c - (len(rows) + 0.8) * rh, 'Phone: the card sits bottom left on a full chart; shown here above the chart so it can be read.', color=cSub, fontsize=10, fontproperties=sans)
fig.savefig(OUT, facecolor=bg); print(OUT)
