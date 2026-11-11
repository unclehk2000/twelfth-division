"""Katen Kyōkotsu tests before claims (6 Nov 2026): AXR-style ladders anchored at each period's open.

Horizons: day (18:00 session), week, month, quarter. R = c x implied vol x sqrt(days / 252) x the period's open
(VIX9D for day, week, month; VIX3M for quarter; the last close before the period opens), or the classic average
(the last 20 days / 4 weeks / 3 months / 3 quarters). Ladder: EQ = open, R+ / R- = open +- R/2, and 1/4 and 1/3 of R in
from each end.
A  c fitted on 2018-24 (median of range / implied move) for NQ, ES (1-minute) and RTY (daily bars).
B  Calibration: share of periods whose range ends beyond 1 x R; hit rates of R+ / R- (either, both); implied vs average.
C  Reactions: at the first touch of each ladder level from inside, race 0.1 x R back toward EQ vs 0.1 x R through it,
   to the period's end (null 50%), NQ + ES 1-minute; clustered by period.
"""
import numpy as np, pandas as pd, hydra, lib
P = pd.read_pickle('cache/panel.pkl')
H = {'D': (1, 'VIX9D', 20), 'W': (5, 'VIX9D', 4), 'M': (21, 'VIX9D', 3), 'Q': (63, 'VIX3M', 3)}

def keys(td_dates, h):
    d = pd.DatetimeIndex(td_dates)
    if h == 'D':
        return d.strftime('%Y%m%d').astype(int)
    if h == 'W':
        iso = d.isocalendar()
        return (iso['year'].values * 100 + iso['week'].values)
    if h == 'M':
        return d.year * 100 + d.month
    return d.year * 10 + (d.month - 1) // 3 + 1

def periods_1m(mk, h):
    """per period: first td, open, high, low (raw contract prices; a roll inside a period is small against W / M / Q ranges)"""
    m = lib.load(mk)
    td = pd.to_datetime(m['td'].astype(str))
    k = np.asarray(keys(td, h))
    df = pd.DataFrame({'k': k, 'td': td, 'O': m['O'], 'H': m['H'], 'L': m['L'], 'C': m['C'], 'i': np.arange(len(k))})
    g = df.groupby('k', sort=True)
    T = pd.DataFrame({'td0': g['td'].first(), 'O': g['O'].first(), 'H': g['H'].max(), 'L': g['L'].min(), 'C': g['C'].last(),
                      'a': g['i'].first(), 'b': g['i'].last() + 1, 'nd': g['td'].nunique()})
    return T, m

def periods_daily(mk, h):
    d = P[[f'{mk}_aO', f'{mk}_aH', f'{mk}_aL', f'{mk}_aC']].dropna()
    d.columns = ['O', 'H', 'L', 'C']
    k = np.asarray(keys(d.index, h))
    g = d.assign(k=k, td=d.index).groupby('k')
    return pd.DataFrame({'td0': g['td'].first(), 'O': g['O'].first(), 'H': g['H'].max(), 'L': g['L'].min(), 'C': g['C'].last(), 'nd': g['td'].nunique()})

