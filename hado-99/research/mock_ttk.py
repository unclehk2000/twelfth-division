"""Tenteikūra mocks: NQ 1-minute, card values computed the way the Pine does (regime from yesterday's closes,
tested two-factor betas, live 60-day betas from daily % changes, DXY / CL live at the chart time)."""
import sys, json
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0, '/home/claude/sb')
from mock_sb2 import draw_card, lum
OUT = sys.argv[1]
B = pd.read_pickle('/home/claude/kyw/bars_NQ_all.pkl')
F = pd.read_pickle('/home/claude/kyw/F_NQ.pkl')
DX = pd.read_pickle('/home/claude/xa/dx_daily.pkl')
DX5 = pd.read_pickle('/home/claude/xa/dx_5m.pkl').set_index('ts')
CLD = pd.read_pickle('/home/claude/xa/cl_daily.pkl')
CL1 = pd.read_pickle('/home/claude/xa/cl_1m.pkl').set_index('ts')
TB = {'NQ': dict(D=[-0.17, -0.80, -1.50], C=[0.160, 0.039, -0.131], R=[7, 6, 29])}
NM = ['WEAK $', 'STRONG $', 'OIL SHOCK']; COL = ['#26a69a', '#ff9800', '#f23645']

def sg(v, f='{:.2f}'):
    return '—' if v is None or np.isnan(v) else ('+' if v > 0 else '−' if v < 0 else '') + f.format(abs(v))

def state(day, now):
    d0 = pd.Timestamp(day)
    prevD = F.index[F.index < d0][-1]
    # regime from yesterday
    c1, c2 = CLD.m1.loc[:prevD].iloc[-1], CLD.m2.loc[:prevD].iloc[-1]
    ts12 = -(c2 / c1 - 1) * 12 * 100
    cl20 = CLD.r.loc[:prevD].iloc[-20:].sum() * 100
    dxp = DX.c.loc[:prevD]
    above = dxp.iloc[-1] > dxp.iloc[-200:].mean()
    shock = ts12 > 15 and cl20 > 10
    reg = 2 if shock else 1 if above else 0
    # live 60-day two-factor betas from daily % changes (index 17:00, DXY daily, CL settle)
    i = (F.ac.pct_change() * 100).loc[:prevD]
    x = (DX.c.pct_change() * 100).reindex(i.index)
    z = (np.exp(CLD.r) - 1).mul(100).reindex(i.index)
    J = pd.concat([i, x, z], axis=1, keys=['y', 'x', 'z']).dropna().iloc[-60:]
    Xm = np.c_[np.ones(len(J)), J.x, J.z]; b = np.linalg.lstsq(Xm, J.y, rcond=None)[0]
    lrD, lrO = J.y.corr(J.x), J.y.corr(J.z)
    # live prices at the chart time
    t = pd.Timestamp(now)
    bars = B[(B.tday == d0) & (B.ts < t)]
    iNow = bars.Close.iloc[-1]
    iPrev = B[B.tday == prevD].Close.iloc[-1]
    dxl = DX5.Close[DX5.index < t - pd.Timedelta(minutes=5)].iloc[-1]
    dxprev = DX5.Close[DX5.index <= pd.Timestamp(prevD) + pd.Timedelta(hours=16, minutes=55)].iloc[-1]
    dNow = DX.c.loc[prevD] * dxl / dxprev                      # cash level moved by the futures' % change
    oNow = CL1.Close[CL1.index < t].iloc[-1]
    oPrev = CLD.m1.loc[prevD]
    carry = (F.next_c.loc[prevD] / F.c.loc[prevD] - 1) * 365 / 91 * 100
    sp = F.next_c.loc[prevD] - F.c.loc[prevD]
    return dict(reg=reg, ts12=ts12, cl20=cl20, above=above, dMa=dxp.iloc[-200:].mean(), bD=b[1], bO=b[2], lrD=lrD, lrO=lrO,
                iNow=iNow, iPrev=iPrev, dNow=dNow, dPrev=DX.c.loc[prevD], oNow=oNow, oPrev=oPrev, carry=carry, sp=sp,
                bars=B[(B.ts >= t - pd.Timedelta(hours=4)) & (B.ts < t)], t=t)

