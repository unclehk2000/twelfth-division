"""Zabimaru and Hihiō mock-ups from NQ / ES / RTY 1-minute data, computed the way the Pine scripts do.
python3 mock_zb.py OUTDIR"""
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
CZ, COK, CU, CD = '#d84315', '#26a69a', '#26a69a', '#ef5350'
R = pd.read_pickle('/home/claude/zb/or2.pkl')
BARS = {s: pd.read_pickle(f'/home/claude/kyw/bars_{s}_all.pkl').query("ts >= '2026-07-20' and ts < '2026-08-28'").set_index('ts') for s in ('NQ', 'ES', 'RTY')}
P = {'NQ': [0.178, 0.201, 0.218, 0.237, 0.252, 0.268, 0.280, 0.293, 0.308, 0.324, 0.341, 0.362, 0.384, 0.405, 0.429, 0.456, 0.497, 0.554, 0.648],
     'ES': [0.139, 0.163, 0.177, 0.192, 0.205, 0.218, 0.234, 0.246, 0.260, 0.274, 0.287, 0.304, 0.321, 0.344, 0.370, 0.399, 0.431, 0.492, 0.590],
     'RTY': [0.202, 0.233, 0.257, 0.273, 0.289, 0.306, 0.320, 0.334, 0.349, 0.365, 0.381, 0.399, 0.420, 0.440, 0.467, 0.499, 0.538, 0.590, 0.674]}
cl = lambda v, a, b: max(a, min(b, v))
sig = lambda z: 100 / (1 + np.exp(-z))
pUp = lambda loc: sig(-2.780 + 5.457 * cl(loc, 0, 1))
pSide = lambda d, lor, v: sig(1.846 - 3.446 * cl(d, 0, 1) - 0.839 * lor + 0.663 * v)
pExt = lambda lor, v, l: sig(-1.392 - 1.180 * lor + 1.007 * v - 0.112 * l)
pOth = lambda lor, v, l: sig(-1.625 - 1.249 * lor + 0.792 * v - 0.109 * l)
gauge = lambda f, n: '█' * int(round(cl(0 if f != f else f, 0, 1) * n)) + '░' * (n - int(round(cl(0 if f != f else f, 0, 1) * n)))
pc0 = lambda p: f'{round(p)}%'


def pct(T, v):
    if v <= T[0]: return 5 * v / T[0]
    if v >= T[18]: return min(99, 95 + 5 * (v - T[18]) / T[18])
    k = 0
    while k < 17 and T[k + 1] <= v: k += 1
    return 5 * (k + 1) + 5 * (v - T[k]) / (T[k + 1] - T[k])


def lum(h):
    return 0.299 * int(h[1:3], 16) + 0.587 * int(h[3:5], 16) + 0.114 * int(h[5:7], 16)


def orstate(sym, day, NOW):
    b = BARS[sym]; d = b[(b.tday == day) & (b.index < NOW)]
    o = d[(d.hm >= 930) & (d.hm < 1000)]
    if not len(o): return None
    r = R[(R.sym == sym) & (R.tday == day)].iloc[0]
    s = dict(O=o.Open.iloc[0], H=o.High.max(), L=o.Low.min(), c959=o.Close.iloc[-1], set=NOW >= pd.Timestamp(day) + pd.Timedelta(hours=10),
             atr10=r.atr10, atr5=r.atr5, t930=o.index[0])
    s['rng'] = s['H'] - s['L']
    a = d[(d.hm >= 1000) & (d.hm < 1615)]
    hh = a[a.High > s['H']].index; ll = a[a.Low < s['L']].index
    s['tH'] = hh[0] if s['set'] and len(hh) else None; s['tL'] = ll[0] if s['set'] and len(ll) else None
    return s


