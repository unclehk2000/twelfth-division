"""Benihime v3 mocks, from 1-minute data, computed the way the Pine script does: today's ORG graded like Zabimaru's opening range
(±0.5 SD), this week's ORG CEs named and carried (last week's Monday and Friday dashed), RTH-only 1-hour structure (swings, shifts,
flip, yesterday's RTH high / low), CE ✓ / fill ✓ labels with the sisters, and the v3 card (triplet, sisters in the fill odds, ICT's
CE by 10:00, week CE, RTH 1H). python3 mock_v3.py OUTDIR"""
import sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plt.rcParams['font.family'] = 'DejaVu Sans'
OUT = sys.argv[1]
BG, MU, GRID, CHT = '#ffffff', '#9aa1b2', '#eef1f6', '#131722'
CB, CT, CS = '#161a23', '#d1d4dc', '#8a93a6'
UP, DN = '#089981', '#f23645'
COLN, COLX, COLY, WK, MU_, MD_, PDC = '#26a69a', '#ff9800', '#7e57c2', '#9c27b0', '#089981', '#f23645', '#2962ff'
BU, BD = '#26a69a', '#ef5350'
BAR = {s: pd.read_pickle(f'/home/claude/kyw/bars_{s}_all.pkl') for s in ('NQ', 'ES', 'RTY')}
for s in BAR: BAR[s] = BAR[s][BAR[s].ts >= '2026-08-15'].set_index('ts')
SC1 = [87, 63, 45, 32, 18]; SO1 = [79, 40, 20, 12, 5]; W5F = [97, 86, 80, 73, 63]; W5C = [98, 93, 89, 84, 78]
BK = ['small', 'below avg', 'above avg', 'large', 'very large']
CKM = [0, 15, 30, 45, 60, 90, 120, 180, 240, 300, 360, 405]
FCK = [0.0, -0.527, -0.713, -0.907, -1.011, -1.274, -1.478, -1.816, -2.168, -2.639, -3.329, -3.85]
CCK = [0.0, -0.139, -0.258, -0.412, -0.519, -0.725, -0.882, -1.158, -1.499, -1.960, -2.718, -3.286]
cl = lambda v, a, b: max(a, min(b, v))
def ck(A, m):
    m = cl(m, 0, 405); i = 0
    while i < 10 and CKM[i + 1] <= m: i += 1
    f = (m - CKM[i]) / (CKM[i + 1] - CKM[i]); return A[i] * (1 - f) + A[i + 1] * f
sig = lambda z: 100 / (1 + np.exp(-z))
onlOr = lambda o: 0.705 if o is None or o != o else cl(o, 0, 1.2)
pFill = lambda mi, lr, d, r, o, ns=0: sig(2.039 + ck(FCK, mi) - 1.051 * lr - 1.186 * cl(d, 0, 3) + 1.243 * cl(r, 0, 1) - 0.814 * onlOr(o) + 0.119 * ns)
pCE = lambda mi, lr, d, o: sig(2.523 + ck(CCK, mi) - 1.022 * lr - 1.389 * cl(d - 0.5, 0, 3) - 0.864 * onlOr(o))
pCE10 = lambda mi, lr, d, o: None if mi >= 30 else sig(2.016 - 0.0576 * cl(mi, 0, 30) - 1.255 * lr - 2.616 * cl(d - 0.5, 0, 3) - 1.028 * onlOr(o))
pAfter = lambda lr, fm, o: sig(1.660 - 0.996 * lr - 0.296 * np.log(1 + max(0, fm)) - 0.662 * onlOr(o))
gauge = lambda f, n: '█' * int(round(cl(0 if f != f else f, 0, 1) * n)) + '░' * (n - int(round(cl(0 if f != f else f, 0, 1) * n)))
fillBar = lambda f: (lambda s: s[:5] + '│' + s[5:])(gauge(f, 10))
pc0 = lambda p: '—' if p is None else f'{round(p)}%'
sgn0 = lambda v: ('+' if v >= 0 else '−') + str(abs(round(v)))
fmt = lambda v, t=0.25: f'{np.floor(v / t + 0.5) * t:,.2f}'
wkOf = lambda d: (d - pd.Timedelta(days=d.dayofweek)).normalize()


