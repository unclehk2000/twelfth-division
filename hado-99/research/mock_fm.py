"""Hadō 99 v3 mocks: the fractal module drawn from fm_sim (a bar-by-bar mirror of the Pine), card rows built as the
Pine builds them, macro rows from mock_ttk. NQ 1m with 15m candles (17 Jun 2026) and NQ 1H with daily candles (28 Apr 2026)."""
import sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0, '/home/claude/sb'); sys.path.insert(0, '/home/claude/xa')
from mock_sb2 import lum
from fm_sim import run, PJ
import mock_ttk as TT
OUT = sys.argv[1]
M = pd.Timedelta(minutes=1)
YPAD = 0.32
BULL, BEAR = '#2962ff', '#f23645'
TAKE = {0: [21, 36, 55, 78], 1: [20, 39, 58, 83]}
TAKEQ = {0: [21, 35, 47, 64], 1: [19, 38, 52, 70]}
HOLD = {0: [28, 48, 67, 82], 1: [19, 46, 65, 81]}
PROJ = {0: [72, 46, 36, 20, 16], 1: [80, 57, 49, 32, 28]}
def prot_hold(left):
    return 93 if left <= 5 else 77 if left <= 10 else 64 if left <= 15 else 52 if left <= 20 else 39
def kf(k):
    return ('%g' % k)
def px(v):
    return f'{v:,.2f}'.replace(',', '')

def fm_rows(st, P, nm, mob, test=True, dxy=None):
    fss = st['fss']
    R = []
    if not fss:
        return [('C2', f'waiting for a {nm} sweep and close back', '', None)]
    s = fss[-1]; bl = s.bull; sc = BULL if bl else BEAR; hs = 'high' if bl else 'low'
    when = (lambda t: (t + pd.Timedelta(hours=6)).strftime('%m/%d')) if P == 1 else (lambda t: t.strftime('%H:%M'))
    pc = round(s.clv * 100)
    R.append(('C2', ('▲ ' if bl else '▼ ') + ('' if mob else ('bull · ' if bl else 'bear · ')) + when(s.t2) + f' · closed {pc}% ' + ('up' if bl else 'down'),
              'in C3' if s.phase == 3 else 'in C4' if s.phase == 4 else 'done', sc))
    if s.took:
        c3 = "✓ took " + ('' if mob else "C2's ") + hs + ' ' + s.tookT.strftime('%H:%M')
    elif s.phase == 3:
        c3 = (('at EQ · ' if mob else 'back at EQ · ') if s.eqHit else '') + (hs + ' ' if mob else f"takes C2's {hs} ") + str((TAKEQ if s.eqHit else TAKE)[P][s.q]) + '%'
    else:
        c3 = f"✗ didn't take C2's {hs}"
    R.append(('C3', c3, '' if mob else px(s.opp), sc if s.took else None))
    lv = ('✗ taken ' + s.deadT.strftime('%H:%M')) if s.dead else (f'holds through C3 {HOLD[P][s.q]}%' if s.phase == 3 else 'held')
    R.append(('C2 LOW' if bl else 'C2 HIGH', lv, px(s.ext), '#787b86' if s.dead else None))
    cv = ('✓ ' + ('in C2 (early)' if s.cisdC2 else s.cisdT.strftime('%H:%M'))) if s.cisd else '—' if s.lvl is None else '✗ C2 broken first' if s.dead else 'waiting'
    R.append(('CISD', cv, px(s.lvl) if s.lvl is not None else '—', sc if s.cisd else None))
    if P == 0 and dxy is not None:
        dchg, dz = dxy
        dv = ('with C2' if dz > 0.5 else 'against C2' if dz < -0.5 else 'flat') + ' · ' + ('▲ ' if dchg >= 0 else '▼ ') + f'{abs(dchg):.2f}%' + ('' if mob else f' ({abs(dz):.1f} sd)')
        dw = ('hold +1.7 · take +1.3' if s.phase == 3 else 'hold +1.7') if dz > 0.5 else 'no edge'
        R.append(('DXY', dv, '' if mob else dw, sc if dz > 0.5 else None))
    if s.cisd and s.pjHit:
        tv = ' · '.join('+' + kf(k) + (' ✓' if s.pjHit[i] else f' {PROJ[P][i]}%' if test else '') for i, k in enumerate(PJ) if i < 4)
        R.append(('TARGETS', tv, '', None))
    if s.cisd:
        pv = ('✗ taken' if s.pTaken else 'holding ' + px(s.pPx)) if s.pDone else '—' if s.dead else 'forming'
        pw = '' if (not s.pDone or s.pTaken) else 'held' if s.phase == 0 else f'to C4 end {prot_hold(s.pLeft)}%' if (P == 0 and test) else 'untested'
        R.append(('PROTECT', pv, pw, sc if s.pDone and not s.pTaken else None))
    return R

