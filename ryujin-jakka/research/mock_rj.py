"""Ryūjin Jakka: Python port of the Pine logic (30-minute history with its own daily ATR, chart-side features, the four linear
models), a port check against the training rows, and the mock (NQ 5 minutes, 23 Oct 2026 as of 10:45 ET)."""
import sys, pickle, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0, '/home/claude/lr'); sys.path.insert(0, '/home/claude/hm')
from lib import load
import events as E
cf, qs = open('/home/claude/rj/coef.txt').read().split('\n')
CF = np.array([float(x) for x in cf.split(',')]).reshape(4, 14); QQ = np.array([float(x) for x in qs.split(',')]).reshape(4, 5)
SA, SB = [120, 480, 930, 1170], [360, 660, 1080, 1320]; SN = ['ASIA', 'LONDON', 'NY AM', 'NY PM']; ST = ['20:00–00:00', '02:00–05:00', '09:30–12:00', '13:30–16:00']
ev = {}
for nm, lst in [(1, E.CPI), (2, E.NFP), (3, E.FOMC)]:
    for t in lst: ev.setdefault(int(pd.Timestamp(t).normalize().value // 86400_000_000_000), set()).add(nm)
vix = pd.read_csv('/mnt/user-data/uploads/VolatilityIndices_daily/VIX.csv', parse_dates=['Date']).set_index('Date').Close
vrel = np.log(vix.shift(1) / vix.rolling(20).mean().shift(1))   # Pine: close[1] / sma(close, 20)[1]
vrelD = vrel.reindex(pd.date_range('2000-01-01', '2027-01-01')).ffill()
vxD = vix.shift(1).reindex(pd.date_range('2000-01-01', '2027-01-01')).ffill(); vx20D = vix.rolling(20).mean().shift(1).reindex(pd.date_range('2000-01-01', '2027-01-01')).ffill()
def rma_sma(x, n=14):   # ta.atr: RMA seeded with the SMA of the first n
    out = np.full(len(x), np.nan); out[n - 1] = np.nanmean(x[:n])
    for i in range(n, len(x)): out[i] = out[i - 1] + (x[i] - out[i - 1]) / n
    return out
m = load('NQ'); rel = (((m['ts'] % 1440) - 1080) % 1440).astype(int); td = m['td'].astype(int)
b = np.flatnonzero(np.diff(td) != 0) + 1; ds = np.r_[0, b]; de = np.r_[b - 1, len(td) - 1]
dH = np.maximum.reduceat(m['H'], ds); dL = np.minimum.reduceat(m['L'], ds); dO = m['O'][ds]; dC = m['C'][de]; nb_ = de - ds + 1; days = td[ds]
pc = np.r_[np.nan, dC[:-1]]; tr = np.nanmax(np.c_[dH - dL, np.abs(dH - pc), np.abs(dL - pc)], axis=1); tr[0] = dH[0] - dL[0]
atrA = rma_sma(tr); atrD = np.r_[np.nan, atrA[:-1]]; atr60 = np.r_[np.nan, pd.Series(atrA).rolling(60).mean().values[:-1]]
def sess_rg(di):
    s, e = ds[di], de[di]; R = rel[s:e + 1]; out = []
    for k in range(4):
        mk = (R >= SA[k]) & (R < SB[k])
        # pushed only when the session's last 30-minute candle exists
        out.append((m['H'][s:e + 1][mk].max() - m['L'][s:e + 1][mk].min()) if mk.any() and (R[mk] >= SB[k] - 30).any() else np.nan)
    return out
def hist_run(d0, d1):
    """the 30-minute request: own Wilder ATR seeded with the first TR, per-session log(range / ATR) arrays of 20."""
    H = [[], [], [], []]; atrX = np.nan; out = {}
    for di in range(d0, d1 + 1):
        if di > d0:
            t_ = tr[di - 1] if di - 1 > d0 else dH[di - 1] - dL[di - 1]
            atrX = t_ if atrX != atrX else atrX + (t_ - atrX) / 14
        out[di] = [(A[-1] if A else np.nan, np.mean(A[-5:]) if len(A) >= 5 else np.nan, np.mean(A) if len(A) >= 20 else np.nan) for A in H]
        if atrX == atrX and atrX > 0:
            for k, rg in enumerate(sess_rg(di)):
                if rg == rg: H[k].append(np.log(max(rg, 0.25) / atrX)); H[k] = H[k][-20:]
    return out
def feats(di, k, L, upto_rel=None):
    """features at session k's first bar on a 1-minute chart"""
    s, e = ds[di], de[di]; R = rel[s:e + 1]; i0 = np.flatnonzero(R >= SA[k])
    if not len(i0): return None
    i0 = i0[0]; a = atrD[di]; hh, ll = m['H'][s:s + i0].max(), m['L'][s:s + i0].min()
    soRg = np.log((hh - ll) / a) if hh > ll else np.log(0.05); soMv = abs(m['C'][s + i0 - 1] - dO[di]) / a
    if k == 0: prv = L[0][0]
    else:
        rg = sess_rg(di)[k - 1]; prv = np.log(max(rg, 0.25) / a) if rg == rg else L[k - 1][0]
    dt = pd.Timestamp(days[di], unit='D'); e_ = ev.get(days[di], set()); cpi, nfp, fom = 1 in e_, 2 in e_, 3 in e_
    evS = (1.0 if (cpi or nfp) else 0.0) if k == 2 else (1.0 if fom else 0.0) if k == 3 else 0.0
    aR = np.log(a / atr60[di]); vR = vrelD.get(dt, 0.0)
    return np.array([1, L[k][0], L[k][1], L[k][2], soRg, soMv, prv, aR, vR, dt.dayofweek, cpi, nfp, fom, evS], float)
# port check: Pine-port forecast vs the training model's forecast on the same days (2025 – Oct 2026, NQ)
T = pd.read_pickle('/home/claude/rj/t16_rows.pkl'); T = T[T.sym == 'NQ'].copy(); T['prev'] = T.prev.fillna(T.l1)
T['evS'] = np.where(T.sess == 'NYPM', T.fomc, np.where(T.sess == 'NYAM', T.cpi | T.nfp, 0))
FE = ['l1', 'l5', 'l20', 'soRg', 'soMv', 'prev', 'atrRel', 'vrel', 'dow', 'cpi', 'nfp', 'fomc', 'evS']; KS = ['Asia', 'London', 'NYAM', 'NYPM']
dA = int(np.searchsorted(days, 20089)); Hs = hist_run(dA - 130, len(days) - 1)
diffs = {k: [] for k in range(4)}; cov = {k: [] for k in range(4)}
for di in range(dA, len(days)):
    if not (1200 <= nb_[di] <= 1440): continue
    for k in range(4):
        x = feats(di, k, Hs[di]); r = T[(T.td == days[di]) & (T.sess == KS[k])]
        if x is None or not len(r) or np.isnan(x).any(): continue
        rr = r.iloc[0]; ref = CF[k, 0] + CF[k, 1:] @ rr[FE].values.astype(float)
        if np.isnan(ref): continue
        mu = CF[k] @ x; diffs[k].append(mu - ref)
        e_ = rr.y - mu; cov[k].append(((e_ >= QQ[k, 1]) & (e_ <= QQ[k, 3]), (e_ >= QQ[k, 0]) & (e_ <= QQ[k, 4])))
for k in range(4):
    d = np.array(diffs[k]); c = np.array(cov[k])
    print(f'port {SN[k]:6s} n {len(d):3d} | forecast diff (log): median |d| {np.median(np.abs(d)):.4f}, p95 {np.quantile(np.abs(d), .95):.4f} (= {100*(np.exp(np.quantile(np.abs(d), .95))-1):.1f}% range) | port bands p25–p75 {100*c[:,0].mean():.1f}% p10–p90 {100*c[:,1].mean():.1f}%')
# mock
d1 = int(np.searchsorted(days, int(pd.Timestamp('2026-10-23').value // 86400e9))); CUT = 1005
L = Hs[d1]; s, e = ds[d1], de[d1]; R = rel[s:e + 1]; a = atrD[d1]
key = R // 5; brk = np.r_[0, np.flatnonzero(np.diff(key)) + 1]; en = np.r_[brk[1:] - 1, len(key) - 1]
bars = [(m['O'][s + i0], m['H'][s + i0:s + i1 + 1].max(), m['L'][s + i0:s + i1 + 1].min(), m['C'][s + i1], R[i0]) for i0, i1 in zip(brk, en) if R[i0] <= CUT]
n = len(bars); xo = lambda r_: next(i for i, b_ in enumerate(bars) if b_[4] >= r_) if r_ <= bars[-1][4] else n - 1 + (r_ - bars[-1][4]) / 5
fig = plt.figure(figsize=(15, 8.8), dpi=130); ax = fig.add_axes([0.03, 0.07, 0.84, 0.85])
for i, (o, h, l, c, r) in enumerate(bars):
    col = '#089981' if c >= o else '#f23645'; ax.plot([i, i], [l, h], color=col, lw=0.6); ax.add_patch(Rectangle((i - 0.3, min(o, c)), 0.6, max(abs(c - o), 0.25), fc=col, ec=col, lw=0.2))
O_ = '#ff6d00'; info = []
lastC = bars[-1][3]; dHi = max(b_[1] for b_ in bars); dLo = min(b_[2] for b_ in bars)
for k in range(4):
    sb = [b_ for b_ in bars if SA[k] <= b_[4] < SB[k]]
    started = len(sb) > 0; live = started and CUT < SB[k]
    if started:
        x = feats(d1, k, L); mu = CF[k] @ x
    else:   # provisional, from what is known now
        x = feats(d1, 2, L).copy(); x[1:4] = L[k]; x[4] = np.log((dHi - dLo) / a); x[5] = abs(lastC - dO[d1]) / a
        rg = sess_rg(d1)[k - 1] if k else np.nan
        # previous session (NY AM) still running at the cut: its range so far
        x[6] = np.log(max(max(b_[1] for b_ in bars if SA[k-1] <= b_[4]) - min(b_[2] for b_ in bars if SA[k-1] <= b_[4]), 0.25) / a)
        e_ = ev.get(days[d1], set()); x[13] = 1.0 if (k == 3 and 3 in e_) else 0.0; mu = CF[k] @ x
    Rq = a * np.exp(mu + QQ[k]); rgN = (max(b_[1] for b_ in sb) - min(b_[2] for b_ in sb)) if started else np.nan
    info.append((started, live, Rq, rgN))
    if started:
        hi, lo = max(b_[1] for b_ in sb), min(b_[2] for b_ in sb); x0 = xo(SA[k]); x1 = xo(SA[k]) + (SB[k] - SA[k]) / 5
        ax.add_patch(Rectangle((x0 - 0.5, lo), x1 - x0, hi - lo, fc=O_, alpha=0.08, ec=O_, lw=0.6))
        ax.text(x0 - 0.5, hi, f' {SN[k]} · p50 {Rq[2]:,.0f} · {100*rgN/Rq[2]:.0f}% used', color=O_, fontsize=7.6, va='bottom', clip_on=True)
        if live:
            for qi, nm, ls_, lw_ in [(2, 'p50', '--', 1.6), (3, 'p75', ':', 1), (4, 'p90', ':', 1)]:
                for yv, side in [(lo + Rq[qi], 'low'), (hi - Rq[qi], 'high')]:
                    ax.plot([n - 1, x1], [yv, yv], color=O_, ls=ls_, lw=lw_)
                    ax.text(x1, yv, f' {nm} from the {side} · {Rq[qi]:,.0f}', color=O_, fontsize=7.2, va='center', clip_on=True)
            ys = [lo + Rq[4], hi - Rq[4]]
ylo = min(dLo, *ys); yhi = max(dHi, *ys); pad = (yhi - ylo) * 0.04; ax.set_ylim(ylo - pad, yhi + pad); ax.set_xlim(-1, n + 60)
ax.yaxis.tick_right(); ax.grid(color='#eef1f6', lw=0.6); ax.tick_params(colors='#131722', labelsize=8, length=0)
for sp in ax.spines.values(): sp.set_color('#eef1f6')
tk_ = [i for i in range(n) if bars[i][4] % 120 == 0]; ax.set_xticks(tk_); ax.set_xticklabels([f"{((bars[i][4] + 1080) % 1440) // 60:02d}:00" for i in tk_])
fig.text(0.03, 0.955, 'Ryūjin Jakka · NQ 5 min · 23 Oct 2026 as of 10:45 ET · machine-learned session range forecasts with calibrated bands', fontsize=10.5, color='#131722', weight='bold')
gauge = lambda f, k: '█' * int(round(min(max(f, 0), 1) * k)) + '░' * (k - int(round(min(max(f, 0), 1) * k)))
rows = [('RYŪJIN JAKKA', 'SESSION RANGES', 'p50 · p25–p75', 'pts')]
for k in range(4):
    st_, lv, Rq, rg = info[k]
    stt = f'live {rg:,.0f}' if lv else (f'done {rg:,.0f}' + (' >p90' if rg > Rq[4] else ' <p10' if rg < Rq[0] else '')) if st_ else f'at {ST[k][:5]}'
    rows.append((f'{SN[k]} {ST[k]}', gauge(rg / Rq[4], 10) if st_ else '', f'{Rq[2]:,.0f} · {Rq[1]:,.0f}–{Rq[3]:,.0f}', stt))
dt = pd.Timestamp(days[d1], unit='D')
rows += [('inputs', '', f'ATR {a:,.0f}', f'VIX {vxD[dt]:.1f} ({100*(vxD[dt]/vx20D[dt]-1):+.0f}% vs 20d)'), ('tested', '', 'bands 47–52%', 'of 50')]
x0, y0, wd, hh = 0.035, 0.92, 0.315, 0.026
for k, (a1, b2, c3, d4) in enumerate(rows):
    yy = y0 - k * hh
    fig.patches.append(Rectangle((x0, yy - hh), wd, hh, transform=fig.transFigure, fc='#e65100' if k == 0 else '#f4f6f9', ec='#e65100' if k == 0 else '#dde1e8', lw=0.6))
    tc = '#ffffff' if k == 0 else '#131722'
    fig.text(x0 + 0.005, yy - hh / 2, a1, fontsize=7.3, color=tc if k == 0 else '#5d6476', va='center', family='monospace')
    fig.text(x0 + 0.115, yy - hh / 2, b2, fontsize=7.3, color=tc if k == 0 else O_, va='center', family='monospace')
    fig.text(x0 + 0.185, yy - hh / 2, c3, fontsize=7.3, color=tc, va='center', family='monospace')
    fig.text(x0 + wd - 0.005, yy - hh / 2, d4, fontsize=7.3, color=tc if k == 0 else '#5d6476', va='center', ha='right', family='monospace')
fig.savefig('/home/claude/rj/RyujinJakka_5m.png', facecolor='white')
print('mock', [(SN[k], round(info[k][2][2]), info[k][3]) for k in range(4)], 'ATR', round(a, 1))
