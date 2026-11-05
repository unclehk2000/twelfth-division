"""Rinnegan v1.1: Python port of the DR / IDR engine (as the Pine runs it on a 5-minute chart), a port check against the T11
test rows, and the DR mock (NQ 5 minutes, 23 Oct 2026: ODR and RDR, IT swing ranges on, ST off)."""
import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0, '/home/claude/lr'); sys.path.insert(0, '/home/claude/rng')
from lib import load, bars, D2025
from mock_rng import port, candles, ST
FG, GR, SUB = '#131722', '#eef1f6', '#5d6476'; BU, BE, EQC, HDR, CDR, CIDR, CSTD = '#26a69a', '#ef5350', '#787b86', '#7e57c2', '#5d6476', '#e65100', '#9598a1'
S = [('RDR', 930, 990, 1320), ('ODR', 540, 600, 870), ('ADR', 90, 150, 480)]
STDR = {'RDR': [72, 42, 22, 12, 7, 4, 3, 2, 2, 1], 'ODR': [84, 60, 41, 28, 21, 15, 12, 9, 7, 5], 'ADR': [83, 60, 40, 25, 17, 11, 7, 5, 4, 3]}
OPP = {'RDR': (17, 19), 'ODR': (35, 37), 'ADR': (29, 31)}


def drport(B, stdN=4):
    O, H, L, C, ts = B['O'], B['H'], B['L'], B['C'], B['ts']
    rel = ((ts % 1440) - 1080) % 1440
    out = []
    for nm, s0, s1, s2 in S:
        cur = None
        for t in range(len(O)):
            r = rel[t]; inW = s0 <= r < s1; inX = s1 <= r < s2; tSt = ts[t] - (r - s0)
            if cur and cur['st'] <= 3 and (ts[t] >= cur['tX'] or (not inW and not inX)):
                cur['st'] = 4; cur['tE'] = t
            if inW and r - s0 < 5 and (cur is None or cur['tA'] != tSt):
                cur = dict(s=nm, tA=tSt, tX=tSt + (s2 - s0), dH=H[t], dL=L[t], iH=None, iL=None, st=1, dir=0, oT=False, bk=False, ext=0.0, t0=t, td=B['td'][t])
                out.append(cur)
            if cur is None or cur['st'] > 3: continue
            if inW and cur['st'] == 1:
                cur['dH'] = max(cur['dH'], H[t]); cur['dL'] = min(cur['dL'], L[t])
                bh, bl = max(O[t], C[t]), min(O[t], C[t])
                cur['iH'] = bh if cur['iH'] is None else max(cur['iH'], bh); cur['iL'] = bl if cur['iL'] is None else min(cur['iL'], bl)
            elif inX:
                if cur['st'] == 1: cur['st'] = 2
                if cur['st'] == 3:
                    w = cur['iH'] - cur['iL']
                    if cur['dir'] == 1:
                        cur['oT'] |= L[t] <= cur['dL']; cur['bk'] |= L[t] <= cur['iH']; cur['ext'] = max(cur['ext'], (H[t] - cur['iH']) / w)
                    else:
                        cur['oT'] |= H[t] >= cur['dH']; cur['bk'] |= H[t] >= cur['iL']; cur['ext'] = max(cur['ext'], (cur['iL'] - L[t]) / w)
                if cur['st'] == 2 and cur['iH'] > cur['iL']:
                    d = 1 if C[t] > cur['dH'] else -1 if C[t] < cur['dL'] else 0
                    if d: cur.update(st=3, dir=d, tC=t, cC=C[t])
    return out