def draw_card(fig, ax, head, rows, dark, fs, corner='tr', mono=True):
    hd0, hd1, pill, hc, pillTx, pillBg = head
    fam = 'DejaVu Sans Mono' if mono else 'DejaVu Sans'
    cBody, cTxt, cSub, cSec = ('#161a23', '#d1d4dc', '#8a93a6', '#1f2430') if dark else ('#f4f6f9', '#131722', '#5d6476', '#e6eaf0')
    W, H = fig.get_size_inches(); rd = fig.canvas.get_renderer()
    def tw(s):
        t = fig.text(0, 0, s, fontsize=fs, family=fam); w_ = t.get_window_extent(rd).width / fig.dpi / W; t.remove(); return w_
    cw = 0.6 * fs / 72 / W; lh = 1.75 * fs / 72 / H
    lab = lambda k: k[1:] if k.startswith('§') else k
    cols = [max(tw(hd0), *(tw(lab(r[0])) for r in rows)), max(tw(hd1), *(tw(r[1]) for r in rows)), max(tw(pill), *(tw(r[2]) for r in rows))]
    wcol = [c + 1.6 * cw for c in cols]; w = sum(wcol)
    bb = ax.get_position()
    x0 = bb.x1 - w - 0.006 if corner in ('tr', 'br') else bb.x0 + 0.004
    y0 = bb.y1 - 0.008 if corner in ('tr', 'tl') else bb.y0 + 0.008 + lh * (len(rows) + 1)
    ht = '#131722' if lum(hc) > 165 else '#ffffff'
    fig.patches.append(Rectangle((x0, y0 - lh), w, lh, transform=fig.transFigure, fc=hc, ec='none', zorder=10))
    fig.text(x0 + 0.8 * cw, y0 - lh / 2, hd0, color=ht, fontsize=fs, family=fam, va='center', zorder=11)
    fig.text(x0 + wcol[0] + 0.8 * cw, y0 - lh / 2, hd1, color=ht, fontsize=fs, family=fam, va='center', zorder=11)
    fig.patches.append(Rectangle((x0 + wcol[0] + wcol[1], y0 - lh), wcol[2], lh, transform=fig.transFigure, fc=pillBg, ec='none', zorder=10))
    fig.text(x0 + wcol[0] + wcol[1] + wcol[2] / 2, y0 - lh / 2, pill, color=pillTx, fontsize=fs, family=fam, va='center', ha='center', zorder=11)
    for k, (a, v, ww, c) in enumerate(rows):
        yy = y0 - lh * (k + 2); sec = a.startswith('§')
        fig.patches.append(Rectangle((x0, yy), w, lh, transform=fig.transFigure, fc=cSec if sec else cBody, ec='none', zorder=10))
        fig.text(x0 + 0.8 * cw, yy + lh / 2, lab(a), color=cTxt if sec else cSub, fontsize=fs, family=fam, va='center', zorder=11)
        fig.text(x0 + wcol[0] + 0.8 * cw, yy + lh / 2, v, color=c or cTxt, fontsize=fs, family=fam, va='center', zorder=11)
        fig.text(x0 + w - 0.8 * cw, yy + lh / 2, ww, color=c or cTxt, fontsize=fs, family=fam, va='center', ha='right', zorder=11)
    fig.patches.append(Rectangle((x0, y0 - lh * (len(rows) + 1)), w, lh * (len(rows) + 1), transform=fig.transFigure, fc='none', ec=hc, lw=1, alpha=0.7, zorder=12))