def card(fig, x0, y0, head, rows, w, cx, fs=8.2, lh=0.027, cw=0.0040):
    ht = '#ffffff'
    fig.patches.append(Rectangle((x0, y0 - lh), w, lh, transform=fig.transFigure, fc=CZ, ec='none', zorder=10))
    fig.text(x0 + 0.006, y0 - lh / 2, head[0], color=ht, fontsize=fs + 0.3, family='DejaVu Sans Mono', va='center', weight='bold', zorder=11)
    fig.text(x0 + cx[0], y0 - lh / 2, head[1], color=ht, fontsize=fs + 0.3, family='DejaVu Sans Mono', va='center', weight='bold', zorder=11)
    if head[2]:
        fig.text(x0 + cx[1], y0 - lh / 2, head[2], color=ht, fontsize=fs + 0.3, family='DejaVu Sans Mono', va='center', zorder=11)
    pw = 0.012 + cw * len(head[3])
    fig.patches.append(Rectangle((x0 + w - pw - 0.004, y0 - lh + 0.004), pw, lh - 0.008, transform=fig.transFigure, fc='#ffffff', ec='none', zorder=11))
    fig.text(x0 + w - pw / 2 - 0.004, y0 - lh / 2, head[3], color=CZ, fontsize=fs, family='DejaVu Sans Mono', va='center', ha='center', weight='bold', zorder=12)
    for k, row in enumerate(rows):
        key, gs, gc, v, rt, wbg = row[:6]
        sub = len(row) > 6 and row[6]
        yy = y0 - lh * (k + 2)
        fig.patches.append(Rectangle((x0, yy), w, lh, transform=fig.transFigure, fc=CB, ec='none', zorder=10))
        fig.text(x0 + 0.006, yy + lh / 2, key, color=CZ if sub else CS, fontsize=fs, family='DejaVu Sans Mono', va='center', zorder=11)
        if gs:
            fig.text(x0 + cx[0], yy + lh / 2, gs, color=gc or CT, fontsize=fs, family='DejaVu Sans Mono', va='center', zorder=11)
        if v:
            fig.text(x0 + cx[1], yy + lh / 2, v, color=CS if sub else CT, fontsize=fs, family='DejaVu Sans Mono', va='center', zorder=11)
        if wbg:
            tw = cw * len(rt) + 0.008
            fig.patches.append(Rectangle((x0 + w - tw, yy), tw, lh, transform=fig.transFigure, fc=wbg, ec='none', zorder=11))
        fig.text(x0 + w - 0.005, yy + lh / 2, rt, color='#ffffff' if wbg else (CS if sub else CT), fontsize=fs, family='DejaVu Sans Mono', va='center', ha='right', zorder=12, weight='bold' if wbg else 'normal')
    fig.patches.append(Rectangle((x0, y0 - lh * (len(rows) + 1)), w, lh * (len(rows) + 1), transform=fig.transFigure, fc='none', ec=CZ, lw=1, zorder=12))


def brk(s):
    th, tl = s['tH'], s['tL']
    if th is not None and tl is not None:
        return (f'▲{th:%H:%M} ▼{tl:%H:%M}' if th <= tl else f'▼{tl:%H:%M} ▲{th:%H:%M}')
    return f'▲ {th:%H:%M}' if th is not None else f'▼ {tl:%H:%M}' if tl is not None else '—'


