# HYDRA pass: each lecture claim is a head with a null. Fish on 2018–24 (day-clustered t, Benjamini–Hochberg 10%), then score
# the locked 2025–26 half once. Effects are in percentage points unless stated.
import numpy as np, pandas as pd, statsmodels.api as sm, warnings
from scipy import stats
warnings.filterwarnings('ignore')
R = pd.read_pickle('rth_rows.pkl'); V = pd.read_pickle('rth_voids.pkl'); M = pd.read_pickle('rth_mss.pkl'); H1 = pd.read_pickle('rth_h1.pkl')
T = pd.read_pickle('rth_trip.pkl'); A = pd.read_pickle('rth_agree.pkl')
heads = []

def clus(x, g):
    """mean of x and its standard error clustered by g"""
    x = pd.Series(np.asarray(x, float)); g = pd.Series(np.asarray(g)); m = x.notna(); x, g = x[m], g[m]
    mu = x.mean(); r = (x - mu).groupby(g.values).sum(); n = len(x)
    return mu, np.sqrt((r ** 2).sum()) / n, n

def paired(name, claim, d, a, b, scale=100):
    for half in ('train', 'test'):
        q = d[d.half == half]
        mu, se, n = clus(q[a].astype(float) - q[b].astype(float), q.tday)
        heads.append(dict(head=name, claim=claim, half=half, n=n, real=scale * q[a].astype(float).mean(), null=scale * q[b].astype(float).mean(), eff=scale * mu, se=scale * se))

def coef(name, claim, d, y, X, logit=False, unit=1.0):
    for half in ('train', 'test'):
        q = d[d.half == half].dropna(subset=[y] + X)
        Xm = sm.add_constant(q[X].astype(float))
        mdl = (sm.Logit if logit else sm.OLS)(q[y].astype(float), Xm).fit(disp=0, cov_type='cluster', cov_kwds={'groups': pd.factorize(q.tday)[0]})
        heads.append(dict(head=name, claim=claim, half=half, n=len(q), real=np.nan, null=np.nan, eff=unit * mdl.params[X[-1]], se=unit * mdl.bse[X[-1]]))

# A · the ORG itself
paired('A1 CE by 10:00 vs mirror', "ICT: '70% likelihood of trading to the CE by 10:00'", R, 'ce10', 'ce10m')
paired('A1b CE by 10:00 vs shuffled RTH', 'same, against the day\'s own bars shuffled within 30 minutes', R, 'ce10', 'ce10_n')
paired('A2 fill by 16:14 vs mirror', 'the full fill is the draw', R, 'fill', 'fillm')
paired('A2b fill by 16:14 vs shuffled RTH', 'same, against shuffled bars', R, 'fill', 'fill_n')
def bins(v, lo, hi):
    v = np.asarray(v, float); return np.nanmean((v > lo) & (v <= hi)) if np.isfinite(v).any() else np.nan
for nm, col, ncol in (('A3 −0.5 SD past the close after the fill', 'ef', 'ef_n'), ('A3b +0.5 SD past the open before the fill', 'eo', 'eo_n')):
    q = R[R[col].notna()].copy()
    pk = (q[col].between(0.4, 0.6, inclusive='right')).astype(float) - q[ncol].apply(lambda v: bins(v, 0.4, 0.6))
    nb = ((q[col].between(0.2, 0.4, inclusive='right')).astype(float) + (q[col].between(0.6, 0.8, inclusive='right')).astype(float)) / 2 - q[ncol].apply(lambda v: (bins(v, 0.2, 0.4) + bins(v, 0.6, 0.8)) / 2)
    q['x'] = pk - nb; q['z0'] = 0.0
    paired(nm, "ICT: the 0.5 projection of the ORG as the run's end (peak at 0.4–0.6 beyond the neighbours, real − shuffled)", q, 'x', 'z0')
# B · carried CEs (the week's ORG CEs, last week's Monday and Friday)
paired('B1 nearest carried CE vs mirror', "carry each day's ORG CE through the week: a draw?", R[R.near_r.notna()], 'near_r', 'near_m')
q = R[R.nC >= 2].copy(); q['pos'] = np.where(q.op > q.cwmax, 'above', np.where(q.op < q.cwmin, 'below', 'inside'))
q2 = q[q.pos != 'inside'].copy(); q2['below'] = (q2.pos == 'below').astype(float); q2['ret100'] = 100 * q2.ret
coef('B2 open below vs above the CE band → RTH return', "above the week's CEs = premium (sell), below = discount (buy); × ATR10 %", q2, 'ret100', ['below'])
q['lspread'] = np.log((q.cwmax - q.cwmin) / q.atr + 0.01); q['lrng'] = np.log(q.rng); q['lgA'] = np.log(q.gA); q['lon_w'] = np.log(q.onW)
coef('B3 CE convergence → RTH range (log-log)', "CEs close together = trading-range environment (expect + coefficient)", q, 'lrng', ['lgA', 'lon_w', 'lspread'])
# C · the jigsaw
paired('C1 RTH takes the overnight high vs shuffled', "'whatever ETH does, RTH will tend to overlap and redeliver'", R, 'onH_r', 'onH_n')
paired('C1b RTH takes the overnight low vs shuffled', 'same, the low', R, 'onL_r', 'onL_n')
V['ld'] = np.log(V.dA + 0.01); V['ethf'] = V.eth.astype(float); V['hitf'] = V.hit.astype(float); V['age1'] = (V.age == 1).astype(float)
coef('C2 RTH void already traded in ETH → RTH trades it (logit)', 'ETH fills the jigsaw first, RTH redelivers', V, 'hitf', ['ld', 'age1', 'ethf'], logit=True)
for nm, p in (('C3 RTH PDH vs mirror', 'rPDH'), ('C3b RTH PDL vs mirror', 'rPDL'), ('C3c ETH PDH vs mirror', 'ePDH'), ('C3d ETH PDL vs mirror', 'ePDL')):
    paired(nm, "yesterday's RTH-only (vs ETH) extremes as draws", R[R[p + '_r'].notna()], p + '_r', p + '_m')
