"""Sharingan research (daily NQ, ES, RTY 2010–26; YM 2017–26).
(a) Look-back liquidity: anchor A = first trading day of a month; levels = high / low of the 20 / 40 / 60 trading days before A.
    For each day t of the cast-forward window (A … A+60) and each level not yet taken, distance at the prior close in ATR14 →
    is it taken within 20 trading days, and by the end of the window? HYDRA form p = logistic(a + b·logit(2Φ(−d/(κ√h)))), per side,
    fit 2010–24 pooled, tested 2025–26 per index.
(b) Daily structure shifts (3-bar swings, close beyond the last opposite swing): spacing from shift to shift, vs a stationary bootstrap."""
import sys, numpy as np, pandas as pd
from scipy.special import ndtr, expit, logit
from scipy.optimize import minimize
sys.path.insert(0, '/home/claude/tpf')
from data import daily, SYMS
from qshift import boot_path
rng = np.random.default_rng(23)
def atr(h, l, c, n=14):
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum(h, pc) - np.minimum(l, pc)
    return pd.Series(tr).rolling(n).mean().to_numpy()
rows = []
if __name__ != "__main__": SYMS = []
for sym in SYMS:
    D = daily(sym); h, l, c = D.ah.values, D.al.values, D.ac.values; A_ = atr(h, l, c); dt = D.index
    first = np.r_[True, dt.month[1:] != dt.month[:-1]]
    for A in np.where(first)[0]:
        if A < 61 or A + 61 > len(h): continue
        for N in (20, 40, 60):
            for side, lev in ((1, h[A - N:A].max()), (-1, l[A - N:A].min())):
                taken_by = np.where((h[A:A + 61] >= lev) if side == 1 else (l[A:A + 61] <= lev))[0]
                tk = taken_by[0] + A if len(taken_by) else 10 ** 9
                for t in range(A, A + 60):
                    if t > tk: break
                    d = (lev - c[t - 1]) * side / A_[t - 1]
                    if not (d > 0) or not np.isfinite(d): continue
                    hw = A + 60 - t + 1
                    y20 = int(tk <= t + 19); yw = int(tk <= A + 60)
                    rows.append((sym, dt[t].year, N, side, d, hw, y20, yw, t - A))
if __name__ != "__main__": raise SystemExit
R = pd.DataFrame(rows, columns=['sym', 'yr', 'N', 'side', 'd', 'hw', 'y20', 'yw', 'day'])
print('rows', len(R), R.groupby('sym').size().to_dict())
def fitp(x, y, h):
    z = x / np.sqrt(h)
    def nll(p):
        k, a, b = np.exp(p[0]), p[1], p[2]
        q = np.clip(2 * ndtr(-z / k), 1e-5, 1 - 1e-5); pp = np.clip(expit(a + b * logit(q)), 1e-6, 1 - 1e-6)
        return -np.mean(y * np.log(pp) + (1 - y) * np.log(1 - pp))
    r = minimize(nll, [0.0, 0.0, 1.0], method='Nelder-Mead', options={'maxiter': 4000, 'xatol': 1e-6, 'fatol': 1e-9}); return np.r_[np.exp(r.x[0]), r.x[1:]]
def predp(par, x, h):
    q = np.clip(2 * ndtr(-(x / np.sqrt(h)) / par[0]), 1e-5, 1 - 1e-5); return expit(par[1] + par[2] * logit(q))
PAR = {}
for side in (1, -1):
    tr = R[(R.yr <= 2024) & (R.side == side)]
    PAR[(side, '20')] = fitp(tr.d.values, tr.y20.values, 20.0)
    PAR[(side, 'w')] = fitp(tr.d.values, tr.yw.values, tr.hw.values.astype(float))
print('params κ, a, b:', {f"{'high' if k[0] == 1 else 'low'}·{k[1]}": np.round(v, 4).tolist() for k, v in PAR.items()})
te = R[R.yr >= 2025].copy(); te['p20'] = np.nan; te['pw'] = np.nan
for side in (1, -1):
    m = te.side == side
    te.loc[m, 'p20'] = predp(PAR[(side, '20')], te.d[m].values, 20.0); te.loc[m, 'pw'] = predp(PAR[(side, 'w')], te.d[m].values, te.hw[m].values.astype(float))
from sklearn.metrics import roc_auc_score
for col, y in (('p20', 'y20'), ('pw', 'yw')):
    b = pd.cut(te[col], [0, .1, .3, .5, .7, .9, 1]); g = te.groupby(b, observed=True).agg(pred=(col, 'mean'), act=(y, 'mean'), n=(y, 'size'))
    print(f'\n{col} test 2025–26: AUC {roc_auc_score(te[y], te[col]):.3f}  ' + ' · '.join(f'{100 * r.pred:.0f}→{100 * r.act:.0f}% (n {r.n})' for r in g.itertuples()))
    for sym in SYMS:
        x = te[te.sym == sym]; print(f'   {sym}: pred {x[col].mean():.3f} act {x[y].mean():.3f}  AUC {roc_auc_score(x[y], x[col]):.3f}')
    for side in (1, -1):
        x = te[te.side == side]; print(f'   side {side}: pred {x[col].mean():.3f} act {x[y].mean():.3f}')
# a readable table: P(taken within 20 days) by distance, highs vs lows, all years
tab = R.assign(db=pd.cut(R.d, [0, .5, 1, 1.5, 2, 3, 4, 6, 10])).groupby(['db', 'side'], observed=True).y20.mean().unstack().round(3)
print('\nP(taken within 20 trading days) by distance in ATR14 (all years, pooled):'); print(tab)
pd.to_pickle(dict(PAR=PAR), 'par_liq.pkl'); R.to_pickle('liq_rows.pkl')
# (b) daily structure shifts
def shifts(h, l, c, k=3):
    n = len(h); sh = []; sl = []; trend = 0; out = []; lastSH = None; lastSL = None
    for i in range(n):
        j = i - k
        if j >= k:
            if h[j] == h[j - k:j + k + 1].max(): lastSH = (j, h[j])
            if l[j] == l[j - k:j + k + 1].min(): lastSL = (j, l[j])
        if lastSL is not None and trend >= 0 and c[i] < lastSL[1]:
            a = lastSL[0]; ext = a + int(np.argmax(h[a:i + 1])) if trend == 1 else None
            if trend == 1: out.append((ext, i, -1))
            trend = -1
        elif lastSH is not None and trend <= 0 and c[i] > lastSH[1]:
            a = lastSH[0]; ext = a + int(np.argmin(l[a:i + 1])) if trend == -1 else None
            if trend == -1: out.append((ext, i, 1))
            trend = 1
    return out
def sstats(h, l, c):
    s = shifts(h, l, c); ex = np.array([x[0] for x in s]); br = np.array([x[1] for x in s])
    sp = np.diff(ex); nxt = br[1:] - ex[:-1]          # from a shift's extreme to the next shift's break
    return dict(per_year=len(s) / (len(h) / 252), med_spacing=np.median(sp), in20_60=np.mean((nxt >= 20) & (nxt <= 60)), lt20=np.mean(nxt < 20), gt60=np.mean(nxt > 60))
out = []
for sym in SYMS:
    D = daily(sym); r = sstats(D.ah.values, D.al.values, D.ac.values)
    B = [sstats(*boot_path(D)) for _ in range(100)]
    out.append(dict(sym=sym) | r | {k + '_null': np.mean([b[k] for b in B]) for k in r})
print('\ndaily structure shifts (3-bar swings), real vs bootstrap:'); print(pd.DataFrame(out).round(3).to_string(index=False))