def zab_rows(day, NOW, mobile=False):
    S = {k: orstate(k, day, NOW) for k in ('NQ', 'ES', 'RTY')}
    s = S['NQ']; rng = s['rng']; ratio = rng / s['atr10']; pl = pct(P['NQ'], ratio); volr = np.log(s['atr5'] / s['atr10'])
    lor = np.log(ratio); loc = (s['c959'] - s['L']) / rng
    side = 0; tB = None
    if s['tH'] is not None or s['tL'] is not None:
        if s['tL'] is None or (s['tH'] is not None and s['tH'] < s['tL']): side, tB = 1, s['tH']
        elif s['tH'] is None or s['tL'] < s['tH']: side, tB = -1, s['tL']
        else: side, tB = 2, s['tH']
    ltb = np.log(max(0, (tB - s['t930']).total_seconds() / 60 - 30) + 1) if tB is not None else 0
    b = BARS['NQ']; d = b[(b.tday == day) & (b.index < NOW)]
    tX = None
    if side in (1, -1):
        a = d[(d.index >= tB) & (d.hm < 1615)]
        hit = a[a.High >= s['H'] + rng].index if side == 1 else a[a.Low <= s['L'] - rng].index
        tX = hit[0] if len(hit) else None
    st = 'BUILDING' if not s['set'] else 'SET' if side == 0 else '▲ BREAK' if side == 1 else '▼ BREAK'
    pU = pUp(loc); pH = pSide(1 - loc, lor, volr); pL = pSide(loc, lor, volr); pX = pExt(lor, volr, ltb); pO = pOth(lor, volr, ltb)
    hRes = f"✓ {s['tH']:%H:%M}" if s['tH'] is not None else (f'other {pc0(pO)}' if side == -1 else pc0(pH) + ('' if mobile else ' by 16:14'))
    lRes = f"✓ {s['tL']:%H:%M}" if s['tL'] is not None else (f'other {pc0(pO)}' if side == 1 else pc0(pL) + ('' if mobile else ' by 16:14'))
    # ORG
    prev = b[(b.tday < day) & (b.hm == 1614)].iloc[-1].Close
    gO = s['O']; g = gO - prev
    rth = d[(d.hm >= 930) & (d.hm < 1615)]
    ce = (gO + prev) / 2
    gce = rth[rth.Low <= ce].index if g > 0 else rth[rth.High >= ce].index
    gfl = rth[rth.Low <= prev].index if g > 0 else rth[rth.High >= prev].index
    sis = []
    for k in ('ES', 'RTY'):
        t = S[k]['tH'] if side == 1 else S[k]['tL'] if side == -1 else None
        due = tB is not None and NOW >= tB + pd.Timedelta(minutes=5)
        ok = t is not None and tB is not None and t <= tB + pd.Timedelta(minutes=5)
        sis.append((k, ok, due))
    nc = sum(1 for _, ok, _ in sis if ok)
    if mobile:
        rows = [('OR', gauge(pl / 100, 5), CZ, '', f"{100 * rng / s['O']:.2f}% · {ratio:.2f}× P{round(pl)}", None)]
        if s['set']:
            rows.append(('FIRST', gauge(pU / 100, 5), CU, '', f'▲ {pc0(pU)} ▼ {pc0(100 - pU)}' if side == 0 else ('▲ ' if side == 1 else '▼ ') + f'{tB:%H:%M}' + (' 1×✓' if tX is not None else f' 1× {pc0(pX)}'), None))
            rows.append(('HI/LO', '', None, '', f'▲ {hRes} ▼ {lRes}', None))
        rows.append(('TRI', '', None, '', ' '.join(f'{k} {brk(S[k])}' for k in ('ES', 'RTY')), None))
        rows.append(('VOL', '', None, '', f"ATR10 {s['atr10']:,.2f} " + ('▲ rising' if volr > 0 else '▼ falling'), None))
        return rows, st, S, side, tB, tX
    rows = [('OR', gauge(pl / 100, 10), CZ, f"{rng:,.2f} pts · {100 * rng / s['O']:.2f}%", f'{ratio:.2f}× ATR · P{round(pl)}', None),
            ('ATR10', gauge(s['atr5'] / s['atr10'] / 2, 10), CU if volr > 0 else CD, f"{s['atr10']:,.2f} pts · {100 * s['atr10'] / s['O']:.2f}%", '▲ rising' if volr > 0 else '▼ falling', None)]
    if s['set']:
        rows += [('FIRST', gauge(pU / 100, 10), CU, f'▲ {pc0(pU)} · ▼ {pc0(100 - pU)}' if side == 0 else ('▲ high ' if side == 1 else '▼ low ') + f'{tB:%H:%M}', 'from 10:00' if side == 0 else '', None),
                 ('HIGH', '', None, f"{s['H']:,.2f}", hRes, COK if s['tH'] is not None else None),
                 ('LOW', '', None, f"{s['L']:,.2f}", lRes, COK if s['tL'] is not None else None)]
        if side in (1, -1):
            rows.append(('1× EXT', '', None, f"{(s['H'] + rng) if side == 1 else (s['L'] - rng):,.2f}", f'✓ {tX:%H:%M}' if tX is not None else f'{pc0(pX)} by 16:14', COK if tX is not None else None))
    else:
        rows.append(('SIDES', '', None, 'after 10:00', '', None))
    rows.append(('TRIPLET', 'pctl', None, 'OR % · × ATR10', 'breaks', None, True))
    for k in ('NQ', 'ES', 'RTY'):
        q = S[k]; rr = q['rng'] / q['atr10']
        rows.append((('› ' if k == 'NQ' else '  ') + k, gauge(pct(P[k], rr) / 100, 10), CZ if k == 'NQ' else CS, f"{100 * q['rng'] / q['O']:.2f}% · {rr:.2f}×", brk(q), None))
    if side in (1, -1):
        rows.append(('SISTERS', '', None, ' · '.join(f"{k} {'✓' if ok else '✗' if due else '…'}" for k, ok, due in sis), f'{nc} of 2 in 5 min', None))
    o18 = b[(b.tday == day) & (b.hm == 1800)].Open.iloc[0]; o00 = b[(b.tday == day) & (b.hm == 0)].Open.iloc[0]
    rr_ = d[(d.hm >= 930) & (d.hm < 1615)]
    h18 = len(rr_[(rr_.Low <= o18) & (rr_.High >= o18)]) > 0; h00 = len(rr_[(rr_.Low <= o00) & (rr_.High >= o00)]) > 0
    rows.append(('OPENS', '', None, f'18:00 {o18:,.2f} · 00:00 {o00:,.2f}', f"{'✓' if h18 else '—'} · {'✓' if h00 else '—'}", None))
    rows.append(('ORG', '', None, ('▲ ' if g >= 0 else '▼ ') + f"{abs(g):,.2f} · {abs(g) / s['atr10']:.2f}× ATR", f'✓ filled {gfl[0]:%H:%M}' if len(gfl) else f'CE ✓ {gce[0]:%H:%M}' if len(gce) else 'open', COK if len(gfl) else None))
    return rows, st, S, side, tB, tX


