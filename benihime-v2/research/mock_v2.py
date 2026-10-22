"""Benihime v2 mocks: the tally card with the fill bar (Desktop and Mobile), from NQ 1-minute data, computed the way
the Pine script does (gaps from 15-minute bars, live odds from the same model functions and constants).
python3 mock_v2.py OUTDIR"""
import sys, json
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plt.rcParams['font.family'] = 'DejaVu Sans'
OUT = sys.argv[1]
BG, MU, GRID, CHT = '#ffffff', '#9aa1b2', '#eef1f6', '#131722'
CB, CT, CS = '#161a23', '#d1d4dc', '#8a93a6'
UP, DN = '#089981', '#f23645'
COLN, COLX, COLY = '#26a69a', '#ff9800', '#7e57c2'
BU, BD = '#26a69a', '#ef5350'          # fill bar colours (inputs' defaults)
N1 = json.load(open('/home/claude/rg/news_dates.json'))
N2 = json.load(open('/home/claude/rg/news_dates2.json'))
MAJ = {'CPI': set(N1['cpi']), 'NFP': set(N1['nfp'])}
OTH = {'PPI': set(d.replace('-', '') for d in N2['ppi']), 'GDP': set(d.replace('-', '') for d in N2['gdp']),
       'PCE': set(d.replace('-', '') for d in N2['pce']), 'RETAIL': set(d.replace('-', '') for d in N2['rs'])}
BALL = pd.read_pickle('/home/claude/kyw/bars_NQ_all.pkl')
BALL = BALL[BALL.ts >= '2026-07-01'].set_index('ts')
SC1 = [87, 63, 45, 32, 18]; SO1 = [79, 40, 20, 12, 5]; W5F = [97, 86, 80, 73, 63]; W5C = [98, 93, 89, 84, 78]
BK = ['small', 'below avg', 'above avg', 'large', 'very large']
# ── the Pine model functions (same constants)
CKM = [0, 15, 30, 45, 60, 90, 120, 180, 240, 300, 360, 405]
FCK = [0.0, -0.514, -0.694, -0.884, -0.987, -1.245, -1.446, -1.779, -2.128, -2.595, -3.284, -3.801]
CCK = [0.0, -0.139, -0.258, -0.412, -0.519, -0.725, -0.882, -1.158, -1.499, -1.960, -2.718, -3.286]
cl = lambda v, a, b: max(a, min(b, v))
def ck(A, m):
    m = cl(m, 0, 405); i = 0
    while i < 10 and CKM[i + 1] <= m: i += 1
    f = (m - CKM[i]) / (CKM[i + 1] - CKM[i]); return A[i] * (1 - f) + A[i + 1] * f
sig = lambda z: 100 / (1 + np.exp(-z))
onlOr = lambda o: 0.705 if o is None or o != o else cl(o, 0, 1.2)
pFill = lambda mi, lr, d, r, o: sig(2.026 + ck(FCK, mi) - 1.071 * lr - 1.174 * cl(d, 0, 3) + 1.323 * cl(r, 0, 1) - 0.815 * onlOr(o))
pCE = lambda mi, lr, d, o: sig(2.523 + ck(CCK, mi) - 1.022 * lr - 1.389 * cl(d - 0.5, 0, 3) - 0.864 * onlOr(o))
pAfter = lambda lr, fm, o: sig(1.660 - 0.996 * lr - 0.296 * np.log(1 + max(0, fm)) - 0.662 * onlOr(o))
gauge = lambda f, n: '█' * int(round(cl(0 if f != f else f, 0, 1) * n)) + '░' * (n - int(round(cl(0 if f != f else f, 0, 1) * n)))
fillBar = lambda f: (lambda s: s[:5] + '│' + s[5:])(gauge(f, 10))
pc0 = lambda p: f'{round(p)}%'
sgn0 = lambda v: ('+' if v >= 0 else '−') + str(abs(round(v)))


def tag(d):
    k = d.strftime('%Y%m%d')
    t = [n for n, s in MAJ.items() if k in s] + [n for n, s in OTH.items() if k in s]
    return ' · '.join(t), any(k in s for s in MAJ.values())