def gaps(B):
    """RTH gaps from 15-minute bars (the 16:00 bar's close, the 09:30 bar's open), newest first, 20 kept"""
    x = B.resample('15min').agg(dict(Open='first', High='max', Low='min', Close='last', tday='first')).dropna()
    G, c16, prev = [], None, None
    for t, r in x.iterrows():
        if prev is not None:
            tp, rp = prev
            if tp.hour * 60 + tp.minute <= 974 < tp.hour * 60 + tp.minute + 15: c16 = rp.Close
        if t.hour * 60 + t.minute == 570 and c16 is not None:
            G.append(dict(day=pd.Timestamp(r.tday), t0=t, O=r.Open, C=c16)); c16 = None
        prev = (t, r)
    G = pd.DataFrame(G); G['g'] = (G.O - G.C).abs(); G['avg20'] = G.g.shift(1).rolling(20).mean()
    G = G.iloc[::-1].reset_index(drop=True).head(10)
    ce, fl = [], []
    for _, r in G.iterrows():
        a = B[B.index >= r.t0]; up = r.O > r.C; m = (r.O + r.C) / 2
        hc = a[a.Low <= m] if up else a[a.High >= m]; hf = a[a.Low <= r.C] if up else a[a.High >= r.C]
        ce.append(hc.index[0] if len(hc) else None); fl.append(hf.index[0] if len(hf) else None)
    G['ceT'] = pd.Series(ce, dtype=object).values; G['flT'] = pd.Series(fl, dtype=object).values
    return G


def sister(sym, day, NOW):
    """[has a gap, O, C, CE time, fill time, 20-session average] today, minute-exact (chart timeframe)"""
    D = pd.read_pickle(f'/home/claude/coc/days_{sym}.pkl').set_index('tday')
    if day not in D.index or pd.isna(D.loc[day].pc): return (False, None, None, None, None, None)
    r = D.loc[day]; b = BAR[sym]; b = b[(b.tday == day) & (b.hm >= 930) & (b.hm <= 1614) & (b.index < NOW)]
    ce = (r.op + r.pc) / 2
    e = b[b.Low <= ce] if r.op > r.pc else b[b.High >= ce]; f = b[b.Low <= r.pc] if r.op > r.pc else b[b.High >= r.pc]
    return (True, r.op, r.pc, e.index[0] if len(e) else None, f.index[0] if len(f) else None, r.avg20)


def rth_structure(B, NOW):
    """RTH-only 1-hour candles from 09:30; the script's rule on finished candles: swings (2 either side), shifts by a close,
    flip, yesterday's RTH high / low"""
    b = B[(B.hm >= 930) & (B.hm <= 1614)].copy()
    b['k'] = (b.index.hour * 60 + b.index.minute - 570) // 60
    c = b.groupby(['tday', 'k']).agg(o=('Open', 'first'), h=('High', 'max'), l=('Low', 'min'), c=('Close', 'last')).reset_index()
    c['t'] = pd.to_datetime(c.tday) + pd.to_timedelta(570 + 60 * c.k, unit='m')
    c['end'] = c.t + pd.Timedelta(minutes=60); c.loc[c.k == 6, 'end'] = c.t + pd.Timedelta(minutes=45)
    c = c[c.end <= NOW].reset_index(drop=True)          # finished candles only
    sw, ms = [], []; sH = sL = None; st = 0
    for i in range(len(c)):
        j = i - 2
        if j >= 2 and c.h[j] > max(c.h[j - 1], c.h[j - 2]) and c.h[j] > max(c.h[j + 1], c.h[j + 2]):
            sH = (c.t[j], c.h[j]); sw.append((c.t[j], c.h[j], 'H'))
        if j >= 2 and c.l[j] < min(c.l[j - 1], c.l[j - 2]) and c.l[j] < min(c.l[j + 1], c.l[j + 2]):
            sL = (c.t[j], c.l[j]); sw.append((c.t[j], c.l[j], 'L'))
        if sH and c.c[i] > sH[1] and st != 1:
            st = 1; ms.append((sH[0], c.t[i], sH[1], 1)); sH = None
        elif sL and c.c[i] < sL[1] and st != -1:
            st = -1; ms.append((sL[0], c.t[i], sL[1], -1)); sL = None
    flip = sL if st == 1 else sH if st == -1 else None
    days = sorted(c.tday.unique()); today = B.tday.iloc[-1]
    prev = [d for d in days if d < today]
    y = c[c.tday == prev[-1]] if prev else None
    return dict(c=c, sw=sw, ms=ms, st=st, flip=flip, pdh=y.h.max() if y is not None else None, pdl=y.l.min() if y is not None else None)


