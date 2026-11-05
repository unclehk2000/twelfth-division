"""Add fresh-raid flags (the leg extreme is the first trade through the level) and ICT location features to the event set."""
import numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/claude/lr'); from lib import load, bars
X = pd.read_pickle('/home/claude/sz/t17_evx.pkl')
out = []
for (sym, u), A in X.groupby(['sym', 'u']):
    m = load(sym); B = bars(m, u); rel = (((B['ts'] % 1440) - 1080) % 1440).astype(int); td = B['td']
    df = pd.DataFrame({'td': td, 'rel': rel, 'H': B['H'], 'L': B['L'], 'O': B['O'], 'C': B['C']})
    wk = (df.td.values + 3) // 7; df['wk'] = wk
    g = df.groupby('td'); gw = df.groupby('wk')
    dHb = g.H.transform(lambda x: x.cummax().shift(1)).values; dLb = g.L.transform(lambda x: x.cummin().shift(1)).values
    wHb = gw.H.transform(lambda x: x.cummax().shift(1)).values; wLb = gw.L.transform(lambda x: x.cummin().shift(1)).values
    D = g.agg(H=('H', 'max'), L=('L', 'min'), O=('O', 'first'))
    W = gw.agg(H=('H', 'max'), L=('L', 'min'), O=('O', 'first'))
    PDH = df.td.map(D.H.shift(1)).values; PDL = df.td.map(D.L.shift(1)).values
    PWH = df.wk.map(W.H.shift(1)).values; PWL = df.wk.map(W.L.shift(1)).values; WO = df.wk.map(W.O).values; DO = df.td.map(D.O).values
    # midnight open (rel 360) and the 08:30 open (rel 870)
    mo = df[df.rel >= 360].groupby('td').O.first(); o83 = df[df.rel >= 870].groupby('td').O.first()
    MO = np.where(rel >= 360, df.td.map(mo).values, np.nan); O83 = np.where(rel >= 870, df.td.map(o83).values, np.nan)
    def since(r0):   # high / low since rel r0 today, before the bar
        s = df.where(df.rel >= r0); hh = s.groupby(df.td).H.transform(lambda x: x.cummax().shift(1)).values; ll = s.groupby(df.td).L.transform(lambda x: x.cummin().shift(1)).values
        return hh, ll
    aH, aL = since(360); lH, lL = since(660)
    AS = df[(df.rel >= 120) & (df.rel < 360)].groupby('td').agg(H=('H', 'max'), L=('L', 'min')); LO = df[(df.rel >= 480) & (df.rel < 660)].groupby('td').agg(H=('H', 'max'), L=('L', 'min'))
    ASH = np.where(rel >= 360, df.td.map(AS.H).values, np.nan); ASL = np.where(rel >= 360, df.td.map(AS.L).values, np.nan)
    LOH = np.where(rel >= 660, df.td.map(LO.H).values, np.nan); LOL = np.where(rel >= 660, df.td.map(LO.L).values, np.nan)
    A = A.copy(); i = A.i.values; xb = i - A.bars_x.values; d = A.dir.values; sb = i - A.bars_leg.values
    sb1 = np.where(td[np.minimum(sb + 1, len(td) - 1)] == td[sb], np.minimum(sb + 1, len(td) - 1), sb)
    x = np.where(d == -1, B['H'][xb], B['L'][xb])
    def fresh(lvH, lvL, befH, befL):
        lv = np.where(d == -1, lvH[xb], lvL[xb]); bf = np.where(d == -1, befH[sb1], befL[sb1])
        first = np.where(d == -1, ~(bf > lv), ~(bf < lv))        # nothing traded through before the leg began (nan-safe)
        hit = np.where(d == -1, x > lv, x < lv)
        return (hit & first & ~np.isnan(lv)).astype(int)
    A['f_pd'] = fresh(PDH, PDL, dHb, dLb); A['f_pw'] = fresh(PWH, PWL, wHb, wLb)
    A['f_as'] = fresh(ASH, ASL, aH, aL); A['f_lo'] = fresh(LOH, LOL, lH, lL)
    A['f_day'] = A.sw_day.values
    e = A.entry.values; ad = A.atrD.values
    A['xMO'] = -d * (e - MO[i]) / ad; A['xDO'] = -d * (e - DO[i]) / ad; A['xWO'] = -d * (e - WO[i]) / ad; A['x83'] = -d * (e - O83[i]) / ad
    pw = (e - PWL[i]) / (PWH[i] - PWL[i]); A['pwx'] = np.where(d == -1, pw, 1 - pw)
    out.append(A); print(sym, u, flush=True)
X = pd.concat(out).sort_index(); X.to_pickle('/home/claude/sz/t17_evx2.pkl'); print(len(X))
print(X.groupby(['u', 'k'])[['f_pd', 'f_pw', 'f_as', 'f_lo', 'f_day', 'sw_pd', 'sw_pw']].mean().round(3))
