"""Shared test helpers: pooled OLS / logit with errors clustered by date, the ✓ rule (p < 0.05 pooled, same sign in
2018–24 and 2025–26, same sign on NQ, ES and RTY)."""
import numpy as np, pandas as pd, statsmodels.formula.api as smf

def cfit(df, formula, kind='ols'):
    """fit with date-clustered errors; drops rows with NaN in the used columns first."""
    import patsy
    d = df.copy()
    d['date'] = df.index
    d = d.reset_index(drop=True)
    y, X = patsy.dmatrices(formula, d, return_type='dataframe', NA_action='drop')
    g = pd.factorize(d.loc[y.index, 'date'])[0]
    import statsmodels.api as sm
    mod = sm.OLS(y, X) if kind == 'ols' else sm.Logit(y, X)
    return mod.fit(cov_type='cluster', cov_kwds={'groups': g}, disp=0) if kind != 'ols' else mod.fit(cov_type='cluster', cov_kwds={'groups': g})

def check(df, formula, term, kind='ols'):
    """pooled coef / p, and the coefficient by half and by symbol; ✓ when it passes the house rule."""
    r = cfit(df, formula, kind)
    out = {'coef': r.params[term], 'p': r.pvalues[term], 'n': int(r.nobs)}
    signs = [np.sign(out['coef'])]
    for h, g in df.groupby('half'):
        rr = cfit(g, formula, kind); out[h] = rr.params[term]; out['p_' + h] = rr.pvalues[term]; signs.append(np.sign(rr.params[term]))
    for s, g in df.groupby('sym'):
        rr = cfit(g, formula, kind); out[s] = rr.params[term]; signs.append(np.sign(rr.params[term]))
    out['ok'] = '✓' if out['p'] < 0.05 and len(set(signs)) == 1 else ''
    return out

def table(rows):
    T = pd.DataFrame(rows).set_index('test')
    cols = ['coef', 'p', 'n', '18-24', 'p_18-24', '25-26', 'p_25-26', 'NQ', 'ES', 'RTY', 'ok']
    return T[[c for c in cols if c in T.columns]]