def chart(ax, w, st, nvis, fs, dark, P, nm, off=5, nprev=4, left_txt='', xfmt='%H:%M', tick=lambda t: t.minute in (0, 30), test=True, ypad=0.32, xshift=pd.Timedelta(0), pv=None):
    bg, fg, grid = ('#131722', '#d1d4dc', '#1e222d') if dark else ('#ffffff', '#131722', '#eef1f6')
    ax.set_facecolor(bg)
    O, H, L, C = (w[k].to_numpy() for k in ('O', 'H', 'L', 'C')); ts = list(w.t)
    n = len(O); b0 = n - nvis; X = lambda b: b - b0
    for b in range(b0, n):
        c = '#089981' if C[b] >= O[b] else '#f23645'
        ax.plot([X(b)] * 2, [L[b], H[b]], color=c, lw=0.6, zorder=2)
        ax.add_patch(Rectangle((X(b) - 0.32, min(O[b], C[b])), 0.64, max(abs(C[b] - O[b]), (H[b] - L[b]) * 0.02 + 0.01), fc=c, ec=c, lw=0.3, zorder=2))
    lo, hi = L[b0:].min(), H[b0:].max(); rg = hi - lo
    ylo, yhi = lo - rg * 0.12, hi + rg * ypad
    fsz = fs * 0.95
    for s in st['fss']:
        col = BULL if s.bull else BEAR
        if s.bExt < b0:
            continue
        dn = s.bull
        # C2 label and the sweep
        ax.text(X(s.bExt), s.ext + (-1 if dn else 1) * rg * 0.012, 'XC2' if s.dead else 'C2', color='#787b86' if s.dead else col, fontsize=fsz, ha='center', va='top' if dn else 'bottom', weight='bold', zorder=6)
        ax.plot([X(max(s.c1x, b0)), X(s.bExt)], [s.c1y] * 2, color='#787b86' if s.dead else col, alpha=0.7, lw=1, zorder=3)
        x2 = s.x2
        # EQ and T-spot
        if not s.dead:
            ax.plot([X(s.b3), X(x2 + 1)], [s.eq] * 2, color=fg, alpha=0.6, lw=0.9, ls=':', zorder=3)
            ax.add_patch(Rectangle((X(s.b3), min(s.open3, s.eq)), (s.boxR or x2) - s.b3 + 1, abs(s.open3 - s.eq), fc='#787b86' if s.dead else col, alpha=0.1, ec='none', zorder=1))
        if s.cisd:
            cc = '#787b86' if s.dead else col
            ax.plot([X(max(s.cisdX0, b0)), X(x2)], [s.lvl] * 2, color=cc, alpha=0.6 if s.dead else 1, lw=2, zorder=4)
            if not s.dead:
                ax.text(X(x2) + 0.6, s.lvl, 'CISD · in C2' if s.cisdC2 else 'CISD', color=cc, fontsize=fsz, va='center', zorder=6)
            if s.pj and not s.dead:
                for i, y in enumerate(s.pj):
                    if y > yhi or y < ylo:
                        continue
                    ax.plot([X(s.pjX0), X(x2 + 1)], [y] * 2, color=col, alpha=0.6, lw=0.9, ls=(0, (1, 2)), zorder=3)
                    t = '+' + kf(PJ[i]) + (' ✓' if s.pjHit[i] else (f' · {PROJ[P][i]}%' if test else ''))
                    ax.text(X(x2 + 1) + 0.6, y, t, color=col, alpha=0.85, fontsize=fsz * 0.92, va='center', zorder=6)
        if s.pDone:
            ax.text(X(s.pB), s.pPx + (-1 if dn else 1) * rg * 0.01, '●', color='#787b86' if s.pTaken else col, fontsize=fsz * 1.1, ha='center', va='top' if dn else 'bottom', zorder=6)
    for bull, e in st['early'].items():
        if e:
            col = BULL if bull else BEAR
            ax.plot([X(e[0]), X(e[2])], [e[1]] * 2, color=col, lw=1, ls='--', zorder=4)
    # HTF candles right of price (PO3), as the Pine draws them from the "HTF candles (PO3)" settings
    pv = dict(dict(style='model', w=0, g=0, wick=1, tags=True, stamps=True, info=True, live=True, opn=False, hl=False, sep=False,
                   body=('#a5d6a7', '#2e2e2e'), border=('#2e2e2e', '#2e2e2e'), wickc=('#2e2e2e', '#2e2e2e')), **(pv or {}))
    hcs = st['hcs']; k = min(nprev, len(hcs)); last = n - 1
    s = st['fss'][-1] if st['fss'] else None
    i2 = next((m for m, h in enumerate(hcs) if s is not None and h.t0 == s.t2), -1)
    top = max(h.h for h in hcs[:k]); bot = min(h.l for h in hcs[:k])
    tsec = 60 if P == 0 else 3600
    W_ = pv['w'] or (6 if tsec <= 120 else 4 if tsec <= 300 else 2); G_ = pv['g'] or (3 if tsec <= 120 else 2)
    x0 = X(last) + off; xE = x0 + (k - 1) * (W_ + G_) + W_
    tgDn = s is None or s.bull; tagC = fg if s is None else (BULL if s.bull else BEAR); subC = '#8a93a6' if dark else '#5d6476'
    def alpha(hexc, tr): return hexc, (100 - tr) / 100
    for j in range(k):
        mm = k - 1 - j; h = hcs[mm]; up = h.c >= h.o
        x1 = x0 + j * (W_ + G_); xm = x1 + W_ // 2
        mc = BULL if up else BEAR
        if pv['style'] == 'custom':
            bd, br, wk = (pv['body'][0 if up else 1], 1), (pv['border'][0 if up else 1], 1), (pv['wickc'][0 if up else 1], 1)
        elif pv['style'] == 'ict':
            bd = ('#a5d6a7', 1) if up else (fg, 1); br = (fg, 1); wk = (fg, 1)
        else:
            bd, br, wk = alpha(mc, 70), alpha(mc, 30), alpha(mc, 30)
        bt, bb = max(h.o, h.c), min(h.o, h.c)
        if h.h > bt: ax.plot([xm, xm], [bt, h.h], color=wk[0], alpha=wk[1], lw=0.9 * pv['wick'], zorder=3, solid_capstyle='butt')
        if h.l < bb: ax.plot([xm, xm], [h.l, bb], color=wk[0], alpha=wk[1], lw=0.9 * pv['wick'], zorder=3, solid_capstyle='butt')
        ax.add_patch(Rectangle((x1, bb), W_, max(bt - bb, rg * 0.003), fc=matplotlib.colors.to_rgba(bd[0], bd[1]), ec='none', zorder=4))
        ax.add_patch(Rectangle((x1, bb), W_, max(bt - bb, rg * 0.003), fc='none', ec=matplotlib.colors.to_rgba(br[0], br[1]), lw=0.9, ls='--' if (mm == 0 and pv['live']) else '-', zorder=4))
        if pv['sep'] and X(h.b0) >= 0:
            ax.axvline(X(h.b0), color='#787b86', alpha=0.45, lw=0.8, ls=':', zorder=1)
        tag = '' if (i2 < 0 or not pv['tags']) else 'C1' if mm == i2 + 1 else 'C2' if mm == i2 else 'C3' if mm == i2 - 1 else 'C4' if mm == i2 - 2 else ''
        stp = ((h.t0 + pd.Timedelta(hours=6)).strftime('%a %d') if P == 1 else h.t0.strftime('%H:%M')) if pv['stamps'] else ''
        dn = ((stp + '\n' if stp else '') + tag) if (tgDn and tag) else stp
        if dn:
            ax.text(xm, h.l - rg * 0.008, dn, color=tagC if (tgDn and tag) else subC, fontsize=fsz * 0.85, ha='center', va='top', zorder=6, linespacing=1.1)
        if not tgDn and tag:
            ax.text(xm, h.h + rg * 0.008, tag, color=tagC, fontsize=fsz * 0.85, ha='center', va='bottom', zorder=6)
    cur = hcs[0]
    hlOn = pv['hl'] and len(hcs) > 1; pc = hcs[1] if hlOn else None; tol = 0.04 * (top - bot)
    opH = pv['opn'] and hlOn and abs(cur.o - pc.h) <= tol; opL = pv['opn'] and hlOn and not opH and abs(cur.o - pc.l) <= tol
    if pv['opn']:
        ax.plot([X(max(cur.b0, b0)), xE], [cur.o] * 2, color='#787b86', alpha=0.8, lw=0.9, ls='--', zorder=3)
        if not (opH or opL): ax.text(xE + 0.6, cur.o, f'open {px(cur.o)}', color='#787b86', fontsize=fsz * 0.85, va='center', zorder=6)
    if hlOn:
        for y, bx, nmx, mrg in ((pc.h, pc.bH, 'H', opH), (pc.l, pc.bL, 'L', opL)):
            ax.plot([X(max(bx, b0)), xE], [y] * 2, color='#787b86', alpha=0.7, lw=0.9, ls=':', zorder=3)
            ax.text(xE + 0.6, y, f'{nmx} {px(y)}' + (f' · open {px(cur.o)}' if mrg else ''), color='#787b86', fontsize=fsz * 0.85, va='center', zorder=6)
    if pv['info']:
        yI = top + (0.08 * (top - bot) if (not tgDn and i2 >= 0 and pv['tags']) else 0)
        ax.text((x0 + xE) / 2, yI + rg * 0.01, f'{nm} · {left_txt}', color=fg, fontsize=fsz * 0.9, ha='center', va='bottom', zorder=6)
    ax.set_xlim(-2, xE + (16 if (pv['opn'] or pv['hl']) else 8))
    ax.set_ylim(ylo, yhi)
    ax.yaxis.tick_right(); ax.tick_params(colors=fg, labelsize=fs, length=0); ax.grid(color=grid, lw=0.6)
    for sp in ax.spines.values(): sp.set_color(grid)
    tk = [X(b) for b in range(b0, n) if tick(ts[b])]
    ax.set_xticks(tk); ax.set_xticklabels([(ts[b0 + x] + xshift).strftime(xfmt) for x in tk])

