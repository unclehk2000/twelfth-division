"""Hydra pass on the NY AM heads: fish on 2018-24 (the ✓ rule also reports 2025-26 and each symbol), then score the live
models once on the locked 2025-26 test."""
import sys, numpy as np, pandas as pd, statsmodels.formula.api as smf, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude/gh2/stats-kit'); from stats_kit import check, table
cols = ['coef', 'p', 'n', '18-24', 'p_18-24', '25-26', 'p_25-26', 'ES', 'NQ', 'RTY', 'ok']
D = pd.read_pickle('ny.pkl'); D['date'] = D.day; D = D.set_index('date')
rows = []
print('=== H-A  nearer level touched first (both sides present), vs the random-walk odds and vs a shifted grid')
for g in ('f', 'k'):
    Z = []
    for nm, real in ((g, 1.0), ('p' + g, 0.0)):
        x = D.dropna(subset=[nm + 'U', nm + 'D', nm + 'first']).copy()
        du, dd = x[nm + 'U'] - x.P, x.P - x[nm + 'D']
        near_up = du <= dd
        x['y'] = np.where(near_up, x[nm + 'first'], 1 - x[nm + 'first'])
        x['rw'] = np.where(near_up, dd / (du + dd), du / (du + dd))
        x['ex'] = x.y - x.rw; x['real'] = real
        Z.append(x)
    Z = pd.concat(Z)
    print(g, Z.groupby('real')[['y', 'rw', 'ex']].mean().round(3).to_string())
    rows.append(check(Z, 'ex ~ real', 'real', test=f'{g}: nearer-first excess, real vs shifted grid'))
    rows.append(check(Z[Z.real == 1], 'ex ~ 1', 'Intercept', test=f'{g}: nearer-first excess over random walk'))
print('=== H-B  the nearer level reached in the NY AM (09:30-10:59) and by 16:59, vs its mirror across the open')
for g in ('f', 'k'):
    x = D.dropna(subset=[g + 'near_am']).copy()
    for h_ in ('am', 'day'):
        L = pd.concat([x.assign(y=x[f'{g}near_{h_}'].astype(float), real=1.0), x.assign(y=x[f'{g}mir_{h_}'].astype(float), real=0.0)])
        print(g, h_, 'near', L[L.real == 1].y.mean().round(3), 'mirror', L[L.real == 0].y.mean().round(3), 'n', len(x))
        rows.append(check(L, 'y ~ real', 'real', test=f'{g}: nearer level by {h_} vs mirror'))
    # outside the grid (one side only): back to the grid vs away
    o = x[~x[g + 'two'].astype(bool)]
    if len(o) > 100:
        L = pd.concat([o.assign(y=o[f'{g}near_am'].astype(float), real=1.0), o.assign(y=o[f'{g}mir_am'].astype(float), real=0.0)])
        print(g, 'outside the grid, NY AM: back to it', L[L.real == 1].y.mean().round(3), 'mirror', L[L.real == 0].y.mean().round(3), 'n', len(o))
        rows.append(check(L, 'y ~ real', 'real', test=f'{g}: outside the grid, back to it by 11:00 vs mirror'))
print('=== H-C  direction: NY AM closes toward the nearer key level')
x = D.dropna(subset=['knear_up', 'Cam']).copy(); x['y'] = ((x.Cam > x.P) == x.knear_up.astype(bool)).astype(float)
print('toward the nearer key level', x.y.mean().round(3), 'n', len(x))
rows.append(check(x.assign(y0=x.y - 0.5), 'y0 ~ 1', 'Intercept', test='NY AM closes toward the nearer key level (vs 50%)'))
x['y2'] = ((x.Cam > x.P) == (x.fpos < 0.5) if False else (x.Cam > x.P)).astype(float)
T = table(rows); print(T[cols].to_string())

print('=== H-D  same-day reach of the five key levels (by 16:59) from a checkpoint: units and extra heads')
K = pd.read_pickle('nyck.pkl'); K['date'] = K.day; K = K.set_index('date')
for u in ('adr', 'atr15', 'awr'):
    K['d_' + u] = (K.d / K[u]).clip(0, 3 if u != 'atr15' else 40)
K['ckf'] = K.ck.astype(str); K = K.dropna(subset=['d_atr15'])
tr, te = K[K.half == '18-24'], K[K.half == '25-26'].copy()
for f in ('y ~ C(ckf)', 'y ~ d_adr + np.sqrt(d_adr) + C(ckf)', 'y ~ d_atr15 + np.sqrt(d_atr15) + C(ckf)', 'y ~ d_awr + np.sqrt(d_awr) + C(ckf)',
          'y ~ (d_adr + np.sqrt(d_adr)) * C(ckf)', 'y ~ d_adr + np.sqrt(d_adr) + C(ckf) + C(dow)', 'y ~ d_adr + np.sqrt(d_adr) + C(ckf) + side',
          'y ~ d_adr + np.sqrt(d_adr) + C(ckf) + inside', 'y ~ d_adr + np.sqrt(d_adr) + C(ckf) + C(f)'):
    m = smf.logit(f, tr).fit(disp=0); p = m.predict(te); print(f'{f:46s} OOS Brier {np.mean((p - te.y) ** 2):.4f}')
K['dc'] = K.d_adr; K['sq'] = np.sqrt(K.dc)
rows2 = [check(K, 'y ~ dc + sq + C(ckf)', 'dc', test='same-day reach | distance (ADR20)'),
         check(K, 'y ~ dc + sq + C(ckf) + side', 'side', test='level above price (vs below)'),
         check(K, 'y ~ dc + sq + C(ckf) + inside', 'inside', test='price between the anchors'),
         check(K.assign(fri=(K.dow == 4).astype(float)), 'y ~ dc + sq + C(ckf) + fri', 'fri', test='Friday'),
         check(K.assign(mon=(K.dow == 0).astype(float)), 'y ~ dc + sq + C(ckf) + mon', 'mon', test='Monday'),
         check(K.assign(anc=K.f.isin([0.0, 1.0]).astype(float)), 'y ~ dc + sq + C(ckf) + anc', 'anc', test='an anchor (0 / 1) vs EQ / SDs')]
T = table(rows2); print(T[cols].to_string())
