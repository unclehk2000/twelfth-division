"""Ryūjin Jakka research: session ranges. Sessions (ET): Asia 20:00–00:00, London 02:00–05:00, NY AM 09:30–12:00, NY PM 13:30–16:00.
Target: log(session high − low) / daily ATR(14). Features known at the session's start: the same session's log range yesterday and
its 5- and 20-day means (HAR), today's earlier sessions, the move and range so far today, ATR against its 60-day mean, VIX against
its 20-day mean (prior close), CPI / NFP / FOMC day flags, the weekday. NQ / ES / RTY 1-minute 2018 – 23 Oct 2026."""
import numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/claude/lr'); sys.path.insert(0, '/home/claude/hm')
from lib import load, D2025
import events as E
SES = {'Asia': (120, 360), 'London': (480, 660), 'NYAM': (930, 1080), 'NYPM': (1170, 1320)}
def rma(x, n=14):
    out = np.full(len(x), np.nan); a = 1.0 / n; out[n - 1] = np.nanmean(x[:n])
    for i in range(n, len(x)): out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out
vix = pd.read_csv('/mnt/user-data/uploads/VolatilityIndices_daily/VIX.csv', parse_dates=['Date']).set_index('Date').Close
vrel = np.log(vix / vix.rolling(20).mean())
ev = {}
for nm, lst in [('cpi', E.CPI), ('nfp', E.NFP), ('fomc', E.FOMC)]:
    for t in lst: ev.setdefault(pd.Timestamp(t).normalize(), set()).add(nm)
rows = []
for sym in ['NQ', 'ES', 'RTY']:
    m = load(sym); rel = (((m['ts'] % 1440) - 1080) % 1440).astype(int); td = m['td'].astype(int)
    df = pd.DataFrame({'td': td, 'rel': rel, 'H': m['H'], 'L': m['L'], 'O': m['O'], 'C': m['C']})
    g = df.groupby('td'); n = g.size()
    D = pd.DataFrame({'H': g.H.max(), 'L': g.L.min(), 'O': g.O.first(), 'C': g.C.last(), 'n': n})
    pc = D.C.shift(1); tr = np.maximum(D.H - D.L, np.maximum((D.H - pc).abs(), (D.L - pc).abs()))
    D['atr'] = np.r_[np.nan, rma(tr.where(D.n >= 1200).ffill().values)[:-1]]
    D['atrRel'] = np.log(D.atr / D.atr.rolling(60).mean())
    for s, (a, b) in SES.items():
        x = df[(df.rel >= a) & (df.rel < b)].groupby('td')
        D[s + '_rg'] = (x.H.max() - x.L.min()); D[s + '_o'] = x.O.first(); D[s + '_nb'] = x.size()
        D[s + '_lr'] = np.log(D[s + '_rg'] / D.atr)
    # the move and range so far at each session's start
    for s, (a, b) in SES.items():
        x = df[df.rel < a].groupby('td')
        D[s + '_soH'] = x.H.max(); D[s + '_soL'] = x.L.min(); D[s + '_soC'] = x.C.last()
    D['date'] = pd.to_datetime(D.index, unit='D')
    D['dow'] = D.date.dt.dayofweek
    D['vrel'] = D.date.map(vrel.shift(1).reindex(pd.date_range('2000-01-01', '2027-01-01')).ffill())
    D['cpi'] = D.date.map(lambda d: 'cpi' in ev.get(d, set())).astype(int); D['nfp'] = D.date.map(lambda d: 'nfp' in ev.get(d, set())).astype(int); D['fomc'] = D.date.map(lambda d: 'fomc' in ev.get(d, set())).astype(int)
    for k, s in enumerate(SES):
        lr = D[s + '_lr']
        R = pd.DataFrame({'td': D.index, 'sym': sym, 'sess': s, 'k': k, 'y': lr,
                          'l1': lr.shift(1), 'l5': lr.shift(1).rolling(5).mean(), 'l20': lr.shift(1).rolling(20).mean(),
                          'soRg': np.log((D[s + '_soH'] - D[s + '_soL']) / D.atr), 'soMv': (D[s + '_soC'] - D.O).abs() / D.atr,
                          'prev': np.log(D[list(SES)[k - 1] + '_rg'] / D.atr) if k > 0 else lr.shift(1) * np.nan,
                          'atrRel': D.atrRel, 'vrel': D.vrel, 'dow': D.dow, 'cpi': D.cpi, 'nfp': D.nfp, 'fomc': D.fomc, 'atr': D.atr, 'rg': D[s + '_rg'], 'nb': D[s + '_nb'], 'n': D.n})
        rows.append(R)
    print(sym, flush=True)
X = pd.concat(rows, ignore_index=True)
X = X[(X.n >= 1200) & (X.n <= 1440) & X.nb.notna()]
exp_nb = X.sess.map({'Asia': 240, 'London': 180, 'NYAM': 150, 'NYPM': 150})
X = X[X.nb >= 0.9 * exp_nb]
X.to_pickle('/home/claude/rj/t16_rows.pkl'); print(len(X), X.groupby('sess').y.describe()[['count', 'mean', 'std']].round(3))
