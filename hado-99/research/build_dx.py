"""DXY cash index daily (Barchart, 2000–2026) and DX futures 5-minute (2023–Aug 2026, Central time → ET)."""
import pandas as pd, numpy as np
d = pd.read_csv('/home/claude/xa/raw/dx/dxy_daily_historical-data-10-15-2026.csv')
d = d[d.Time.str.match(r'^\d{4}-\d{2}-\d{2}$', na=False)]
d['date'] = pd.to_datetime(d.Time)
d = d.set_index('date').sort_index()
for k in ('Open', 'High', 'Low', 'Latest'):
    d[k] = pd.to_numeric(d[k], errors='coerce')
X = pd.DataFrame({'o': d.Open, 'h': d.High, 'l': d.Low, 'c': d.Latest})
X['r'] = np.log(X.c).diff()
X['tr20'] = np.log(X.c / X.c.shift(20)) * 100           # 20-day trend, %
X['ma200'] = X.c / X.c.rolling(200).mean() - 1
X['vol20'] = X.r.rolling(20).std() * np.sqrt(252) * 100
X = X[X.index >= '2017-01-01']
X.to_pickle('/home/claude/xa/dx_daily.pkl')
print(len(X), X.index.min().date(), X.index.max().date(), 'ann vol %.1f%%' % (X.r.std() * np.sqrt(252) * 100))
m = pd.read_csv('/home/claude/xa/raw/dx/DXY_2023_2026_5min_continuous.csv')
m['ts'] = pd.to_datetime(m.Date + ' ' + m.Time) + pd.Timedelta(hours=1)
m = m.sort_values('ts').drop_duplicates('ts')
for k in ('Open', 'High', 'Low', 'Close'):
    m[k] = pd.to_numeric(m[k], errors='coerce')
m = m[['ts', 'Open', 'High', 'Low', 'Close', 'Contract']]
m.to_pickle('/home/claude/xa/dx_5m.pkl')
print(len(m), m.ts.min(), m.ts.max(), m.Contract.nunique())
# what time is the cash daily close? compare with the futures 5-minute closes at 16:00 / 17:00 ET on a few days
j = m.set_index('ts').Close
for dd in ('2025-03-12', '2025-06-18', '2026-01-21'):
    print(dd, 'daily', X.c.get(pd.Timestamp(dd)), {h: j.get(pd.Timestamp(dd + ' ' + h)) for h in ('15:55', '16:55', '17:00')})
