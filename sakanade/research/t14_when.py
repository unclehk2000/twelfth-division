"""When the day's high and low form (session of the final extreme) and which weekday holds the week's high and low.
NQ + ES + RTY 1-minute, 2018 – 23 Oct 2026; 2025–26 shown beside 2018–24."""
import numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/claude/lr'); from lib import load, D2025
rows = []; wrows = []
for sym in ['NQ', 'ES', 'RTY']:
    m = load(sym); rel = ((m['ts'] % 1440) - 1080) % 1440; td = m['td'].astype(np.int64)
    df = pd.DataFrame({'td': td, 'rel': rel, 'H': m['H'], 'L': m['L']})
    g = df.groupby('td')
    n = g.size(); ok = n[n >= 1200].index
    ih = g.H.idxmax(); il = g.L.idxmin()
    d = pd.DataFrame({'tH': df.rel.values[ih.values], 'tL': df.rel.values[il.values]}, index=ih.index).loc[ok]
    d['sym'] = sym; rows.append(d)
    dd = pd.DataFrame({'td': ok}); dd['wk'] = (dd.td + 3) // 7; dd['dow'] = pd.to_datetime(dd.td, unit='D').dt.dayofweek
    dh = g.H.max().loc[ok].values; dl = g.L.min().loc[ok].values; dd['h'] = dh; dd['l'] = dl
    for wk, w in dd.groupby('wk'):
        if len(w) < 4: continue
        wrows.append((sym, w.td.iloc[0], w.dow.values[np.argmax(w.h.values)], w.dow.values[np.argmin(w.l.values)]))
D = pd.concat(rows); D['era'] = np.where(D.index >= D2025, '2025–26', '2018–24')
bins = [0, 360, 720, 930, 1140, 1380]; lab = ['Asia 18:00–00:00', 'London 00:00–06:00', 'NY open 06:00–09:30', 'NY AM 09:30–13:00', 'NY PM 13:00–17:00']
for side in ['tH', 'tL']:
    t = D.groupby('era')[side].apply(lambda x: pd.cut(x, bins, right=False, labels=lab).value_counts(normalize=True).reindex(lab)).unstack(0) * 100
    print('day', 'HIGH' if side == 'tH' else 'LOW', '\n', t.round(1))
W = pd.DataFrame(wrows, columns=['sym', 'td', 'dH', 'dL']); W['era'] = np.where(W.td >= D2025, '2025–26', '2018–24')
for side in ['dH', 'dL']:
    t = W.groupby('era')[side].value_counts(normalize=True).unstack(0).reindex(range(5)) * 100
    t.index = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']; print('week', 'HIGH' if side == 'dH' else 'LOW', '\n', t.round(1))
