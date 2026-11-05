import numpy as np


def ratio_diff(ar, br, an, bn, g):
    """Ratio estimators P_r = sum ar / sum br and P_n = sum an / sum bn with the day-clustered SE of P_r − P_n (linearised)."""
    ar, br, an, bn = [np.asarray(x, float) for x in (ar, br, an, bn)]
    Pr = ar.sum() / br.sum(); Pn = an.sum() / bn.sum()
    z = (ar - Pr * br) / br.mean() - (an - Pn * bn) / bn.mean()
    _, inv = np.unique(np.asarray(g), return_inverse=True)
    s = np.bincount(inv, weights=z)
    se = np.sqrt((s ** 2).sum()) / len(z)
    zr = (ar - Pr * br) / br.mean(); sr = np.bincount(inv, weights=zr)
    return Pr, Pn, Pr - Pn, se, np.sqrt((sr ** 2).sum()) / len(z), int(br.sum())