def mock(fn):
    m = load('NQ'); B = bars(m, 5)
    kE = int(np.argmax(B['ts'] >= int(pd.Timestamp('2026-10-23 12:30').value // 60e9)))
    k0 = kE - 5000
    BB = {k: (v[k0:kE] if hasattr(v, '__len__') and len(v) == len(B['H']) else v) for k, v in B.items()}
    R, _ = port(BB, retire=120, sides=(1, -1))
    R = [d for d in R if d['lay'] == 1]
    DDs = drport(BB)
    n = len(BB['H']); t0 = int(np.argmax(BB['ts'] >= int(pd.Timestamp('2026-10-23 01:00').value // 60e9))); s0 = t0
    O, H, L, C, ts = [BB[k][s0:] for k in ['O', 'H', 'L', 'C', 'ts']]
    nb = len(O); X = lambda tt: tt - s0
    fig = plt.figure(figsize=(15, 8.6), dpi=130); ax = fig.add_axes([0.03, 0.07, 0.86, 0.84]); candles(ax, O, H, L, C)
    rows = []
    for d in DDs:
        if d['t0'] < s0: continue
        x1 = X(d['t0']); xe = X(d['t0']) + (d['tX'] - d['tA']) // 5
        live = d['st'] <= 3; xr = min(xe, nb - 1 + 8) if live else X(d.get('tE', n - 1))
        a = 1.0 if live else 0.5
        ax.plot([x1, xr], [d['dH']] * 2, color=CDR, lw=1.1, alpha=a); ax.plot([x1, xr], [d['dL']] * 2, color=CDR, lw=1.1, alpha=a)
        ax.plot([x1, xr], [d['iH']] * 2, color=CIDR, lw=1, ls='--', alpha=a); ax.plot([x1, xr], [d['iL']] * 2, color=CIDR, lw=1, ls='--', alpha=a)
        ax.plot([x1, xr], [(d['iH'] + d['iL']) / 2] * 2, color=CIDR, lw=0.8, ls=':', alpha=0.6 * a)
        ax.add_patch(Rectangle((x1, d['iL']), xr - x1, d['iH'] - d['iL'], fc=CIDR, alpha=0.08 * a, ec='none'))
        ax.text(x1, d['dH'], d['s'], color=CDR, fontsize=8, va='bottom', alpha=a)
        if d['st'] >= 3 and 'tC' in d:
            xc = X(d['tC']); c = BU if d['dir'] == 1 else BE; w = d['iH'] - d['iL']
            ax.text(xc, d['cC'], ('▲ ' if d['dir'] == 1 else '▼ ') + d['s'], color=c, fontsize=8, va='top' if d['dir'] == 1 else 'bottom', ha='center')
            for k in range(1, 5):
                lv = d['iH'] + 0.5 * k * w if d['dir'] == 1 else d['iL'] - 0.5 * k * w
                ax.plot([xc, xr], [lv] * 2, color=CSTD, lw=0.8, ls=':', alpha=a)
                ax.text(xr, lv, f" {'+' if d['dir'] == 1 else '−'}{k / 2:.1f} · {STDR[d['s']][k - 1]}%", color=CSTD, fontsize=7, va='center', alpha=a, clip_on=True)
        if live:
            nm = d['s'] + ((' ▲ ' if d['dir'] == 1 else ' ▼ ') + pd.Timestamp(int(BB['ts'][d['tC']]), unit='m').strftime('%H:%M') if d['st'] == 3 else ' waiting')
            g = f"opp {'✗' if d['oT'] else '·'} IDR {'✓' if d['bk'] else '·'} +{np.floor(d['ext'] * 2) / 2:.1f}" if d['st'] == 3 else f"DR {d['dH'] - d['dL']:.2f}"
            rows.append((nm, g, f"opp {OPP[d['s']][0]}%" if d['st'] == 3 else 'confirm 92%', f"{OPP[d['s']][1]}" if d['st'] == 3 else '', BU if d['dir'] == 1 else BE if d['dir'] == -1 else CDR))
    sw = []
    for d in R:
        x1 = max(d['tS'] - s0, 0); live = d['st'] <= 1; x2 = nb - 1 + 8 if live else d.get('tE', n - 1) - s0
        if x2 < 0: continue
        c = BU if d['dir'] == 1 else BE; a = 0.9 if live else 0.4
        ax.plot([x1, x2], [d['z']] * 2, color=c, lw=1.1, alpha=a); ax.plot([x1, x2], [d['h']] * 2, color=c, lw=1.1, ls='--', alpha=a)
        ax.plot([x1, x2], [d['eq']] * 2, color=EQC, lw=0.8, ls=':', alpha=a)
        p = min(max((C[-1] - d['h']) / (d['z'] - d['h']), 0), 1)
        nm = 'IT' + (' ▲' if d['dir'] == 1 else ' ▼')
        ax.text(x2, d['z'], f" {nm} 0 first {100*p:.0f}%" if live else f" {nm} {ST[d['st']]}", color=c, alpha=a, fontsize=8, va='bottom' if d['dir'] == 1 else 'top')
        if live: sw.append((nm + (' EQ✓' if d['st'] == 1 else ''), p, d['w'], c))
    lo, hi = L.min(), H.max(); pad = (hi - lo) * 0.06; ax.set_ylim(lo - pad, hi + pad); ax.set_xlim(-1, nb + 34)
    ax.yaxis.tick_right(); ax.grid(color=GR, lw=0.6); ax.tick_params(colors=FG, labelsize=8, length=0)
    for sp in ax.spines.values(): sp.set_color(GR)
    tk = [i for i in range(nb) if ts[i] % 120 == 0]; ax.set_xticks(tk); ax.set_xticklabels([pd.Timestamp(int(ts[i]), unit='m').strftime('%H:%M') for i in tk])
    fig.text(0.03, 0.955, 'Rinnegan v1.1 · NQ 5 min · 23 Oct 2026 to 12:30 · defining ranges (ODR, RDR: DR solid, IDR dashed, STD dotted with reach odds) + IT dealing ranges', fontsize=10.5, color=FG, weight='bold')
    gauge = lambda f, k: '█' * int(round(f * k)) + '░' * (k - int(round(f * k)))
    cr = [('RINNEGAN', 'DEALING RANGES', '0 first · now', '5', None)]
    for nm, p, w, c in sw[::-1][:2]: cr.append((nm, gauge(p, 10), f'{100*p:.0f}%', f'{w:.1f}×ATR', c))
    for r in rows: cr.append(r)
    cr += [('TESTED', 'ST · IT', '', 'chance', HDR), ('0 after EQ', '', '37% · 41%', '37 · 43', None), ('DR side race', '', '49–52%', '50', None), ('live odds', '', '= position', '±3', None)]
    x0, y0, wd, hh = 0.63, 0.90, 0.265, 0.029
    for k, (a, b, c3, d4, col) in enumerate(cr):
        yy = y0 - k * hh
        fig.patches.append(Rectangle((x0, yy - hh), wd, hh, transform=fig.transFigure, fc=HDR if k == 0 else '#f4f6f9', ec=HDR if k == 0 else '#dde1e8', lw=0.6))
        tc = '#ffffff' if k == 0 else FG
        fig.text(x0 + 0.006, yy - hh / 2, a, fontsize=7.4, color=tc if k == 0 else (col if col == HDR else SUB), va='center', family='monospace')
        fig.text(x0 + 0.088, yy - hh / 2, b, fontsize=7.4, color=tc if k == 0 else (col or SUB), va='center', family='monospace')
        fig.text(x0 + 0.178, yy - hh / 2, c3, fontsize=7.4, color=tc, va='center', family='monospace')
        fig.text(x0 + wd - 0.006, yy - hh / 2, d4, fontsize=7.4, color=tc if k == 0 else SUB, va='center', ha='right', family='monospace')
    fig.savefig(fn, facecolor='white'); plt.close(fig)


if __name__ == '__main__':
    mock('/home/claude/rng/mock/Rinnegan_v11_5m_DR_IDR.png')
    m = load('NQ'); B = bars(m, 5); P = pd.DataFrame(drport(B))
    T = pd.read_pickle('/home/claude/lr/t11_rows.pkl'); T = T[T.sym == 'NQ']
    for s in ['RDR', 'ODR', 'ADR']:
        a = P[(P.s == s) & (P.st >= 3) & (P.dir != 0)]; b = T[(T.sess == s) & (T.dr != 0)]
        print(s, f'port: sessions {len(P[P.s == s])}, confirmed {len(a)}, opp traded {100*a.oT.mean():.1f}%, IDR back {100*a.bk.mean():.1f}%, +1 STD {100*(a.ext >= 1).mean():.1f}%',
              f'| test: sessions {len(T[T.sess == s])}, confirmed {len(b)}, opp {100*b.oT.mean():.1f}%, IDR back {100*b.bk.mean():.1f}%, +1 STD {100*(b.ex >= 1).mean():.1f}%')
