import numpy as np, pandas as pd
from split import show, clus, wkof
exec(open('analyze4.py').read().split("for nm, zf")[0])
Z = add(pd.read_pickle('zones.pkl')); Q = add(pd.read_pickle('ctl.pkl'))
q = Q.groupby('of')[['rej', 'rejCE', 'inside']].mean(); F = Z[Z.kind == 'FVG'].join(q, rsuffix='_c')
F = F[F.inside.notna()]
F['wq'] = pd.qcut(F.w, 3, labels=['narrow', 'mid', 'wide'])
F['bq'] = pd.qcut(F.c2body, 3, labels=['small c2', 'mid c2', 'big c2'])
F['rq'] = pd.qcut(F.rv2, 3, labels=['low rvol', 'mid rvol', 'high rvol'])
F['ms'] = np.where(F.brk, 'break', 'no break'); F['sw'] = np.where(F.swp, 'sweep', 'no sweep')
F['pw'] = np.where(F.pwpos.isna(), 'na', np.where(((F.dir == 1) & (F.pwpos < 0.5)) | ((F.dir == -1) & (F.pwpos > 0.5)), 'PW aligned', 'PW against'))
F['age'] = pd.cut(F.tT - F.t0, [0, 1, 5, 20, 60, 999], labels=['next day', '2–5', '6–20', '21–60', '60+'])
F['per'] = np.where(F.yr >= 2025, '2025–26', '2010–24')
F['dirn'] = np.where(F.dir == 1, 'bull', 'bear')
for by in ['per', 'dirn', 'sym', 'wq', 'bq', 'rq', 'ms', 'sw', 'pw', 'age']:
    show(F, 'inside', by)
