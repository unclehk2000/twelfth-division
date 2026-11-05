"""Sharingan v3 mock: the LTF IPDA layers (QT fractal), the Quarterly Theory quarters and the entry model with its scorecard,
computed the way Sharingan.pine computes them, on NQ minute data. python3 mock_sharingan3.py OUT 'YYYY-MM-DD HH:MM' TF(5|15)"""
import sys, json
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from lay import load, units
plt.rcParams['font.family'] = 'DejaVu Sans'
OUT, NOWS, TF = sys.argv[1], sys.argv[2], int(sys.argv[3])
NOW = pd.Timestamp(NOWS); nowm = int(NOW.value // 60_000_000_000)
BG, MU, GRID, CHT = '#ffffff', '#9aa1b2', '#eef1f6', '#131722'
UP, DN, cH, cL, cF = '#089981', '#f23645', '#d32f2f', '#00897b', '#e53935'
QC = {0: '#787b86', 1: '#ff5252', 2: '#4caf50', 3: '#2962ff'}; QL = 'AMDX'
COEF = json.load(open('reach_coef.json'))
m = load('NQ'); keep = m['ts'] < nowm
m = {k: v[keep] for k, v in m.items()}
fmt = lambda v: f'{v:,.2f}'
LAY = ['M5', 'M15'] if TF == 5 else ['M15', 'H']
UM = {'M1': 1, 'M5': 5, 'M15': 15, 'H': 60}; PER = {'M1': '22.5m', 'M5': '90m', 'M15': '6h', 'H': 'day'}
TRN = {'M5': 0.45, 'M15': 0.25, 'H': 0.0} if TF == 5 else {'M15': 0.25, 'H': 0.0}
# chart bars
key = m['ts'] // TF
st = np.r_[0, np.flatnonzero(np.diff(key) != 0) + 1]
X = pd.DataFrame({'t': m['ts'][st], 'O': m['O'][st], 'H': np.maximum.reduceat(m['H'], st), 'L': np.minimum.reduceat(m['L'], st), 'C': m['C'][np.r_[st[1:] - 1, len(key) - 1]]})
nshow = 300 if TF == 5 else 260
X = X.iloc[-nshow:].reset_index(drop=True); n = len(X)
def ix(t):
    i = np.searchsorted(X.t.values, t, side='right') - 1
    return i + (t - X.t.values[max(i, 0)]) / TF if i >= 0 else -1 + (t - X.t.values[0]) / TF
fig = plt.figure(figsize=(19, 10.6), dpi=100, facecolor=BG)
ax = fig.add_axes([0.01, 0.05, 0.58, 0.84])
for sp in ax.spines.values(): sp.set_visible(False)
ax.set_facecolor(BG); ax.yaxis.tick_right(); ax.tick_params(axis='y', colors=MU, labelsize=8); ax.tick_params(axis='x', length=0); ax.grid(color=GRID, lw=0.7, zorder=0)
for i, q in X.iterrows():
    c = UP if q.C >= q.O else DN
    ax.plot([i, i], [q.L, q.H], color=c, lw=0.7, zorder=4)
    ax.add_patch(Rectangle((i - 0.33, min(q.O, q.C)), 0.66, max(abs(q.C - q.O), 0.25), fc=c, ec=c, lw=0.2, zorder=5))
xm = n - 1 + 6; last = X.C.iloc[-1]
lo_, hi_ = X.L.min(), X.H.max()
# ── layers
rows = []
for Lr in LAY:
    U = units(m, Lr); ps = U['ps']; k = len(ps) - 1
    a = ps[k - 1]; nU = len(U['O']) - 1 - a
    lv = [U['H'][a - N:a].max() for N in (20, 40, 60)] + [U['L'][a - N:a].min() for N in (20, 40, 60)]
    lt = [U['ts'][a - N + np.argmax(U['H'][a - N:a])] for N in (20, 40, 60)] + [U['ts'][a - N + np.argmin(U['L'][a - N:a])] for N in (20, 40, 60)]
    atr = (U['H'][-15:-1] - U['L'][-15:-1]).mean()
    co = COEF[f'{Lr}_h20']; tr = TRN[Lr]
    best = {True: None, False: None}
    for j in range(6):
        v = lv[j]; isH = j < 3
        if j % 3 and lv[j - 1] == v: continue
        nm = ['20', '40', '60'][j % 3]
        for jj in range(j % 3 + 1, 3):
            if lv[(0 if isH else 3) + jj] == v: nm += '/' + ['20', '40', '60'][jj]
        aft = (U['H'][a:] >= v) if isH else (U['L'][a:] <= v)
        sw = np.flatnonzero(aft)
        col = cH if isH else cL; al = 1 - tr
        x0 = ix(lt[j])
        if len(sw):
            tk = U['ts'][a + sw[0]]
            ax.plot([x0, ix(tk)], [v, v], color=col, alpha=al, lw=0.9, ls=':', zorder=3)
            ax.text(ix(tk), v, '✕', color=col, alpha=al, fontsize=8, ha='center', va='center', zorder=6)
        else:
            d = ((v - last) if isH else (last - v)) / atr
            p = 1 / (1 + np.exp(-(co[0] + co[1] * np.log(max(d, 0.02)) + (co[2] if isH else 0)))) if d > 0 else 1
            ax.plot([x0, xm], [v, v], color=col, alpha=al, lw=1.0, zorder=3)
            if lo_ - 30 < v < hi_ + 30:
                ax.text(xm + 0.5, v, f"{Lr} {'BSL' if isH else 'SSL'} {nm} {fmt(v)} · {round(p * 100)}%", color=col, alpha=max(al, 0.6), fontsize=7, va='center', zorder=6)
            if (isH and v > last and (best[True] is None or v < best[True][0])) or (not isH and v < last and (best[False] is None or v > best[False][0])):
                best[isH] = (v, d, p)
            lo_, hi_ = min(lo_, v) if abs(v - last) < 6 * atr else lo_, max(hi_, v) if abs(v - last) < 6 * atr else hi_
    # cast-forward marks
    nxt = None
    for N in (20, 40, 60):
        if a + N < len(U['ts']):
            tm = U['ts'][a + N]
        else:
            tm = U['ts'][-1] + (a + N - (len(U['ts']) - 1)) * UM[Lr]
            if nxt is None: nxt = (N, tm)
        xx = ix(tm)
        if -1 < xx < n + 40:
            ax.axvline(xx, color=cF, alpha=0.5 * (1 - tr) + 0.15, lw=0.8, ls=':', zorder=2)
            ax.text(xx + 0.4, hi_, f'{Lr} +{N}', color=cF, alpha=0.6, fontsize=7, va='bottom')
    rows.append((Lr, best, nxt, atr))
# ── QT quarters: day (6h) and session (90 min) for 5m; week and day for 15m
mod = lambda t: (t + 360) % 1440
def qboxes(kind):
    out = []
    for i, q in X.iterrows():
        t = int(q.t); md = mod(t); td = (t + 360) // 1440
        if kind == 'day': cid, qq = td, md // 360
        elif kind == 'session': cid, qq = td * 4 + md // 360, (md % 360) // 90
        else:
            dw = pd.Timestamp(td * 1440, unit='m').dayofweek
            if dw > 3: continue
            cid, qq = td - dw, dw
        cid, qq = int(cid), int(qq)
        if not out or out[-1][0] != (cid, qq): out.append([(cid, qq), i, i, q.H, q.L, q.O])
        else: o = out[-1]; o[2] = i; o[3] = max(o[3], q.H); o[4] = min(o[4], q.L)
    return out
QTK = ['day', 'session'] if TF == 5 else ['week', 'day']
qnow = {}
for kind in QTK:
    bx = qboxes(kind)
    cyc = sorted(set(b[0][0] for b in bx))[-2:]
    for (cid, qq), i0, i1, h, l, o in bx:
        if cid not in cyc: continue
        ax.add_patch(Rectangle((i0 - 0.5, l), i1 - i0 + 1, h - l, fc=QC[qq], alpha=0.10 if kind != 'session' else 0.13, ec=QC[qq], lw=0.7, zorder=1))
        ax.text(i0 - 0.3, h, QL[qq], color=QC[qq], fontsize=7, va='top', ha='left', zorder=6, alpha=0.9)
        if qq == 1 and cid == cyc[-1]:
            ax.plot([i0 - 0.5, n - 1], [o, o], color=QC[1], ls='--', lw=0.9, alpha=0.8, zorder=3)
            ax.text(n - 0.5, o, {'day': 'true day open', 'session': 'true session open', 'week': 'true week open'}[kind], color=QC[1], fontsize=7, va='center', alpha=0.9)
            qnow[kind] = (QL[[b for b in bx if b[0][0] == cid][-1][0][1]], o)
        elif cid == cyc[-1]:
            qnow.setdefault(kind, (QL[[b for b in bx if b[0][0] == cid][-1][0][1]], None))
# ── entry model: tested trades (t5) in the window, drawn; scorecard over ~70 days of chart bars
T = pd.read_pickle('t5_rows_lvl.pkl') if False else pd.read_pickle('t5_rows.pkl')
tfk = '5-60' if TF == 5 else '15-240'
T = T[(T.sym == 'NQ') & (T.tf == tfk) & (T.filled == 1) & (T.tsC < nowm)].drop_duplicates(['side', 'tsSw', 'E']).copy()
win = T[T.tsC >= nowm - 70 * 1440]
res = np.where(win.preM >= 2, 'NF', np.where(win.mfe >= 2, 'W', 'L'))
W, Lz, NF = (res == 'W').sum(), (res == 'L').sum(), (res == 'NF').sum(); Rt = 2 * W - Lz
vis = T[T.tsC >= X.t.iloc[0]].tail(3)
for _, r in vis.iterrows():
    sgn = r.side; E, S = sgn * r.E, sgn * r.S; R = abs(E - S)
    c = '#0068bd' if sgn == 1 else '#bd0000'
    x0 = ix(r.tsSw); x1 = min(ix(r.tsC) + 25, n + 2)
    ax.plot([x0, x1], [E, E], color=c, lw=1.8, zorder=5); ax.text(x0, E, ('+OB ' if sgn == 1 else '−OB ') + fmt(E), color=c, fontsize=7, va='bottom' if sgn == -1 else 'top', ha='right')
    ax.plot([x0, x1], [S, S], color=c, lw=0.9, ls=':', alpha=0.6, zorder=5)
    for k in (1, 2, 3):
        y = E + sgn * k * R; ax.plot([x0, x1], [y, y], color=c, lw=0.8, alpha=0.45, zorder=5); ax.text(x1 + 0.3, y, f'{k}R', color=c, fontsize=6.5, va='center', alpha=0.8)
    out = 'NF' if r.preM >= 2 else 'W' if r.mfe >= 2 else 'L'
    if r.tsC > nowm - 360: continue      # too recent to know its outcome at this time
    ax.text(x1, E + sgn * (2.6 * R if out == 'W' else -1.4 * R), {'W': '◆', 'L': '✕', 'NF': '◆'}[out], color={'W': '#00a113', 'L': '#ff5252', 'NF': '#ea9023'}[out], fontsize=9, ha='center', va='center', zorder=7)
ticks = [i for i, t in enumerate(X.t) if t % (180 if TF == 5 else 720) == 0]
ax.set_xticks(ticks); ax.set_xticklabels([pd.Timestamp(X.t[i], unit='m').strftime('%H:%M' if TF == 5 else '%a %H:%M') for i in ticks], color=MU, fontsize=8)
pad = (hi_ - lo_) * 0.05; ax.set_xlim(-1, n + 48); ax.set_ylim(lo_ - pad, hi_ + pad)
# ── card (the v3 rows under the v2 header)
CB, CT, CS, ACC = '#ffffff', '#131722', '#4a5163', '#eef1f6'
cr = [('◆ SHARINGAN   NQ1!   ' + f'{NOW:%d %b %Y %H:%M}' + ' · daily rows as in v2 above ↓', None, None, None, 'h')]
for Lr, best, nxt, atr in rows[::-1]:
    bh, bl = best[True], best[False]
    cr.append((f'{Lr} · {PER[Lr]}', f'BSL {fmt(bh[0])} · {bh[1]:.1f} · {round(bh[2]*100)}%' if bh else 'BSL all swept', f'SSL {fmt(bl[0])} · {bl[1]:.1f} · {round(bl[2]*100)}%' if bl else 'SSL all swept',
               f'+{nxt[0]} {pd.Timestamp(nxt[1], unit="m"):%H:%M}' if nxt else '+60 ✓', ''))
qs = lambda k, ab: (f"{k} {qnow[k][0]}" + (f" · {ab} {'▲' if last >= qnow[k][1] else '▼'}" if qnow[k][1] else '')) if k in qnow else ''
cr.append(('QT', qs('week', 'TWO'), qs('day', 'TDO'), qs('session', 'TSO'), ''))
lt_ = T.iloc[-1]; o_ = 'no fill' if lt_.preM >= 2 else '2R ✓' if lt_.mfe >= 2 else 'stopped ✕'
cr.append((f"MODEL {'5m–1H' if TF == 5 else '15m–4H'}", f"{'▲' if lt_.side == 1 else '▼'} {o_} {pd.Timestamp(lt_.tsC, unit='m'):%H:%M %d %b}", 'SMT ES', '', ''))
nr = W + Lz
cr.append(('SCORE', f'W {W} · L {Lz} · NF {NF}', f'win {round(100*W/nr)}% · BE 33%' if nr else 'win —', f"{'+' if Rt >= 0 else ''}{Rt:.1f}R", ''))
x0c, y0c, wc, lh = 0.615, 0.92, 0.38, 0.03
cw = [0.0, 0.072, 0.2, 0.322]
for k, row in enumerate(cr):
    yy = y0c - lh * (k + 1)
    fig.patches.append(Rectangle((x0c, yy), wc, lh, transform=fig.transFigure, fc=ACC if row[-1] == 'h' or k == 0 else CB, ec='#d5dae4', lw=0.6, zorder=10))
    if row[-1] == 'h':
        fig.text(x0c + 0.004, yy + lh / 2, row[0], fontsize=8.2, family='DejaVu Sans Mono', va='center', color=CT, weight='bold', zorder=11); continue
    for c_, txt in enumerate(row[:4]):
        if not txt: continue
        col = CS if c_ == 0 else (cH if txt.startswith('BSL') else cL if txt.startswith('SSL') else CT)
        if row[0] == 'SCORE' and c_ == 3: col = '#26a69a' if Rt >= 0 else '#ef5350'
        fig.text(x0c + 0.004 + cw[c_], yy + lh / 2, txt, fontsize=7.2, family='DejaVu Sans Mono', va='center', color=col, zorder=11)
fig.text(0.01, 0.958, f"Sharingan v3 · NQ1! {TF}-minute · {NOW:%a %-d %b %Y %H:%M} ET · the lower timeframes", color=CHT, fontsize=13, weight='bold')
fig.text(0.01, 0.931, f"Layers {' + '.join(LAY)} (look-back highs / lows with reach odds, ✕ when swept, cast-forward marks), Quarterly Theory {' + '.join(QTK)} quarters (A / M / D / X) with true opens, "
         f"and the {'5m–1H' if TF == 5 else '15m–4H'} entry model's last setups with its scorecard. NQ data; TradingView will differ.", color='#5d6476', fontsize=9)
f = f"{OUT}/Sharingan_v3_{TF}m_{NOW:%Y%m%d_%H%M}.png"; plt.savefig(f, dpi=100, facecolor=BG); plt.close(fig); print('saved', f, 'score', W, Lz, NF, Rt)
