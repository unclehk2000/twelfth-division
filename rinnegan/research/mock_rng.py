"""Rinnegan: a Python port of the Pine logic (swings, ranges, states, keep-N), a port check against the T1 test rows, and the
mock PNGs (NQ 15-minute and 5-minute to 23 Oct 2026, desktop card; a mobile card)."""
import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0, '/home/claude/lr'); from lib import load, bars, D2025
FG, GR, SUB = '#131722', '#eef1f6', '#5d6476'; BU, BE, EQC, HDR = '#26a69a', '#ef5350', '#787b86', '#7e57c2'


def port(B, keepN=2, minW=0.25, hz=(60, 120), retire=None, sides=(1, -1)):
    H, L, C, O, ts = B['H'], B['L'], B['C'], B['O'], B['ts']; n = len(H)
    atr = np.r_[np.nan, pd.Series(H - L).rolling(14).mean().values[:-1]]
    sH, sL, iH, iL = [], [], [], []
    used = {}
    R, done = [], []
    for t in range(n):
        # step live ranges
        for d in R:
            if d['st'] <= 1 and t > d['bc']:
                up = d['dir'] == 1
                h0 = H[t] > d['z'] if up else L[t] < d['z']
                h1 = L[t] < d['h'] if up else H[t] > d['h']
                hE = L[t] <= d['eq'] if up else H[t] >= d['eq']
                if d['st'] == 0:
                    d['st'] = 5 if (h0 and hE) else 3 if h0 else ((4 if h1 else 1) if hE else 0)
                else:
                    d['st'] = 5 if (h0 and h1) else 2 if h0 else 4 if h1 else 1
                if d['st'] >= 2 and 'tE' not in d: d['tE'] = t
                lim = retire if retire else hz[d['lay']]
                if d['st'] <= 1 and t - d['bc'] >= lim:
                    d['st'] = 6; d['tE'] = t
        if t < 3: continue
        nSTH = H[t - 1] > H[t - 2] and H[t - 1] > H[t]; nSTL = L[t - 1] < L[t - 2] and L[t - 1] < L[t]
        nITH = nITL = False; itHi = itLo = None
        if nSTL:
            sL.append((L[t - 1], t - 1))
            if len(sL) >= 3 and sL[-2][0] < sL[-3][0] and sL[-2][0] < sL[-1][0]: iL.append(sL[-2]); nITL = True; itLo = sL[-2][1]
        if nSTH:
            sH.append((H[t - 1], t - 1))
            if len(sH) >= 3 and sH[-2][0] > sH[-3][0] and sH[-2][0] > sH[-1][0]: iH.append(sH[-2]); nITH = True; itHi = sH[-2][1]
        trig = []
        if nSTH and 1 in sides: trig.append((1, 0, t - 1))
        if nSTL and -1 in sides: trig.append((-1, 0, t - 1))
        if nITH and 1 in sides: trig.append((1, 1, itHi))
        if nITL and -1 in sides: trig.append((-1, 1, itLo))
        for dr, lay, hi in trig:
            prior = (sL if lay == 0 else iL) if dr == 1 else (sH if lay == 0 else iH)
            q = len(prior) - 1
            while q >= 0 and prior[q][1] >= hi: q -= 1
            if q < 1: continue
            p, ix = prior[q]; p2 = prior[q - 1][0]
            if not (p < p2 if dr == 1 else p > p2) or used.get((dr, lay)) == ix or not (atr[t] > 0) or t - ix > 400: continue
            top = H[ix:t + 1].max(); bot = L[ix:t + 1].min()
            if not (bot >= p if dr == 1 else top <= p): continue
            used[(dr, lay)] = ix
            w = (top - bot) / atr[t]
            if w < minW: continue
            m = 0.5 * (top + bot)
            fv = any((L[k] > H[k - 2] and H[k - 2] < m) if dr == 1 else (H[k] < L[k - 2] and L[k - 2] > m) for k in range(ix + 2, t + 1))
            d = dict(dir=dr, lay=lay, z=top if dr == 1 else bot, h=bot if dr == 1 else top, eq=m, tS=ix, bc=t, fvg=fv, w=w, st=0)
            R.append(d); done.append(d)
            same = [e for e in R if e['lay'] == lay and e['dir'] == dr]
            if len(same) > keepN:
                for e in same[:len(same) - keepN]: R.remove(e)
    return R, done