def rows(s, mob):
    reg = s['reg']; T = TB['NQ']; bD, bO = T['D'][reg], T['C'][reg]
    iChg = (s['iNow'] / s['iPrev'] - 1) * 100; dChg = (s['dNow'] / s['dPrev'] - 1) * 100; oChg = (s['oNow'] / s['oPrev'] - 1) * 100
    impD, impO = bD * dChg, bO * oChg; imp = impD + impO
    pts = lambda pc: pc * s['iPrev'] / 100
    same = np.sign(imp) == np.sign(iChg) and iChg != 0
    share = min(imp / iChg, 1.0) * 100 if same else None
    regC = COL[reg]
    head = ('MACRO' if mob else 'BAKUDŌ 58 · MACRO', s['t'].strftime('%m/%d %H:%M' if mob else '%m/%d · %H:%M') + ('' if mob else ' ET'), NM[reg], regC)
    wv = 'DXY and CL, both against' if reg == 2 else ('DXY · 1% ≈ ' + sg(bD) + '%') if reg == 1 else ('CL · 1% ≈ ' + sg(bO) + '%')
    ww = ('1% each ≈ ' + sg(bD) + '% / ' + sg(bO) + '%') if reg == 2 else (sg(pts(bD), '{:.0f}') + ' pts' if reg == 1 else sg(pts(bO), '{:.0f}') + ' pts')
    R = [('WATCH', wv, '' if (mob and reg == 2) else ww, regC),
         ('DXY', f"{s['dNow']:.2f} {'▲' if dChg >= 0 else '▼'} {sg(dChg)}%" + ('' if mob else f" · 200d {s['dMa']:.2f}"), ('' if mob else '→ ') + sg(impD) + '%' + ('' if mob else f" ({sg(pts(impD), '{:.0f}')})"), None),
         ('OIL', f"{s['oNow']:.2f} {'▲' if oChg >= 0 else '▼'} {sg(oChg)}%" + ('' if mob else f" · bkwd {sg(s['ts12'], '{:.1f}')}%/yr"), ('' if mob else '→ ') + sg(impO) + '%' + ('' if mob else f" ({sg(pts(impO), '{:.0f}')})"), None),
         ('TODAY', f"NQ {sg(iChg)}%" + ('' if mob else f" ({sg(pts(iChg), '{:.0f}')})") + f" · $+oil {sg(imp)}%", f'{share:.0f}%' if same else 'not macro', regC if same and share >= 50 else None),
         ('LIVE β', f"60d · DXY {sg(s['bD'])} · CL {sg(s['bO'])}", f'tested {sg(bD)} / {sg(bO)}', None),
         ('SHOCK', f"CL 20d {sg(s['cl20'], '{:.1f}')}% · bkwd {sg(s['ts12'], '{:.1f}')}%", 'ON' if reg == 2 else 'needs +10 / 15', COL[2] if reg == 2 else None),
         ('CARRY', f"{sg(s['carry'])}%/yr · next {sg(s['sp'], '{:.0f}')} pts", sg(-s['sp'] / 91, '{:.1f}') + ' pts/day', None)]
    if mob:
        R = [r for r in R if r[0] in ('WATCH', 'DXY', 'OIL', 'TODAY')]
    return head, R

