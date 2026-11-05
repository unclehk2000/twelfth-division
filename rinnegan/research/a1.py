import numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/claude/lr')
from lib import D2025
from rat import ratio_diff
D = pd.read_pickle('/home/claude/lr/t1_rows.pkl')
R = 4
D['g'] = D.sym + D.td.astype(str)
D['era'] = np.where(D.td >= D2025, 'score', 'fish')


def line(d, num, den, lab):
    ar = num(d.o); br = den(d.o)
    an = np.mean([num(d[f'o{r}']) for r in range(R)], 0); bn = np.mean([den(d[f'o{r}']) for r in range(R)], 0)
    Pr, Pn, dd, se, ser, nb = ratio_diff(ar, br, an, bn, d.g)
    return f'{lab:34s} real {100*Pr:5.1f}% (±{100*ser:3.1f})  flip {100*Pn:5.1f}%  diff {100*dd:+5.1f} ±{100*se:3.1f}  n={nb}'


comp = lambda o: (o == 1).astype(float)
res = lambda o: o.isin([1, 2]).astype(float)
dirc = lambda o: (o == 0).astype(float)
dres = lambda o: o.isin([0, 1, 2, 3]).astype(float)
one = lambda o: np.ones(len(o))
print('A. after the 50% touch: P(0 breaks before 100 is taken)  [fadi "completion"]')
for era in ['fish', 'score']:
    for lay in ['ST', 'IT']:
        for u in [5, 15, 60]:
            d = D[(D.era == era) & (D.layer == lay) & (D.u == u)]
            print(era, line(d, comp, res, f'{lay} {u}m'))
print('\nB. direct continuation: 0 broken before the 50% touch')
for era in ['fish', 'score']:
    for lay in ['ST', 'IT']:
        d = D[(D.era == era) & (D.layer == lay)]
        print(era, line(d, dirc, lambda o: (o != 5).astype(float), f'{lay} all tf'))
print('\nC. Tip 1: invalidation after touch, split by a bull FVG in the discount half')
inv = lambda o: (o == 2).astype(float)
for era in ['fish', 'score']:
    for lay in ['ST', 'IT']:
        for f in [0, 1]:
            d = D[(D.era == era) & (D.layer == lay) & (D.fvg == f)]
            print(era, line(d, inv, res, f'{lay} fvgInDiscount={f}'))
print('\nD. Tip 2: both sides swept within the horizon, by width/ATR')
D['wb'] = pd.cut(D.w, [0, 1, 2, 4, 1e9], labels=['<1', '1-2', '2-4', '4+'])
both = lambda o: o
for era in ['fish', 'score']:
    for lay in ['ST', 'IT']:
        for wb in ['<1', '1-2', '2-4', '4+']:
            d = D[(D.era == era) & (D.layer == lay) & (D.wb == wb)]
            ar = d.both.values; an = np.mean([d[f'b{r}'].values for r in range(R)], 0)
            Pr, Pn, dd, se, ser, nb = ratio_diff(ar, np.ones(len(d)), an, np.ones(len(d)), d.g)
            print(era, f'{lay} width {wb:4s}  real {100*Pr:5.1f}%  flip {100*Pn:5.1f}%  diff {100*dd:+5.1f} ±{100*se:3.1f}  n={nb}')
print('\nE. score era by symbol, ST+IT pooled, completion after touch')
for s in ['NQ', 'ES', 'RTY']:
    d = D[(D.era == 'score') & (D.sym == s)]
    print(line(d, comp, res, s))
print('\nshare of outcomes (score, real):', D[D.era == 'score'].o.value_counts(normalize=True).sort_index().round(3).to_dict())
