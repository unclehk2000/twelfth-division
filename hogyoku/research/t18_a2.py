"""Cross-market regressions: C3 return (ATR) on own C2 features and the partners' (the other three markets) C2 features.
Pooled over the four markets with market intercepts; fit on 2018–24, scored on 2025–26. Errors clustered by day (two-way
cluster over the four markets' rows on the same candle is implied by clustering on td)."""
import numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/claude/lr'); from lib import D2025
import statsmodels.api as sm
SY = ['NQ', 'ES', 'YM', 'RTY']
def prep(tf):
    W = pd.read_pickle(f'/home/claude/pdm/mat_{tf}.pkl'); rows = []
    for s in SY:
        o = W[s].copy(); P = [p for p in SY if p != s]; o['sym'] = s
        for c in ['r2', 'body', 'cl', 'dh', 'dl', 'uw', 'lw', 'rng']:
            o['p_' + c] = np.mean([W[p][c] for p in P], axis=0)
        o['p_shi'] = np.mean([W[p].shi for p in P], axis=0); o['p_slo'] = np.mean([W[p].slo for p in P], axis=0)
        rows.append(o)
    L = pd.concat(rows).reset_index(names='key')
    L['cl'] = L.cl.fillna(0.5).clip(-2, 3); L['p_cl'] = L.p_cl.fillna(0.5).clip(-2, 3)
    L = L.replace([np.inf, -np.inf], np.nan).dropna(subset=['r3', 'r2', 'body', 'uw', 'lw', 'p_r2', 'p_body', 'p_uw', 'p_lw'])
    for c in ['r2', 'body', 'p_r2', 'p_body', 'r3', 'dh', 'dl', 'p_dh', 'p_dl', 'uw', 'lw', 'p_uw', 'p_lw']: L[c] = L[c].clip(-6, 6)
    return L
OWN = ['r2', 'body', 'cl', 'shi', 'slo', 'uw', 'lw']
CROSS = ['p_r2', 'p_body', 'p_cl', 'p_shi', 'p_slo', 'p_uw', 'p_lw']
def fit(L, X, lbl):
    F = L[L.td < D2025]; S = L[L.td >= D2025]
    D = pd.get_dummies(F.sym, drop_first=False).astype(float)
    m = sm.OLS(F.r3.values, np.c_[D.values, F[X].values]).fit(cov_type='cluster', cov_kwds={'groups': F.td.values})
    Ds = pd.get_dummies(S.sym).reindex(columns=D.columns, fill_value=0).astype(float)
    pS = np.c_[Ds.values, S[X].values] @ m.params; pS0 = Ds.values @ m.params[:4]     # intercept-only baseline (drift)
    r2o = 1 - np.sum((S.r3 - pS) ** 2) / np.sum((S.r3 - pS0) ** 2)
    hit = np.mean(np.sign(pS - pS0) == np.sign(S.r3 - pS0))
    return m, r2o, hit, pS - pS0
if __name__ == '__main__':
    for tf in ['D', '240', '60', '15']:
        L = prep(tf); L.to_pickle(f'/home/claude/pdm/reg_{tf}.pkl')
        print(f'\n===== {tf} =====')
        for lbl, X in [('own only', OWN), ('cross only', CROSS), ('own + cross', OWN + CROSS)]:
            m, r2o, hit, _ = fit(L, X, lbl)
            co = ' '.join(f'{x}={b:+.3f}(t{t:+.1f})' for x, b, t in zip(X, m.params[4:], m.tvalues[4:]))
            print(f'  {lbl:12s} OOS R² {100*r2o:+.2f}%  sign hit vs drift {100*hit:.1f}% | {co}')
        # the key cross-market term, per market and per era
        for s in SY:
            Ls = L[L.sym == s]
            for era, E in [('18–24', Ls[Ls.td < D2025]), ('25–26', Ls[Ls.td >= D2025])]:
                mm = sm.OLS(E.r3.values, sm.add_constant(E[['r2', 'p_r2']].values)).fit(cov_type='cluster', cov_kwds={'groups': E.td.values})
                print(f'    {s:3s} {era}: r3 = {mm.params[0]:+.3f} {mm.params[1]:+.3f}·own r2 (t{mm.tvalues[1]:+.1f}) {mm.params[2]:+.3f}·partners r2 (t{mm.tvalues[2]:+.1f})  n {len(E)}')