def candles(ax, O, H, L, C, w=0.62):
    for i in range(len(O)):
        c = '#089981' if C[i] >= O[i] else '#f23645'
        ax.plot([i, i], [L[i], H[i]], color=c, lw=0.7, zorder=2)
        ax.add_patch(Rectangle((i - w / 2, min(O[i], C[i])), w, max(abs(C[i] - O[i]), 1e-6), fc=c, ec=c, lw=0.3, zorder=2))


ST = {0: 'live', 1: 'EQ touched', 2: '✓ 0 after EQ', 3: '✓ 0 before EQ', 4: '✗ 100 taken', 5: 'both on one candle', 6: 'retired'}


def mock(sym, u, nbars, fn, mobile=False, title=''):
    m = load(sym); B = bars(m, u)
    k0 = len(B['H']) - 6000
    BB = {k: (v[k0:] if hasattr(v, '__len__') and len(v) == len(B['H']) else v) for k, v in B.items()}
    R, _ = port(BB, retire=120)
    n = len(BB['H']); s0 = n - nbars
    O, H, L, C, ts = [BB[k][s0:] for k in ['O', 'H', 'L', 'C', 'ts']]
    fig = plt.figure(figsize=(15, 8.4) if not mobile else (6.2, 9.6), dpi=130); fig.patch.set_facecolor('white')
    ax = fig.add_axes([0.03, 0.07, 0.86, 0.84] if not mobile else [0.04, 0.06, 0.78, 0.66])
    candles(ax, O, H, L, C)
    xE = nbars - 1 + 8
    rows = []
    for d in R:
        x1 = max(d['tS'] - s0, 0); live = d['st'] <= 1
        x2 = xE if live else d.get('tE', n - 1) - s0
        if x2 < 0: continue
        c = BU if d['dir'] == 1 else BE; a = 1.0 if live else 0.45
        ax.plot([x1, x2], [d['z']] * 2, color=c, lw=1.1, alpha=a)
        ax.plot([x1, x2], [d['h']] * 2, color=c, lw=1.1, ls='--', alpha=a)
        ax.plot([x1, x2], [d['eq']] * 2, color=EQC, lw=0.9, ls=':', alpha=a)
        for f in (0.25, 0.75):
            ax.plot([x1, x2], [d['h'] + f * (d['z'] - d['h'])] * 2, color=EQC, lw=0.6, ls=':', alpha=0.45 * a)
        ax.add_patch(Rectangle((x1, min(d['eq'], d['h'])), x2 - x1, abs(d['eq'] - d['h']), fc=c, alpha=0.07 if live else 0.035, ec='none'))
        nm = ('ST' if d['lay'] == 0 else 'IT') + (' ▲' if d['dir'] == 1 else ' ▼')
        p = min(max((C[-1] - d['h']) / (d['z'] - d['h']), 0), 1)
        txt = f" {nm} 0 first {100*p:.0f}%" + (' · EQ ✓' if d['st'] == 1 else '') if live else f" {nm} {ST[d['st']]}"
        ax.text(x2, d['z'], txt, color=c, alpha=a, fontsize=8 if not mobile else 7, va='bottom' if d['dir'] == 1 else 'top')
        if live: rows.append((nm + (' EQ✓' if d['st'] == 1 else ''), p, d['w'], c))
    lo, hi = L.min(), H.max(); pad = (hi - lo) * 0.06; ax.set_ylim(lo - pad, hi + pad); ax.set_xlim(-1, xE + (26 if not mobile else 30))
    ax.yaxis.tick_right(); ax.grid(color=GR, lw=0.6); ax.tick_params(colors=FG, labelsize=8, length=0)
    for sp in ax.spines.values(): sp.set_color(GR)
    every = 360 if u >= 15 else 120
    tk = [i for i in range(len(ts)) if ts[i] % every == 0]
    ax.set_xticks(tk); ax.set_xticklabels([pd.Timestamp(int(ts[i]), unit='m').strftime('%a %H:%M') for i in tk])
    fig.text(0.03, 0.955 if not mobile else 0.975, title, fontsize=10.5 if not mobile else 9, color=FG, weight='bold')
    # card
    gauge = lambda f, k: '█' * int(round(f * k)) + '░' * (k - int(round(f * k)))
    cr = [('RINNEGAN', '' if mobile else 'DEALING RANGES', '0 first' if mobile else '0 first · now', f'{u}', None)]
    rows = rows[::-1][:2 if mobile else 4]
    for nm, p, w, c in rows: cr.append((nm, gauge(p, 6 if mobile else 10), f'{100*p:.0f}%', f'{w:.1f}×ATR', c))
    if not mobile:
        cr += [('TESTED', 'ST · IT', '', 'chance', HDR), ('0 before EQ', '', '29% · 29%', '30 · 30', None), ('0 after EQ', '', '37% · 41%', '37 · 43', None),
               ('no FVG in 100½', '', '66% · 62%', '65 · 60', None), ('both ends <1 ATR', '', '81% · —', '82', None), ('live odds', '', '= position', '±3', None)]
    x0, y0, wd, hh = (0.645, 0.90, 0.25, 0.029) if not mobile else (0.04, 0.955, 0.78, 0.026)
    cols = (0.006, 0.075, 0.16, 0.245) if not mobile else (0.01, 0.25, 0.55, 0.77)
    for k, (a, b, c3, d4, col) in enumerate(cr):
        yy = y0 - k * hh
        fig.patches.append(Rectangle((x0, yy - hh), wd, hh, transform=fig.transFigure, fc=HDR if k == 0 else '#f4f6f9', ec=HDR if k == 0 else '#dde1e8', lw=0.6))
        tc = '#ffffff' if k == 0 else FG
        fig.text(x0 + cols[0], yy - hh / 2, a, fontsize=7.6, color=tc if k == 0 else (col if col == HDR else SUB), va='center', family='monospace')
        fig.text(x0 + cols[1], yy - hh / 2, b, fontsize=7.6, color=tc if k == 0 else (col or SUB), va='center', family='monospace')
        fig.text(x0 + cols[2], yy - hh / 2, c3, fontsize=7.6, color=tc, va='center', family='monospace')
        fig.text(x0 + wd - 0.006, yy - hh / 2, d4, fontsize=7.6, color=tc if k == 0 else SUB, va='center', ha='right', family='monospace')
    fig.savefig(fn, facecolor='white'); plt.close(fig)
    return R