def window_1m(day, T):
    B = TT.B
    w = B[(B.tday == pd.Timestamp(day)) & (B.ts < T) & (B.ts >= T - pd.Timedelta(hours=3))].rename(columns={'Open': 'O', 'High': 'H', 'Low': 'L', 'Close': 'C', 'ts': 't'}).reset_index(drop=True)
    key = w.t.dt.floor('15min').to_numpy(); ts = list(w.t)
    st = run(w.O.to_numpy(), w.H.to_numpy(), w.L.to_numpy(), w.C.to_numpy(), ts, key,
             c4_end=lambda s, b: int((s.t3 + 30 * M - (ts[b] + M)) / M))
    return w, st

def window_1h(T):
    Hb = pd.read_pickle('/home/claude/xa/nq_1h.pkl')
    w = Hb[(Hb.hk < T) & (Hb.hk >= T - pd.Timedelta(days=12))].rename(columns={'hk': 't'}).reset_index(drop=True)
    st = run(w.O.to_numpy(), w.H.to_numpy(), w.L.to_numpy(), w.C.to_numpy(), list(w.t), w.tday.to_numpy())
    return w, st

def macro(day, now, mob):
    s = TT.state(day, now)
    h, R = TT.rows(s, mob)
    return s, h, R


DX5 = pd.read_pickle('/home/claude/xa/dx_5m.pkl').drop_duplicates('ts').set_index('ts').Close.sort_index()
C15 = (DX5.shift(-2) / DX5.shift(1) - 1) * 100
SD15 = C15.rolling(4000, min_periods=1000).std().shift(1)
IDX = pd.read_pickle('/home/claude/xa/idx_NQ.pkl')
PR = pd.read_pickle('/home/claude/xa/P_rng.pkl')