def gaps(B, session):
    b = B if session == 'ETH' else B[(B.hm >= 930) & (B.hm < 1615)]
    x = b.resample('15min').agg(dict(Open='first', High='max', Low='min', Close='last', tday='first')).dropna()
    G, c16, prev = [], None, None
    for t, r in x.iterrows():
        if prev is not None:
            tp, rp = prev
            if tp.hour * 60 + tp.minute <= 974 < tp.hour * 60 + tp.minute + 15:
                c16 = rp.Close
        if t.hour * 60 + t.minute == 570 and c16 is not None:
            G.append(dict(day=r.tday, t0=t, O=r.Open, C=c16)); c16 = None
        prev = (t, r)
    G = pd.DataFrame(G)
    G['g'] = (G.O - G.C).abs()
    G['avg20'] = G.g.shift(1).rolling(20).mean()
    G = G.iloc[::-1].reset_index(drop=True).head(20)
    ce, fl = [], []
    for _, r in G.iterrows():
        a = b[b.index >= r.t0]
        up = r.O > r.C; m = (r.O + r.C) / 2
        hc = a[a.Low <= m] if up else a[a.High >= m]
        hf = a[a.Low <= r.C] if up else a[a.High >= r.C]
        ce.append(hc.index[0] if len(hc) else None); fl.append(hf.index[0] if len(hf) else None)
    G['ceT'] = pd.Series(ce, dtype=object).values
    G['flT'] = pd.Series(fl, dtype=object).values
    G['tag'] = [tag(d)[0] for d in G.day]
    G['maj'] = [tag(d)[1] for d in G.day]
    return G, b


def lum(h):
    return 0.299 * int(h[1:3], 16) + 0.587 * int(h[3:5], 16) + 0.114 * int(h[5:7], 16)


def state(G, b, B, NOW):
    """today's live numbers, as the card computes them"""
    r0 = G.iloc[0]
    O, C, g = r0.O, r0.C, r0.g; up = O > C
    a20 = r0.avg20; rr = g / a20; bk = 0 if rr < 0.5 else 1 if rr < 1 else 2 if rr < 1.5 else 3 if rr < 2.5 else 4
    lr = np.log(rr)
    d0 = r0.t0.normalize()
    on = B[(B.index >= d0 - pd.Timedelta(hours=6)) & (B.index < d0 + pd.Timedelta(hours=9, minutes=30))]
    onH, onL = on.High.max(), on.Low.min()
    onl = (O - onL) / (onH - onL) if up else (onH - O) / (onH - onL)
    today = b[b.index >= r0.t0]
    ex = today.Low.min() if up else today.High.max()
    retr = (O - ex) / g if up else (ex - O) / g
    px_ = today.Close.iloc[-1]
    dist = (px_ - C) / g if up else (C - px_) / g
    mins = (NOW - r0.t0).total_seconds() / 60
    top, bot = max(O, C), min(O, C)
    u1 = today[today.High >= top + g].index; s1 = today[today.Low <= bot - g].index
    fld = pd.notna(r0.flT); ceh = pd.notna(r0.ceT)
    fmin = (r0.flT - r0.t0).total_seconds() / 60 if fld else None
    return dict(O=O, C=C, g=g, up=up, a20=a20, rr=rr, bk=bk, lr=lr, onl=onl, onH=onH, onL=onL, retr=retr, dist=dist, mins=mins,
                top=top, bot=bot, u1=u1[0] if len(u1) else None, s1=s1[0] if len(s1) else None, fld=fld, ceh=ceh,
                flT=r0.flT, ceT=r0.ceT, fmin=fmin, px=px_,
                pF=None if fld else pFill(mins, lr, dist, retr, onl), pC=None if ceh else pCE(mins, lr, dist, onl),
                pF0=pFill(0, lr, 1, 0, onl), onE=pFill(0, lr, 1, 0, onl) - pFill(0, lr, 1, 0, 0.705),
                pOv=pAfter(lr, fmin, onl) if fld else SO1[bk])