if __name__ == '__main__':
    out = '/home/claude/rng/mock/'
    mock('NQ', 15, 170, out + 'Rinnegan_15m.png', title='Rinnegan · NQ 15 min to 23 Oct 2026 · ST and IT dealing ranges with their live odds')
    mock('NQ', 5, 200, out + 'Rinnegan_5m.png', title='Rinnegan · NQ 5 min · 23 Oct 2026')
    mock('NQ', 15, 110, out + 'Rinnegan_mobile.png', mobile=True, title='Rinnegan · NQ 15 min · Mobile')
    # port check: the port's ranges and outcomes vs the T1 rows, NQ 15m (T1 horizons: ST 60, IT 120 candles)
    m = load('NQ'); B = bars(m, 15)
    _, done = port(B, keepN=10 ** 9, hz=(60, 120))
    P = pd.DataFrame(done); P['td'] = B['td'][P.bc]
    T = pd.read_pickle('/home/claude/lr/t1_rows.pkl'); T = T[(T.sym == 'NQ') & (T.u == 15)]
    for lay, ln in [(0, 'ST'), (1, 'IT')]:
        a = P[P.lay == lay]; b = T[T.layer == ln]
        ma = a.st.map({3: 'direct', 2: 'complete', 4: 'failed', 5: 'both', 6: 'open', 0: 'open', 1: 'open'}).value_counts(normalize=True).round(3).to_dict()
        mb = b.o.map({0: 'direct', 1: 'complete', 2: 'failed', 5: 'both', 3: 'open', 4: 'open'}).value_counts(normalize=True).round(3).to_dict()
        print(ln, 'port', len(a), ma); print(ln, 'test', len(b), mb)