def lum(h): return 0.299 * int(h[1:3], 16) + 0.587 * int(h[3:5], 16) + 0.114 * int(h[5:7], 16)


def card(fig, x0, y0, head, rows, col, w, cx, fs=8.0, lh=0.0245, cw=0.0040):
    ht = '#131722' if lum(col) > 165 else '#ffffff'
    fig.patches.append(Rectangle((x0, y0 - lh), w, lh, transform=fig.transFigure, fc=col, ec='none', zorder=10))
    fig.text(x0 + 0.006, y0 - lh / 2, head[0], color=ht, fontsize=fs + 0.3, family='DejaVu Sans Mono', va='center', weight='bold', zorder=11)
    fig.text(x0 + cx[0], y0 - lh / 2, head[1], color=ht, fontsize=fs + 0.3, family='DejaVu Sans Mono', va='center', weight='bold', zorder=11)
    if head[2]: fig.text(x0 + cx[1], y0 - lh / 2, head[2], color=ht, fontsize=fs + 0.3, family='DejaVu Sans Mono', va='center', zorder=11)
    pw = 0.012 + cw * len(head[3])
    fig.patches.append(Rectangle((x0 + w - pw - 0.004, y0 - lh + 0.004), pw, lh - 0.008, transform=fig.transFigure, fc='#131722' if lum(col) > 165 else '#ffffff', ec='none', zorder=11))
    fig.text(x0 + w - pw / 2 - 0.004, y0 - lh / 2, head[3], color=col, fontsize=fs, family='DejaVu Sans Mono', va='center', ha='center', weight='bold', zorder=12)
    for k, (key, gs, gc, v, rt, wbg, vc) in enumerate(rows):
        yy = y0 - lh * (k + 2)
        fig.patches.append(Rectangle((x0, yy), w, lh, transform=fig.transFigure, fc=CB, ec='none', zorder=10))
        fig.text(x0 + 0.006, yy + lh / 2, key, color=CS, fontsize=fs, family='DejaVu Sans Mono', va='center', zorder=11)
        if gs: fig.text(x0 + cx[0], yy + lh / 2, gs, color=col if gc == 'hc' else gc, fontsize=fs, family='DejaVu Sans Mono', va='center', zorder=11)
        tc = vc or CT
        if v: fig.text(x0 + cx[1], yy + lh / 2, v, color=tc, fontsize=fs, family='DejaVu Sans Mono', va='center', zorder=11)
        if wbg:
            tw = cw * len(rt) + 0.008
            fig.patches.append(Rectangle((x0 + w - tw, yy), tw, lh, transform=fig.transFigure, fc=wbg, ec='none', zorder=11))
        fig.text(x0 + w - 0.005, yy + lh / 2, rt, color=('#131722' if lum(wbg) > 165 else '#ffffff') if wbg else tc, fontsize=fs, family='DejaVu Sans Mono', va='center', ha='right', zorder=12, weight='bold' if wbg else 'normal')
    fig.patches.append(Rectangle((x0, y0 - lh * (len(rows) + 1)), w, lh * (len(rows) + 1), transform=fig.transFigure, fc='none', ec=col, lw=1, zorder=12))


