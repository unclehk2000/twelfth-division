"""Getsuga card design iterations (local, no TradingView). State is computed the way the Pine script does, from NQ 1-minute
data. Renders the week card and the NY AM card in candidate layouts, light theme (the chart's Auto theme on a light chart).
python3 cards.py OUTDIR 'YYYY-MM-DD HH:MM'"""
import sys, json
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
OUT = sys.argv[1]; NOW = pd.Timestamp(sys.argv[2] if len(sys.argv) > 2 else '2026-09-16 10:15')
LT = dict(body='#f4f6f9', txt='#131722', sub='#5d6476', head='#1e88e5', ok='#26a69a', up='#26a69a', dn='#ef5350', form='#f9a825', hl='#dbe7fb', line='#1e88e5')
JW = json.load(open('/home/claude/gt/live_v2.json')); JN = json.load(open('/home/claude/gt/ny_coef.json'))
cl = lambda v, a, b: max(a, min(b, v))
fmt = lambda v: f'{v:,.2f}'
gauge = lambda f, n: '█' * int(round(cl(0 if f != f else f, 0, 1) * n)) + '░' * (n - int(round(cl(0 if f != f else f, 0, 1) * n)))
sig = lambda z: 100 / (1 + np.exp(-z))
FXW = [-0.326, 0, 1, 2, 3]


def pWeek(I, a, b, x, d):
    xx = cl(x, -0.326, 4.0); dd = d
    if xx >= 3:
        it = I[4]; dd = d / np.sqrt(max(4 - xx, 0.01))
    else:
        i = 0 if xx < 0 else int(np.floor(xx)) + 1; f = (xx - FXW[i]) / (FXW[i + 1] - FXW[i]); it = I[i] * (1 - f) + I[i + 1] * f
    dc = cl(dd, 0, 3); return sig(it + a * dc + b * np.sqrt(dc))