def rows_desktop(G, s, bc):
    up = s['up']; bk = s['bk']; prog = 1.0 if s['fld'] else cl(s['retr'], 0, 1)
    ontx = ('at the ON high' if up else 'at the ON low') if s['onl'] >= 0.85 else ('upper half of ON' if up else 'lower half of ON') if s['onl'] >= 0.5 else ('lower half of ON' if up else 'upper half of ON')
    upTx = f"✓ {s['u1']:%H:%M}" if s['u1'] is not None else pc0(SC1[bk] if up else s['pOv'])
    dnTx = f"✓ {s['s1']:%H:%M}" if s['s1'] is not None else pc0(s['pOv'] if up else SC1[bk])
    ovT = s['s1'] if up else s['u1']
    px_ = s['px']
    o = G[[not pd.notna(v) for v in G.flT]].copy(); o['ce'] = (o.O + o.C) / 2
    ab = o[o.ce > px_].sort_values('ce').head(1); be = o[o.ce < px_].sort_values('ce', ascending=False).head(1)
    R = [('GAP', gauge(s['rr'] / 2.5, 10), 'hc', ('▲ ' if up else '▼ ') + f"{s['g']:,.2f} pts · {100 * s['g'] / s['C']:.2f}%", f"{s['rr']:.1f}× · {BK[bk]}", None),
         ('OPEN', gauge(s['onl'], 10), CS, ontx, f"fill {sgn0(s['onE'])}", None),
         ('FILL', fillBar(prog), bc, ('filled' if s['fld'] else f'{round(100 * prog)}% back') + f" · {s['C']:,.2f}", f"✓ {s['flT']:%H:%M}" if s['fld'] else f"{pc0(s['pF'])} by 16:14", BU if s['fld'] else None),
         ('CE', '', None, f"{(s['O'] + s['C']) / 2:,.2f}", f"✓ {s['ceT']:%H:%M}" if s['ceh'] else f"{pc0(s['pC'])} by 16:14", BU if s['ceh'] else None),
         ('±1 SD', '', None, f'▲ {upTx} · ▼ {dnTx}', 'after fill' if s['fld'] and ovT is None else 'by 16:14', None),
         ('5 SESS', '', None, f'fill {W5F[bk]}% · CE {W5C[bk]}%', 'staircase', None),
         ('AVG', '', None, f"20 sessions · {s['a20']:,.2f} pts", f"{100 * s['a20'] / s['C']:.2f}%", None),
         ('ABOVE', '', None, f'CE {ab.ce.iloc[0]:,.2f}' if len(ab) else 'no open gap', f'{ab.day.iloc[0]:%m/%d}' if len(ab) else '', None),
         ('BELOW', '', None, f'CE {be.ce.iloc[0]:,.2f}' if len(be) else 'no open gap', f'{be.day.iloc[0]:%m/%d}' if len(be) else '', None)]
    return R


def rows_mobile(s, bc):
    up = s['up']; bk = s['bk']; prog = 1.0 if s['fld'] else cl(s['retr'], 0, 1)
    upTx = f"✓{s['u1']:%H:%M}" if s['u1'] is not None else pc0(SC1[bk] if up else s['pOv'])
    dnTx = f"✓{s['s1']:%H:%M}" if s['s1'] is not None else pc0(s['pOv'] if up else SC1[bk])
    return [('GAP', gauge(s['rr'] / 2.5, 5), 'hc', '', ('▲ ' if up else '▼ ') + f"{s['g']:,.2f} · {s['rr']:.1f}×", None),
            ('FILL', fillBar(prog), bc, '', f"✓ {s['flT']:%H:%M}" if s['fld'] else pc0(s['pF']), BU if s['fld'] else None),
            ('CE', '', None, '', f"✓ {s['ceT']:%H:%M}" if s['ceh'] else pc0(s['pC']), BU if s['ceh'] else None),
            ('±1 SD', '', None, '', f'▲ {upTx} ▼ {dnTx}', None)]


