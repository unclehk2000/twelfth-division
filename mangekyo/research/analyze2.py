import numpy as np, pandas as pd
from split import show
exec(open('analyze1.py').read().split("F['wk']")[0])
F['wq'] = pd.qcut(F.w, 3, labels=['narrow', 'mid', 'wide'])
F['bq'] = pd.qcut(F.c2body, 3, labels=['small c2', 'mid c2', 'big c2'])
F['rq'] = pd.qcut(F.rv2, 3, labels=['low rvol', 'mid rvol', 'high rvol'])
F['ms'] = np.where(F.brk & F.swp, 'sweep+break', np.where(F.brk, 'break', np.where(F.swp, 'sweep', 'neither')))
F['pw'] = np.where(F.pwpos.isna(), 'na', np.where(((F.dir == 1) & (F.pwpos < 0.5)) | ((F.dir == -1) & (F.pwpos > 0.5)), 'PW aligned', 'PW against'))
F['tr'] = np.where(F.trend > 0, 'with 20d', 'against 20d')
for v in ['hold10', 'bounce', 'T20']:
    for by in ['wq', 'bq', 'rq', 'ms', 'pw', 'tr', 'dow']:
        show(F, v, by)