def chart(ax, s, fs, dark=False):
    bg, fg, grid = ('#131722', '#d1d4dc', '#1e222d') if dark else ('#ffffff', '#131722', '#eef1f6')
    ax.set_facecolor(bg)
    v = s['bars'].reset_index(drop=True)
    for i, r in v.iterrows():
        c = '#089981' if r.Close >= r.Open else '#f23645'
        ax.plot([i, i], [r.Low, r.High], color=c, lw=0.6)
        ax.add_patch(Rectangle((i - 0.32, min(r.Open, r.Close)), 0.64, max(abs(r.Close - r.Open), 0.25), fc=c, ec=c, lw=0.3))
    ax.axhline(s['iPrev'], color='#787b86', lw=0.8, ls=':')
    ax.text(len(v) + 1, s['iPrev'], 'prior close', fontsize=fs, color=fg, va='center')
    ax.set_xlim(-2, len(v) + 40)
    lo, hi = v.Low.min(), v.High.max(); pad = (hi - lo) * 0.1
    ax.set_ylim(min(lo, s['iPrev']) - pad, max(hi, s['iPrev']) + pad * 2.5)
    ax.yaxis.tick_right(); ax.tick_params(colors=fg, labelsize=fs, length=0); ax.grid(color=grid, lw=0.6)
    for sp in ax.spines.values(): sp.set_color(grid)
    ticks = [i for i, r in v.iterrows() if r.ts.minute == 0]
    ax.set_xticks(ticks); ax.set_xticklabels([v.ts[i].strftime('%H:%M') for i in ticks])

if __name__ == '__main__':
    out = []
    s = state('2026-03-20', '2026-03-20 11:00')
    fig = plt.figure(figsize=(16, 8.4), dpi=115, facecolor='#ffffff')
    ax = fig.add_axes([0.02, 0.06, 0.93, 0.86]); chart(ax, s, 7.6)
    h, R = rows(s, False); draw_card(fig, ax, h, R, False, 8.2, 'tr', True); out.append((h, R))
    fig.text(0.02, 0.965, 'Bakudō 58 · NQ 1 min · Fri 20 Mar 2026, 11:00 ET · oil-shock regime · Layout: Desktop', fontsize=11, color='#131722', weight='bold')
    fig.savefig(f'{OUT}/Bakudo58_Desktop_shock.png', facecolor='#ffffff'); plt.close(fig)
    s = state('2026-06-17', '2026-06-17 11:00')
    fig = plt.figure(figsize=(16, 8.4), dpi=115, facecolor='#131722')
    ax = fig.add_axes([0.02, 0.06, 0.93, 0.86]); chart(ax, s, 7.6, True)
    h, R = rows(s, False); draw_card(fig, ax, h, R, True, 8.2, 'tr', True); out.append((h, R))
    fig.text(0.02, 0.965, 'Bakudō 58 · NQ 1 min · Wed 17 Jun 2026, 11:00 ET · strong-dollar regime · Layout: Desktop, dark', fontsize=11, color='#d1d4dc', weight='bold')
    fig.savefig(f'{OUT}/Bakudo58_Desktop_strong_dollar.png', facecolor='#131722'); plt.close(fig)
    fig = plt.figure(figsize=(9.6, 9.4), dpi=120, facecolor='#e9ecf2')
    for k, (day, now, cap) in enumerate((('2026-06-17', '2026-06-17 11:00', 'Strong $ · Wed 17 Jun 11:00'), ('2025-12-12', '2025-12-12 11:00', 'Weak $ · Fri 12 Dec 11:00'))):
        s = state(day, now)
        x0 = 0.03 + k * 0.5
        fig.patches.append(Rectangle((x0 - 0.008, 0.03), 0.456, 0.89, transform=fig.transFigure, fc='#ffffff', ec='#131722', lw=6, zorder=0))
        ax = fig.add_axes([x0, 0.07, 0.38, 0.83]); ax.set_zorder(2)
        fs = 0.38 * 9.6 * 72 / (65 * 0.55)
        chart(ax, s, fs * 0.9)
        h, R = rows(s, True); draw_card(fig, ax, h, R, False, fs, 'tr', False); out.append((h, R))
        fig.text(x0 + 0.22, 0.945, cap, fontsize=9.5, color='#131722', ha='center', weight='bold')
    fig.savefig(f'{OUT}/Bakudo58_Mobile.png', facecolor='#e9ecf2'); plt.close(fig)
    for h, R in out:
        print(h)
        for r in R: print('   ', r)