def dxy_c2(s):
    t2 = s.t2
    a, b = DX5.get(t2 + pd.Timedelta(minutes=10)), DX5.get(t2 - pd.Timedelta(minutes=5))
    sd = SD15.get(t2)
    if a is None or b is None or sd is None or np.isnan(sd):
        return None
    ch = (a / b - 1) * 100
    return ch, (-1 if s.bull else 1) * ch / sd

def range_row(day, T, mob, regC):
    d = pd.Timestamp(day)
    adr = IDX.adr20.loc[d]
    prev = IDX.index[IDX.index < d][-1]
    yr = (IDX.h.loc[prev] - IDX.l.loc[prev]) / IDX.adr20.loc[prev]
    pr = PR[(PR.index == d) & (PR.sym == 'NQ')].iloc[0]
    dz, cz = pr.dxabsr, pr.clabsr
    mx = max(dz, cz); big = mx >= 2
    m = (1.07 if big else 0.92) if yr < 1 else (1.16 if big else 1.06) if yr < 1.5 else (1.51 if big else 1.33)
    exp = adr * m
    B = TT.B; bars = B[(B.tday == d) & (B.ts < T)]
    used = (bars.High.max() - bars.Low.min()) / exp * 100
    who = 'DXY' if dz >= cz else 'CL'
    v = f'≈ {exp:.0f} pts' + ('' if mob else f' ({m:.2f}× ADR)') + (f' · after {who} {mx:.1f} sd' if big else '')
    return ('RANGE', v, f'{used:.0f}% used', regC if big else None), dict(adr=adr, yr=yr, dz=dz, cz=cz, m=m)