def chart(fig, rect, day, start, NOW, S, side, tB, tX, ypad=0.08, hihio=False):
    b = BARS['NQ']; x = b[(b.index >= start) & (b.index < NOW)]
    ax = fig.add_axes(rect)
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
    lo, hi = x.Low.min(), x.High.max()
    if S is not None and not hihio:
        for hm, col, ls, nm in ((1800, '#c9a227', '-', '18:00'), (0, '#787b86', ':', '00:00')):
            s0 = b[(b.tday == day) & (b.hm == hm)]
            if len(s0):
                y = s0.Open.iloc[0]; rth = x[(x.hm >= 930) & (x.hm < 1615)]
                a = 0.45 if len(rth[(rth.Low <= y) & (rth.High >= y)]) else 1.0
                ax.plot([max(ix(s0.index[0]), -2), n + 40], [y, y], color=col, ls=ls, lw=1.2, alpha=a, zorder=3)
                ax.text(n + 41, y, nm, color=col, fontsize=7.2, va='center', alpha=a)
                lo, hi = min(lo, y), max(hi, y)
    if S is not None:
        s = S['NQ']; rng = s['rng']
        x0 = ix(s['t930']); x1e = ix(pd.Timestamp(day) + pd.Timedelta(hours=10)); xr = n + 40
        ax.add_patch(Rectangle((x0, s['L']), min(x1e, n) - x0, rng, fc=CZ, alpha=0.13, ec=CZ, lw=1, zorder=2))
        ax.plot([x0 - 3, x0 - 3], [s['L'], s['H']], color=CZ, lw=1, alpha=0.8, zorder=3)
        ax.text(x0 - 5, (s['H'] + s['L']) / 2, f"{rng:,.2f} · {100 * rng / s['O']:.2f}% · {rng / s['atr10']:.2f}× ATR", ha='right', va='center', fontsize=7.4, color=CHT, zorder=8)
        # the octant grid: follows the range while it forms, runs on after 10:00 (edges 2 solid, EQ 2 dashed, quarters 2 solid, eighths 1 dotted)
        xg = n - 1 + 1 if not s['set'] else xr
        G = [(1.0, CZ, 2.0, '-', 1, 'OR high'), (0.0, CZ, 2.0, '-', 1, 'OR low'), (0.5, CZ, 2.0, '--', 1, 'EQ'),
             (0.25, '#ff7043', 2.0, '-', 1, '25%'), (0.75, '#ff7043', 2.0, '-', 1, '75%')] + [(f, CZ, 0.9, ':', 0.45, '') for f in (0.125, 0.375, 0.625, 0.875)]
        for f, c, lw, ls, a, lab in G:
            y = s['L'] + f * rng
            ax.plot([x0, xg], [y, y], color=c, lw=lw, ls=ls, alpha=a, zorder=3)
            if lab:
                ax.text(xg + 1, y, lab, color=c, fontsize=7.2, va='center', alpha=min(1, a + 0.1))
        if s['set']:
            L = lambda y, ls, a, lab: (ax.plot([x1e, xr], [y, y], color=CZ, ls=ls, lw=1, alpha=a, zorder=3), ax.text(xr + 1, y, lab, color=CZ, fontsize=7.2, va='center', alpha=min(1, a + 0.2)))
            L(s['H'] + 0.5 * rng, ':', 0.55, '+0.5×'); L(s['L'] - 0.5 * rng, ':', 0.55, '−0.5×')
            L(s['H'] + rng, '--', 0.8, '+1×'); L(s['L'] - rng, '--', 0.8, '−1×')
            L(s['H'] + 2 * rng, '-', 0.8, '+2×'); L(s['L'] - 2 * rng, '-', 0.8, '−2×')
            hi = max(hi, s['H'] + rng * 1.1); lo = min(lo, s['L'] - rng * 1.1)
            if tB is not None:
                sis = []
                for k in ('ES', 'RTY'):
                    t = S[k]['tH'] if side == 1 else S[k]['tL']
                    ok = t is not None and t <= tB + pd.Timedelta(minutes=5)
                    sis.append(f"{k} {'✓' if ok else '✗' if NOW >= tB + pd.Timedelta(minutes=5) else '…'}")
                yb = s['H'] if side == 1 else s['L']
                ax.text(ix(tB), yb + (rng * 0.12 if side == 1 else -rng * 0.12), ('▲ ' if side == 1 else '▼ ') + f'{tB:%H:%M} · ' + ' · '.join(sis), color=CU if side == 1 else CD, fontsize=7.6, ha='center', va='bottom' if side == 1 else 'top', zorder=9, weight='bold')
    ticks = [i for i, t in enumerate(x.index) if t.minute == 0 and t.hour % 2 == 0] if not hihio else [i for i, t in enumerate(x.index) if t.minute == 0 and t.hour % 6 == 0]
    ax.set_xticks(ticks); ax.set_xticklabels([x.index[i].strftime('%H:%M') if not hihio or x.index[i].hour else x.index[i].strftime('%a %d') for i in ticks], color=MU, fontsize=8)
    ax.set_xlim(-2, n + 55); ax.set_ylim(lo - (hi - lo) * ypad, hi + (hi - lo) * ypad)
    return ax, x, ix


