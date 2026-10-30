"""Join an asset's daily settle-to-settle returns to the index prices at the same ET clock time."""
import pandas as pd, numpy as np

def idx(S):
    D = pd.read_pickle(f'/home/claude/xa/idx_{S}.pkl')
    for k in ('p1430', 'p1500', 'p1600', 'p1700'):
        same = D[k + '_c'] == D[k + '_c'].shift(1)
        D['r' + k[1:]] = np.log(D[k] / D[k].shift(1)).where(same)
    return D

def panel(X, mark, syms=('NQ', 'ES', 'RTY')):
    """X: asset daily frame with 'r' (settle-to-settle log return). mark: index clock mark matching the asset's settle."""
    out = []
    for S in syms:
        D = idx(S)
        J = D.join(X.add_prefix('x_'), how='inner')
        J['rI'] = J['r' + mark]
        J['sym'] = S
        out.append(J)
    P = pd.concat(out)
    P['half'] = np.where(P.index < '2025-01-01', '18-24', '25-26')
    return P
