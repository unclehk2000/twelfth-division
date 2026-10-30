"""CL daily (Barchart, per contract, settle = 'Latest') → front / second month, roll-safe returns, term structure."""
import pandas as pd, numpy as np, glob, os
MON = dict(F=1, G=2, H=3, J=4, K=5, M=6, N=7, Q=8, U=9, V=10, X=11, Z=12)
rows = []
for f in sorted(glob.glob('/home/claude/xa/raw/cld/CL*.csv')):
    c = os.path.basename(f)[:-4]
    d = pd.read_csv(f)
    d = d[d.Time.str.match(r'^\d{4}-\d{2}-\d{2}$', na=False)]
    d['date'] = pd.to_datetime(d.Time)
    d['ctr'] = c
    d['dm'] = pd.Timestamp(2000 + int(c[3:5]), MON[c[2]], 1)          # delivery month
    rows.append(d[['date', 'ctr', 'dm', 'Open', 'High', 'Low', 'Latest', 'Volume', 'Open Int']])
A = pd.concat(rows).rename(columns={'Latest': 'settle', 'Open Int': 'oi', 'Volume': 'vol'})
for k in ('Open', 'High', 'Low', 'settle', 'vol', 'oi'):
    A[k] = pd.to_numeric(A[k], errors='coerce')
A = A[A.date >= '2017-10-01'].sort_values(['date', 'dm'])
last = A.groupby('ctr').date.max()                                      # last trade date in the file
A['ltd'] = A.ctr.map(last)
# business-day index to measure days to expiry
days = pd.DatetimeIndex(sorted(A.date.unique()))
pos = pd.Series(np.arange(len(days)), index=days)
A['dte'] = A.ltd.map(pos) - A.date.map(pos)
A = A[A.dte >= 0]
# M1 = nearest contract with more than 5 trading days left (roll 5 days before last trade); M2, M3 next
live = A[A.dte > 5].sort_values(['date', 'dm'])
live['k'] = live.groupby('date').cumcount() + 1
P = live[live.k <= 7].pivot_table(index='date', columns='k', values='settle')
C = live[live.k <= 2].pivot_table(index='date', columns='k', values='ctr', aggfunc='first')
D = pd.DataFrame({'m1': P[1], 'm2': P[2], 'm3': P[3], 'm7': P.get(7), 'ctr1': C[1], 'ctr2': C[2]})
# OHLC of M1
m1 = live[live.k == 1].set_index('date')
D['o'], D['h'], D['l'], D['oi1'], D['vol1'] = m1.Open, m1.High, m1.Low, m1.oi, m1.vol
# roll-safe return: today's M1 settle against the same contract's prior settle
S = A.pivot_table(index='date', columns='ctr', values='settle')
prev = S.shift(1)
D['r'] = [np.log(D.m1.iat[i] / prev.at[d, D.ctr1.iat[i]]) if d in prev.index and pd.notna(prev.at[d, D.ctr1.iat[i]]) and prev.at[d, D.ctr1.iat[i]] > 0 and D.m1.iat[i] > 0 else np.nan
          for i, d in enumerate(D.index)]
# term structure: M2 over M1, annualised (monthly spacing); > 0 contango, < 0 backwardation
D['ts12'] = (D.m2 / D.m1 - 1) * 12 * 100
D['ts17'] = (D.m7 / D.m1 - 1) * 2 * 100                                 # 6-month spread, annualised %
D.to_pickle('/home/claude/xa/cl_daily.pkl')
print(len(D), D.index.min().date(), D.index.max().date())
print(D[['m1', 'm2', 'ctr1', 'ctr2', 'r', 'ts12', 'ts17']].iloc[::200].round(3).to_string())
print('ts12 by year', D.ts12.groupby(D.index.year).mean().round(1).to_dict())
print('neg prices', (D.m1 <= 0).sum(), 'r nan', D.r.isna().sum(), 'ann vol', (D.r.std() * np.sqrt(252)).round(3))