def card(fig, x0, y0, head, rows, col, w, cx, fs=8.2, lh=0.027, cw=0.0040):
    """cx = x offsets of the gauge and value columns (from x0)"""
    ht = '#131722' if lum(col) > 165 else '#ffffff'
    fig.patches.append(Rectangle((x0, y0 - lh), w, lh, transform=fig.transFigure, fc=col, ec='none', zorder=10))
    fig.text(x0 + 0.006, y0 - lh / 2, head[0], color=ht, fontsize=fs + 0.3, family='DejaVu Sans Mono', va='center', weight='bold', zorder=11)
    fig.text(x0 + cx[0], y0 - lh / 2, head[1], color=ht, fontsize=fs + 0.3, family='DejaVu Sans Mono', va='center', weight='bold', zorder=11)
    if head[2]:
        fig.text(x0 + cx[1], y0 - lh / 2, head[2], color=ht, fontsize=fs + 0.3, family='DejaVu Sans Mono', va='center', zorder=11)
    pw = 0.012 + cw * len(head[3])
    fig.patches.append(Rectangle((x0 + w - pw - 0.004, y0 - lh + 0.004), pw, lh - 0.008, transform=fig.transFigure, fc='#131722' if lum(col) > 165 else '#ffffff', ec='none', zorder=11))
    fig.text(x0 + w - pw / 2 - 0.004, y0 - lh / 2, head[3], color=col, fontsize=fs, family='DejaVu Sans Mono', va='center', ha='center', weight='bold', zorder=12)
    for k, (key, gs, gc, v, rt, wbg) in enumerate(rows):
        yy = y0 - lh * (k + 2)
        fig.patches.append(Rectangle((x0, yy), w, lh, transform=fig.transFigure, fc=CB, ec='none', zorder=10))
        fig.text(x0 + 0.006, yy + lh / 2, key, color=CS, fontsize=fs, family='DejaVu Sans Mono', va='center', zorder=11)
        if gs:
            fig.text(x0 + cx[0], yy + lh / 2, gs, color=col if gc == 'hc' else gc, fontsize=fs, family='DejaVu Sans Mono', va='center', zorder=11)
        if v:
            fig.text(x0 + cx[1], yy + lh / 2, v, color=CT, fontsize=fs, family='DejaVu Sans Mono', va='center', zorder=11)
        if wbg:
            tw = cw * len(rt) + 0.008
            fig.patches.append(Rectangle((x0 + w - tw, yy), tw, lh, transform=fig.transFigure, fc=wbg, ec='none', zorder=11))
        fig.text(x0 + w - 0.005, yy + lh / 2, rt, color=('#131722' if lum(wbg) > 165 else '#ffffff') if wbg else CT, fontsize=fs, family='DejaVu Sans Mono', va='center', ha='right', zorder=12, weight='bold' if wbg else 'normal')
    fig.patches.append(Rectangle((x0, y0 - lh * (len(rows) + 1)), w, lh * (len(rows) + 1), transform=fig.transFigure, fc='none', ec=col, lw=1, zorder=12))


