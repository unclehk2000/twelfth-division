"""Rikugan tests before claims (6 Nov 2026).

R = c x prior VIX9D close / 100 / sqrt(252) x the session's 18:00 open (c = 1.54 NQ, 1.13 ES, fitted 2018-24).
A  Extension past k x R (k = 0.50, 0.77, 1.00, 1.31, 1.64): at the first minute the session's range reaches k x R, the side
   that made the new extreme is the extension. Race from that minute's close: 0.25 x R further that way before 0.25 x R back,
   to 17:00. Null 50%; each band is also compared with the 0.50R extension (same sessions' earlier, ordinary extension).
B  Next-band reach odds: when the range first reaches band b, how often does it reach the next band by 17:00, by the time
   block of the crossing. Rates fitted on 2018-24 and scored on 2025-26 (Brier against the flat rate per band).
C  Sessions that end beyond each band (the band's meaning), and where the session ends against the implied box.
"""
import numpy as np, pandas as pd, hydra, lib
P = pd.read_pickle('cache/panel.pkl')
C_DAY = {'NQ': 1.54, 'ES': 1.13}
BANDS = [0.61, 0.77, 1.00, 1.31, 1.64]
BLOCKS = [('18:00-02:00', 0, 480), ('02:00-08:30', 480, 870), ('08:30-12:00', 870, 1080), ('12:00-17:00', 1080, 1380)]

def sessions(mk):
    m = lib.load(mk); td = m['td']
    st = np.r_[0, np.flatnonzero(np.diff(td)) + 1]; en = np.r_[st[1:], len(td)]
    v9 = P['VIX9D'].shift(1)
    D = lib.daily(m)
    full = set(int(d.strftime('%Y%m%d')) for d in D.index[(D['n'] >= 1000) & (D['last'] >= 16 * 60 + 50)])
    for a, b in zip(st, en):
        t = int(td[a])
        if t not in full:
            continue
        day = pd.Timestamp(str(t))
        if day not in v9.index or np.isnan(v9[day]):
            continue
        R = C_DAY[mk] * v9[day] / 100 / np.sqrt(252) * m['O'][a]
        yield day, R, m['ts'][a:b], m['H'][a:b], m['L'][a:b], m['C'][a:b]

def rel(ts):
    return ((ts % 1440) - 1080) % 1440

def run(mk):
    ext, reach, fin = [], [], []
    for day, R, ts, H, L, C in sessions(mk):
        hi = np.maximum.accumulate(H); lo = np.minimum.accumulate(L); rg = hi - lo
        newhi = np.r_[True, hi[1:] > hi[:-1]]
        final = rg[-1] / R
        fin.append(dict(day=day, final=final, close_pos=(C[-1] - lo[-1]) / max(rg[-1], 1e-9)))
        for k in [0.50, 0.77, 1.00, 1.31, 1.64]:
            ix = np.flatnonzero(rg >= k * R)
            if len(ix) == 0:
                continue
            i = ix[0]
            up = bool(newhi[i]) if not (newhi[i] and L[i] == lo[i]) else H[i] - hi[i - 1] >= lo[i - 1] - L[i] if i > 0 else True
            d = 0.25 * R; e = C[i]
            hu = np.flatnonzero(H[i + 1:] >= e + d); hd = np.flatnonzero(L[i + 1:] <= e - d)
            iu = hu[0] if len(hu) else 10 ** 9; idn = hd[0] if len(hd) else 10 ** 9
            out = np.nan if iu == idn else float((iu < idn) == up)
            ext.append(dict(day=day, k=k, up=up, hit=out, tod=rel(ts[i])))
        for j, b in enumerate(BANDS[:-1]):
            ix = np.flatnonzero(rg >= b * R)
            if len(ix) == 0:
                continue
            reach.append(dict(day=day, band=b, nxt=BANDS[j + 1], tod=rel(ts[ix[0]]), hit=float(final >= BANDS[j + 1])))
    E, Rc, F = pd.DataFrame(ext), pd.DataFrame(reach), pd.DataFrame(fin)
    for X in (E, Rc, F):
        X['per'] = hydra.period(X['day']); X['mk'] = mk
    return E, Rc, F