def build(NOW, view):
    """everything the script computes at NOW on NQ; view = '1m' (ETH 1-minute) or '1h' (RTH 1-hour)"""
    B = BAR['NQ'][BAR['NQ'].index < NOW]
    G = gaps(B); r0 = G.iloc[0]; today = r0.day
    O, C, g = r0.O, r0.C, r0.g; up = O > C; a20 = r0.avg20; rr = g / a20
    bk = 0 if rr < 0.5 else 1 if rr < 1 else 2 if rr < 1.5 else 3 if rr < 2.5 else 4; lr = np.log(rr)
    d0 = r0.t0.normalize()
    on = B[(B.index >= d0 - pd.Timedelta(hours=6)) & (B.index < d0 + pd.Timedelta(hours=9, minutes=30))]
    onl = (O - on.Low.min()) / (on.High.max() - on.Low.min()) if up else (on.High.max() - O) / (on.High.max() - on.Low.min())
    td = B[B.index >= r0.t0]; ex = td.Low.min() if up else td.High.max(); retr = (O - ex) / g if up else (ex - O) / g
    px_ = td.Close.iloc[-1]; dist = (px_ - C) / g if up else (C - px_) / g; mins = (NOW - r0.t0).total_seconds() / 60
    top, bot = max(O, C), min(O, C)
    u1 = td[td.High >= top + g].index; s1 = td[td.Low <= bot - g].index
    fld, ceh = pd.notna(r0.flT), pd.notna(r0.ceT)
    S = {s: sister(s, today, NOW) for s in ('NQ', 'ES', 'RTY')}
    ns = sum(1 for s in ('ES', 'RTY') if S[s][0] and S[s][4] is not None and S[s][4] <= td.index[-1])
    st = dict(O=O, C=C, g=g, up=up, a20=a20, rr=rr, bk=bk, lr=lr, onl=onl, retr=retr, dist=dist, mins=mins, top=top, bot=bot, px=px_,
              u1=u1[0] if len(u1) else None, s1=s1[0] if len(s1) else None, fld=fld, ceh=ceh, flT=r0.flT, ceT=r0.ceT, ns=ns,
              pF=None if fld else pFill(mins, lr, dist, retr, onl, ns), pF00=None if fld else pFill(mins, lr, dist, retr, onl, 0),
              pC=None if ceh else pCE(mins, lr, dist, onl), pC10=None if ceh else pCE10(mins, lr, dist, onl),
              pF0=pFill(0, lr, 1, 0, onl), onE=pFill(0, lr, 1, 0, onl) - pFill(0, lr, 1, 0, 0.705),
              pOv=pAfter(lr, (r0.flT - r0.t0).total_seconds() / 60, onl) if fld else SO1[bk])
    R = rth_structure(B, NOW)
    cw = wkOf(today)
    W = []
    for i, r in G.iterrows():
        tag = r.day.strftime('%a') if wkOf(r.day) == cw else ('last ' + r.day.strftime('%a')) if wkOf(r.day) == cw - pd.Timedelta(days=7) and r.day.dayofweek in (0, 4) else ''
        W.append(tag)
    G['wk'] = W
    return dict(B=B, G=G, st=st, S=S, R=R, today=today, NOW=NOW)