def macro_card(day, T, mob):
    s = TT.state(day, T)
    h, R = TT.rows(s, False)
    reg = s['reg']; regC = TT.COL[reg]
    rr, info = range_row(day, T, mob, regC)
    R = [R[0], rr] + R[1:]
    if mob:
        _, Rm = TT.rows(s, True)
        R = [Rm[0], rr] + [r for r in Rm if r[0] in ('DXY', 'OIL')]
    head = ('MACRO' if mob else 'HADŌ 99 · MACRO', T.strftime('%m/%d %H:%M' if mob else '%m/%d · %H:%M') + ('' if mob else ' ET'), TT.NM[reg], regC, regC, '#ffffff' if lum(regC) <= 165 else '#131722')
    return head, R, info

def fm_head(st, nm, mob, dark, T):
    s = st['fss'][-1] if st['fss'] else None
    live = s is not None and s.phase > 0 and not s.dead
    neu = '#2a2e39' if dark else '#c9ced8'
    hc = (BULL if s.bull else BEAR) if live else neu
    txt, body = ('#d1d4dc', '#161a23') if dark else ('#131722', '#f4f6f9')
    return ('FRACTAL' if mob else 'HADŌ 99 · FRACTAL', T.strftime('%m/%d %H:%M' if mob else '%m/%d · %H:%M') + ('' if mob else ' ET'), nm, hc, hc if live else txt, ('#ffffff' if lum(hc) <= 165 else '#131722') if live else body)