def pDay(m, mins, d, end):
    """m: model with checkpoints (minutes after 09:30); end: minutes after 09:30 at the horizon (89 = 10:59, 449 = 16:59)."""
    X = [(c // 100 - 9) * 60 + c % 100 - 30 for c in m['ck']]; I = m['ints']
    if mins >= X[-1]:
        it = I[-1]; d = d / np.sqrt(max((end - mins) / (end - X[-1]), 0.01))
    else:
        i = max(0, np.searchsorted(X, mins, side='right') - 1); f = (mins - X[i]) / (X[i + 1] - X[i]); it = I[i] * (1 - f) + I[i + 1] * f
    dc = cl(d, 0, 30); return sig(it + m['dc'] * dc + m['sq'] * np.sqrt(dc))


B = pd.read_pickle('/home/claude/kyw/bars_NQ_all.pkl').query("ts >= '2026-07-01' and ts < '2026-10-10'").set_index('ts')
B['wk'] = B.tday - pd.to_timedelta(B.tday.dt.dayofweek, unit='D')
Q = B.resample('15min').agg(dict(Open='first', High='max', Low='min', Close='last', tday='first', hm='first')).dropna()
tr = np.maximum(Q.High - Q.Low, np.maximum((Q.High - Q.Close.shift()).abs(), (Q.Low - Q.Close.shift()).abs()))
ATR = pd.Series(tr.ewm(alpha=1 / 14, adjust=False).mean().values, index=Q.index + pd.Timedelta(minutes=15))


def mid(day):
    o = Q[(Q.tday == day) & ((Q.hm >= 1800) | (Q.hm < 930))]
    return (o.High.max() + o.Low.min()) / 2, min(o.High.idxmax(), o.Low.idxmin())


def state(NOW):
    b = B[B.index < NOW]; wk = b.wk.iloc[-1]; cur = b[b.wk == wk]; prev = b[b.wk == wk - pd.Timedelta(days=7)]
    wks = sorted(w for w in B.wk.unique() if w < wk)[-4:]; awr = np.mean([B[B.wk == w].High.max() - B[B.wk == w].Low.min() for w in wks])
    F, fT0 = mid(prev.tday.max()); M, mT0 = mid(cur.tday.min()); R = F - M; lvl = lambda f: M + f * R
    set_t = cur[(cur.tday == cur.tday.min()) & (cur.hm == 930)].index[0]; after = cur[cur.index >= set_t]
    hit = lambda y: (lambda m: after.index[m][0] if m.any() else None)((after.Low.values <= y) & (after.High.values >= y))
    px = cur.Close.iloc[-1]; tdi = cur.tday.iloc[-1].dayofweek; dstart = cur.tday.iloc[-1] - pd.Timedelta(hours=6)
    x = tdi - 1 + cl((NOW - dstart).total_seconds() / (23 * 3600), 0, 1)
    today = cur[cur.tday == cur.tday.iloc[-1]]; rth = today[(today.hm >= 930) & (today.hm < 1700)]
    t930 = rth.index[0] if len(rth) else None
    a15 = ATR.asof(t930) if t930 is not None else ATR.asof(NOW)
    mins = (NOW - t930).total_seconds() / 60 if t930 is not None else -1
    s = dict(NOW=NOW, F=F, M=M, R=R, awr=awr, px=px, x=x, PWH=prev.High.max(), PWL=prev.Low.min(), wH=cur.High.max(), wL=cur.Low.min(),
             a15=a15, mins=mins, o930=rth.Open.iloc[0] if len(rth) else None, rH=rth.High.max() if len(rth) else None, rL=rth.Low.min() if len(rth) else None)
    s['tPH'] = (lambda m: cur.index[m][0] if m.any() else None)(cur.High.values > s['PWH'])
    s['tPL'] = (lambda m: cur.index[m][0] if m.any() else None)(cur.Low.values < s['PWL'])
    s['key'] = {f: (lvl(f), hit(lvl(f))) for f in (1.5, 1.0, 0.5, 0.0, -0.5)}
    s['grid'] = [(f, lvl(f)) for f in np.round(np.arange(-1, 2.0001, 0.125), 3)]
    s['fpos'] = (px - M) / R
    return s


NAMES = {1.5: '1.5 SD', 1.0: '1 FRI', 0.5: '0.5 EQ', 0.0: '0 MON', -0.5: '-0.5 SD', 2.0: '2 SD', -1.0: '-1 SD'}
wt = lambda t: f'{t:%a %H:%M}'


def wk_odds(s, y, t):
    return None if t is not None else pWeek(JW['fib']['ints'], JW['fib']['dc'], JW['fib']['sq'], s['x'], abs(y - s['px']) / s['awr'])


def pw_odds(s, side):
    t = s['tPH'] if side == 'H' else s['tPL']
    if t is not None: return None
    d = max(s['PWH'] - s['px'], 0) if side == 'H' else max(s['px'] - s['PWL'], 0)
    return pWeek(JW['pw']['ints'], JW['pw']['dc'], JW['pw']['sq'], s['x'], d / s['awr'])


def draw_table(ax, x0, y0, rows, widths, title_cells, pill, lh=0.034, fs=8.4, cw=0.0052):
    """rows: list of lists of (text, fg, bg, align, bold). Column widths fit the longest text, as a TradingView table does."""
    txt = lambda c: (c[0] if isinstance(c, tuple) else c) or ''
    ncol = len(widths)
    widths = [max([len(txt(r[i])) for r in rows if i < len(r)] + [len(title_cells[i]) if i < len(title_cells) else 0, len(pill[0]) if pill and i == ncol - 1 else 0]) * cw + 0.014 for i in range(ncol)]
    W = sum(widths); xs = np.cumsum([0] + widths[:-1]) + x0
    ax.add_patch(Rectangle((x0, y0 - lh), W, lh, fc=LT['head'], ec='none'))
    for i, tx in enumerate(title_cells):
        if tx: ax.text(xs[i] + 0.006, y0 - lh / 2, tx, color='#ffffff', fontsize=fs, family='DejaVu Sans Mono', va='center', weight='bold' if i == 0 else 'normal')
    if pill:
        pw = widths[-1]; ax.add_patch(Rectangle((xs[-1], y0 - lh), pw, lh, fc='#ffffff', ec='none'))
        ax.text(xs[-1] + pw / 2, y0 - lh / 2, pill[0], color=pill[1], fontsize=fs, family='DejaVu Sans Mono', va='center', ha='center')
    for r, row in enumerate(rows):
        yy = y0 - lh * (r + 2)
        for i, cell in enumerate(row):
            c5 = list(cell) if isinstance(cell, tuple) else [cell]
            tx, fg, bg, al, bold = c5 + ['', None, None, 'left', False][len(c5):]
            ax.add_patch(Rectangle((xs[i], yy), widths[i], lh, fc=bg or LT['body'], ec='none'))
            xx = xs[i] + (widths[i] - 0.006 if al == 'right' else 0.006)
            ax.text(xx, yy + lh / 2, tx, color=fg or LT['txt'], fontsize=fs, family='DejaVu Sans Mono', va='center', ha=al, weight='bold' if bold else 'normal')
    ax.add_patch(Rectangle((x0, y0 - lh * (len(rows) + 1)), W, lh * (len(rows) + 1), fc='none', ec=LT['head'], lw=1.2))
    return x0 + W


def res_cell(t, p, today=False):
    if t is not None:
        return ('✓ ' + (f'{t:%H:%M}' if today else wt(t)), '#ffffff', LT['ok'], 'right', True)
    return (f'{round(p)}% by Fri' if p is not None else '—', None, None, 'right')


def week_A(s):           # the current layout
    rr = abs(s['R']) / s['awr']; lo, hi = min(s['F'], s['M']), max(s['F'], s['M']); fp = s['fpos']
    rows = [[('RANGE', LT['sub']), (gauge(rr, 10), LT['head']), f"{fmt(s['F'])} → {fmt(s['M'])}", (f"{fmt(abs(s['R']))} pts · {rr:.2f}× AWR4", None, None, 'right')],
            [('NOW', LT['sub']), (gauge((s['px'] - lo) / (hi - lo), 10), LT['head']), f"{np.floor(fp * 8) / 8:g} – {np.floor(fp * 8) / 8 + .125:g}", (fmt(s['px']), None, None, 'right')]]
    order = (1.5, 1.0, 0.5, 0.0, -0.5) if s['R'] > 0 else (-0.5, 0.0, 0.5, 1.0, 1.5)
    for f in order:
        y, t = s['key'][f]; rows.append([(NAMES[f], LT['sub']), '', fmt(y) + ('' if t else f" · {abs(y - s['px']) / s['awr']:.2f}× away"), res_cell(t, wk_odds(s, y, t))])
    rows.append([('PWH', LT['sub']), '', fmt(s['PWH']), res_cell(s['tPH'], pw_odds(s, 'H'))])
    rows.append([('PWL', LT['sub']), '', fmt(s['PWL']), res_cell(s['tPL'], pw_odds(s, 'L'))])
    rows.append([('WEEK', LT['sub']), (gauge((s['wH'] - s['wL']) / s['awr'], 10), LT['head']), f"{fmt(s['wH'] - s['wL'])} pts so far", (f"{(s['wH'] - s['wL']) / s['awr']:.2f}× AWR4", None, None, 'right')])
    return rows, [0.06, 0.08, 0.20, 0.13], ['GETSUGA', 'FRI → MON', f"{s['NOW']:%m/%d} · {s['NOW']:%H:%M} ET"]


def week_B(s):           # the ladder: every level and PWH / PWL in price order, with price slotted in
    rr = abs(s['R']) / s['awr']
    items = [(NAMES[f], y, t, wk_odds(s, y, t), 'fib') for f, (y, t) in s['key'].items()]
    items += [('PWH', s['PWH'], s['tPH'], pw_odds(s, 'H'), 'pw'), ('PWL', s['PWL'], s['tPL'], pw_odds(s, 'L'), 'pw')]
    items.sort(key=lambda z: -z[1])
    rows = [[('RANGE', LT['sub']), (gauge(rr, 8), LT['head']), f"{fmt(s['F'])} → {fmt(s['M'])}", (f"{fmt(abs(s['R']))} · {rr:.2f}× AWR4", None, None, 'right')]]
    placed = False
    for nm, y, t, p, kind in items:
        if not placed and y < s['px']:
            rows.append([('▸ PRICE', LT['head'], LT['hl'], 'left', True), ('', None, LT['hl']), (f"{fmt(s['px'])} · at {s['fpos']:.2f}", LT['txt'], LT['hl'], 'left', True), ('', None, LT['hl'])]); placed = True
        d = abs(y - s['px']) / s['awr']
        rows.append([(nm, LT['sub'] if kind == 'fib' else '#9598a1'), ('' if t else (gauge(1 - d / 0.5, 8), LT['head'] if y > s['px'] else LT['dn'])), fmt(y) + ('' if t else f" · {d:.2f}×"), res_cell(t, p)])
    if not placed:
        rows.append([('▸ PRICE', LT['head'], LT['hl'], 'left', True), ('', None, LT['hl']), (f"{fmt(s['px'])} · at {s['fpos']:.2f}", LT['txt'], LT['hl'], 'left', True), ('', None, LT['hl'])])
    rows.append([('WEEK', LT['sub']), (gauge((s['wH'] - s['wL']) / s['awr'], 8), LT['head']), f"{fmt(s['wH'] - s['wL'])} pts so far", (f"{(s['wH'] - s['wL']) / s['awr']:.2f}× AWR4", None, None, 'right')])
    return rows, [0.062, 0.07, 0.19, 0.12], ['GETSUGA', 'WEEK', f"{s['NOW']:%m/%d} · {s['NOW']:%H:%M} ET"]


def week_C(s):           # compact
    rr = abs(s['R']) / s['awr']
    up = [(NAMES[f], y, t) for f, (y, t) in s['key'].items() if y > s['px']]; dn = [(NAMES[f], y, t) for f, (y, t) in s['key'].items() if y < s['px']]
    na = min(up, key=lambda z: z[1]) if up else None; nb = max(dn, key=lambda z: z[1]) if dn else None
    done = ' · '.join(f"{NAMES[f].split()[0]} {t:%a}" for f, (y, t) in s['key'].items() if t is not None)
    rows = [[('RANGE', LT['sub']), (gauge(rr, 8), LT['head']), f"{fmt(s['F'])} → {fmt(s['M'])}", (f"{rr:.2f}× AWR4", None, None, 'right')],
            [('ABOVE', LT['sub']), '', f"{na[0]} {fmt(na[1])}" if na else '—', res_cell(na[2], wk_odds(s, na[1], na[2])) if na else '—'],
            [('PRICE', LT['head'], None, 'left', True), '', f"{fmt(s['px'])} · at {s['fpos']:.2f}", ''],
            [('BELOW', LT['sub']), '', f"{nb[0]} {fmt(nb[1])}" if nb else '—', res_cell(nb[2], wk_odds(s, nb[1], nb[2])) if nb else '—'],
            [('TRADED', LT['sub']), '', done or '—', ''],
            [('PW', LT['sub']), '', f"▲ {fmt(s['PWH'])} · ▼ {fmt(s['PWL'])}", (('✓' if s['tPH'] else f"{round(pw_odds(s, 'H'))}%") + ' · ' + ('✓' if s['tPL'] else f"{round(pw_odds(s, 'L'))}%"), None, None, 'right')],
            [('WEEK', LT['sub']), (gauge((s['wH'] - s['wL']) / s['awr'], 8), LT['head']), f"{fmt(s['wH'] - s['wL'])} pts", (f"{(s['wH'] - s['wL']) / s['awr']:.2f}× AWR4", None, None, 'right')]]
    return rows, [0.062, 0.07, 0.20, 0.11], ['GETSUGA', 'WEEK', f"{s['NOW']:%m/%d} · {s['NOW']:%H:%M}"]


def ny_levels(s):
    """The two nearest grid levels above and below price, with today's odds (by 11:00 and by 16:59) or ✓ if traded today."""
    g = s['grid']; px = s['px']; KEYF = (1.5, 1.0, 0.5, 0.0, -0.5)
    up8 = sorted([z for z in g if z[1] > px], key=lambda z: z[1])[:1]; dn8 = sorted([z for z in g if z[1] < px], key=lambda z: -z[1])[:1]
    upk = sorted([z for z in g if z[1] > px and z[0] in KEYF], key=lambda z: z[1])[:1]; dnk = sorted([z for z in g if z[1] < px and z[0] in KEYF], key=lambda z: -z[1])[:1]
    up = sorted({z[0]: z for z in up8 + upk}.values(), key=lambda z: z[1]); dn = sorted({z[0]: z for z in dn8 + dnk}.values(), key=lambda z: -z[1])
    out = []
    for f, y in up[::-1] + dn:
        traded = s['rL'] is not None and s['rL'] <= y <= s['rH']
        d = abs(y - px) / s['a15']
        am = None if traded or s['mins'] >= 89 or s['mins'] < 0 else pDay(JN['am'], max(s['mins'], 0), d, 89)
        dy = None if traded or s['mins'] < 0 else pDay(JN['day'], max(s['mins'], 0), d, 449)
        nm = NAMES.get(f, f'{f:g}')
        out.append((nm, f, y, d, am, dy, traded, y > px))
    return out


def ny_A(s):             # matrix: level | price | away | by 11:00 | by 16:59
    L = ny_levels(s); rows = []
    hdr = [('', LT['sub']), ('PRICE', LT['sub']), ('AWAY', LT['sub'], None, 'right'), ('11:00', LT['sub'], None, 'right'), ('16:59', LT['sub'], None, 'right')]
    rows.append(hdr)
    placed = False
    for nm, f, y, d, am, dy, traded, above in L:
        if not placed and not above:
            rows.append([('▸ NOW', LT['head'], LT['hl'], 'left', True), (fmt(s['px']), LT['txt'], LT['hl'], 'left', True), ('', None, LT['hl']), ('', None, LT['hl']), ('', None, LT['hl'])]); placed = True
        tag = ('▲ ' if above else '▼ ') + nm
        if traded:
            rows.append([(tag, LT['sub']), fmt(y), (f'{d:.1f} ATR', None, None, 'right'), ('✓ today', '#ffffff', LT['ok'], 'right', True), ('✓', '#ffffff', LT['ok'], 'right', True)])
        else:
            rows.append([(tag, LT['sub']), fmt(y), (f'{d:.1f} ATR', None, None, 'right'), (f'{round(am)}%' if am is not None else '—', None, None, 'right'), (f'{round(dy)}%' if dy is not None else '—', None, None, 'right')])
    KEYF = (1.5, 1.0, 0.5, 0.0, -0.5)
    ku = [z for z in L if z[7] and z[1] in KEYF]; kd = [z for z in L if not z[7] and z[1] in KEYF]
    pu = None
    if ku and kd:
        du, dd = ku[-1][2] - s['px'], s['px'] - kd[0][2]; pu = 100 * dd / (du + dd)
    if pu is not None:
        rows.append([('FIRST', LT['sub']), (f"▲ {ku[-1][0]}", LT['up']), (f"{round(pu)}%", LT['up'], None, 'right'), (f"▼ {kd[0][0]}", LT['dn'], None, 'right'), (f"{round(100 - pu)}%", LT['dn'], None, 'right')])
    rows.append([('ATR15', LT['sub']), fmt(s['a15']), ('', None), ('', None), ('', None)])
    return rows, [0.07, 0.085, 0.06, 0.06, 0.055], ['NY AM', '15M', f"{s['NOW']:%H:%M}", '', '']


def ny_B(s):             # 4-column tally, house style
    L = ny_levels(s); rows = []
    rows.append([('ATR15', LT['sub']), '', fmt(s['a15']) + ' pts', ((f"open {fmt(s['o930'])}" if s['o930'] else 'pre-market'), None, None, 'right')])
    for nm, f, y, d, am, dy, traded, above in L:
        tag = ('▲ ' if above else '▼ ') + nm
        rv = ('✓ today', '#ffffff', LT['ok'], 'right', True) if traded else ((f"AM {round(am)}% · day {round(dy)}%" if am is not None else f"day {round(dy)}%"), None, None, 'right')
        rows.append([(tag, LT['sub']), (gauge(1 - d / 4, 6), LT['up'] if above else LT['dn']), f"{fmt(y)} · {d:.1f}×", rv])
    KEYF = (1.5, 1.0, 0.5, 0.0, -0.5)
    ku = [z for z in L if z[7] and z[1] in KEYF]; kd = [z for z in L if not z[7] and z[1] in KEYF]
    pu = None
    if ku and kd:
        du, dd = ku[-1][2] - s['px'], s['px'] - kd[0][2]; pu = 100 * dd / (du + dd)
    if pu is not None:
        rows.append([('FIRST', LT['sub']), (gauge(pu / 100, 6), LT['up']), f"▲ {ku[-1][0]} vs ▼ {kd[0][0]}", (f"▲ {round(pu)}% · ▼ {round(100 - pu)}%", None, None, 'right')])
    return rows, [0.065, 0.06, 0.19, 0.125], ['NY AM', '15M', f"{s['NOW']:%m/%d} · {s['NOW']:%H:%M} ET"]


if __name__ == '__main__':
    s = state(NOW)
    fig = plt.figure(figsize=(16, 11), dpi=100, facecolor='#e9ebef'); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    ax.text(0.02, 0.975, f"Getsuga card iterations · NQ1! {NOW:%a %-d %b %Y %H:%M} ET · light theme", fontsize=13, weight='bold', color=LT['txt'])
    y = 0.94; x0 = 0.02; fp = s['fpos']
    for lbl, fn in (('W-A  current', week_A), ('W-B  ladder (price slotted in)', week_B), ('W-C  compact', week_C)):
        ax.text(x0, y, lbl, fontsize=10, color=LT['sub'], weight='bold')
        rows, wd, title = fn(s)
        x0 = draw_table(ax, x0, y - 0.01, rows, wd, title + [''] * (len(wd) - len(title) - 1), ('INSIDE' if 0 <= fp <= 1 else 'PAST', LT['head']), fs=7.6, lh=0.03, cw=0.0047) + 0.02
    y = 0.5; x0 = 0.02
    for lbl, fn in (('N-A  matrix', ny_A), ('N-B  tally', ny_B)):
        ax.text(x0, y, lbl, fontsize=10, color=LT['sub'], weight='bold')
        rows, wd, title = fn(s)
        x0 = draw_table(ax, x0, y - 0.01, rows, wd, title + [''] * (len(wd) - len(title) - 1), ('AM' if 0 <= s['mins'] < 90 else 'PM' if s['mins'] >= 90 else 'PRE', LT['head']), fs=7.6, lh=0.03, cw=0.0047) + 0.03
    plt.savefig(f'{OUT}/cards_iter{sys.argv[3] if len(sys.argv) > 3 else 1}.png', dpi=100, facecolor='#e9ebef'); plt.close(fig)
    print({k: s[k] for k in ('px', 'a15', 'mins', 'o930', 'rH', 'rL', 'fpos')})


def week_B2(s):
    rr = abs(s['R']) / s['awr']; fp = s['fpos']
    items = [(NAMES[f], y, t, wk_odds(s, y, t), 'fib') for f, (y, t) in s['key'].items()]
    items += [('PWH', s['PWH'], s['tPH'], pw_odds(s, 'H'), 'pw'), ('PWL', s['PWL'], s['tPL'], pw_odds(s, 'L'), 'pw')]
    items.sort(key=lambda z: -z[1])
    rows = [[('RANGE', LT['sub']), (gauge(rr, 8), LT['head']), f"{fmt(s['F'])} → {fmt(s['M'])}", (f"{fmt(abs(s['R']))} · {rr:.2f}× AWR4", None, None, 'right')]]
    prow = [('▸ PRICE', LT['head'], LT['hl'], 'left', True), ('', None, LT['hl']), (f"{fmt(s['px'])} · at {fp:.2f}", LT['txt'], LT['hl'], 'left', True),
            ('inside' if 0 <= fp <= 1 else 'past ' + ('1' if (fp > 1) else '0'), LT['head'], LT['hl'], 'right', True)]
    placed = False
    for nm, y, t, p, kind in items:
        if not placed and y < s['px']:
            rows.append(prow); placed = True
        d = abs(y - s['px']) / s['awr']; above = y > s['px']
        rows.append([(nm, LT['sub'] if kind == 'fib' else '#9598a1'), ('' if t else (gauge(1 - d / 0.5, 8), LT['up'] if above else LT['dn'])),
                     fmt(y) + ('' if t else f" · {d:.2f}×"), res_cell(t, p)])
    if not placed:
        rows.append(prow)
    rows.append([('WEEK', LT['sub']), (gauge((s['wH'] - s['wL']) / s['awr'], 8), LT['head']), f"{fmt(s['wH'] - s['wL'])} pts so far", (f"{(s['wH'] - s['wL']) / s['awr']:.2f}× AWR4", None, None, 'right')])
    return rows, [0] * 4, ['GETSUGA', 'WEEK', f"{s['NOW']:%m/%d} · {s['NOW']:%H:%M} ET"]


def ny_A2(s):
    L = ny_levels(s); m = s['mins']
    rows = [[('', LT['sub']), ('PRICE', LT['sub']), ('×ATR15', LT['sub'], None, 'right'), ('11:00', LT['sub'], None, 'right'), ('16:59', LT['sub'], None, 'right')]]
    prow = [('▸ NOW', LT['head'], LT['hl'], 'left', True), (fmt(s['px']), LT['txt'], LT['hl'], 'left', True), ('', None, LT['hl']), ('', None, LT['hl']), ('', None, LT['hl'])]
    placed = False
    for nm, f, y, d, am, dy, traded, above in L:
        if not placed and not above:
            rows.append(prow); placed = True
        tag = ('▲ ' if above else '▼ ') + nm
        if traded:
            rows.append([(tag, LT['sub']), fmt(y), (f'{d:.1f}', None, None, 'right'), ('✓ today', '#ffffff', LT['ok'], 'right', True), ('', '#ffffff', LT['ok'])])
        else:
            rows.append([(tag, LT['sub']), fmt(y), (f'{d:.1f}', None, None, 'right'), (f'{round(am)}%' if am is not None else '—', None, None, 'right'), (f'{round(dy)}%' if dy is not None else '—', None, None, 'right')])
    if not placed:
        rows.append(prow)
    KEYF = (1.5, 1.0, 0.5, 0.0, -0.5)
    ku = [z for z in L if z[7] and z[1] in KEYF]; kd = [z for z in L if not z[7] and z[1] in KEYF]
    if ku and kd:
        du, dd = ku[-1][2] - s['px'], s['px'] - kd[0][2]; pu = 100 * dd / (du + dd)
        rows.append([('FIRST', LT['sub']), (f"▲ {ku[-1][0]}", LT['up']), (f"{round(pu)}%", LT['up'], None, 'right'), (f"▼ {kd[0][0]}", LT['dn'], None, 'right'), (f"{round(100 - pu)}%", LT['dn'], None, 'right')])
    rows.append([('OPEN', LT['sub']), fmt(s['o930']) if s['o930'] else '—', (f"at {(s['o930'] - s['M']) / s['R']:.2f}" if s['o930'] else '', None, None, 'right'), ('ATR15', LT['sub'], None, 'right'), (fmt(s['a15']), None, None, 'right')])
    return rows, [0] * 5, ['NY AM', '', f"{s['NOW']:%H:%M} ET", '']


def sheet(times, out):
    fig = plt.figure(figsize=(16, 11), dpi=100, facecolor='#e9ebef'); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    ax.text(0.02, 0.975, 'Getsuga card iteration 3 · week ladder (top) + NY AM matrix (bottom), two moments of the same day', fontsize=13, weight='bold', color=LT['txt'])
    x0 = 0.02
    for t in times:
        s = state(pd.Timestamp(t)); fp = s['fpos']
        ax.text(x0, 0.94, f"NQ1! {s['NOW']:%a %-d %b %H:%M} ET", fontsize=10, color=LT['sub'], weight='bold')
        r1, w1, t1 = week_B2(s)
        xe = draw_table(ax, x0, 0.93, r1, w1, t1, ('INSIDE' if 0 <= fp <= 1 else 'PAST', LT['head']), fs=7.6, lh=0.03, cw=0.0047)
        r2, w2, t2 = ny_A2(s)
        st = 'AM' if 0 <= s['mins'] < 90 else 'PM' if 90 <= s['mins'] < 450 else 'PRE'
        xe2 = draw_table(ax, x0, 0.93 - 0.03 * (len(r1) + 1) - 0.04, r2, w2, t2, (st, LT['head']), fs=7.6, lh=0.03, cw=0.0047)
        x0 = max(xe, xe2) + 0.04
    plt.savefig(out, dpi=100, facecolor='#e9ebef'); plt.close(fig)
