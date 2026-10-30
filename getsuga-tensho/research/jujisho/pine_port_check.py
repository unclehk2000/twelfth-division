"""Port of the Pine Jūjishō detection (15-minute chart bars fed with their 1-minute intrabars) checked against build.py."""
import numpy as np, pandas as pd
b = pd.read_pickle('/home/claude/kyw/bars_NQ_all.pkl').reset_index(drop=True)
b = b[b.ts >= '2025-01-01'].reset_index(drop=True)
ts = b.ts.to_numpy().astype('datetime64[m]').astype(np.int64) * 60000
hm = b.hm.to_numpy(); H = b.High.to_numpy(); L = b.Low.to_numpy(); tdy = b.tday.to_numpy()
bucket = (ts // (15 * 60000))            # 15-minute chart bars (ET-naive minutes; 15-min alignment is the same)
st = np.r_[0, np.flatnonzero(bucket[1:] != bucket[:-1]) + 1]; en = np.r_[st[1:], len(b)]
s930 = None; done = True; b1 = b2 = None; found = {}
for s, e in zip(st, en):
    if not (hm[s] <= 959 and hm[e - 1] >= 930):
        continue
    for j in range(s, e):
        t, h, l, m = ts[j], H[j], L[j], hm[j]
        if m >= 930 and (s930 is None or t - s930 > 12 * 3600000):
            s930 = t - ((m // 100) * 60 + m % 100 - 570) * 60000; done = False; b1 = b2 = None
        if not done and b2 is not None and m >= 930 and t < s930 + 1800000:
            if l > b2[0] or h < b2[1]:
                done = True; bu = l > b2[0]
                found[pd.Timestamp(ts[j], unit='ms').normalize()] = (1 if bu else -1, l if bu else b2[1], b2[0] if bu else h)
        b2, b1 = b1, (h, l)
D = pd.read_pickle('days.pkl').set_index('date'); D = D[D.index >= '2025-01-01']
ok = bad = 0
for d, r in D.iterrows():
    if pd.isna(r.fp):
        bad += d in found; continue
    f = found.get(d)
    if f and f[0] == r.fp and abs(f[1] - r.top) < 1e-9 and abs(f[2] - r.bot) < 1e-9: ok += 1
    else: bad += 1; print('mismatch', d.date(), f, (r.fp, r.top, r.bot))
print('match', ok, 'mismatch', bad)
