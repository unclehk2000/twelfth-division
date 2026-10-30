"""Intraday divergence vs the dollar (2023 – Aug 2026): at checkpoint T, index move since the anchor against
beta × DX move since the anchor (beta = the index's 60-day daily beta to DXY, known the day before). Does the gap
close by 16:00 (index T→16:00 ~ gap)?"""
import sys; sys.path.insert(0, '/home/claude/xa')
import pandas as pd, numpy as np
from tests import check, table
M = pd.read_pickle('/home/claude/xa/dx_5m.pkl').set_index('ts')
P = pd.read_pickle('/home/claude/xa/P_dx.pkl')
# prior-day 60-day beta per symbol
bet = {}
for S, d in P.groupby('sym'):
    d = d.sort_index()
    cov = (d.y * d.x).rolling(60).mean() - d.y.rolling(60).mean() * d.x.rolling(60).mean()
    bet[S] = (cov / d.x.rolling(60).var()).shift(1)
dxc = M.Close
rows_all = []
for S in ('NQ', 'ES', 'RTY'):
    B = pd.read_pickle(f'/home/claude/kyw/bars_{S}_all.pkl')
    B = B[(B.ts >= '2023-01-02') & (B.ts <= '2026-08-28')]
    B = B.set_index('ts')
    for day, b in B.groupby('tday'):
        if b.Contract.nunique() > 1:
            continue
        def px(hm):
            x = b[b.hm == hm]
            return x.Close.iloc[0] if len(x) else np.nan
        def dx(t):
            x = dxc.get(t)
            return x
        a930 = b[b.hm == 930].Open
        if not len(a930):
            continue
        o = a930.iloc[0]
        c16 = px(1559)
        d0 = pd.Timestamp(day)
        # DX at 09:30 (bar starting 09:25 closes at 09:30)
        dx930 = dx(d0 + pd.Timedelta(hours=9, minutes=25))
        on_px = b.Open.iloc[0]; on_t = b.index[0]
        dxon = dx(on_t - pd.Timedelta(minutes=5)) if dx(on_t - pd.Timedelta(minutes=5)) is not None else dx(on_t)
        be = bet[S].get(d0)
        for T in (1000, 1030, 1100, 1200, 1400):
            pt = px(T - 1 if T % 100 else T - 41)
            dxt = dx(d0 + pd.Timedelta(hours=T // 100, minutes=T % 100) - pd.Timedelta(minutes=5))
            if any(v is None or (isinstance(v, float) and np.isnan(v)) for v in (pt, dxt, dx930, c16, be)):
                continue
            ri = np.log(pt / o) * 100
            rd = np.log(dxt / dx930) * 100
            ri_on = np.log(pt / on_px) * 100
            rd_on = np.log(dxt / dxon) * 100 if dxon else np.nan
            rows_all.append(dict(date=d0, sym=S, T=T, beta=be, ri=ri, rd=rd, gap=ri - be * rd,
                                 gap_on=ri_on - be * rd_on, fwd=np.log(c16 / pt) * 100))
R = pd.DataFrame(rows_all).set_index('date')
R['half'] = np.where(R.index < '2025-01-01', '18-24', '25-26')
R.to_pickle('/home/claude/xa/R_dxgap.pkl')
out = []
for T, d in R.groupby('T'):
    out.append(dict(test=f'{T}: fwd ~ gap since 09:30', **check(d, 'fwd ~ gap', 'gap')))
    out.append(dict(test=f'{T}: fwd ~ gap since 18:00', **check(d.dropna(subset=['gap_on']), 'fwd ~ gap_on', 'gap_on')))
    out.append(dict(test=f'{T}: fwd ~ DX move since 09:30', **check(d, 'fwd ~ rd', 'rd')))
print(len(R), R.groupby('T').size().to_dict())
print(table(out).round(4).to_string())
