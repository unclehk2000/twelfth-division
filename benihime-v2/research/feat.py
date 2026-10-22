"""Benihime v2 research: features for each RTH gap, known at 09:30 (or 09:45 for the first-candle test).
Oriented so + = the gap's direction (away from the fill).
out_pdr  open beyond the prior day's RTH extreme in the gap's direction (up gap: open > PDH)
on_loc   open's place in the overnight range (18:00-09:29), 1 = at the ON extreme in the gap's direction
on_thru  the overnight already traded back through the prior close (pre-filled overnight)
pd_with  the prior RTH session moved in the gap's direction (close vs open)
pd_cloc  prior close's place in the prior RTH range, 1 = at the extreme in the gap's direction
f15_away first 15-min candle (09:30-09:44) close vs open in gap-size units, + = away from the fill
f15_hit  gap filled inside the first 15 minutes
f15_ce   CE reached inside the first 15 minutes
dx_z     DX futures overnight change (16:14 -> 09:29 ET) in sd of the prior 20 days', oriented: + = DXY moved the way that
         supports the gap (DXY down for an up gap: index/dollar contrarian)
Writes feat.pkl (rows of rg_rows3 + features)."""
import numpy as np, pandas as pd

R = pd.read_pickle('/home/claude/rg/rg_rows3.pkl')
out = []
for sym in ('NQ', 'ES', 'RTY'):
    b = pd.read_pickle(f'/home/claude/kyw/bars_{sym}_all.pkl')[['ts', 'Open', 'High', 'Low', 'Close', 'tday', 'hm']].reset_index(drop=True)
    O, H, L, C = (b[c].to_numpy() for c in ('Open', 'High', 'Low', 'Close'))
    hm = b.hm.to_numpy(); td = b.tday.to_numpy()
    # day boundaries
    starts = np.r_[0, np.flatnonzero(td[1:] != td[:-1]) + 1]
    ends = np.r_[starts[1:], len(b)]
    info = {}
    for s, e in zip(starts, ends):
        h = hm[s:e]
        rth = np.flatnonzero((h >= 930) & (h <= 1614)) + s
        on = np.flatnonzero((h < 930) | (h >= 1800)) + s
        f15 = np.flatnonzero((h >= 930) & (h <= 944)) + s
        if len(rth) < 300:
            continue
        info[td[s]] = dict(rH=H[rth].max(), rL=L[rth].min(), rO=O[rth[0]], rC=C[rth[-1]],
                           onH=H[on].max() if len(on) else np.nan, onL=L[on].min() if len(on) else np.nan,
                           f15H=H[f15].max(), f15L=L[f15].min(), f15C=C[f15[-1]], f15O=O[f15[0]])
    days = sorted(info)
    prev = {days[i]: days[i - 1] for i in range(1, len(days))}
    rs = R[R.sym == sym]
    for i, r in rs.iterrows():
        d = r.tday
        if d not in info or d not in prev:
            continue
        p, t = info[prev[d]], info[d]
        up = r.up; s = 1 if up else -1; g = r.g; pc = r.pc; op = r.op
        rng = p['rH'] - p['rL']; onr = t['onH'] - t['onL']
        f = dict(idx=i)
        f['out_pdr'] = (op > p['rH']) if up else (op < p['rL'])
        f['on_loc'] = ((op - t['onL']) / onr if up else (t['onH'] - op) / onr) if onr > 0 else np.nan
        f['on_thru'] = (t['onL'] <= pc) if up else (t['onH'] >= pc)
        f['pd_with'] = (p['rC'] > p['rO']) if up else (p['rC'] < p['rO'])
        f['pd_cloc'] = ((pc - p['rL']) / rng if up else (p['rH'] - pc) / rng) if rng > 0 else np.nan
        f['f15_away'] = s * (t['f15C'] - t['f15O']) / g
        f['f15_hit'] = (t['f15L'] <= pc) if up else (t['f15H'] >= pc)
        f['f15_ce'] = (t['f15L'] <= (op + pc) / 2) if up else (t['f15H'] >= (op + pc) / 2)
        f['pdr_rel'] = rng
        out.append(f)
F = pd.DataFrame(out).set_index('idx')
D = R.join(F, how='inner')

# DXY overnight change, from DX futures 5-minute bars (2023 - Aug 2026), ET
m = pd.read_pickle('/home/claude/xa/dx_5m.pkl').sort_values('ts').reset_index(drop=True)
m['hm'] = m.ts.dt.hour * 100 + m.ts.dt.minute
m['date'] = m.ts.dt.normalize()
c1610 = m[m.hm == 1610].groupby('date').Close.last()        # the 16:10 bar closes 16:14:59
c0925 = m[m.hm == 925].groupby('date').Close.last()         # the 09:25 bar closes 09:29:59
dxo = {}
dates = sorted(set(c0925.index))
pcl = c1610.sort_index()
for d in dates:
    prior = pcl[pcl.index < d]
    if len(prior) == 0:
        continue
    pdte = prior.index[-1]
    if (d - pdte).days > 4:
        continue
    dxo[d] = (c0925[d] - prior.iloc[-1]) / prior.iloc[-1] * 100
dx = pd.Series(dxo).sort_index()
sd = dx.abs().shift(1).rolling(20).mean()
dxz = (dx / sd).rename('dxz')
D = D.join(dxz, on='tday')
D['dx_z'] = np.where(D.up, -1, 1) * D.dxz
D.to_pickle('/home/claude/rg/bh2/feat.pkl')
print(D.shape, D.dx_z.notna().sum())
print(D[['out_pdr', 'on_loc', 'on_thru', 'pd_with', 'pd_cloc', 'f15_away', 'f15_hit', 'dx_z']].describe(include='all').T)