def add_R(T, h, c=None):
    days, vcol, navg = H[h]
    v = P[vcol].shift(1)
    T = T.copy()
    T['v'] = T['td0'].map(lambda d: v.get(d, np.nan))
    T['iv'] = T['v'] / 100 * np.sqrt(days / 252)
    T['rng'] = (T['H'] - T['L']) / T['O']
    T['avg'] = T['rng'].shift(1).rolling(navg, min_periods=max(2, navg // 2)).mean()
    T['per'] = ['fish' if d.year <= hydra.FISH_END else 'test' for d in T['td0']]
    minn = {'D': 1, 'W': 4, 'M': 15, 'Q': 40}[h]
    T = T[(T['nd'] >= minn)].dropna(subset=['iv', 'avg'])
    if c is None:
        c = (T.loc[T.per == 'fish', 'rng'] / T.loc[T.per == 'fish', 'iv']).median()
    T['Ri'] = c * T['iv']
    return T, c

def calib(T):
    out = {}
    for p, g in T.groupby('per'):
        for nm, R in (('implied', g['Ri']), ('average', g['avg'])):
            up = (g['H'] - g['O']) / g['O'] >= R / 2; dn = (g['O'] - g['L']) / g['O'] >= R / 2
            out[(p, nm)] = dict(n=len(g), beyond=(g['rng'] >= R).mean(), either=(up | dn).mean(), both=(up & dn).mean(),
                                err=np.abs(np.log(g['rng'] / R)).mean())
    return out

def reactions(mk, h, c):
    T, m = periods_1m(mk, h)
    T, _ = add_R(T, h, c)
    rows = []
    for k, r in T.iterrows():
        a, b = int(r['a']), int(r['b'])
        Hh, Ll = m['H'][a:b], m['L'][a:b]
        O = r['O']; R = r['Ri'] * O; d = 0.1 * R
        lv = {'R+': O + R / 2, '1/4 R+': O + R / 2 - R / 4, '1/3 R+': O + R / 2 - R / 3,
              '1/3 R-': O - R / 2 + R / 3, '1/4 R-': O - R / 2 + R / 4, 'R-': O - R / 2}
        for nm, L in lv.items():
            upper = nm.endswith('+')
            hit = np.flatnonzero(Hh >= L) if upper else np.flatnonzero(Ll <= L)
            if len(hit) == 0:
                continue
            i = hit[0]
            # from the level: back toward EQ by d (reversal) or through by d (continuation), from the next minute on
            rev_t = (Ll[i + 1:] <= L - d) if upper else (Hh[i + 1:] >= L + d)
            con_t = (Hh[i + 1:] >= L + d) if upper else (Ll[i + 1:] <= L - d)
            ir = np.flatnonzero(rev_t); ic = np.flatnonzero(con_t)
            a1 = ir[0] if len(ir) else 10 ** 9; a2 = ic[0] if len(ic) else 10 ** 9
            if a1 == a2:
                continue
            rows.append(dict(k=f'{mk}{k}', per=r['per'], level=nm, rev=float(a1 < a2)))
    return pd.DataFrame(rows)

if __name__ == '__main__':
    pd.set_option('display.width', 220)
    C = {}
    print('=== A / B: c (fish) and calibration; beyond = range >= R, either / both = open +- R/2 reached, err = mean abs log error ===')
    for mk in ('NQ', 'ES', 'RTY'):
        for h in ('D', 'W', 'M', 'Q'):
            if mk == 'RTY':
                T = periods_daily(mk, h)
            else:
                T, _ = periods_1m(mk, h)
            T, c = add_R(T, h)
            C[(mk, h)] = c
            cb = calib(T)
            line = f'{mk} {h} c {c:.2f} |'
            for p in ('fish', 'test'):
                i, a = cb[(p, 'implied')], cb[(p, 'average')]
                line += f" {p} n {i['n']}: beyond {i['beyond']*100:.0f}% either {i['either']*100:.0f}% both {i['both']*100:.0f}% err {i['err']:.3f} (avg {a['err']:.3f}, beyond {a['beyond']*100:.0f}%) |"
            print(line)
    pd.to_pickle(C, 'cache/katen_c.pkl')
    print('=== C: first touch of each level, reversal 0.1R toward EQ before 0.1R through (NQ + ES, implied ladder) ===')
    for h in ('D', 'W', 'M', 'Q'):
        X = pd.concat([reactions(mk, h, C[(mk, h)]) for mk in ('NQ', 'ES')])
        for lvl in ('R+', '1/4 R+', '1/3 R+', '1/3 R-', '1/4 R-', 'R-'):
            res = {}
            for p in ('fish', 'test'):
                g = X[(X.level == lvl) & (X.per == p)]
                res[p] = hydra.rate(g.rev.values, g.k.values)
            v = hydra.verdict(res['fish'], res['test'], key='r')
            print(f"{h} {lvl:7s} fish {hydra.fmt(res['fish'])} | test {hydra.fmt(res['test'])} | {v}")