if __name__ == '__main__':
    out = []
    # the settings each mock shows: 1m in the ICT colours with the forming candle's open and the last candle's high / low,
    # 1H in the default model colours with separators, and a custom set
    PV1 = dict(style='ict', opn=True, hl=True)
    PV2 = dict(style='model', sep=True)
    PV3 = dict(style='custom', body=('#26a69a', '#ef5350'), border=('#26a69a', '#ef5350'), wickc=('#131722', '#131722'), wick=2, stamps=True, hl=True)
    # ── 1m – 15m, light
    day, T = '2026-06-17', pd.Timestamp('2026-06-17 10:27')
    w, st = window_1m(day, T)
    hM, RM, info = macro_card(day, T, False)
    RF = fm_rows(st, 0, '15m', False, dxy=dxy_c2(st['fss'][-1]))
    fig = plt.figure(figsize=(16, 9), dpi=115, facecolor='#ffffff')
    ax = fig.add_axes([0.02, 0.05, 0.93, 0.87])
    chart(ax, w, st, 110, 7.6, False, 0, '15m', off=12, nprev=5, left_txt='2:40', ypad=0.95, pv=PV1)
    ax.set_ylim(ax.get_ylim()[0] - (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.42, ax.get_ylim()[1])
    draw_card(fig, ax, hM, RM, False, 8.2, 'tr', True); draw_card(fig, ax, fm_head(st, '15m', False, False, T), RF, False, 8.2, 'br', True)
    out += [(hM, RM), (fm_head(st, '15m', False, False, T), RF)]
    fig.text(0.02, 0.965, 'Hadō 99 · NQ 1 min · Wed 17 Jun 2026, 10:27 ET · HTF candles: ICT colours, forming candle\'s open, last candle\'s high / low · Layout: Desktop', fontsize=11, color='#131722', weight='bold')
    fig.savefig(f'{OUT}/Hado99_1m15m_Desktop.png', facecolor='#ffffff'); plt.close(fig)
    # ── 1m – 15m, custom colours
    fig = plt.figure(figsize=(16, 9), dpi=115, facecolor='#ffffff')
    ax = fig.add_axes([0.02, 0.05, 0.93, 0.87])
    chart(ax, w, st, 110, 7.6, False, 0, '15m', off=12, nprev=5, left_txt='2:40', ypad=0.95, pv=PV3)
    ax.set_ylim(ax.get_ylim()[0] - (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.42, ax.get_ylim()[1])
    draw_card(fig, ax, hM, RM, False, 8.2, 'tr', True); draw_card(fig, ax, fm_head(st, '15m', False, False, T), RF, False, 8.2, 'br', True)
    fig.text(0.02, 0.965, 'Hadō 99 · NQ 1 min · Wed 17 Jun 2026, 10:27 ET · HTF candles: Custom colours (teal / red bodies, black wicks at width 2), last candle\'s high / low', fontsize=11, color='#131722', weight='bold')
    fig.savefig(f'{OUT}/Hado99_1m15m_Custom.png', facecolor='#ffffff'); plt.close(fig)
    # ── 1H – 1D, dark
    day2, T2 = '2026-04-28', pd.Timestamp('2026-04-28 12:00')
    w2, st2 = window_1h(T2)
    hM2, RM2, _ = macro_card(day2, T2, False)
    RF2 = fm_rows(st2, 1, '1D', False)
    fig = plt.figure(figsize=(16, 9), dpi=115, facecolor='#131722')
    ax = fig.add_axes([0.02, 0.05, 0.93, 0.87])
    chart(ax, w2, st2, 115, 7.6, True, 1, '1D', off=12, nprev=5, left_txt='5h 0m', xfmt='%a %d', tick=lambda t: t.hour == 18, ypad=0.85, xshift=pd.Timedelta(hours=6), pv=PV2)
    ax.set_ylim(ax.get_ylim()[0] - (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.30, ax.get_ylim()[1])
    draw_card(fig, ax, hM2, RM2, True, 8.2, 'tr', True); draw_card(fig, ax, fm_head(st2, '1D', False, True, T2), RF2, True, 8.2, 'br', True)
    out += [(hM2, RM2), (fm_head(st2, '1D', False, True, T2), RF2)]
    fig.text(0.02, 0.965, 'Hadō 99 · NQ 1 hour · Tue 28 Apr 2026, 12:00 ET · HTF candles: Model colours (default), separators on · Layout: Desktop, dark', fontsize=11, color='#d1d4dc', weight='bold')
    fig.savefig(f'{OUT}/Hado99_1H1D_Desktop.png', facecolor='#131722'); plt.close(fig)
    # ── mobile: 1m with both cards
    fig = plt.figure(figsize=(9.6, 9.4), dpi=120, facecolor='#e9ecf2')
    fs = 0.38 * 9.6 * 72 / (65 * 0.55)
    for k in range(2):
        x0 = 0.03 + k * 0.5
        fig.patches.append(Rectangle((x0 - 0.008, 0.03), 0.456, 0.89, transform=fig.transFigure, fc='#ffffff', ec='#131722', lw=6, zorder=0))
        ax = fig.add_axes([x0, 0.07, 0.38, 0.83]); ax.set_zorder(2)
        if k == 0:
            hm, Rm, _ = macro_card(day, T, True)
            Rf = [r for r in fm_rows(st, 0, '15m', True, dxy=dxy_c2(st['fss'][-1])) if r[0] in ('C2', 'C3', 'CISD', 'PROTECT')]
            chart(ax, w, st, 60, fs * 0.9, False, 0, '15m', off=8, nprev=4, left_txt='2:40', ypad=0.8, pv=dict(PV1, w=4, g=2, opn=False, hl=False))
            ax.set_ylim(ax.get_ylim()[0] - (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.35, ax.get_ylim()[1])
            hf = fm_head(st, '15m', True, False, T); cap = '1m – 15m · Wed 17 Jun 10:27'
        else:
            hm, Rm, _ = macro_card(day2, T2, True)
            Rf = [r for r in fm_rows(st2, 1, '1D', True) if r[0] in ('C2', 'C3', 'CISD', 'PROTECT')]
            chart(ax, w2, st2, 70, fs * 0.9, False, 1, '1D', off=12, nprev=4, left_txt='5h 0m', xfmt='%a', tick=lambda t: t.hour == 18, ypad=0.8, xshift=pd.Timedelta(hours=6))
            ax.set_ylim(ax.get_ylim()[0] - (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.35, ax.get_ylim()[1])
            hf = fm_head(st2, '1D', True, False, T2); cap = '1H – 1D · Tue 28 Apr 12:00'
        draw_card(fig, ax, hm, Rm, False, fs, 'tr', False); draw_card(fig, ax, hf, Rf, False, fs, 'br', False)
        out += [(hm, Rm), (hf, Rf)]
        fig.text(x0 + 0.22, 0.945, cap, fontsize=9.5, color='#131722', ha='center', weight='bold')
    fig.savefig(f'{OUT}/Hado99_Mobile.png', facecolor='#e9ecf2'); plt.close(fig)
    print('range info 06/17', {k: round(float(v), 3) for k, v in info.items()})
    for h, R in out:
        print(h[:3])
        for r in R: print('   ', r[:3])