def draw(fig, rect, x, M, xpad, label_x, evlbl=True, title_dates=False, prevSD=True):
    G, st, R, S = M['G'], M['st'], M['R'], M['S']
    ax = fig.add_axes(rect)
    for s_ in ax.spines.values(): s_.set_visible(False)
    ax.set_facecolor(BG); ax.yaxis.tick_right(); ax.tick_params(axis='y', colors=MU, labelsize=8); ax.tick_params(axis='x', length=0); ax.grid(color=GRID, lw=0.7, zorder=0)
    n = len(x); w = 0.6 if n > 200 else 0.62
    ix = lambda t: float(np.searchsorted(x.index, t))
    for i, (t, q) in enumerate(x.iterrows()):
        c = UP if q.c >= q.o else DN
        ax.plot([i, i], [q.l, q.h], color=c, lw=0.6 if n > 200 else 0.9, zorder=4)
        ax.add_patch(Rectangle((i - w / 2, min(q.o, q.c)), w, max(abs(q.c - q.o), 0.25), fc=c, ec=c, lw=0.2, zorder=5))
    xr = n - 1 + xpad
    LBL = []; thr = 0.1 * G.iloc[0].avg20
    def place(y, tx, col, bold=False):
        hit = [k for k, (yy, _, _, _) in enumerate(LBL) if abs(yy - y) <= thr]
        if hit: LBL[hit[0]] = (LBL[hit[0]][0], LBL[hit[0]][1] + '\n' + tx, LBL[hit[0]][2], LBL[hit[0]][3])
        else: LBL.append((y, tx, col, bold))
    lo_v, hi_v = x.l.min(), x.h.max()
    for i, r in G.iterrows():
        base = COLN
        al = 1.0 if i < 5 else 0.55 if i < 10 else 0.35
        if pd.notna(r.flT): al *= 0.6
        x1 = max(ix(r.t0), -1)
        top, bot, g = max(r.O, r.C), min(r.O, r.C), r.g
        feat = i == 0
        L = lambda y, ls='-', a=al, lw=1.0, col=base: ax.plot([x1, xr], [y, y], color=col, lw=lw, ls=ls, alpha=a, zorder=3)
        L(top, lw=2 if feat else 1); L(bot, lw=2 if feat else 1)
        ce = (top + bot) / 2
        if r.wk:
            thisW = not r.wk.startswith('last')
            L(ce, '-' if thisW else (0, (5, 3)), 1.0 if thisW else 0.75, 2 if thisW else 1, WK)
            kc = r.ceT
            place(ce, f"{r.wk} ORG CE {fmt(ce)}" + (f" ✓ {kc:%a %H:%M}" if pd.notna(kc) else '') + (' · filled' if pd.notna(r.flT) else ''), WK, True)
        else:
            L(ce, '--', lw=2 if feat else 1)
            if i < 5: place(ce, f'RTH {r.day:%m/%d}' + (' · filled' if pd.notna(r.flT) else ' · CE' if pd.notna(r.ceT) else ''), CHT)
        if i == 0:
            ax.add_patch(Rectangle((x1, bot), xr - x1, g, fc=base, alpha=0.08 * (0.6 if pd.notna(r.flT) else 1), ec='none', zorder=1))
        if feat:
            for k in range(1, 8):
                if k != 4: L(bot + k * g / 8, '-' if k % 2 == 0 else ':', al * (0.85 if k % 2 == 0 else 0.45), 1.0)
            for k_, nm in ((0.5, '+0.5 SD'), (-0.5, '−0.5 SD')):
                y = top + k_ * g if k_ > 0 else bot + k_ * g
                L(y, ':', al, 1.0); place(y, f"{r.day:%a} {nm}", base)
            place(r.O, f"{r.day:%a} ORG 09:30 open {fmt(r.O)} · {'premium' if r.O > r.C else 'discount'}", base)
            place(r.C, f"{r.day:%a} ORG close (16:14) {fmt(r.C)}", base)
        elif 5 <= i < 10:
            L(bot + g / 4, ':', al * 0.65, 0.8); L(bot + 3 * g / 4, ':', al * 0.65, 0.8)
        if i < 5 and (i == 0 or prevSD):
            L(top + g, (0, (6, 3)), al, 1.2); L(bot - g, (0, (6, 3)), al, 1.2); L(top + 2 * g, '-', al, 1.2); L(bot - 2 * g, '-', al, 1.2)
            place(top + 2 * g, f"{r.day:%a} +2 SD", base); place(bot - 2 * g, f"{r.day:%a} −2 SD", base)
    # RTH-only structure
    for t, p, k in R['sw'][-12:]:
        if t >= x.index[0]:
            ax.annotate('▼' if k == 'H' else '▲', (ix(t), p), xytext=(0, 4 if k == 'H' else -11), textcoords='offset points', ha='center', fontsize=7.5, color=MD_ if k == 'H' else MU_, zorder=7)
    for t0, t1, lv, dr in R['ms'][-3:]:
        if t1 >= x.index[0]:
            a, b_ = max(ix(t0), 0), ix(t1)
            ax.plot([a, b_], [lv, lv], color=MU_ if dr > 0 else MD_, lw=1.1, ls='--', zorder=6)
            ax.text(b_, lv, 'RTH MSS ' + ('▲' if dr > 0 else '▼'), color=MU_ if dr > 0 else MD_, fontsize=7.4, ha='center', va='bottom' if dr > 0 else 'top', zorder=7, weight='bold')
    if R['flip']:
        ft, fv = R['flip']
        ax.plot([max(ix(ft), 0), xr], [fv, fv], color=MU_ if R['st'] == 1 else MD_, lw=1, ls=':', zorder=3)
        ms_ = R['ms'][-1] if R['ms'] else None
        place(fv, f"RTH {'▲' if R['st'] == 1 else '▼'}" + (f" since {ms_[1]:%m/%d %H:%M}" if ms_ else '') + f" · flip {fmt(fv)}", MU_ if R['st'] == 1 else MD_)
    d0 = ix(M['today'] - pd.Timedelta(hours=6))
    for v, nm in ((R['pdh'], 'RTH PDH'), (R['pdl'], 'RTH PDL')):
        if v is not None:
            ax.plot([max(d0, 0), xr], [v, v], color=PDC, lw=0.9, ls=':', zorder=3); place(v, f'{nm} {fmt(v)}', PDC)
    # CE ✓ / fill ✓ with the sisters
    if evlbl:
        for key, lvl, nm, fill in (('ceT', (st['O'] + st['C']) / 2, 'CE', False), ('flT', st['C'], 'fill', True)):
            t = st[key]
            if pd.notna(t) and t >= x.index[0]:
                ss = ''
                for s in ('ES', 'RTY'):
                    ok, o_, c_, tc, tf, a_ = S[s]; tt = tf if fill else tc
                    ss += f' · {s}' + (' —' if not ok else ' ✓' if tt is not None and tt <= t + pd.Timedelta(minutes=5) else ' ✗' if M['NOW'] > t + pd.Timedelta(minutes=5) else ' …')
                xx = ix(t)
                ax.annotate(f'{nm} ✓ {t:%H:%M}{ss}', (xx, lvl), xytext=(0, -14 if st['up'] else 14), textcoords='offset points', ha='center', va='top' if st['up'] else 'bottom', fontsize=7.4, color=CHT,
                            bbox=dict(fc=WK if not fill else (BU if st['up'] else BD), alpha=0.2, ec='none', boxstyle='round,pad=0.3'), zorder=9)
    for y, tx, col, bold in LBL:
        ax.text(label_x(n), y, tx, color=col, fontsize=7.0, va='center', zorder=8, clip_on=True, linespacing=1.25, weight='bold' if bold else 'normal')
    return ax, lo_v, hi_v


