"""Getsuga Tenshō v2 mock-ups: Friday's Shikai mid (1) -> Monday's (0), computed the way the Pine script does, from NQ
1-minute data drawn as 15-minute candles. python3 mock_gt2.py OUTDIR"""
import sys, json
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plt.rcParams['font.family'] = 'DejaVu Sans'
OUT = sys.argv[1]
BG, MU, GRID, CHT = '#ffffff', '#9aa1b2', '#eef1f6', '#131722'
CB, CT, CS = '#161a23', '#d1d4dc', '#8a93a6'
UP, DN, CH, COK, CFORM = '#089981', '#f23645', '#1e88e5', '#26a69a', '#f9a825'
FIB, FIB8, SDC, PWC, WOC = '#2962ff', '#94aefc', '#9c27b0', '#787b86', '#c9a227'
C25, C375, C50 = '#2196f3', '#5c6bc0', '#ab47bc'
J = json.load(open('/home/claude/gt/live_v2.json'))
FX = [-0.326, 0, 1, 2, 3]
cl = lambda v, a, b: max(a, min(b, v))
gauge = lambda f, n: '█' * int(round(cl(0 if f != f else f, 0, 1) * n)) + '░' * (n - int(round(cl(0 if f != f else f, 0, 1) * n)))
fmt = lambda v: f'{v:,.2f}'


def pReach(I, a, b, x, d):
    xx = cl(x, -0.326, 4.0); dd = d
    if xx >= 3:
        it = I[4]; dd = d / np.sqrt(max(4 - xx, 0.01))
    else:
        i = 0 if xx < 0 else int(np.floor(xx)) + 1; f = (xx - FX[i]) / (FX[i + 1] - FX[i]); it = I[i] * (1 - f) + I[i + 1] * f
    dc = cl(dd, 0, 3)
    return 100 / (1 + np.exp(-(it + a * dc + b * np.sqrt(dc))))


B = pd.read_pickle('/home/claude/kyw/bars_NQ_all.pkl').query("ts >= '2026-07-01' and ts < '2026-10-10'").set_index('ts')
B['wk'] = B.tday - pd.to_timedelta(B.tday.dt.dayofweek, unit='D')
Q = B.resample('15min').agg(dict(Open='first', High='max', Low='min', Close='last', tday='first', hm='first', wk='first')).dropna()


def shikai_mid(day):
    """Overnight (18:00 -> 09:29) of a trading day on 15-minute bars: mid and the earlier extreme's time."""
    o = Q[(Q.tday == day) & ((Q.hm >= 1800) | (Q.hm < 930))]
    return (o.High.max() + o.Low.min()) / 2, min(o.High.idxmax(), o.Low.idxmin())


