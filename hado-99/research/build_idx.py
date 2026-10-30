"""Index side of the cross-asset study (NQ / ES / RTY, 2018–26).
daily  xa/idx_{S}.pkl : the F_ table (front by roll, next contract, annualised carry %, calendar flags), plus
         clock marks from 1-minute bars (09:30 open; prices at 14:30, 15:00, 16:00, 17:00 ET), ADR20, VIX,
         and where the close sits in the prior week's and prior quarter's back-adjusted range (premium > 0.5).
hourly xa/idxh_{S}.pkl: hour-end prices with a contract id, so returns never span a roll."""
import pandas as pd, numpy as np

def third_friday(y, m):
    d = pd.Timestamp(y, m, 15)
    return d + pd.Timedelta(days=(4 - d.weekday()) % 7)

EXP = [third_friday(y, m) + pd.Timedelta(hours=9, minutes=30) for y in range(2017, 2028) for m in (3, 6, 9, 12)]
EXP = pd.DatetimeIndex(EXP)
VIX = pd.read_csv('/home/claude/mac/vix_daily.csv', parse_dates=['DATE']).set_index('DATE').CLOSE

def ctr_ids(B):
    """contract id per bar: the labelled contract, or (continuous segments) the next quarterly expiry."""
    nxt = EXP[np.searchsorted(EXP.values, B.ts.values, side='right')]
    return np.where(B.Contract.values != 'CONT', B.Contract.values, pd.DatetimeIndex(nxt).strftime('EXP%Y%m'))

def build(S):
    B = pd.read_pickle(f'/home/claude/kyw/bars_{S}_all.pkl')
    B = B[B.ts >= '2017-12-01'].reset_index(drop=True)
    B['ctr'] = ctr_ids(B)
    # hourly: the close of each hh:59 bar = the price at the next hour
    h = B[B.ts.dt.minute == 59][['ts', 'Close', 'ctr', 'tday']].copy()
    h['t'] = h.ts + pd.Timedelta(minutes=1)
    h = h.set_index('t')[['Close', 'ctr', 'tday']].rename(columns={'Close': 'px'})
    h['r'] = np.log(h.px).diff().where(h.ctr == h.ctr.shift())
    h.to_pickle(f'/home/claude/xa/idxh_{S}.pkl')
    # daily clock marks
    marks = {'o0930': (930, 'Open'), 'p0930': (929, 'Close'), 'p1430': (1429, 'Close'), 'p1500': (1459, 'Close'),
             'p1600': (1559, 'Close'), 'p1700': (1658, 'Close')}
    D = pd.DataFrame(index=pd.DatetimeIndex(sorted(B.tday.unique()), name='date'))
    for k, (hm, col) in marks.items():
        x = B[B.hm == hm].groupby('tday').agg(v=(col, 'last'), c=('ctr', 'last'))
        D[k] = x.v
        D[k + '_c'] = x.c
    F = pd.read_pickle(f'/home/claude/kyw/F_{S}.pkl')
    F = F[F.index >= '2017-12-01']
    D = F.join(D, how='left')
    D['adr20'] = (D.h - D.l).rolling(20).mean().shift(1)
    D['vix'] = VIX.reindex(D.index).ffill()
    D['r'] = np.log(D.ac).diff()                                   # back-adjusted close to close
    # prior week / quarter back-adjusted ranges and where today's close sits in them
    wk = D.index.to_period('W-FRI')
    q = D.index.to_period('Q')
    for nm, per in (('wk', wk), ('q', q)):
        g = D.groupby(per)
        H, L = g.ah.max(), g.al.min()
        pH, pL = H.shift(1).reindex(per).values, L.shift(1).reindex(per).values
        D[f'{nm}_pH'], D[f'{nm}_pL'] = pH, pL
        D[f'{nm}_pos'] = (D.ac - pL) / (pH - pL)                    # >0.5 premium of the prior range
        # to date: the running range of the current week / quarter
        D[f'{nm}_tdH'] = g.ah.cummax().values
        D[f'{nm}_tdL'] = g.al.cummin().values
    D['wk'] = wk
    D['q'] = q
    D['sym'] = S
    D = D[D.index >= '2018-01-01']
    D.to_pickle(f'/home/claude/xa/idx_{S}.pkl')
    return D, h

if __name__ == '__main__':
    for S in ('NQ', 'ES', 'RTY'):
        D, h = build(S)
        print(S, len(D), D.index.min().date(), D.index.max().date(), '| hourly', len(h), h.r.notna().mean().round(3),
              '| marks', D[['o0930', 'p1430', 'p1500', 'p1600']].notna().mean().round(3).to_dict(),
              '| carry %', D.carry.groupby(D.index.year).mean().round(2).to_dict())
