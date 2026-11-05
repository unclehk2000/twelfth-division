"""HYDRA on the price delivery matrix, part 1. For each market's C2 formation, C3's direction (close-to-close from C2's close), in
the formation's own direction (bull C2 and expansion up → long). Null 50% (any driftless price). Long and short reported apart,
since index futures drift up. Fish 2018–24 | score 2025–26 | per market (score+fish). Errors clustered by day."""
import numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/claude/lr'); from lib import cse, D2025
SY = ['NQ', 'ES', 'YM', 'RTY']
def long_table(W):
    rows = []
    for s in SY:
        o = W[s].copy(); P = [p for p in SY if p != s]
        o['sym'] = s; o['nPlo'] = sum(W[p].slo for p in P); o['nPhi'] = sum(W[p].shi for p in P)
        o['pr2'] = np.mean([W[p].r2 for p in P], axis=0); o['spread'] = o.r2 - o.pr2
        col = np.sign(o.body); o['psp'] = (sum((np.sign(W[p].body) != col).astype(int) for p in P) > 0).astype(int)
        o['nPbull'] = sum((W[p].form == 'bullC2').astype(int) for p in P); o['nPbear'] = sum((W[p].form == 'bearC2').astype(int) for p in P)
        o['nPup'] = sum((W[p].form == 'expUp').astype(int) for p in P); o['nPdn'] = sum((W[p].form == 'expDn').astype(int) for p in P)
        rows.append(o)
    L = pd.concat(rows); L['up'] = (L.r3 > 0).astype(float); L.loc[L.r3 == 0, 'up'] = 0.5
    return L
def wr(g, d):    # win% in direction d (+1 long, -1 short)
    y = g.up.values if d == 1 else 1 - g.up.values
    mu, se, n = cse(y - 0.5, g.td.values); return 50 + 100 * mu, 100 * se, n
def line(lbl, g, d):
    f = g[g.td < D2025]; s = g[g.td >= D2025]
    a = wr(f, d); b = wr(s, d); sy = ' '.join(f'{wr(g[g.sym == q], d)[0]:4.1f}' for q in SY)
    return f'  {lbl:44s} {"L" if d == 1 else "S"} fish {a[0]:5.1f}±{a[1]:3.1f} {a[2]:6d} | score {b[0]:5.1f}±{b[1]:3.1f} {b[2]:5d} | NQ ES YM RTY {sy}'
if __name__ == '__main__':
    for tf in ['D', '240', '60', '15']:
        W = pd.read_pickle(f'/home/claude/pdm/mat_{tf}.pkl'); L = long_table(W); L.to_pickle(f'/home/claude/pdm/long_{tf}.pkl')
        print(f'\n===== {tf} ({len(W)} aligned candles) =====')
        print(line('all candles (drift check)', L, 1))
        for f_, d in [('bullC2', 1), ('bearC2', -1), ('expUp', 1), ('expDn', -1), ('inside', 1), ('outside', 1)]:
            print(line(f'own {f_}', L[L.form == f_], d))
        # cross-market SMT readings
        print('  -- SMT at the low (bullish readings → long) --')
        b = L[L.form == 'bullC2']
        print(line('own bull C2, all 3 partners swept the low too', b[b.nPlo == 3], 1))
        print(line('own bull C2, ≥1 partner held its low (own SMT)', b[b.nPlo < 3], 1))
        h = L[(L.slo == 0) & (L.nPlo >= 1)]
        print(line('own held its low, ≥1 partner swept (partner SMT)', h, 1))
        print(line('… and own closed up (C2 bullish body)', h[h.body > 0], 1))
        print('  -- SMT at the high (bearish readings → short) --')
        b = L[L.form == 'bearC2']
        print(line('own bear C2, all partners swept the high too', b[b.nPhi == 3], -1))
        print(line('own bear C2, ≥1 partner held its high (own SMT)', b[b.nPhi < 3], -1))
        h = L[(L.shi == 0) & (L.nPhi >= 1)]
        print(line('own held its high, ≥1 partner swept (partner SMT)', h, -1))
        print(line('… and own closed down', h[h.body < 0], -1))
        print('  -- PSP (candle colours disagree) --')
        print(line('PSP, own green → long', L[(L.psp == 1) & (L.body > 0)], 1))
        print(line('PSP, own red → short', L[(L.psp == 1) & (L.body < 0)], -1))
        print('  -- relative strength (own C2 return minus partners) --')
        q = L.spread.quantile([0.2, 0.8]).values
        print(line('own strongest fifth vs partners → long', L[L.spread >= q[1]], 1))
        print(line('own weakest fifth vs partners → long', L[L.spread <= q[0]], 1))