def state(NOW):
    b = B[B.index < NOW]
    wk = b.wk.iloc[-1]; cur = b[b.wk == wk]; prev = b[b.wk == wk - pd.Timedelta(days=7)]
    wks = sorted(w for w in B.wk.unique() if w < wk)[-4:]          # the 4 weeks before (weekly bars skip a week with no data)
    awr = np.mean([(lambda w: w.High.max() - w.Low.min())(B[B.wk == w]) for w in wks])
    F, fT0 = shikai_mid(prev.tday.max()); M, mT0 = shikai_mid(cur.tday.min())
    R = F - M; lvl = lambda f: M + f * R
    set_t = cur[(cur.tday == cur.tday.min()) & (cur.hm == 930)].index[0]
    after = cur[cur.index >= set_t]
    first = lambda m: after.index[m][0] if m.any() else None
    hit = lambda y: first((after.Low.values <= y) & (after.High.values >= y))
    px = cur.Close.iloc[-1]
    tdi = cur.tday.iloc[-1].dayofweek; dstart = cur.tday.iloc[-1] - pd.Timedelta(hours=6)
    x = tdi - 1 + cl((NOW - dstart).total_seconds() / (23 * 3600), 0, 1)
    s = dict(wk=wk, cur=cur, prev=prev, F=F, fT0=fT0, M=M, mT0=mT0, R=R, awr=awr, px=px, x=x, set_t=set_t,
             PWH=prev.High.max(), PWL=prev.Low.min(), wkO=cur.Open.iloc[0], wkT0=cur.index[0], wH=cur.High.max(), wL=cur.Low.min(),
             wTH=cur.High.idxmax(), wTL=cur.Low.idxmin(), tPH=first(cur.High.values > prev.High.max()) if False else None)
    s['tPH'] = (lambda m: cur.index[m][0] if m.any() else None)(cur.High.values > s['PWH'])
    s['tPL'] = (lambda m: cur.index[m][0] if m.any() else None)(cur.Low.values < s['PWL'])
    s['lv'] = {f: (lvl(f), hit(lvl(f))) for f in (1.5, 1.0, 0.5, 0.0, -0.5)}
    s['odds'] = {f: (None if t is not None else pReach(J['fib']['ints'], J['fib']['dc'], J['fib']['sq'], x, abs(y - px) / awr)) for f, (y, t) in s['lv'].items()}
    s['pwo'] = (None if s['tPH'] else pReach(J['pw']['ints'], J['pw']['dc'], J['pw']['sq'], x, max(s['PWH'] - px, 0) / awr),
                None if s['tPL'] else pReach(J['pw']['ints'], J['pw']['dc'], J['pw']['sq'], x, max(px - s['PWL'], 0) / awr))
    s['fpos'] = (px - M) / R
    return s


def rows(s, mobile=False):
    wt = lambda t: f'{t:%a %H:%M}'
    fp = s['fpos']; rr = abs(s['R']) / s['awr']
    lo, hi = min(s['F'], s['M']), max(s['F'], s['M'])
    oct_ = (f"beyond {'2' if fp > 2 else '−1'} · {fp:.2f}" if (fp > 2 or fp < -1) else f"past SD · {fp:.2f}" if (fp > 1.5 or fp < -0.5) else f"{np.floor(fp * 8) / 8:g} – {np.floor(fp * 8) / 8 + 0.125:g}")
    res = lambda f: (f"✓ {wt(s['lv'][f][1])}", COK) if s['lv'][f][1] is not None else (f"{round(s['odds'][f])}% by Fri", None)
    if mobile:
        sh = lambda f: '✓' if s['lv'][f][1] is not None else f"{round(s['odds'][f])}%"
        return [('RANGE', gauge(rr, 5), CH, '', f"{fmt(abs(s['R']))} · {rr:.2f}×", None),
                ('NOW', gauge((s['px'] - lo) / (hi - lo), 5), CH, '', oct_, None),
                ('1 / 0', '', None, '', f"1 {sh(1.0)} · 0 {sh(0.0)}", COK if s['lv'][1.0][1] is not None and s['lv'][0.0][1] is not None else None),
                ('SD', '', None, '', f"1.5 {sh(1.5)} · −.5 {sh(-0.5)}", COK if s['lv'][1.5][1] is not None and s['lv'][-0.5][1] is not None else None)]
    R = [('RANGE', gauge(rr, 10), CH, f"{fmt(s['F'])} → {fmt(s['M'])}", f"{fmt(abs(s['R']))} pts · {rr:.2f}× AWR4", None),
         ('NOW', gauge((s['px'] - lo) / (hi - lo), 10), CH, oct_, fmt(s['px']), None)]
    order = (1.5, 1.0, 0.5, 0.0, -0.5) if s['R'] > 0 else (-0.5, 0.0, 0.5, 1.0, 1.5)
    names = {1.5: '1.5 SD', 1.0: '1 FRI', 0.5: '0.5 EQ', 0.0: '0 MON', -0.5: '-0.5 SD'}
    for f in order:
        y, t = s['lv'][f]; txt, bg = res(f)
        R.append((names[f], '', None, fmt(y) + ('' if t is not None else f" · {abs(y - s['px']) / s['awr']:.2f}× away"), txt, bg))
    for nm, y, t, p in (('PWH', s['PWH'], s['tPH'], s['pwo'][0]), ('PWL', s['PWL'], s['tPL'], s['pwo'][1])):
        R.append((nm, '', None, fmt(y), f"✓ {wt(t)}" if t is not None else f"{round(p)}% by Fri", COK if t is not None else None))
    R.append(('WEEK', gauge((s['wH'] - s['wL']) / s['awr'], 10), CH, f"{fmt(s['wH'] - s['wL'])} pts so far", f"{(s['wH'] - s['wL']) / s['awr']:.2f}× AWR4", None))
    return R