def chart(fig, ax_rect, x, G, xr_pad=1.24, ypad=0.1, session='ETH', ticks_mode='eth', show_lbl=True):
    ax = fig.add_axes(ax_rect)
    for s_ in ax.spines.values():
        s_.set_visible(False)
    ax.set_facecolor(BG); ax.yaxis.tick_right(); ax.tick_params(axis='y', colors=MU, labelsize=8); ax.tick_params(axis='x', length=0)
    ax.grid(color=GRID, lw=0.7, zorder=0)
    n = len(x); w = 0.6
    ix = lambda t: float(np.searchsorted(x.index, t))
    for i, (t, q) in enumerate(x.iterrows()):
        c = UP if q.Close >= q.Open else DN
        ax.plot([i, i], [q.Low, q.High], color=c, lw=0.6, zorder=4)
        ax.add_patch(Rectangle((i - w / 2, min(q.Open, q.Close)), w, max(abs(q.Close - q.Open), 0.25), fc=c, ec=c, lw=0.2, zorder=5))
    xr = n - 1 + max(6, n // 120)
    A20 = G.iloc[0].avg20
    LBL = []

    def place(y, tx, col):
        hit = [k for k, (yy, _, _) in enumerate(LBL) if abs(yy - y) <= 0.1 * A20]
        if hit:
            LBL[hit[0]] = (LBL[hit[0]][0], LBL[hit[0]][1] + '\n' + tx, LBL[hit[0]][2])
        else:
            LBL.append((y, tx, col))
    for i, r in G.iterrows():
        base = COLX if r.maj else COLY if r.tag else COLN
        al = 1.0 if i < 5 else 0.55 if i < 10 else 0.35
        if pd.notna(r.flT):
            al *= 0.6
        x1 = max(ix(r.t0), -1)
        top, bot, g = max(r.O, r.C), min(r.O, r.C), r.g
        L = lambda y, ls='-', a=al, lw=1.0: ax.plot([x1, xr], [y, y], color=base, lw=lw, ls=ls, alpha=a, zorder=3)
        L(top); L(bot); L((top + bot) / 2, '--')
        if i < 5:
            ax.add_patch(Rectangle((x1, bot), xr - x1, g, fc=base, alpha=0.08 * (0.6 if pd.notna(r.flT) else 1), ec='none', zorder=1))
            for k in range(1, 8):
                if k != 4:
                    L(bot + k * g / 8, ':', al * (0.65 if k % 2 == 0 else 0.35), 0.8)
            s = ' · filled' if pd.notna(r.flT) else ' · CE' if pd.notna(r.ceT) else ''
            if show_lbl:
                place((top + bot) / 2, f'RTH {r.day:%m/%d}' + (f' · {r.tag}' if r.tag else '') + s, CHT)
        elif i < 10:
            L(bot + g / 4, ':', al * 0.65, 0.8); L(bot + 3 * g / 4, ':', al * 0.65, 0.8)
        if i < 5 or r.tag:
            L(top + g, (0, (6, 3)), al, 1.2); L(bot - g, (0, (6, 3)), al, 1.2)
            L(top + 2 * g, '-', al, 1.2); L(bot - 2 * g, '-', al, 1.2)
            dn = r.day.strftime('%a') + ('' if i < 5 else ' ' + r.day.strftime('%m/%d')) + (' ' + r.tag if r.tag else '')
            if show_lbl:
                place(top + 2 * g, dn + ' +2 SD', base); place(bot - 2 * g, dn + ' −2 SD', base)
    for y, tx, col in LBL:
        ax.text(n + max(7, n // 110), y, tx, color=col, fontsize=7.2, va='center', zorder=8, clip_on=True, linespacing=1.3, weight='bold' if col != CHT else 'normal')
    if ticks_mode == 'eth':
        ticks = [i for i, t in enumerate(x.index) if t.minute == 0 and t.hour % 2 == 0]
        lab = [x.index[i].strftime('%H:%M') for i in ticks]
    else:
        ticks = [i for i, t in enumerate(x.index) if (t.minute == 0 and t.hour in (11, 13, 15)) or (t.hour == 9 and t.minute == 30)]
        lab = [x.index[i].strftime('%a %d') if x.index[i].hour == 9 else x.index[i].strftime('%H:%M') for i in ticks]
    ax.set_xticks(ticks); ax.set_xticklabels(lab, color=MU, fontsize=8)
    lo, hi = x.Low.min(), x.High.max()
    ax.set_xlim(-2, n * xr_pad); ax.set_ylim(lo - (hi - lo) * ypad, hi + (hi - lo) * ypad)
    return ax


def desktop(NOW, session, start, barmode, fname, title, sub, ypad=0.1):
    B = BALL[BALL.index < NOW]
    G, b = gaps(B, session)
    s = state(G, b, B, NOW)
    bc = (BU if s['fld'] else BD) if barmode == 'Progress' else (BU if s['up'] else BD)
    x = b[b.index >= start][['Open', 'High', 'Low', 'Close']]
    fig = plt.figure(figsize=(18, 10.4), dpi=100, facecolor=BG)
    chart(fig, [0.02, 0.05, 0.60, 0.85], x, G, ypad=ypad, ticks_mode='eth' if session == 'ETH' else 'rth')
    tg, mj = tag(G.iloc[0].day)
    col = COLX if mj else COLY if tg else COLN
    card(fig, 0.648, 0.885, ('BENIHIME', 'RTH GAP', f'{G.iloc[0].day:%m/%d} · {NOW:%H:%M} ET', tg or 'NORMAL'), rows_desktop(G, s, bc), col, 0.272, (0.042, 0.091))
    fig.text(0.02, 0.955, title, color=CHT, fontsize=13, weight='bold')
    fig.text(0.02, 0.928, sub, color='#5d6476', fontsize=9)
    plt.savefig(f'{OUT}/{fname}', dpi=100, facecolor=BG); plt.close(fig)
    print(fname, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items() if k in ('rr', 'onl', 'retr', 'dist', 'mins', 'pF', 'pC', 'pF0', 'onE', 'pOv', 'fmin')})
    return s


def mobile(fname, title):
    fig = plt.figure(figsize=(12, 10.4), dpi=100, facecolor=BG)
    for k, (NOW, start, lab) in enumerate(((pd.Timestamp('2026-10-08 10:30'), pd.Timestamp('2026-10-08 08:00'), 'live, 10:30 ET'),
                                          (pd.Timestamp('2026-10-09 08:45'), pd.Timestamp('2026-10-08 13:00'), 'pre-market, 08:45 ET'))):
        B = BALL[BALL.index < NOW]
        G, b = gaps(B, 'ETH')
        x0 = 0.03 + k * 0.5
        fig.patches.append(Rectangle((x0 - 0.01, 0.03), 0.44, 0.9, transform=fig.transFigure, fc='none', ec='#c9ced8', lw=1.5, zorder=0))
        fig.text(x0, 0.905, lab, color='#5d6476', fontsize=9.5)
        x = b[b.index >= start][['Open', 'High', 'Low', 'Close']]
        chart(fig, [x0, 0.06, 0.37, 0.6], x, G, xr_pad=1.05, ypad=0.12, show_lbl=False)
        if k == 0:
            s = state(G, b, B, NOW)
            rows = rows_mobile(s, BU if s['up'] else BD)
            head = ('BENIHIME', f'{G.iloc[0].day:%m/%d} {NOW:%H:%M}', '', 'NORMAL')
            tg, mj = tag(G.iloc[0].day)
        else:
            # outside RTH: the 16:14 close, if it opened now, the next session
            c16 = b[(b.index.hour == 16) & (b.index.minute == 14)].Close.iloc[-1]
            px_ = x.Close.iloc[-1]; g0 = px_ - c16
            a20 = (G.g.iloc[:20]).mean(); rr = abs(g0) / a20
            on = B[(B.index >= NOW.normalize() - pd.Timedelta(hours=6))]
            H, L = max(on.High.max(), px_), min(on.Low.min(), px_)
            onl = (px_ - L) / (H - L) if g0 > 0 else (H - px_) / (H - L)
            pif = pFill(0, np.log(rr), 1, 0, onl)
            nd = NOW.normalize(); tg, mj = tag(nd)
            rows = [('CLOSE', '', None, '', f'16:14 {c16:,.2f}', None),
                    ('IF NOW', gauge(rr / 2.5, 5), 'hc', '', ('▲ ' if g0 >= 0 else '▼ ') + f'{abs(g0):,.2f} · fill {pc0(pif)}', None),
                    ('NEXT', '', None, '', (tg + ' 08:30') if tg else 'normal', None)]
            head = ('BENIHIME', f'{nd:%m/%d} {NOW:%H:%M}', '', tg or 'NORMAL')
            print('pre-market', round(g0, 2), round(rr, 2), round(onl, 2), round(pif, 1))
        col = COLX if mj else COLY if tg else COLN
        card(fig, x0 + 0.19, 0.875, head, rows, col, 0.235, (0.063, 0.1), fs=8.6, lh=0.034, cw=0.006)
    fig.text(0.03, 0.955, title, color=CHT, fontsize=13, weight='bold')
    plt.savefig(f'{OUT}/{fname}', dpi=100, facecolor=BG); plt.close(fig)


desktop(pd.Timestamp('2026-10-08 10:30'), 'ETH', pd.Timestamp('2026-10-07 13:00'), 'Gap direction', 'Benihime_v2_live_1m.png',
        'Benihime · NQ1! 1-minute ETH: Thu 8 Oct 2026 at 10:30 ET · the tally card with the fill bar',
        'Today\'s ▼ gap has come 83% of the way back (CE ✓ 10:22), 24% of a gap from the fill. The FILL bar takes the gap\'s colour (▼ red). '
        'Odds: size, time, distance now, retracement so far, open vs the overnight range. NQ data; TradingView will differ.', 0.1)
desktop(pd.Timestamp('2026-09-24 13:00'), 'RTH', pd.Timestamp('2026-09-23 09:30'), 'Progress', 'Benihime_v2_filled_RTH.png',
        'Benihime · NQ1! 1-minute RTH: Thu 24 Sep 2026 at 13:00 ET · filled, "Progress" bar colour',
        'The ▼ gap filled at 12:40: the bar turns green and the cell reads ✓ 12:40. The side beyond the prior close now shows the odds after the fill '
        '(a later fill goes less far). RTH chart. TradingView will differ.', 0.08)
mobile('Benihime_v2_Mobile.png', 'Benihime · Mobile layout: live (Thu 8 Oct, 10:30 ET) and pre-market (Fri 9 Oct, 08:45 ET)')
