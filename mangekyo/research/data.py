"""Mangekyō research — data layer.
Daily OHLC 2010–26 (YM 2017–26) for NQ, ES, RTY, YM from the per-contract Barchart tables:
  U = unadjusted continuous (front contract each day, rolls 8 calendar days before expiry, as TradingView's 1! jumps),
  B = back-adjusted continuous (additive), the same candles with the roll jump removed,
  K = each contract's own history (the 'front-month contract' chart, e.g. NQZ2026 with its deferred months).
Volume: daily front-contract volume (NQ per contract to Z24; ES / RTY / YM and NQ from H25 the market total), and from 1-minute
bars 2018–26 the front contract's ETH and RTH volume.  ATR = Wilder RMA(14) of the true range, as Pine's ta.atr."""
import numpy as np, pandas as pd, glob, os
BASE = '/mnt/user-data/uploads/nq_es_rty_daily_task2_1/per_contract'
YMB = '/home/claude/kyw/ym_daily_layout/per_contract/YM'
SYMS = ['NQ', 'ES', 'RTY', 'YM']
PRE = {'NQ': 'nq', 'ES': 'es', 'RTY': 'qr', 'YM': 'ym'}
W = '/home/claude/mgk'

def rma(x, n):
    x = np.asarray(x, float); out = np.full(len(x), np.nan)
    ok = np.where(np.isfinite(x))[0]
    if len(ok) < n: return out
    s = ok[0]; out[s + n - 1] = np.nanmean(x[s:s + n]); a = 1.0 / n
    for i in range(s + n, len(x)):
        out[i] = out[i - 1] + a * ((x[i] if np.isfinite(x[i]) else out[i - 1]) - out[i - 1])
    return out

def atr(h, l, c, n=14):
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.c_[h - l, np.abs(h - pc), np.abs(l - pc)], axis=1)
    tr[0] = h[0] - l[0]
    return rma(tr, n)

def minute_volume(sym):
    f = f'{W}/mv_{sym}.pkl'
    if os.path.exists(f): return pd.read_pickle(f)
    b = pd.read_pickle(f'/home/claude/kyw/bars_{sym}_all.pkl')
    v = b.groupby('tday').Volume.sum().rename('v_eth')
    r = b[(b.hm >= 930) & (b.hm < 1600)].groupby('tday').Volume.sum().rename('v_rth')
    k = b.groupby('tday').Contract.last().str.lower().rename('mcon')
    out = pd.concat([v, r, k], axis=1, sort=True); out.index = pd.DatetimeIndex(out.index)
    out.to_pickle(f); return out

def daily(sym):
    F = pd.read_pickle(f'/home/claude/kyw/F_{sym}.pkl').copy(); F.index = pd.DatetimeIndex(F.index)
    D = pd.DataFrame(index=F.index)
    D['con'] = F.contract; D['roll'] = F.contract != F.contract.shift(1); D.iloc[0, D.columns.get_loc('roll')] = False
    for a, b in (('o', 'o'), ('h', 'h'), ('l', 'l'), ('c', 'c')):
        D['u' + a] = F[b].astype(float)
    for a, b in (('o', 'ao'), ('h', 'ah'), ('l', 'al'), ('c', 'ac')):
        D['b' + a] = F[b].astype(float)
    D['v'] = F.vol_front.astype(float)
    D['atrB'] = atr(D.bh.values, D.bl.values, D.bc.values)
    D['atrU'] = atr(D.uh.values, D.ul.values, D.uc.values)
    mv = minute_volume(sym)
    D = D.join(mv, how='left')
    D['dow'] = D.index.dayofweek
    D['wk'] = (D.index - pd.to_timedelta(D.index.dayofweek, unit='D')).normalize()
    D['yr'] = D.index.year
    return D

def contracts(sym):
    d = YMB if sym == 'YM' else f'{BASE}/{sym}'
    out = {}
    for f in sorted(glob.glob(f'{d}/*.csv')):
        code = os.path.basename(f)[:-4].lower()
        df = pd.read_csv(f, parse_dates=['Date']).set_index('Date').sort_index()
        df.columns = [c.lower() for c in df.columns]
        out[code] = df
    return out

if __name__ == '__main__':
    for s in SYMS:
        D = daily(s)
        print(s, D.index.min().date(), D.index.max().date(), len(D), 'rolls', int(D.roll.sum()),
              'v_eth days', int(D.v_eth.notna().sum()), 'atrB last', round(D.atrB.iloc[-1], 1),
              'roll gap mean |U open - prev U close| / ATR on roll days',
              round((np.abs(D.uo - D.uc.shift(1)) / D.atrB)[D.roll].mean(), 2),
              'other days', round((np.abs(D.uo - D.uc.shift(1)) / D.atrB)[~D.roll].mean(), 2))
        C = contracts(s); print('   contracts', len(C), list(C)[:3], list(C)[-3:])
