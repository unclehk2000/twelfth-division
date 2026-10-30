"""CL 1-minute (FOMC weeks, Barchart, Central time) → ET, one contract per day (the CL front month from cl_daily)."""
import pandas as pd, numpy as np, glob, os
D = pd.read_pickle('/home/claude/xa/cl_daily.pkl')
rows = []
for f in sorted(glob.glob('/home/claude/xa/raw/cl1m/CL*.csv')):
    c = os.path.basename(f)[:-4]
    d = pd.read_csv(f)
    d = d[d.Time.str.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$', na=False)]
    d['ts'] = pd.to_datetime(d.Time) + pd.Timedelta(hours=1)          # Central → Eastern
    d['ctr'] = c
    rows.append(d[['ts', 'ctr', 'Open', 'High', 'Low', 'Latest', 'Volume']])
M = pd.concat(rows).rename(columns={'Latest': 'Close'})
for k in ('Open', 'High', 'Low', 'Close', 'Volume'):
    M[k] = pd.to_numeric(M[k], errors='coerce')
# trading day: bars from 18:00 ET belong to the next day
M['tday'] = (M.ts + pd.Timedelta(hours=6)).dt.normalize()
# keep the front month (by cl_daily's ctr1 on that trading day), else the most active contract that day
front = D.ctr1.reindex(M.tday.unique())
M['front'] = M.tday.map(front)
vol = M.groupby(['tday', 'ctr']).Volume.sum().reset_index().sort_values('Volume').groupby('tday').last().ctr
M['act'] = M.tday.map(vol)
pick = M.front.where(M.front.isin(M.groupby('tday').ctr.unique().explode().values), M.act)
M = M[M.ctr == M.front.fillna(M.act)]
M = M.sort_values('ts').drop_duplicates('ts')
M.to_pickle('/home/claude/xa/cl_1m.pkl')
days = M.groupby('tday').size()
print(len(M), 'days', len(days), 'bars/day median', int(days.median()), M.ts.min(), M.ts.max())
print(days.groupby(days.index.year).size().to_dict())