# D · RTH-only structure
paired('D2 last RTH-only swing high vs mirror', 'RTH-only 1h swing points as liquidity', R[R.rsH_r.notna()], 'rsH_r', 'rsH_m')
paired('D2b last RTH-only swing low vs mirror', 'same, swing low', R[R.rsL_r.notna()], 'rsL_r', 'rsL_m')
H1 = H1.reset_index(drop=True); H1['pos'] = H1.groupby('sym').cumcount()
dd = []
for s in ('NQ', 'ES', 'RTY'):
    h = H1[H1.sym == s].reset_index(drop=True); key = dict(zip(zip(h.k, h.h), h.index))
    atr = pd.read_pickle(f'/home/claude/coc/days_{s}.pkl').atr10.values
    for r in M[M.sym == s].itertuples():
        i = key.get((r.k, r.h))
        if i is None or i + 7 >= len(h) or not np.isfinite(atr[r.k]): continue
        dd.append((s, h.tday[i], r.dir, (h.c[i + 7] - r.c) * r.dir / atr[r.k]))
DM = pd.DataFrame(dd, columns=['sym', 'tday', 'dir', 'y']); DM['tday'] = pd.to_datetime(DM.tday); DM['half'] = np.where(DM.tday.dt.year >= 2025, 'test', 'train')
for half in ('train', 'test'):   # drift-neutral: average of the bullish and bearish shifts' mean follow-through
    q = DM[DM.half == half]; mb, sb, nb_ = clus(q[q.dir == 1].y, q[q.dir == 1].tday); ms, ss, ns = clus(q[q.dir == -1].y, q[q.dir == -1].tday)
    heads.append(dict(head='D1 RTH-only 1h shift → next 7 RTH hours', claim='RTH-only market structure shift carries on (× ATR10 %, drift-neutral)', half=half, n=nb_ + ns, real=100 * mb, null=100 * ms, eff=100 * (mb + ms) / 2, se=100 * np.sqrt(sb ** 2 + ss ** 2) / 2))
# E · "rarely three trending sessions"
q = R.dropna(subset=['lon', 's79', 'rth_tr']).copy()
tr = lambda v: np.where(v >= 0.5, 1, np.where(v <= -0.5, -1, 0))
q['L'], q['P'], q['X'] = tr(q.lon), tr(q.s79), tr(q.rth_tr)
q = q[q.P != 0]; q['two'] = (q.L == q.P).astype(float); q['same3'] = (q.X == q.P).astype(float)
coef('E1 London + 7–9 trending → RTH trends on', "ICT: 'rarely three sessions trend in a row' (expect − coefficient)", q, 'same3', ['two'])
# F · the triplet (Zabimaru's sisters, on the ORG)
for tgt in ('fill', 'ce'):
    q = T[T.tgt == tgt].copy(); q['ld'] = np.log(q.d + 0.01); q['lg'] = np.log(q.gR); q['yf'] = q.y.astype(float)
    for m in sorted(q.cp.unique()): q[f'c{m}'] = (q.cp == m).astype(float)
    X = [f'c{m}' for m in sorted(q.cp.unique())[1:]] + ['ld', 'lg', 'nsis']
    coef(f'F1 sisters already {tgt}ed → this one (logit, per sister)', 'Zabimaru-style triplet on the gap', q, 'yf', X, logit=True)
A['div'] = (~A.withboth).astype(float); A['lg'] = np.log(A.gR); A['ff'] = A.fill.astype(float)
coef('F2 gap against a sister → fills (logit)', 'NQ / ES / RTY gapping different ways (an ORG SMT)', A, 'ff', ['lg', 'div'], logit=True)

Hd = pd.DataFrame(heads)
tr_ = Hd[Hd.half == 'train'].copy(); tr_['z'] = tr_.eff / tr_.se; tr_['p'] = 2 * stats.norm.sf(tr_.z.abs())
m = len(tr_); o = tr_.p.rank(method='first'); tr_['bh'] = tr_.p <= 0.10 * o / m
srt = tr_.sort_values('p'); thr = 0.0;
for i, p in enumerate(srt.p.values, 1):
    if p <= 0.10 * i / m: thr = p
tr_['bh'] = tr_.p <= thr
te = Hd[Hd.half == 'test'].set_index('head')
tr_['test_eff'] = tr_['head'].map(te.eff); tr_['test_se'] = tr_['head'].map(te.se); tr_['test_n'] = tr_['head'].map(te.n)
tr_['test_z'] = tr_.test_eff / tr_.test_se
tr_['held'] = tr_.bh & (np.sign(tr_.test_eff) == np.sign(tr_.eff)) & (tr_.test_z.abs() >= 1.645)
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 60)
print(tr_[['head', 'n', 'real', 'null', 'eff', 'se', 'z', 'bh', 'test_n', 'test_eff', 'test_z', 'held']].round(2).to_string(index=False))
tr_.to_pickle('rth_heads.pkl'); Hd.to_pickle('rth_heads_all.pkl')
print('\nICT 70% check, CE by 10:00 by size (gR):')
R['sz'] = pd.cut(R.gR, [0, 0.5, 1, 1.5, 2.5, 99])
print((100 * R.groupby('sz', observed=True)[['ce10', 'ce10m', 'ce16', 'fill']].mean().astype(float)).round(1).to_string())
print('all', round(100 * R.ce10.mean(), 1))
