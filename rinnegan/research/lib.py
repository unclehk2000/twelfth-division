"""Shared helpers for the 'learn from these codes' HYDRA tests (Nov 2026).
Fish 2018–2024, score once on 2025 – 23 Oct 2026. Day-clustered SEs. Null = per-bar sign flip (keeps |moves|, drops direction)."""
import numpy as np
from numba import njit

D2025 = int(np.datetime64('2025-01-01', 'D').astype(np.int64))


def load(sym):
    Z = np.load(f'/home/claude/sh3/m_{sym}.npz')
    return {k: Z[k] for k in Z.files}


def bars(m, u):
    """u-minute bars (ET wall clock), split at contract changes. Hourly bars start on the hour (18:00 first)."""
    key = m['ts'] // u
    brk = np.flatnonzero((np.diff(key) != 0) | (np.diff(m['ct']) != 0)) + 1
    st = np.r_[0, brk]
    en = np.r_[brk - 1, len(key) - 1]
    B = dict(O=m['O'][st], C=m['C'][en], H=np.maximum.reduceat(m['H'], st), L=np.minimum.reduceat(m['L'], st),
             ts=m['ts'][st], ct=m['ct'][st].astype(np.int64), td=m['td'][st].astype(np.int64), i0=st, i1=en)
    rng = B['H'] - B['L']
    c = np.cumsum(np.r_[0, rng])
    atr = np.full(len(rng), np.nan)
    atr[14:] = (c[14:-1] - c[:-15]) / 14.0      # mean range of the 14 bars before
    B['atr'] = atr
    return B


def neg(B):
    """Mirror prices for the bear side: highs become lows."""
    N = dict(B)
    N['O'] = -B['O']; N['C'] = -B['C']; N['H'] = -B['L']; N['L'] = -B['H']
    return N


@njit(cache=True)
def coin(t, rep):
    x = np.uint64(t) * np.uint64(0x9E3779B97F4A7C15) + np.uint64(rep + 1) * np.uint64(0xBF58476D1CE4E5B9)
    x ^= x >> np.uint64(30); x *= np.uint64(0xBF58476D1CE4E5B9)
    x ^= x >> np.uint64(27); x *= np.uint64(0x94D049BB133111EB)
    x ^= x >> np.uint64(31)
    return 1.0 if (x & np.uint64(1)) == np.uint64(1) else -1.0


@njit(cache=True)
def flipbar(H, L, C, t, cp, rep):
    """Flipped bar t given the flipped previous close cp. Returns (h, l, c)."""
    e = coin(t, rep)
    if e > 0:
        return cp + (H[t] - C[t - 1]), cp + (L[t] - C[t - 1]), cp + (C[t] - C[t - 1])
    return cp - (L[t] - C[t - 1]), cp - (H[t] - C[t - 1]), cp - (C[t] - C[t - 1])


def cse(y, g):
    """Mean and day-clustered SE of y (float array) with cluster ids g."""
    y = np.asarray(y, float); g = np.asarray(g)
    ok = ~np.isnan(y); y = y[ok]; g = g[ok]
    n = len(y)
    if n < 2:
        return np.nan, np.nan, n
    mu = y.mean()
    _, inv = np.unique(g, return_inverse=True)
    s = np.bincount(inv, weights=y - mu)
    return mu, np.sqrt((s ** 2).sum()) / n, n


def fmt(mu, se, n, pct=True):
    if pct:
        return f'{100*mu:5.1f}% ±{100*se:4.1f} (n={n})'
    return f'{mu:+.3f} ±{se:.3f} (n={n})'
