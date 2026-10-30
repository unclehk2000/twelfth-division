"""Getsuga Jūjishō research, step 1: the data. NQ 1-minute 2018 → 23 Oct 2026 (ET).
One row per 09:30 session (calendar date of its 09:30 bar), so a holiday session that the data fold into the next trading
day (e.g. Juneteenth Friday into Monday) stays on its own date, as on a TradingView chart.
First presented FVG (FPFVG), as Byakugan detects it: on 1-minute bars, the first three consecutive candles that all start at
or after 09:30 and whose third candle starts by 09:59, with a wick gap (bull: low3 > high1, bear: high3 < low1). Gap = high1
→ low3 (bull) or high3 → low1 (bear); CE = its midpoint. It is presented when the third candle closes.
Writes days.pkl (one row per session)."""
import numpy as np, pandas as pd
b = pd.read_pickle('/home/claude/kyw/bars_NQ_all.pkl').reset_index(drop=True)
O, H, L, C, V = (b[c].to_numpy() for c in ('Open', 'High', 'Low', 'Close', 'Volume'))
hm = b.hm.to_numpy(); con = b.Contract.to_numpy(); ts = b.ts
cal = ts.dt.normalize().to_numpy()
rthm = (hm >= 930) & (hm < 1700)
idx = np.flatnonzero(rthm)
# group RTH bars by calendar date
dates = cal[idx]; st = np.r_[0, np.flatnonzero(dates[1:] != dates[:-1]) + 1]; en = np.r_[st[1:], len(idx)]
rows = []
for s, e in zip(st, en):
    rth = idx[s:e]
    if len(rth) < 60 or hm[rth[0]] > 945:
        continue
    d = pd.Timestamp(dates[s])
    # the trading day's full range for ADR (the 18:00 → 17:00 day that contains this session)
    r = dict(date=d, dow=d.dayofweek, i930=rth[0], o930=O[rth[0]], rthH=H[rth].max(), rthL=L[rth].min(), rthV=V[rth].sum(),
             c_end=C[rth[-1]], rth_end=rth[-1], con=con[rth[-1]], nbars=len(rth))
    w = rth[(hm[rth] >= 930) & (hm[rth] <= 959)]
    for j in range(len(w) - 2):
        i1, i3 = w[j], w[j] + 2
        if i3 > w[-1] or hm[i3] > 959:
            break
        if L[i3] > H[i1]:
            r.update(fp=1, top=L[i3], bot=H[i1])
        elif H[i3] < L[i1]:
            r.update(fp=-1, top=L[i1], bot=H[i3])
        else:
            continue
        r.update(i1=i1, i3=i3, fpt=hm[i3], ce=(r['top'] + r['bot']) / 2, gap=r['top'] - r['bot'], P0=C[i3])
        r['pre_rng'] = H[rth[0]:i3 + 1].max() - L[rth[0]:i3 + 1].min()
        rest = np.arange(i3 + 1, rth[-1] + 1)
        r['rest_rng'] = H[rest].max() - L[rest].min()
        am = rest[hm[rest] < 1100]
        r['am_rng'] = H[am].max() - L[am].min() if len(am) else np.nan
        break
    rows.append(r)
D = pd.DataFrame(rows)
D['rrng'] = D.rthH - D.rthL
D['radr5'] = D.rrng.shift(1).rolling(5).mean()
D['medV'] = D.rthV.rolling(60, min_periods=20).median().shift(1)
D['half'] = D.nbars < 300
D['wk'] = D.date - pd.to_timedelta(D.dow, unit='D')
D.to_pickle('days.pkl')
print('sessions', len(D), 'with FPFVG', D.fp.notna().sum(), f"({D.fp.notna().mean():.1%})", 'half/holiday sessions', int(D.half.sum()))
print('FPFVG third-candle minute quantiles', D.fpt.quantile([.1, .25, .5, .75, .9]).tolist())
print(D[D.date >= '2026-10-19'][['date', 'fp', 'top', 'bot', 'ce', 'gap', 'fpt', 'P0']].to_string())
