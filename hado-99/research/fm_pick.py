import pandas as pd, numpy as np
from fm_sim import run
B = pd.read_pickle('/home/claude/kyw/bars_NQ_all.pkl')
B = B[(B.ts >= '2026-01-05') & (B.ts < '2026-08-27')].reset_index(drop=True)
M = pd.Timedelta(minutes=1)
res = []
for day, g in B.groupby('tday'):
    g = g.reset_index(drop=True)
    for hh in range(10, 13):
        for mm in range(0, 60, 5):
            T = pd.Timestamp(day) + pd.Timedelta(hours=hh, minutes=mm)
            w = g[(g.ts >= T - pd.Timedelta(hours=2, minutes=30)) & (g.ts < T)]
            if len(w) < 140:
                continue
            key = w.ts.dt.floor('15min').to_numpy()
            ts = list(w.ts)
            st = run(w.Open.to_numpy(), w.High.to_numpy(), w.Low.to_numpy(), w.Close.to_numpy(), ts, key,
                     c4_end=lambda s, b: int((s.t3 + 30 * M - (ts[b] + M)) / M))
            if not st['fss']:
                continue
            s = st['fss'][-1]
            if s.phase in (3, 4) and s.cisd and s.took and s.pDone and not s.pTaken and not s.dead and s.pjHit and sum(s.pjHit) >= 1:
                res.append(dict(T=T, bull=s.bull, early=s.cisdC2, phase=s.phase, hits=sum(s.pjHit), q=s.q, n=len(st['fss']), left=s.pLeft,
                                rng=s.opp - s.ext if s.bull else s.ext - s.opp))
R = pd.DataFrame(res)
print(len(R))
print(R[(R.early) & (R.hits.between(1, 3))].sample(min(25, len(R)), random_state=1).sort_values('T').to_string())