def rows_v3(M):
    st, S = M['st'], M['S']
    up, bk = st['up'], st['bk']; prog = 1.0 if st['fld'] else cl(st['retr'], 0, 1)
    upTx = f"✓ {st['u1']:%H:%M}" if st['u1'] is not None else pc0(SC1[bk] if up else st['pOv'])
    dnTx = f"✓ {st['s1']:%H:%M}" if st['s1'] is not None else pc0(st['pOv'] if up else SC1[bk])
    ce = (st['O'] + st['C']) / 2
    rows = [('GAP', gauge(st['rr'] / 2.5, 10), 'hc', ('▲ ' if up else '▼ ') + f"{st['g']:,.2f} · {100 * st['g'] / st['C']:.2f}% · {'premium' if up else 'discount'}", f"{st['rr']:.1f}× · {BK[bk]}", None, None),
            ('FILL', fillBar(prog), BU if up else BD, ('filled' if st['fld'] else f'{round(100 * prog)}% back') + f" · {st['C']:,.2f}", f"✓ {st['flT']:%H:%M}" if st['fld'] else f"{pc0(st['pF'])} by 16:14", BU if st['fld'] else None, None),
            ('CE', '', None, f'{ce:,.2f}' + ('' if st['ceh'] or st['pC10'] is None else f" · 10:00 {pc0(st['pC10'])}"), f"✓ {st['ceT']:%H:%M}" if st['ceh'] else f"{pc0(st['pC'])} by 16:14", BU if st['ceh'] else None, None),
            ('±1 SD', '', None, f'▲ {upTx} · ▼ {dnTx}', 'by 16:14', None, None)]
    ss = []
    for s_ in ('ES', 'RTY'):
        ok, o_, c_, tc, tf, a_ = S[s_]
        if not ok: ss.append(f'{s_} —'); continue
        rk = abs(o_ - c_) / a_; now = M['B'].index[-1]
        mk = '✓' if tf is not None and tf <= now else '½' if tc is not None and tc <= now else '✗'
        ss.append(f"{s_} {'▲' if o_ > c_ else '▼'}{rk:.1f}× {mk}")
    add = None if st['fld'] else st['pF'] - st['pF00']
    rows.append(('SISTERS', '', None, ' · '.join(ss), '' if st['fld'] else f'fill {sgn0(add)}', None, None))
    return rows