def card(fig, x0, y0, head, rows_, w, cx, fs=8.2, lh=0.027, cw=0.0040, pill_col=CH):
    fig.patches.append(Rectangle((x0, y0 - lh), w, lh, transform=fig.transFigure, fc=CH, ec='none', zorder=10))
    for xx, tx, wgt in ((0.006, head[0], 'bold'), (cx[0], head[1], 'bold'), (cx[1], head[2], 'normal')):
        if tx:
            fig.text(x0 + xx, y0 - lh / 2, tx, color='#ffffff', fontsize=fs + 0.3, family='DejaVu Sans Mono', va='center', weight=wgt, zorder=11)
    pw = 0.012 + cw * len(head[3])
    fig.patches.append(Rectangle((x0 + w - pw - 0.004, y0 - lh + 0.004), pw, lh - 0.008, transform=fig.transFigure, fc='#ffffff', ec='none', zorder=11))
    fig.text(x0 + w - pw / 2 - 0.004, y0 - lh / 2, head[3], color=pill_col, fontsize=fs, family='DejaVu Sans Mono', va='center', ha='center', weight='bold', zorder=12)
    for k, (key, gs, gc, v, rt, wbg) in enumerate(rows_):
        yy = y0 - lh * (k + 2)
        fig.patches.append(Rectangle((x0, yy), w, lh, transform=fig.transFigure, fc=CB, ec='none', zorder=10))
        fig.text(x0 + 0.006, yy + lh / 2, key, color=CS, fontsize=fs, family='DejaVu Sans Mono', va='center', zorder=11)
        if gs:
            fig.text(x0 + cx[0], yy + lh / 2, gs, color=gc or CT, fontsize=fs, family='DejaVu Sans Mono', va='center', zorder=11)
        if v:
            fig.text(x0 + cx[1], yy + lh / 2, v, color=CT, fontsize=fs, family='DejaVu Sans Mono', va='center', zorder=11)
        if wbg:
            tw = cw * len(rt) + 0.008
            fig.patches.append(Rectangle((x0 + w - tw, yy), tw, lh, transform=fig.transFigure, fc=wbg, ec='none', zorder=11))
        fig.text(x0 + w - 0.005, yy + lh / 2, rt, color='#ffffff' if wbg else CT, fontsize=fs, family='DejaVu Sans Mono', va='center', ha='right', zorder=12, weight='bold' if wbg else 'normal')
    fig.patches.append(Rectangle((x0, y0 - lh * (len(rows_) + 1)), w, lh * (len(rows_) + 1), transform=fig.transFigure, fc='none', ec=CH, lw=1, zorder=12))


