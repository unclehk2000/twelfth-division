# compact minute arrays for the Sharingan LTF tests: ts (minutes since epoch, ET wall clock), OHLC, contract id, trading day
import numpy as np, pandas as pd, sys
src = {'NQ': '/home/claude/kyw/bars_NQ_ext.pkl', 'ES': '/home/claude/kyw/bars_ES_all.pkl', 'RTY': '/home/claude/kyw/bars_RTY_all.pkl'}
for s, f in src.items():
    b = pd.read_pickle(f)
    b = b[b.ts <= '2026-10-23 16:59']
    ts = (b.ts.values.astype('datetime64[m]').astype(np.int64))
    ct = pd.factorize(b.Contract)[0].astype(np.int16)
    td = (b.tday.values.astype('datetime64[D]').astype(np.int64)).astype(np.int32)
    np.savez(f'm_{s}.npz', ts=ts, O=b.Open.values.astype(np.float64), H=b.High.values.astype(np.float64), L=b.Low.values.astype(np.float64), C=b.Close.values.astype(np.float64), ct=ct, td=td)
    print(s, len(ts), pd.Timestamp(ts[0], unit='m'), pd.Timestamp(ts[-1], unit='m'))