def desktop_1m(NOW, start, fname, title, sub):
    M = build(NOW, '1m')
    B = M['B']; x = B[B.index >= start][['Open', 'High', 'Low', 'Close']].rename(columns=dict(Open='o', High='h', Low='l', Close='c'))
    fig = plt.figure(figsize=(19, 11.2), dpi=100, facecolor=BG)
    n = len(x)
    ax, lo, hi = draw(fig, [0.015, 0.05, 0.585, 0.85], x, M, max(8, n // 100), lambda n: n + max(9, n // 95))
    ax.set_xlim(-2, n * 1.30)
    ticks = [i for i, t in enumerate(x.index) if t.minute == 0 and t.hour % 2 == 0]
    ax.set_xticks(ticks); ax.set_xticklabels([x.index[i].strftime('%H:%M') for i in ticks], color=MU, fontsize=8)
    ax.set_ylim(lo - (hi - lo) * 0.06, hi + (hi - lo) * 0.06)
    card(fig, 0.635, 0.895, ('BENIHIME', 'RTH ORG', f"{M['today']:%m/%d} · {NOW:%H:%M} ET", 'NORMAL'), rows_v3(M), COLN, 0.30, (0.05, 0.105))
    fig.text(0.015, 0.962, title, color=CHT, fontsize=13, weight='bold'); fig.text(0.015, 0.937, sub, color='#5d6476', fontsize=9)
    plt.savefig(f'{OUT}/{fname}', dpi=100, facecolor=BG); plt.close(fig)
    st = M['st']; print(fname, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in st.items() if k in ('rr', 'onl', 'retr', 'dist', 'mins', 'pF', 'pF00', 'pC', 'pC10', 'ns')}, 'RTH', M['R']['st'], M['R']['flip'], M['R']['pdh'], M['R']['pdl'])


def desktop_1h(NOW, start, fname, title, sub):
    M = build(NOW, '1h')
    x = M['R']['c']; x = x[x.t >= start].set_index('t')[['o', 'h', 'l', 'c']]
    # the forming hour too, as the chart shows it
    B = M['B']; b = B[(B.hm >= 930) & (B.hm <= 1614) & (B.tday == M['today'])]
    kk = (NOW.hour * 60 + NOW.minute - 570) // 60; tk = M['today'] + pd.Timedelta(minutes=570 + 60 * kk)
    f = b[b.index >= tk]
    if len(f): x.loc[tk] = [f.Open.iloc[0], f.High.max(), f.Low.min(), f.Close.iloc[-1]]
    fig = plt.figure(figsize=(19, 11.2), dpi=100, facecolor=BG)
    n = len(x)
    ax, lo, hi = draw(fig, [0.015, 0.05, 0.585, 0.85], x, M, 2.0, lambda n: n + 1.6, evlbl=True, prevSD=False)
    ax.set_xlim(-1, n + 24)
    days = sorted(set(x.index.normalize()))
    for d in days[1:]: ax.axvline(float(np.searchsorted(x.index, d + pd.Timedelta(minutes=570))) - 0.5, color='#90caf9', lw=0.8, alpha=0.7, zorder=1)
    ax.set_xticks([float(np.searchsorted(x.index, d + pd.Timedelta(minutes=570))) for d in days]); ax.set_xticklabels([f'{d:%a %d}' for d in days], color=MU, fontsize=8)
    ax.set_ylim(lo - (hi - lo) * 0.05, hi + (hi - lo) * 0.05)
    card(fig, 0.635, 0.895, ('BENIHIME', 'RTH ORG', f"{M['today']:%m/%d} · {NOW:%H:%M} ET", 'NORMAL'), rows_v3(M), COLN, 0.30, (0.05, 0.105))
    fig.text(0.015, 0.962, title, color=CHT, fontsize=13, weight='bold'); fig.text(0.015, 0.937, sub, color='#5d6476', fontsize=9)
    plt.savefig(f'{OUT}/{fname}', dpi=100, facecolor=BG); plt.close(fig)
    print(fname, 'RTH', M['R']['st'], M['R']['flip'], 'ms', M['R']['ms'][-2:])


desktop_1m(pd.Timestamp('2026-10-20 10:12'), pd.Timestamp('2026-10-19 13:00'), 'Benihime_v3_live_1m.png',
           'Benihime v3 · NQ1! 1-minute ETH · Tue 20 Oct 2026 10:12 ET · the ORG as the day\'s dealing range',
           "Today's ▼ discount gap graded like Zabimaru's OR (±0.5 SD), CE ✓ 10:05 with ES ✓ and RTY ✓; ES has filled its own, so the fill odds carry +1 sister. "
           "The compact card keeps the live odds; the week's CEs, RTH-only structure and yesterday's RTH high / low live on the chart. NQ, ES, RTY data; TradingView will differ.")
desktop_1m(pd.Timestamp('2026-10-20 11:30'), pd.Timestamp('2026-10-20 06:00'), 'Benihime_v3_filled_1m.png',
           'Benihime v3 · NQ1! 1-minute ETH · Tue 20 Oct 2026 11:30 ET · filled, with the sisters',
           'Fill ✓ 10:15 · ES ✓ (filled 09:54) · RTY ✗ (its tiny ▲ gap never filled). The SISTERS row holds the triplet in one line (✓ filled, ½ CE only). NQ, ES, RTY data; TradingView will differ.')
desktop_1h(pd.Timestamp('2026-10-23 13:00'), pd.Timestamp('2026-10-12'), 'Benihime_v3_RTH_1h_jigsaw.png',
           'Benihime v3 · NQ1! 1-hour, RTH session (the jigsaw) · Fri 23 Oct 2026 13:00 ET',
           "RTH-only swings ▼▲ and shifts, this week's ORG CEs carried to Friday (✓ when traded), last week's Monday and Friday dashed, today's ORG graded; previous days' SDs switched off. NQ data; TradingView will differ.")
