import numpy as np
from scipy.special import ndtr, expit, logit
from scipy.optimize import minimize
def fitp(x, y, h):
    z = x / np.sqrt(h)
    def nll(p):
        k, a, b = np.exp(p[0]), p[1], p[2]
        q = np.clip(2 * ndtr(-z / k), 1e-5, 1 - 1e-5); pp = np.clip(expit(a + b * logit(q)), 1e-6, 1 - 1e-6)
        return -np.mean(y * np.log(pp) + (1 - y) * np.log(1 - pp))
    r = minimize(nll, [0.0, 0.0, 1.0], method='Nelder-Mead', options={'maxiter': 4000, 'xatol': 1e-6, 'fatol': 1e-9}); return np.r_[np.exp(r.x[0]), r.x[1:]]
def predp(par, x, h):
    q = np.clip(2 * ndtr(-(x / np.sqrt(h)) / par[0]), 1e-5, 1 - 1e-5); return expit(par[1] + par[2] * logit(q))