def desktop(day, NOW, start, fname, title, sub):
    rows, st, S, side, tB, tX = zab_rows(day, NOW)
    fig = plt.figure(figsize=(18, 10.4), dpi=100, facecolor=BG)
    chart(fig, [0.02, 0.05, 0.60, 0.85], day, start, NOW, S, side, tB, tX)
    card(fig, 0.655, 0.885, ('ZABIMARU', 'OPENING RNG', f'{NOW:%m/%d} · {NOW:%H:%M} ET', st), rows, 0.275, (0.05, 0.10))
    fig.text(0.02, 0.955, title, color=CHT, fontsize=13, weight='bold'); fig.text(0.02, 0.928, sub, color='#5d6476', fontsize=9)
    plt.savefig(f'{OUT}/{fname}', dpi=100, facecolor=BG); plt.close(fig)


def mobile(day, fname, title):
    fig = plt.figure(figsize=(12, 10.4), dpi=100, facecolor=BG)
    for k, (NOW, start, lab) in enumerate(((pd.Timestamp(day) + pd.Timedelta(hours=9, minutes=48), pd.Timestamp(day) + pd.Timedelta(hours=8), 'building, 09:48 ET'),
                                          (pd.Timestamp(day) + pd.Timedelta(hours=10, minutes=40), pd.Timestamp(day) + pd.Timedelta(hours=8, minutes=30), 'after the break, 10:40 ET'))):
        rows, st, S, side, tB, tX = zab_rows(day, NOW, mobile=True)
        x0 = 0.03 + k * 0.5
        fig.patches.append(Rectangle((x0 - 0.01, 0.03), 0.44, 0.9, transform=fig.transFigure, fc='none', ec='#c9ced8', lw=1.5, zorder=0))
        fig.text(x0, 0.905, lab, color='#5d6476', fontsize=9.5)
        chart(fig, [x0, 0.06, 0.37, 0.56], day, start, NOW, S, side, tB, tX, ypad=0.06)
        card(fig, x0 + 0.165, 0.875, ('ZABIMARU', f'{NOW:%m/%d} {NOW:%H:%M}', '', st), rows, 0.255, (0.065, 0.1), fs=8.4, lh=0.034, cw=0.006)
    fig.text(0.03, 0.955, title, color=CHT, fontsize=13, weight='bold')
    plt.savefig(f'{OUT}/{fname}', dpi=100, facecolor=BG); plt.close(fig)