def chart(fig, rect, s, NOW, start, lbl=True, fs_lbl=7.2, dc_off=15):
    x = Q[(Q.index >= start) & (Q.index < NOW)]
    ax = fig.add_axes(rect)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_facecolor(BG); ax.yaxis.tick_right(); ax.tick_params(axis='y', colors=MU, labelsize=8); ax.tick_params(axis='x', length=0)
    ax.grid(color=GRID, lw=0.7, zorder=0)
    n = len(x); w = 0.6
    ix = lambda t: float(np.searchsorted(x.index, t))
    for i, (t, q) in enumerate(x.iterrows()):
        c = UP if q.Close >= q.Open else DN
        ax.plot([i, i], [q.Low, q.High], color=c, lw=0.6, zorder=4)
        ax.add_patch(Rectangle((i - w / 2, min(q.Open, q.Close)), w, max(abs(q.Close - q.Open), 0.25), fc=c, ec=c, lw=0.2, zorder=5))
    last = n - 1
    # day candles, Session Map style: neutral colour, light body, wicks, name + high above, low below, 25 / 37.5 / 50% ticks
    xc = last + dc_off; step = 4 + 6
    cands = [(f'{d:%a}', g.Open.iloc[0], g.High.max(), g.Low.min(), g.Close.iloc[-1], g.High.idxmax(), g.Low.idxmin()) for d, g in s['cur'][s['cur'].index < NOW].groupby('tday')]
    cands.append(('Week', s['wkO'], s['wH'], s['wL'], s['px'], s['wTH'], s['wTL']))
    for nm, o, h, l, c, tH, tL in cands:
        bt, bb, xm = max(o, c), min(o, c), xc + 2
        ax.add_patch(Rectangle((xc, bb), 4, max(bt - bb, 0.5), fc=CHT, alpha=0.15, ec='none', zorder=6))
        ax.add_patch(Rectangle((xc, bb), 4, max(bt - bb, 0.5), fc='none', ec=CHT, lw=0.8, zorder=6))
        ax.plot([xm, xm], [bt, h], color=CHT, lw=0.8, zorder=6); ax.plot([xm, xm], [l, bb], color=CHT, lw=0.8, zorder=6)
        ax.text(xm, h + 4, f'{nm}\n{fmt(h)}', ha='center', va='bottom', fontsize=6, color=CHT, zorder=7, bbox=dict(fc='#e7e8ea', ec='none', pad=1))
        ax.text(xm, l - 4, fmt(l), ha='center', va='top', fontsize=6, color=CHT, zorder=7)
        dn = tH < tL or (tH == tL and c < o)
        for q, col, tx in ((0.25, C25, '25%'), (0.375, C375, '37.5%'), (0.5, C50, '50%')):
            y = l + q * (h - l) if dn else h - q * (h - l)
            ax.plot([xc + 4, xc + 10], [y, y], color=col, lw=0.8, zorder=6)
            ax.text(xc + 10.3, y, tx, fontsize=5.5, color=col, va='center', zorder=7)
        xc += step
    x2 = xc + 6
    # the range: from Friday's mid line start, through the week
    x1 = ix(s['fT0'])
    for k in range(-4, 13):
        f = k / 8
        if k < 0 and k != -4 or k > 8 and k != 12:
            continue
        y = s['M'] + f * s['R']
        if k in (0, 8): col, lw, ls = FIB, 2, '-'
        elif k == 4: col, lw, ls = FIB, 1, '--'
        elif k in (2, 6): col, lw, ls = FIB, 1, '-'
        elif k in (12, -4): col, lw, ls = SDC, 2, '-'
        else: col, lw, ls = FIB8, 1, ':'
        ax.plot([x1, x2], [y, y], color=col, lw=lw, ls=ls, zorder=3)
        if lbl:
            nm = ' · Fri mid' if k == 8 else ' · Mon mid' if k == 0 else ' · SD' if k in (12, -4) else ''
            ax.text(x2 + 1, y, f'{f:g} ({fmt(y)}){nm}', color=col, fontsize=fs_lbl, va='center')
    w0 = ix(s['wkT0'])
    for nm, y, va in (('PWH', s['PWH'], 'bottom'), ('PWL', s['PWL'], 'top')):
        ax.plot([w0, x2], [y, y], color=PWC, lw=1, ls=':', zorder=2)
        if lbl:
            ax.text(w0 + 1, y + (1 if va == 'bottom' else -1) * abs(s['R']) * 0.02, f'{nm} ({fmt(y)})', color=PWC, fontsize=fs_lbl, va=va, zorder=8)
    ax.plot([w0, x2], [s['wkO']] * 2, color=WOC, lw=1, ls=':', zorder=2)
    if lbl:
        ax.text(w0 + 1, s['wkO'] + abs(s['R']) * 0.03, f"Week open ({fmt(s['wkO'])})", color=WOC, fontsize=fs_lbl, va='bottom', zorder=8)
    ticks = [i for i, t in enumerate(x.index) if t.hour == 0 and t.minute == 0]
    ax.set_xticks(ticks); ax.set_xticklabels([x.index[i].strftime('%a %d') for i in ticks], color=MU, fontsize=8)
    lo = min(x.Low.min(), s['M'] - 0.6 * abs(s['R']), s['F'] - 0.6 * abs(s['R'])); hi = max(x.High.max(), s['M'] + 0.6 * abs(s['R']), s['F'] + 0.6 * abs(s['R']))
    ax.set_xlim(-2, x2 + (42 if lbl else 4)); ax.set_ylim(lo - (hi - lo) * 0.05, hi + (hi - lo) * 0.07)
    return ax


