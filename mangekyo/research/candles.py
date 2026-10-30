"""Daily candle variants (back-adjusted additively to the latest contract).
SET: close = the settlement (Barchart's daily close; it matches the 15:59–16:00 ET settlement minute).  TradingView 'Use
     settlement as close on daily interval' on.
LST: close = the last trade, the 16:59 ET minute's close (TradingView's setting off).  2018–26 only (1-minute data).
Open, high and low are the same under both (18:00 open, the full session's extremes)."""
import numpy as np, pandas as pd, os
from data import daily
W = '/home/claude/mgk'
def last_close(sym):
    f = f'{W}/lc_{sym}.pkl'
    if os.path.exists(f): return pd.read_pickle(f)
    b = pd.read_pickle(f'/home/claude/kyw/bars_{sym}_all.pkl')
    b = b[b.hm <= 1659]
    g = b.sort_values('ts').groupby('tday').agg(lc=('Close', 'last'), lhm=('hm', 'last'), mk=('Contract', 'last'),
                                                 mo=('Open', 'first'), mh=('High', 'max'), ml=('Low', 'min'), fhm=('hm', 'first'))
    g.index = pd.DatetimeIndex(g.index); g.to_pickle(f); return g
def variant(sym, v):
    D = daily(sym)
    adj = D.bc - D.uc
    if v == 'SET':
        return D, D.bo.values, D.bh.values, D.bl.values, D.bc.values
    g = last_close(sym).reindex(D.index)
    ok = (g.mk.str.lower() == D.con) & (g.lhm >= 1655)
    lc = np.where(ok, g.lc + adj, np.nan)
    D = D.copy(); D['lc'] = lc
    keep = np.isfinite(lc)
    D = D[keep]
    # Open/High/Low from the daily table (same session), close swapped
    return D, D.bo.values, D.bh.values, D.bl.values, D.lc.values
if __name__ == '__main__':
    for s in ['NQ', 'ES', 'RTY', 'YM']:
        D, O, H, L, C = variant(s, 'LST')
        S = D.bc.values
        dd = (C - S) / D.atrB.values
        print(s, len(D), D.index.min().date(), 'last − settle: median |Δ| {:.3f} ATR, 90th pct {:.3f}, share > 0.1 ATR {:.2f}'.format(np.nanmedian(np.abs(dd)), np.nanpercentile(np.abs(dd), 90), np.nanmean(np.abs(dd) > 0.1)))
        # body direction flips
        up_s = S > O; up_l = C > O
        print('    candle colour differs on {:.1%} of days'.format(np.mean(up_s != up_l)))
