import pandas as pd, numpy as np
from fm_sim import run
B = pd.read_pickle('/home/claude/kyw/bars_NQ_all.pkl')
B = B[(B.ts >= '2025-11-01') & (B.ts < '2026-08-27')].reset_index(drop=True)
B['hk'] = B.ts.dt.floor('60min')
Hb = B.groupby(['hk', 'Contract'], sort=True).agg(O=('Open', 'first'), H=('High', 'max'), L=('Low', 'min'), C=('Close', 'last'), tday=('tday', 'first'), n=('ts', 'size')).reset_index()
# front contract only: the one with the most bars that trading day
fr = B.groupby(['tday', 'Contract']).size().reset_index(name='k').sort_values('k').groupby('tday').tail(1)[['tday', 'Contract']]
Hb = Hb.merge(fr, on=['tday', 'Contract']).sort_values('hk').reset_index(drop=True)
Hb.to_pickle('/home/claude/xa/nq_1h.pkl')
res = []
days = sorted(Hb.tday.unique())
for d in days[10:]:
    for hh in (10, 12, 14):
        T = pd.Timestamp(d) + pd.Timedelta(hours=hh)
        w = Hb[(Hb.hk < T) & (Hb.hk >= T - pd.Timedelta(days=12))]
        st = run(w.O.to_numpy(), w.H.to_numpy(), w.L.to_numpy(), w.C.to_numpy(), list(w.hk), w.tday.to_numpy())
        if not st['fss']:
            continue
        s = st['fss'][-1]
        if s.phase == 3 and s.cisd and s.pj and not s.dead:
            res.append(dict(T=T, bull=s.bull, early=s.cisdC2, took=s.took, hits=sum(s.pjHit), q=s.q, prot=s.pDone and not s.pTaken, n=len(st['fss'])))
R = pd.DataFrame(res)
print(len(R)); print(R[R.hits.between(1, 2)].tail(40).to_string())
