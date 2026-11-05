"""Mangekyō (merged) mock: NQ, 23 Oct 2026 as of 11:00 ET. Daily mode on a 15-minute chart and weekly (Eternal) mode on a 1-hour
chart: the gaps on show, the graded gap, the PO3 candles with the live candle forming now, and the compact card. Daily candles are
the back-adjusted front month to 9 Oct and the front contract (NQZ26) from the 1-minute data after."""
import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy.stats import norm
sys.path.insert(0, '/home/claude/mgk'); sys.path.insert(0, '/home/claude/lr')
from data import daily, atr
from gaps import detect
from lib import load
CB, CS, CSB, CVI, CINV, CCE, AMB = '#26a69a', '#ef5350', '#42a5f5', '#9575cd', '#ff9800', '#089981', '#f9a825'
T = pd.Timestamp('2026-10-23 11:00'); tmin = int((T - pd.Timestamp('1970-01-01')).total_seconds() // 60)
m = load('NQ'); ts = m['ts']; td = m['td'].astype(int); rel = ((ts % 1440) - 1080) % 1440
D = daily('NQ'); D = D[D.index <= '2026-10-09'][['bo', 'bh', 'bl', 'bc']].rename(columns={'bo': 'o', 'bh': 'h', 'bl': 'l', 'bc': 'c'})
days = []
for d in np.unique(td[(td > int(pd.Timestamp('2026-10-09').value // 86400e9)) & (ts <= tmin)]):
    k = np.flatnonzero((td == d) & (ts <= tmin)); days.append((pd.Timestamp(int(d), unit='D'), m['O'][k[0]], m['H'][k].max(), m['L'][k].min(), m['C'][k[-1]]))
X = pd.concat([D, pd.DataFrame(days, columns=['date', 'o', 'h', 'l', 'c']).set_index('date')])
price = X.c.iloc[-1]
def reachP(d, h, up, W):
    k, a, b = ((1.0, -0.5945, 1.4802) if up else (2.1, -2.823, 1.4882)) if W else ((0.625, 0.2108, 0.9973) if up else (1.05, -1.0257, 1.0638))
    q = np.clip(2 * norm.cdf(-(d / np.sqrt(max(h, .25))) / k), 1e-5, 1 - 1e-5); return 1 / (1 + np.exp(-(a + b * np.log(q / (1 - q)))))
def pTouch(kind, w, W):
    lw = np.log(max(w, .01)); a, b = {(0, 0): (1.9063, 1.4383), (0, 1): (1.8216, 1.5525), (0, 2): (1.1063, 1.0892), (1, 0): (2.129, 1.6756), (1, 1): (1.959, 1.516), (1, 2): (1.3113, 1.3707)}[(int(W), kind)]
    return 1 / (1 + np.exp(-(a + b * lw)))
def gaps_for(C, W):
    """C: completed candles (o h l c), the forming candle separate. Returns gaps on show with their state."""
    O, H, L, Cc = C.o.values, C.h.values, C.l.values, C.c.values; A = atr(H, L, Cc)
    z = detect(O, H, L, Cc, A); n = len(Cc)
    mF, dF, mS, mV, LB = (0.10, 0.25, 0.10, 0.05, 52) if W else (0.25, 0.5, 0.25, 0.10, 60)
    out = []
    for r in z.itertuples():
        w = (r.top - r.bot) / A[r.t0]; kind = {'FVG': 0, 'SB': 1, 'VI': 2}[r.kind]
        mid = r.t0 - 1 if r.kind != 'VI' else r.t0
        disp = (Cc[mid] - O[mid]) * r.dir / A[r.t0]
        if (kind == 0 and (w < mF or disp < dF)) or (kind == 1 and w < mS) or (kind == 2 and w < mV): continue
        if n - 1 - r.t0 > LB: continue
        tT = tX = tY = None
        for t in range(r.t0 + 1, n):
            if tX is None:
                if tT is None and ((r.dir == 1 and L[t] <= r.top) or (r.dir == -1 and H[t] >= r.bot)): tT = t
                if (r.dir == 1 and Cc[t] < r.bot) or (r.dir == -1 and Cc[t] > r.top): tX = t
            elif tY is None and ((r.dir == 1 and Cc[t] > r.top) or (r.dir == -1 and Cc[t] < r.bot)): tY = t
        if tY is not None or (tX is not None and kind != 0): continue
        nm = {0: ('▲ BISI' if r.dir == 1 else '▼ SIBI'), 1: ('▲ SB' if r.dir == 1 else '▼ SB'), 2: ('▲ VI' if r.dir == 1 else '▼ VI')}[kind]
        if tX is not None: nm = '▼ IFVG' if r.dir == 1 else '▲ IFVG'
        col = CINV if tX is not None else CSB if kind == 1 else CVI if kind == 2 else (CB if r.dir == 1 else CS)
        out.append(dict(top=r.top, bot=r.bot, dir=r.dir, kind=kind, t0=r.t0, t1=r.t1, mid=mid, w=w, tT=tT, tX=tX, nm=nm, col=col, date=C.index[mid], cand=[(O[i], H[i], L[i], Cc[i], C.index[i]) for i in range(r.t1, r.t0 + 1)]))
    return out, A[-1], Cc[-1]
def scene(W, chart_u, nbars, fname, always=False):
    if W:
        wk = X.index - pd.to_timedelta(X.index.dayofweek, unit='D'); g = X.groupby(wk)
        Wk = pd.DataFrame({'o': g.o.first(), 'h': g.h.max(), 'l': g.l.min(), 'c': g.c.last()})
        comp, form = Wk.iloc[:-1], Wk.iloc[-1]
    else:
        comp, form = X.iloc[:-1], X.iloc[-1]
    G, a, lastC = gaps_for(comp, W)
    fH, fL, fO = form.h, form.l, form.o
    role = lambda g: -g['dir'] if g['tX'] is not None else g['dir']
    def todayIn(g): return (fL <= g['top']) if role(g) == 1 else (fH >= g['bot'])
    def inside(g): return g['bot'] <= price <= g['top']
    def glyph(g): return ('↺', CINV) if g['tX'] is not None else ('◐', AMB) if inside(g) else ('✓', CS) if (g['tT'] is not None or todayIn(g)) else ('✕', CB)
    G = sorted(G, key=lambda g: (g['kind'] * 10 + (g['tX'] is not None), -(g['top'] - g['bot'])))
    keep = []
    for g in G:
        if any(role(k) == role(g) and min(g['top'], k['top']) - max(g['bot'], k['bot']) >= 0.5 * min(g['top'] - g['bot'], k['top'] - k['bot']) for k in keep): continue
        keep.append(g)
    G = keep
    A_ = sorted([g for g in G if g['bot'] > price], key=lambda g: g['bot'])[:2]; B_ = sorted([g for g in G if g['top'] < price], key=lambda g: -g['top'])[:2]; I_ = [g for g in G if inside(g)]
    focus = sorted(I_, key=lambda g: (g['kind'], -g['t0']))[0] if I_ else None
    if focus is None and always:
        dA = A_[0]['bot'] - price if A_ else 1e9; dB = price - B_[0]['top'] if B_ else 1e9
        focus = A_[0] if dA < dB else (B_[0] if B_ else None)
    # chart candles
    sel = np.flatnonzero((ts <= tmin) & (ts > tmin - nbars * chart_u * 1.6)); key = ts[sel] // chart_u
    br = np.r_[0, np.flatnonzero(np.diff(key)) + 1]; en = np.r_[br[1:] - 1, len(key) - 1]
    bars = [(m['O'][sel[i]], m['H'][sel[i:j + 1]].max(), m['L'][sel[i:j + 1]].min(), m['C'][sel[j]], ts[sel[i]]) for i, j in zip(br, en)][-nbars:]
    n = len(bars)
    fig = plt.figure(figsize=(15, 8.6), dpi=130); ax = fig.add_axes([0.03, 0.07, 0.84, 0.85])
    for i, (o, h, l, c, t) in enumerate(bars):
        col = '#089981' if c >= o else '#f23645'; ax.plot([i, i], [l, h], color=col, lw=0.7); ax.add_patch(Rectangle((i - 0.32, min(o, c)), 0.64, max(abs(c - o), 0.5), fc=col, ec=col))
    xE = n + 12 + 4 * 6 + 10
    for g in A_ + B_ + I_:
        ax.add_patch(Rectangle((0, g['bot']), xE, g['top'] - g['bot'], fc=g['col'], alpha=0.14 if g is not focus else 0.2, ec=g['col'], lw=0.8))
        if g is focus:
            for k in range(9):
                y = g['bot'] + (g['top'] - g['bot']) * k / 8; ce = k == 4
                ax.plot([0, xE], [y, y], color=CCE if ce else '#131722', lw=1.6 if ce else 0.6, alpha=1 if ce else 0.35)
                fr = (8 - k) / 8 if g['dir'] == 1 else k / 8
                if k % 2 == 0 or ce: ax.text(xE + 0.5, y, f"{fr:g} ({y:,.2f})" + (f"   {'W' if W else 'D'} {g['nm']} · {('wk ' + g['date'].strftime('%d %b %y')) if W else g['date'].strftime('%a %d %b')}" if k == 8 else ''), fontsize=7, color=CCE if ce else ('#131722' if k != 8 else g['col']), va='center', weight='bold' if k == 8 else None)
        else:
            ce = (g['top'] + g['bot']) / 2; ax.plot([0, xE], [ce, ce], color=g['col'], lw=0.8, ls='--')
            ax.text(xE + 0.5, g['top'] if role(g) == 1 else g['bot'], f"{'W' if W else 'D'} {g['nm']} · {('wk ' + g['date'].strftime('%d %b %y')) if W else g['date'].strftime('%a %d %b')}", fontsize=7, color=g['col'], va='bottom' if role(g) == 1 else 'top')
    # PO3 (Hadō 99's candle system, Model colours): the gap's candles tagged C1–C3, then the forming candle dashed, countdown over the group
    if focus is not None:
        pWd, pS = (4, 2) if not W else (2, 2)
        x = n + 12; step = pWd + pS
        cands = focus['cand'] + [(fO, fH, fL, price, None)]
        tags = ['C1', 'C2', 'C3'][:len(focus['cand'])] + ['']
        tDn = focus['dir'] == 1; tagC = focus['col']
        for j, (o, h, l, c, dt) in enumerate(cands):
            x1 = x + j * step; xm = x1 + pWd / 2; live = dt is None; up = c >= o; mc = CB if up else CS
            bt, bb = max(o, c), min(o, c)
            ax.plot([xm, xm], [bt, h], color=mc, alpha=0.7, lw=1); ax.plot([xm, xm], [l, bb], color=mc, alpha=0.7, lw=1)
            ax.add_patch(Rectangle((x1, bb), pWd, max(bt - bb, 0.5), fc=mc, alpha=0.3, ec=mc, lw=1.1, ls='--' if live else '-'))
            stp = 'Fri 23' if (live and not W) else ('19 Oct' if live else (dt.strftime('%d %b') if W else dt.strftime('%a %d')))
            dn = stp + ('\n' + tags[j] if (tDn and tags[j]) else '')
            ax.text(xm, l, dn, fontsize=6.5, color=tagC if (tDn and tags[j]) else '#5d6476', ha='center', va='top', linespacing=1.3)
            if not tDn and tags[j]: ax.text(xm, h, tags[j], fontsize=6.5, color=tagC, ha='center', va='bottom')
        top = max([cc[1] for cc in cands] + [focus['top']]); xc = x + (len(cands) * step - pS) / 2
        ax.text(xc, top, ('W · 06h 00m' if W else 'D · 06h 00m'), fontsize=7, color='#131722', ha='center', va='bottom')
        xe = x + len(cands) * step - pS
        ax.add_patch(Rectangle((x - 1, focus['bot']), xe - x + 2, focus['top'] - focus['bot'], fc=focus['col'], alpha=0.12, ec=focus['col'], lw=0.6))
        ce = (focus['top'] + focus['bot']) / 2; ax.plot([x - 1, xe + 1], [ce, ce], color=CCE, ls='--', lw=1)
        ax.plot([x - 1, xe + step], [price, price], color='#131722', ls=':', lw=1)
    ys = [b[1] for b in bars] + [b[2] for b in bars] + [g['top'] for g in A_ + B_ + I_] + [g['bot'] for g in A_ + B_ + I_]
    if focus is not None: ys += [c[1] for c in focus['cand']] + [c[2] for c in focus['cand']]
    lo, hi = min(ys), max(ys); pad = (hi - lo) * 0.05; ax.set_ylim(lo - pad, hi + pad); ax.set_xlim(-1, xE + 26)
    ax.yaxis.tick_right(); ax.grid(color='#eef1f6', lw=0.6); ax.tick_params(colors='#131722', labelsize=8, length=0)
    for sp in ax.spines.values(): sp.set_color('#eef1f6')
    step_t = max(1, n // 8); tk = list(range(0, n, step_t)); ax.set_xticks(tk); ax.set_xticklabels([pd.Timestamp(int(bars[i][4]), unit='m').strftime('%a %H:%M') for i in tk], fontsize=7.5)
    fig.text(0.03, 0.955, f"Mangekyō · {'Weekly · Eternal Mangekyō on 1 hour' if W else 'Daily · Mangekyō on 15 minutes'} · NQ · 23 Oct 2026 as of 11:00 ET · PO3 {'when price is inside a gap' if not always else 'always (nearest gap)'} · Hadō 99 candles (Model colours)", fontsize=10.5, color='#131722', weight='bold')
    # card
    rows = [('title', f"● {'ETERNAL MANGEKYŌ · W' if W else 'MANGEKYŌ · D'}   NQ1! · {'52w' if W else '60d'}"), ('hdr', ['WEEKLY GAP' if W else 'DAILY GAP', 'RANGE', '', '4W · 12W' if W else 'FRI · 20D'])]
    def odds(g, up):
        if g['tX'] is not None: return '—'
        first = g['tT'] is None and todayIn(g)
        if first: return f"holds {100 * pTouch(g['kind'], g['w'], W):.0f}%"
        if g['tT'] is not None or todayIn(g): return '—'
        d = (g['bot'] - lastC) / a if up else (lastC - g['top']) / a
        h1, h2 = (4, 12) if W else (1, 20)
        return f"{100 * reachP(d, h1, up, W):.0f}% · {100 * reachP(d, h2, up, W):.0f}%" if d > 0 else '100%'
    nm = lambda g: g['nm'] + ' ' + (g['date'].strftime('%a %d') if (not W and (X.index[-1] - g['date']).days < 7) else g['date'].strftime('%d %b'))
    for g in A_[::-1]: rows.append(('gap', [nm(g), f"{g['bot']:,.2f}–{g['top']:,.2f}", glyph(g), odds(g, True)], g['col']))
    rows.append(('price', f"— {price:,.2f}"))
    for g in I_[:2]: rows.append(('gap', [nm(g), f"{g['bot']:,.2f}–{g['top']:,.2f}", glyph(g), odds(g, False)], g['col']))
    for g in B_: rows.append(('gap', [nm(g), f"{g['bot']:,.2f}–{g['top']:,.2f}", glyph(g), odds(g, False)], g['col']))
    if focus is not None and I_:
        pos = (focus['top'] - price) / (focus['top'] - focus['bot']) if role(focus) == 1 else (price - focus['bot']) / (focus['top'] - focus['bot'])
        hf = 0 if pos <= 0 else 1 if pos <= 0.5 else 2; side = ['back outside', 'near half, CE held', 'past CE'][hf]
        pb = {False: {0: (0.439, 0.342, 0.161), 1: (0.508, 0.448, 0.198), 2: (0.324, 0.241, 0.159)}, True: {0: (0.612, 0.506, 0.293), 1: (0.563, 0.567, 0.176), 2: (0.484, 0.538, 0.526)}}[W][focus['kind']][hf]
        rows.append(('warn', f"◐ IN {nm(focus)} · {side} · close here → {'4W' if W else '10D'} {100 * pb:.0f}%", AMB))
    x0, y0, wd, hh = 0.035, 0.92, 0.385, 0.027
    cw = [0.0, 0.125, 0.285, 0.31]
    for k, row in enumerate(rows):
        yy = y0 - k * hh; kind = row[0]
        bg = '#eef1f6' if kind in ('title', 'hdr', 'price') else '#ffffff'
        fig.patches.append(Rectangle((x0, yy - hh), wd, hh, transform=fig.transFigure, fc=bg, ec='#d5dae4', lw=0.6))
        if kind in ('title', 'price', 'warn'):
            fig.text(x0 + 0.006, yy - hh / 2, row[1], fontsize=7.6, color=row[2] if kind == 'warn' else '#131722', va='center', family='monospace')
        else:
            for j, txt in enumerate(row[1]):
                t, c = (txt if isinstance(txt, tuple) else (txt, None))
                colr = '#4a5163' if kind == 'hdr' else (row[2] if j == 0 else (c if j == 2 else '#131722'))
                fig.text(x0 + 0.006 + cw[j], yy - hh / 2, t, fontsize=7.6, color=colr, va='center', family='monospace', weight='bold' if j == 2 else None)
    fig.savefig(fname, facecolor='white'); print(fname, 'rows', len(rows), 'gaps', len(A_), len(I_), len(B_), 'focus', None if focus is None else focus['nm'])
scene(False, 15, 110, '/home/claude/mg3/Mangekyo_daily_15m.png', always=True)
scene(True, 60, 110, '/home/claude/mg3/Mangekyo_weekly_1h.png')
