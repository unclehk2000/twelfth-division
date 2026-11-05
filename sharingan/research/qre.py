"""Quarterly range expectation (Sharingan v3.1). Daily back-adjusted NQ / ES / RTY 2010 – 23 Oct 2026.
q = quarter range ÷ (ADR × √63), ADR = mean daily high − low of the N trading days before the quarter's first day.
Pick N by out-of-sample dispersion (fish quarters 2010–2021, score 2022–2026). Then the live table: P(quarter range ≥ the
expected range by quarter end | share of the quarter elapsed, share of the expected range used), from every trading day
of every quarter (clustered by quarter)."""
import numpy as np, pandas as pd, json
out = {}
rows = []
for sym in ['NQ', 'ES', 'RTY']:
    d = pd.read_csv(f'/home/claude/upd/raw/{sym}_daily_continuous.csv', parse_dates=['Date'])
    d = d[(d.Date >= '2009-10-01') & (d.AdjHigh > d.AdjLow)].reset_index(drop=True)
    d['rg'] = d.AdjHigh - d.AdjLow
    d['q'] = d.Date.dt.to_period('Q')
    for N in [5, 10, 20, 40, 60]:
        d[f'adr{N}'] = d.rg.rolling(N).mean().shift(1)
    for q, g in d.groupby('q'):
        if q < pd.Period('2010Q1') or len(g) < 55:
            continue
        i0 = g.index[0]
        hi = g.AdjHigh.cummax().values; lo = g.AdjLow.cummin().values
        fin = hi[-1] - lo[-1]
        r = dict(sym=sym, q=str(q), n=len(g), fin=fin, qo=g.AdjOpen.iloc[0], last=q == pd.Period('2026Q4'))
        for N in [5, 10, 20, 40, 60]:
            r[f'a{N}'] = d.loc[i0, f'adr{N}']
        r['path_rng'] = hi - lo; r['days'] = np.arange(1, len(g) + 1)
        # which side extended: up excursion vs down excursion from the open (for the open-anchored version)
        r['up'] = hi[-1] - g.AdjOpen.iloc[0]; r['dn'] = g.AdjOpen.iloc[0] - lo[-1]
        rows.append(r)
Q = pd.DataFrame(rows)
Q = Q[~Q['last']]
Q['score'] = Q.q.str[:4].astype(int) >= 2022
print('quarters', len(Q), 'score', Q.score.sum())
print('\nN  | log-ratio sd fish  score | median q fish score')
best = None
for N in [5, 10, 20, 40, 60]:
    lr = np.log(Q.fin / (Q[f'a{N}'] * np.sqrt(63)))
    sf, ss = lr[~Q.score].std(), lr[Q.score].std()
    print(f'{N:2d} | {sf:.3f} {ss:.3f} | {np.exp(lr[~Q.score].median()):.3f} {np.exp(lr[Q.score].median()):.3f}')
    if best is None or sf < best[1]:
        best = (N, sf)
N = best[0]
print('chosen N =', N, '(lowest fish dispersion)')
ratio = Q.fin / (Q[f'a{N}'] * np.sqrt(63))
qs = {p: float(np.quantile(ratio[~Q.score], p)) for p in [0.1, 0.25, 0.5, 0.75, 0.9]}
print('fish quantiles', {k: round(v, 3) for k, v in qs.items()})
for nm, m in [('fish', ~Q.score), ('score', Q.score)]:
    r = ratio[m]
    print(nm, 'share below p25 %.1f  p50 %.1f  p75 %.1f  n=%d' % (100 * (r < qs[0.25]).mean(), 100 * (r < qs[0.5]).mean(), 100 * (r < qs[0.75]).mean(), len(r)))
# open-anchored: max(up, dn) relative to expected range
# live table from each day of each quarter
L = []
for _, r in Q.iterrows():
    R50 = qs[0.5] * r[f'a{N}'] * np.sqrt(63)
    for k, (pr, dd) in enumerate(zip(r.path_rng, r.days)):
        L.append(dict(q=r.q, sym=r.sym, score=r.score, e=dd / r.n, u=pr / R50, hit=float(r.fin >= R50), hit75=float(r.fin >= R50 * qs[0.75] / qs[0.5])))
L = pd.DataFrame(L)
L['eb'] = pd.cut(L.e, [0, 0.25, 0.5, 0.75, 1.0001], labels=False, right=False)
L['ub'] = pd.cut(L.u, [0, 0.5, 0.75, 1.0, 1e9], labels=False, right=False)
tab = L[~L.score].groupby(['eb', 'ub']).hit.mean().unstack()
tab75 = L[~L.score].groupby(['eb', 'ub']).hit75.mean().unstack()
cnt = L[~L.score].groupby(['eb', 'ub']).q.nunique().unstack()
print('\nP(reach expected range by quarter end) fish — rows: elapsed <25/25-50/50-75/75-100%, cols: used <50/50-75/75-100/100+%')
print((100 * tab).round(0)); print('quarters per cell'); print(cnt)
print('P(reach the p75 range)'); print((100 * tab75).round(0))
# calibration check on the score era: Brier of the table vs a flat 50%
S = L[L.score].copy()
S['p'] = [tab.loc[e, u] if (e in tab.index and u in tab.columns and not np.isnan(tab.loc[e, u])) else 0.5 for e, u in zip(S.eb, S.ub)]
S.loc[S.ub == 3, 'p'] = 1.0
b1 = ((S.p - S.hit) ** 2).mean(); b0 = ((S.hit.mean() - S.hit) ** 2).mean(); bb = ((0.5 - S.hit) ** 2).mean()
print(f'\nscore era Brier: table {b1:.4f} vs constant base rate {b0:.4f} vs 0.5 {bb:.4f}; base rate {S.hit.mean():.3f} (quarters {S.q.nunique()} × syms)')
out = dict(N=N, q=qs, tab=(tab.values * 100).round(0).tolist(), tab75=(tab75.values * 100).round(0).tolist())
json.dump(out, open('/home/claude/sh3/q/qre.json', 'w'), indent=1)
# current quarter snapshot (2026Q4 so far) for NQ
