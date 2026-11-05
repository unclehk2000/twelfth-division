"""Price delivery matrix: NQ, ES, YM, RTY on 15m, 1H, 4H (18:00-anchored: 18, 22, 02, 06, 10, 14) and D (18:00–17:00) candles.
For each completed candle C2 and its predecessor C1, per market: sweeps of C1's high / low, where C2 closed in C1's range, the
formation (bull C2 = swept the low and closed back above it; bear C2; expansion up / down; inside), C2's return, body, wicks and
range in ATR (mean range of the 14 candles before). Outcome: C3's close-to-close return from C2's close, in ATR, and whether C3
traded through C2's high / low. Candles are aligned across the four markets; pairs that cross a contract roll are dropped."""
import numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/claude/lr'); from lib import load
SYMS = ['NQ', 'ES', 'YM', 'RTY']
def candles(sym, tf):
    m = load(sym); rel = (((m['ts'] % 1440) - 1080) % 1440).astype(np.int64); td = m['td'].astype(np.int64)
    blk = np.zeros_like(rel) if tf == 'D' else rel // {'15': 15, '60': 60, '240': 240}[tf]
    key = td * 1000 + blk
    brk = np.flatnonzero(np.diff(key) != 0) + 1; st = np.r_[0, brk]; en = np.r_[brk - 1, len(key) - 1]
    df = pd.DataFrame({'key': key[st], 'td': td[st], 'blk': blk[st], 'O': m['O'][st], 'C': m['C'][en], 'H': np.maximum.reduceat(m['H'], st), 'L': np.minimum.reduceat(m['L'], st),
                       'ct': m['ct'][st].astype(np.int64), 'ct2': m['ct'][en].astype(np.int64), 'nb': en - st + 1, 'r0': rel[st]})
    df = df[(df.ct == df.ct2) & (df.r0 < 1380)]
    df = df.sort_values('nb', ascending=False).drop_duplicates('key').sort_values('key')
    rng = (df.H - df.L).values; df['atr'] = pd.Series(rng).rolling(14).mean().shift(1).values
    return df.reset_index(drop=True)
def features(df):
    d = df.copy()
    for k, s in [(1, 1), (3, -1)]:      # C1 = previous candle, C3 = next candle
        for c in ['O', 'H', 'L', 'C', 'ct', 'key']:
            d[f'{c}{k}'] = d[c].shift(s)
    ok = (d.ct1 == d.ct) & (d.ct3 == d.ct)
    a = d.atr
    d['shi'] = (d.H > d.H1).astype(int); d['slo'] = (d.L < d.L1).astype(int)
    d['cl'] = (d.C - d.L1) / (d.H1 - d.L1).replace(0, np.nan)
    d['form'] = np.select([(d.slo == 1) & (d.shi == 0) & (d.C > d.L1), (d.shi == 1) & (d.slo == 0) & (d.C < d.H1), d.C > d.H1, d.C < d.L1, (d.shi == 0) & (d.slo == 0)],
                          ['bullC2', 'bearC2', 'expUp', 'expDn', 'inside'], 'outside')
    d['r2'] = (d.C - d.C1) / a; d['body'] = (d.C - d.O) / a; d['rng'] = (d.H - d.L) / a; d['rng1'] = (d.H1 - d.L1) / a
    d['uw'] = (d.H - np.maximum(d.O, d.C)) / a; d['lw'] = (np.minimum(d.O, d.C) - d.L) / a
    d['dh'] = (d.H - d.H1) / a; d['dl'] = (d.L1 - d.L) / a          # sweep depth (positive = swept) in ATR
    d['r3'] = (d.C3 - d.C) / a; d['t3h'] = (d.H.shift(-1) > d.H).astype(int); d['t3l'] = (d.L.shift(-1) < d.L).astype(int)
    d['t3h1'] = (d.H.shift(-1) > d.H1).astype(int); d['t3l1'] = (d.L.shift(-1) < d.L1).astype(int)
    d['nxtkey'] = d.key.shift(-1)
    return d[ok & d.atr.notna() & (d.atr > 0)]
COLS = ['shi', 'slo', 'cl', 'form', 'r2', 'body', 'rng', 'rng1', 'uw', 'lw', 'dh', 'dl', 'r3', 't3h', 't3l', 't3h1', 't3l1', 'C', 'H', 'L', 'atr', 'nxtkey']
if __name__ == '__main__':
    for tf in ['D', '240', '60', '15']:
        F = {}
        for s in SYMS:
            F[s] = features(candles(s, tf)).set_index('key')[['td', 'blk'] + COLS]
        keys = F['NQ'].index
        for s in SYMS[1:]: keys = keys.intersection(F[s].index)
        # the next candle must also be the same key in all four markets (aligned C3)
        W = pd.concat({s: F[s].loc[keys] for s in SYMS}, axis=1)
        same = np.ones(len(W), bool)
        for s in SYMS[1:]: same &= (W[(s, 'nxtkey')].values == W[('NQ', 'nxtkey')].values)
        W = W[same]
        W.to_pickle(f'/home/claude/pdm/mat_{tf}.pkl'); print(tf, len(W), flush=True)