def block(t):
    for nm, a, b in BLOCKS:
        if a <= t < b:
            return nm
    return BLOCKS[-1][0]

if __name__ == '__main__':
    pd.set_option('display.width', 220)
    out = [run(mk) for mk in ('NQ', 'ES')]
    E = pd.concat([o[0] for o in out]); Rc = pd.concat([o[1] for o in out]); F = pd.concat([o[2] for o in out])
    E.to_pickle('cache/rik_ext.pkl'); Rc.to_pickle('cache/rik_reach.pkl'); F.to_pickle('cache/rik_final.pkl')
    print('=== A: extension past k x R, race 0.25R further vs back (continue rate) ===')
    for k in [0.50, 0.77, 1.00, 1.31, 1.64]:
        res = {}
        for p in ('fish', 'test'):
            g = E[(E.k == k) & (E.per == p)]; base = E[(E.k == 0.50) & (E.per == p)]
            r = hydra.rate(g.hit.values, (g.day.astype(str) + g.mk).values)
            dd = hydra.diff(g.hit.values, (g.day.astype(str) + g.mk).values, base.hit.values, (base.day.astype(str) + base.mk).values) if k != 0.50 else None
            bym = ' '.join(f"{mk} {g[g.mk == mk].hit.mean()*100:.1f}%" for mk in ('NQ', 'ES'))
            updn = f"up {g[g.up].hit.mean()*100:.1f}% / down {g[~g.up].hit.mean()*100:.1f}%"
            res[p] = r
            print(f"k {k:.2f} {p}: continue {r['r']*100:.1f}% (n {r['n']}, p vs 50 {r['p']:.3f}) {bym} | {updn}" + (f" | vs 0.50R ext: Δ {dd['d']*100:+.1f} pt (p {dd['p']:.3f})" if dd else ''))
        print('   verdict vs 50%:', hydra.verdict(res['fish'], res['test'], key='r'))
    print('=== B: next-band reach odds by crossing time (fish rate -> test rate, n) ===')
    Rc['blk'] = Rc['tod'].map(block)
    tab = Rc.groupby(['band', 'blk', 'per'])['hit'].agg(['mean', 'size']).unstack('per')
    print((tab.round(3)).to_string())
    f = Rc[Rc.per == 'fish']; t = Rc[Rc.per == 'test']
    rate_bb = f.groupby(['band', 'blk'])['hit'].mean(); rate_b = f.groupby('band')['hit'].mean()
    pb = t.set_index(['band', 'blk']).index.map(lambda ix: rate_bb.get(ix, np.nan))
    pf = t['band'].map(rate_b)
    br_bb = np.nanmean((t['hit'].values - np.array(pb)) ** 2); br_b = np.mean((t['hit'] - pf) ** 2)
    print(f'test Brier: band x time block {br_bb:.4f} vs band only {br_b:.4f} (n {len(t)})')
    print('=== C: share of sessions ending beyond each band (fish / test) ===')
    for p in ('fish', 'test'):
        g = F[F.per == p]
        print(p, ' '.join(f"{b:.2f}R: {(g.final >= b).mean()*100:.1f}%" for b in BANDS), f"| median {g.final.median():.2f}R | n {len(g)}")
    print('=== C2: where the session closes in its own range (0 = low, 1 = high), by final range ===')
    F['fb'] = pd.cut(F['final'], [0, 0.77, 1.31, 9], labels=['under 0.77R', '0.77-1.31R', 'over 1.31R'])
    print(F.groupby(['fb', 'per'], observed=True)['close_pos'].agg(lambda s: f"{(s > 0.75).mean()*100:.0f}% top quarter / {(s < 0.25).mean()*100:.0f}% bottom").unstack())
