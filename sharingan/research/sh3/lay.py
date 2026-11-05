"""Sharingan LTF IPDA layers, built as a Quarterly Theory fractal.
Each layer keeps ICT's 20 / 40 / 60 counts but on its own unit, anchored to the last closed period one QT cycle down:
  H   : unit 1 hour,  period the trading day (18:00–17:00 ET)          ~ daily IPDA's day / month
  M15 : unit 15 min, period the 6-hour QT session (18, 00, 06, 12)
  M5  : unit 5 min,  period the 90-minute QT quarter
  M1  : unit 1 min,  period the 22.5-minute QT quarter
Anchor = first unit of the last closed period; look back = the 20 / 40 / 60 units left of it; cast forward = +20 / +40 / +60 units."""
import numpy as np

LAYERS = {'H': 60, 'M15': 15, 'M5': 5, 'M1': 1}


def period_key(layer, ts, td):
    if layer == 'H':
        return td.astype(np.int64)
    if layer == 'M15':
        return ts // 360
    if layer == 'M5':
        return ts // 90
    return (ts * 2) // 45


def load(sym):
    Z = np.load(f'/home/claude/sh3/m_{sym}.npz')
    return {k: Z[k] for k in Z.files}


def units(m, layer):
    """Unit bars (OHLC) by unit key and contract; their period, start ts and trading day."""
    u = LAYERS[layer]
    key = m['ts'] // u
    brk = np.flatnonzero((np.diff(key) != 0) | (np.diff(m['ct']) != 0)) + 1
    st = np.r_[0, brk]
    U = dict(O=m['O'][st], C=m['C'][np.r_[brk - 1, len(key) - 1]], H=np.maximum.reduceat(m['H'], st), L=np.minimum.reduceat(m['L'], st),
             ts=m['ts'][st], ct=m['ct'][st].astype(np.int64), td=m['td'][st].astype(np.int64))
    U['P'] = period_key(layer, U['ts'], U['td'])
    pb = np.r_[0, np.flatnonzero(np.diff(U['P']) != 0) + 1]
    U['ps'] = pb                                   # first unit of each period
    rng = U['H'] - U['L']
    c = np.cumsum(np.r_[0, rng])
    atr = np.full(len(rng), np.nan)
    atr[14:] = (c[14:-1] - c[:-15]) / 14.0          # mean range of the 14 units before
    U['atr'] = atr
    return U
