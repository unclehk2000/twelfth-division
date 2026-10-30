"""Front month vs continuous: what the daily gaps look like on each.
U (unadjusted 1!): the roll jump (next − front close on the roll date) in ATR; gaps formed before a roll sit at the old contract's prices.
K (the contract's own chart): in the 60 trading days before it became front, its candles were the deferred month's (volume a few %
of the front's): compare its gaps with the front's over the same dates."""
import numpy as np, pandas as pd
from data import daily, contracts, SYMS
from gaps import detect
res = {}
for s in SYMS:
    D = daily(s); C = contracts(s)
    r = D.index[D.roll]
    prev = D.uc.shift(1)
    # spread on the roll date: the new contract's prior close minus the old contract's prior close (same date)
    sp = []
    for d in r:
        i = D.index.get_loc(d)
        new = D.con.iloc[i]; old = D.con.iloc[i - 1]; dp = D.index[i - 1]
        if new in C and old in C and dp in C[new].index and dp in C[old].index:
            sp.append((d, (C[new].loc[dp, 'close'] - C[old].loc[dp, 'close']) / D.atrB.iloc[i - 1], C[new].loc[dp, 'close'] / C[old].loc[dp, 'close'] - 1))
    sp = pd.DataFrame(sp, columns=['date', 'atr', 'pct']).set_index('date')
    # K view: each contract's own candles over the 60 trading days before its front period, vs the front's candles
    kz = []; bz = []; volr = []
    for code in D.con.unique():
        if code not in C: continue
        idx = np.where(D.con.values == code)[0]
        if len(idx) == 0 or idx[0] < 80: continue
        i0 = idx[0]; win = D.index[i0 - 60:i0]
        K = C[code].reindex(D.index[i0 - 62:i0]).dropna()
        if len(K) < 55: continue
        A = D.atrB.reindex(K.index).values
        zk = detect(K.open.values, K.high.values, K.low.values, K.close.values, A, kinds=('FVG',))
        zk['date'] = K.index[zk.t0.values]; zk = zk[zk.date.isin(win)]
        F = D.loc[K.index]
        zb = detect(F.uo.values, F.uh.values, F.ul.values, F.uc.values, A, kinds=('FVG',))
        zb['date'] = F.index[zb.t0.values]; zb = zb[zb.date.isin(win)]
        # same gap = same formation date and direction
        kk = set(zip(zk.date, zk.dir)); bb = set(zip(zb.date, zb.dir))
        kz.append((code, len(kk), len(bb), len(kk & bb)))
        volr.append((K.volume / F.v.reindex(K.index)).median())
    kz = pd.DataFrame(kz, columns=['code', 'nK', 'nF', 'both'])
    yrs = sp.index.year
    print(f"{s}: roll jump |next − front| = {sp.atr.abs().median():.2f} ATR median ({sp.pct.abs().median()*100:.2f}% of price); "
          f"2010–19 {sp.atr.abs()[yrs<2020].median():.2f}, 2020–21 {sp.atr.abs()[(yrs>=2020)&(yrs<2022)].median():.2f}, 2022–26 {sp.atr.abs()[yrs>=2022].median():.2f} ATR; "
          f"sign + share {(sp.atr>0).mean():.2f}")
    print(f"    K view, 60 days before front: gaps on the contract {kz.nK.sum()}, on the front {kz.nF.sum()}, same date+side {kz.both.sum()} "
          f"({kz.both.sum()/kz.nF.sum():.2f} of the front's, {kz.both.sum()/kz.nK.sum():.2f} of the contract's); median volume ratio {np.nanmedian(volr):.3f}")
    res[s] = dict(sp=sp, kz=kz)
pd.to_pickle(res, '/home/claude/mgk/frontcont.pkl')