NOW = pd.Timestamp(sys.argv[2] if len(sys.argv) > 2 else '2026-09-16 13:00')
s = state(NOW)
fp = s['fpos']; abv = s['px'] > max(s['F'], s['M'])
st = ('▲ ' if abv else '▼ ') + 'PAST ' + ('1.5' if fp > 1.5 else '−0.5') if (fp > 1.5 or fp < -0.5) else ('▲ ' if abv else '▼ ') + 'PAST ' + ('1' if fp > 1 else '0') if (fp > 1 or fp < 0) else 'INSIDE'
pc = CH if st == 'INSIDE' else UP if abv else DN
print({k: v for k, v in s.items() if k in ('F', 'fT0', 'M', 'mT0', 'R', 'awr', 'px', 'x', 'PWH', 'PWL', 'wkO', 'fpos', 'tPH', 'tPL')})
print({f: (round(y, 2), t) for f, (y, t) in s['lv'].items()}, {f: (None if p is None else round(p)) for f, p in s['odds'].items()}, s['pwo'])
fig = plt.figure(figsize=(18, 10.4), dpi=100, facecolor=BG)
chart(fig, [0.02, 0.05, 0.63, 0.85], s, NOW, s['fT0'] - pd.Timedelta(hours=8))
card(fig, 0.685, 0.885, ('GETSUGA', 'FRI → MON', f'{NOW:%m/%d} · {NOW:%H:%M} ET', st), rows(s), 0.29, (0.045, 0.095), pill_col=pc)
fig.text(0.02, 0.955, f"Getsuga Tenshō · NQ1! 15-minute, {NOW:%a %-d %b %Y %H:%M} ET · Friday's Shikai mid (1) → Monday's (0) as this week's dealing range", color=CHT, fontsize=13, weight='bold')
fig.text(0.02, 0.928, f"{s['prev'].tday.max():%a %-d %b} mid → {s['cur'].tday.min():%a %-d %b} mid in eighths, SDs at 1.5 / −0.5 (purple), PWH / PWL and the week open as dotted reference lines, the day candles + the week in the Session Map's style. Mock-up from NQ data; TradingView will differ.", color='#5d6476', fontsize=9)
plt.savefig(f'{OUT}/Getsuga_Desktop_15m.png', dpi=100, facecolor=BG); plt.close(fig)
fig = plt.figure(figsize=(7, 10.4), dpi=100, facecolor=BG)
chart(fig, [0.04, 0.05, 0.8, 0.70], s, NOW, s['set_t'] - pd.Timedelta(hours=4), lbl=False)
card(fig, 0.36, 0.95, ('GETSUGA', f'{NOW:%m/%d} {NOW:%H:%M}', '', st), rows(s, mobile=True), 0.6, (0.17, 0.3), fs=8.6, lh=0.034, cw=0.0105, pill_col=pc)
plt.savefig(f'{OUT}/Getsuga_Mobile.png', dpi=100, facecolor=BG); plt.close(fig)
print('done')
