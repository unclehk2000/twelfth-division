"""Export the day GBM to Pine (nested ternaries, one line per tree) and verify the export against sklearn."""
import numpy as np, pandas as pd, pickle, sys
M = pickle.load(open('/home/claude/sk/t13_models.pkl', 'rb'))['day']
gb, FE = M['gb'], M['FE']
lr = gb.learning_rate
p0 = gb.init_.class_prior_[1]; init = float(np.log(p0 / (1 - p0)))
VN = {'lz': 'fLz', 'side': 'fSd', 'r': 'fR', 'ru': 'fRu', 'age': 'fAge', 'pos': 'fPos', 'xRef': 'fRef', 'opn': 'fOpn', 'tEx': 'fTx', 'evA': 'fEv', 'dow': 'fDow'}
def expr(t, node):
    if t.children_left[node] == -1:
        return f'{t.value[node][0][0] * lr:.5f}'
    f = FE[t.feature[node]]; thr = t.threshold[node]
    return f'({VN[f]} <= {thr:.5f} ? {expr(t, t.children_left[node])} : {expr(t, t.children_right[node])})'
lines = [expr(est[0].tree_, 0) for est in gb.estimators_]
# python evaluator of the same text, to check
def pyeval(row):
    env = {VN[k]: row[k] for k in FE}
    tot = init
    for ln in lines:
        e = ln
        # convert "a <= b ? c : d" ternaries to python via a tiny recursive parser
        tot += float(tern(e, env))
    return 1 / (1 + np.exp(-tot))
def tern(s, env):
    s = s.strip()
    if s[0] != '(':
        return float(s)
    s = s[1:-1]
    # split "cond ? A : B" at top level
    depth = 0; q = c = -1
    for i, ch in enumerate(s):
        if ch == '(': depth += 1
        elif ch == ')': depth -= 1
        elif ch == '?' and depth == 0 and q < 0: q = i
        elif ch == ':' and depth == 0 and q >= 0: c = i; break
    cond = s[:q]; A = s[q + 1:c]; B = s[c + 1:]
    v, thr = cond.split('<=')
    return tern(A, env) if env[v.strip()] <= float(thr) else tern(B, env)
D = pd.read_pickle('/home/claude/sk/t13_day.pkl').sample(2000, random_state=3)
from scipy.stats import norm
D['lz'] = np.log(np.clip(2 * norm.cdf(M['k0'] * D.z) - 1, 1e-6, 1 - 1e-6) / (1 - np.clip(2 * norm.cdf(M['k0'] * D.z) - 1, 1e-6, 1 - 1e-6)))
D = D[np.isfinite(D.xRef)]
pk = gb.predict_proba(D[FE].values)[:, 1]
pe = np.array([pyeval(r) for _, r in D.iterrows()])
print('max |sklearn − export|', np.abs(pk - pe).max(), 'init', init, 'trees', len(lines), 'chars', sum(len(l) for l in lines))
body = '\n'.join(f'    s += {l}' for l in lines)
pine = f'''// day model: gradient-boosted trees ({len(lines)} × depth 3, learning rate {lr}), trained on NQ + ES + RTY 1-minute 2018–24
dayTrees(float fLz, float fSd, float fR, float fRu, float fAge, float fPos, float fRef, float fOpn, float fTx, float fEv, float fDow) =>
    float s = {init:.6f}
{body}
    1.0 / (1.0 + math.exp(-s))'''
open('/home/claude/sk/day_trees.pine', 'w').write(pine)
print(pine[:600])