def hihio(fname, NOW, start):
    b = BARS['NQ']; x = b[(b.index >= start) & (b.index < NOW)]
    fig = plt.figure(figsize=(18, 10.4), dpi=100, facecolor=BG)
    ax, x, ix = chart(fig, [0.02, 0.05, 0.86, 0.85], None, start, NOW, None, 0, None, None, ypad=0.05, hihio=True)
    n = len(x)
    days = sorted(set(x.tday))
    for dd in days[-3:]:
        e = pd.Timestamp(dd) + pd.Timedelta(hours=16, minutes=59)
        rth = b[(b.tday == dd) & (b.hm >= 930) & (b.hm < 1615)]
        for nm, hm, col, ls in (('18:00', 1800, '#c9a227', '-'), ('00:00', 0, '#787b86', ':')):
            s0 = b[(b.tday == dd) & (b.hm == hm)]
            if not len(s0): continue
            t0, y = s0.index[0], s0.Open.iloc[0]
            if t0 < start: continue
            x2 = ix(e) if e < NOW else n + 35
            hit = rth[(rth.Low <= y) & (rth.High >= y) & (rth.index < NOW)]
            a = 0.45 if len(hit) else 1.0
            ax.plot([ix(t0), x2], [y, y], color=col, ls=ls, lw=1.3, alpha=a, zorder=3)
            ax.text(x2 + 2, y, nm, color=col, fontsize=7.6, va='center', alpha=a)
    fig.text(0.02, 0.955, 'Hihiō · NQ1! 15-minute ETH: the 18:00 open (gold) and the midnight open (dotted), each run to 16:59 of its trading day', color=CHT, fontsize=13, weight='bold')
    fig.text(0.02, 0.928, 'Lines fade once RTH trades through them. NQ + ES + RTY 2018–26: RTH reached the midnight open 68% of days (a level the same distance on the other side of the 09:30 open: 66%), the 18:00 open 64% (61%): references, not magnets.', color='#5d6476', fontsize=9)
    plt.savefig(f'{OUT}/{fname}', dpi=100, facecolor=BG); plt.close(fig)


day = pd.Timestamp('2026-08-04')
desktop(day, pd.Timestamp('2026-08-04 11:30'), pd.Timestamp('2026-08-04 07:00'), 'Zabimaru_Desktop_1m.png',
        'Zabimaru · NQ1! 1-minute: Tue 4 Aug 2026 at 11:30 ET · opening range, octant grid and session opens',
        'Octant grid (quarters emphasised) on the OR, the 18:00 open (gold) and midnight open (dotted) built in. Broken up at 10:05 after ES (10:01) and RTY (10:02); 1× still ahead (40% by 16:14). Odds from NQ + ES + RTY 2018–26. TradingView rendering will differ.')
mobile(day, 'Zabimaru_Mobile.png', 'Zabimaru · Mobile layout: Tue 4 Aug 2026, building (09:48) and after the break (10:40)')
print('done')
