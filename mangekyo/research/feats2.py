"""Zones under each close variant (SET, LST, and ICT's 'widest of the two' rule), with matched no-gap controls for every kind.
Control near edge = the same candle point the real zone hangs from (FVG: candle 3's low / high; VI and SB: candle 3's body
bottom / top), pseudo-zone of the real width below (bull) / above (bear) it."""
import numpy as np, pandas as pd, sys
from data import daily
from gaps import detect, lifecycle
from feats import features
from candles import variant

def cond(kind, d, O, H, L, C, t):
    bt = np.maximum(O, C); bb = np.minimum(O, C)
    if kind == 'FVG': return (L[t] > H[t - 2]) if d == 1 else (H[t] < L[t - 2])
    if kind == 'VI': return (bb[t] > bt[t - 1]) if d == 1 else (bt[t] < bb[t - 1])
    return ((bb[t] > bt[t - 1]) & (bb[t - 1] > bt[t - 2])) if d == 1 else ((bt[t] < bb[t - 1]) & (bt[t - 1] < bb[t - 2]))

def edge(kind, d, O, H, L, C, t):
    if kind == 'FVG': return L[t] if d == 1 else H[t]
    return np.minimum(O[t], C[t]) if d == 1 else np.maximum(O[t], C[t])

def controls_all(z, O, H, L, C, A, M=5, seed=7):
    n = len(C); t = np.arange(2, n); rng = np.random.default_rng(seed); out = []
    for kind in z.kind.unique():
        c2 = t if kind == 'VI' else t - 1
        body = (C[c2] - O[c2]) / A[t]
        for d in (1, -1):
            ok = (~cond(kind, d, O, H, L, C, t)) & np.isfinite(A[t]) & (body * d > 0)
            ct = t[ok]; cb = body[ok] * d
            e = edge(kind, d, O, H, L, C, ct); cd0 = (C[ct] - e) * d / A[ct]
            for r in z[(z.dir == d) & (z.kind == kind)].itertuples():
                m = (np.abs(ct - r.t0) <= 504) & (np.abs(ct - r.t0) > 3)
                if m.sum() < 20: continue
                dist = ((cb[m] - r.c2body) / 0.35) ** 2 + ((cd0[m] - r.d0) / 0.25) ** 2
                for j in ct[m][np.argsort(dist + rng.random(m.sum()) * 1e-9)[:M]]:
                    a = A[j]; ee = edge(kind, d, O, H, L, C, j)
                    top, bot = (ee, ee - r.w * a) if d == 1 else (ee + r.w * a, ee)
                    out.append((j, d, 'CTL', top, bot, j - 2, r.Index, kind))
    return pd.DataFrame(out, columns=['t0', 'dir', 'kind', 'top', 'bot', 't1', 'of', 'okind'])

def run(sym, v, start=None):
    if v == 'WIDE':
        DS, OS, HS, LS, CS = variant(sym, 'SET'); DL, OL, HL, LL, CL = variant(sym, 'LST')
        DS = DS.loc[DL.index]; i = DS.index
        OS, HS, LS, CS = DS.bo.values, DS.bh.values, DS.bl.values, DS.bc.values
        A = DL.atrB.values
        zs = detect(OS, HS, LS, CS, A, kinds=('VI', 'SB')); zl = detect(OL, HL, LL, CL, A, kinds=('VI', 'SB'))
        zs['w0'] = zs.top - zs.bot; zl['w0'] = zl.top - zl.bot; zs['src'] = 'SET'; zl['src'] = 'LST'
        zz = pd.concat([zs, zl]).sort_values('w0', ascending=False).drop_duplicates(['t0', 'dir', 'kind']).sort_values('t0')
        # lifecycle on the chart's own closes: ICT keeps SET on, so the settlement close decides 'closed beyond'
        D, O, H, L, C = DL, OS, HS, LS, CS
        z = lifecycle(zz.drop(columns=['w0']).reset_index(drop=True), O, H, L, C, A)
        z['src'] = zz.src.values
    else:
        D, O, H, L, C = variant(sym, v)
        if v == 'SET':
            DL = variant(sym, 'LST')[0]; D = D.loc[DL.index]; O, H, L, C = D.bo.values, D.bh.values, D.bl.values, D.bc.values
        A = D.atrB.values
        z = detect(O, H, L, C, A)
        z = lifecycle(z, O, H, L, C, A)
    Dv = D.copy(); Dv['b' + 'c'] = C   # features read closes from the variant
    z = features(Dv, z); z['sym'] = sym; z['var'] = v
    z.index = [f'{sym}{v}{i}' for i in range(len(z))]
    q = controls_all(z, O, H, L, C, A)
    q = lifecycle(q, O, H, L, C, A); q = features(Dv, q); q['sym'] = sym; q['var'] = v
    return z, q

if __name__ == '__main__':
    R = []; Q = []
    for s in ['NQ', 'ES', 'RTY', 'YM']:
        for v in ['SET', 'LST', 'WIDE']:
            z, q = run(s, v); R.append(z); Q.append(q)
            print(s, v, z.groupby('kind').size().to_dict(), 'ctl', len(q), flush=True)
    pd.concat(R).to_pickle('zones_var.pkl'); pd.concat(Q, ignore_index=True).to_pickle('ctl_var.pkl')
