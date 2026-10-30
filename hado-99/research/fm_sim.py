"""Bar-by-bar Python mirror of the Bakudō 58 fractal module (for the mocks). Bars: arrays O, H, L, C, t (Timestamps),
key (higher-timeframe bucket per bar). Bullish and bearish, CISD trackers, setups, projections, protected swings."""
import numpy as np

PJ = [1.0, 2.0, 2.5, 4.0, 4.5]


class HC:
    def __init__(s, o, h, l, c, t0, b):
        s.o, s.h, s.l, s.c, s.t0, s.b0, s.bH, s.bL = o, h, l, c, t0, b, b, b


class FS:
    def __init__(s, **k):
        s.__dict__.update(k)
        s.phase = 3; s.dead = False; s.deadT = None; s.took = False; s.tookT = None; s.eqHit = False
        s.cisd = False; s.cisdC2 = False; s.cisdB = None; s.cisdT = None; s.cisdX0 = None
        s.pj = None; s.pjHit = None; s.x2 = None
        s.pPend = False; s.pDone = False; s.pTaken = False; s.pPx = None; s.pB = None; s.pLeft = None
        s.boxR = None


def run(O, H, L, C, t, key, keep=2, upto=None, c4_end=None, tf_ms=60000, fm_tf='15'):
    n = len(O) if upto is None else upto
    hcs, fss = [], []
    tr = {True: dict(L=None, B=None, ok=False, T=None), False: dict(L=None, B=None, ok=False, T=None)}
    early = {True: None, False: None}
    gone = []

    def cisdLvl(b, bull):
        st = 1 if ((C[b] > O[b]) if bull else (C[b] < O[b])) else 0
        lv, lb = None, None
        for i in range(st, 11):
            j = b - i
            if j < 0:
                break
            opp = C[j] < O[j] if bull else C[j] > O[j]
            if opp:
                lv = O[j] if lv is None else (max(lv, O[j]) if bull else min(lv, O[j])); lb = j
            elif C[j] != O[j]:
                break
        return (O[b] if lv is None else lv), (b if lb is None else lb)

    def confirm(s, b, early_):
        s.cisd = True; s.cisdC2 = early_; s.cisdB = b; s.cisdT = t[b]; s.cisdX0 = s.lvlB
        r = (s.lvl - s.ext) if s.bull else (s.ext - s.lvl)
        if r > 0:
            s.pj = [(s.lvl + k * r) if s.bull else (s.lvl - k * r) for k in PJ]
            s.pjHit = [False] * 5
            s.pjX0 = b

    for b in range(n):
        new = b > 0 and key[b] != key[b - 1]
        if b == 0:
            hcs.insert(0, HC(O[b], H[b], L[b], C[b], t[b], b))
            continue
        if new:
            for s in fss:
                if s.phase == 3:
                    s.phase = 4; s.boxR = b - 1
                elif s.phase == 4:
                    s.phase = 0
            if len(hcs) >= 2:
                c2, c1 = hcs[0], hcs[1]
                for bull in (True, False):
                    isC2 = (c2.l < c1.l and c2.c > c1.l) if bull else (c2.h > c1.h and c2.c < c1.h)
                    if not isC2:
                        continue
                    rng = c2.h - c2.l
                    clv = ((c2.c - c2.l) / rng if bull else (c2.h - c2.c) / rng) if rng > 0 else 0.5
                    q = 0 if clv < .25 else 1 if clv < .5 else 2 if clv < .75 else 3
                    s = FS(bull=bull, t2=c2.t0, t3=t[b], bExt=c2.bL if bull else c2.bH, ext=c2.l if bull else c2.h,
                           opp=c2.h if bull else c2.l, eq=(c2.h + c2.l) / 2, clv=clv, q=q,
                           lvl=tr[bull]['L'], lvlB=tr[bull]['B'], c1x=c1.bL if bull else c1.bH, c1y=c1.l if bull else c1.h,
                           b3=b, open3=O[b])
                    if tr[bull]['ok'] and s.lvl is not None:
                        confirm(s, b, True)
                        s.cisdB = tr[bull]['T']
                    fss.append(s)
                while len(fss) > keep:
                    gone.append(fss.pop(0))
            hcs.insert(0, HC(O[b], H[b], L[b], C[b], t[b], b))
            del hcs[10:]
            for bull in (True, False):
                tr[bull] = dict(L=None, B=None, ok=False, T=None); early[bull] = None
        else:
            cur = hcs[0]
            if H[b] > cur.h:
                cur.h = H[b]; cur.bH = b
            if L[b] < cur.l:
                cur.l = L[b]; cur.bL = b
            cur.c = C[b]
        if len(hcs) >= 2:
            cur, prv = hcs[0], hcs[1]
            if L[b] == cur.l and cur.l < prv.l and b == cur.bL:
                lv, lb = cisdLvl(b, True); tr[True] = dict(L=lv, B=lb, ok=False, T=None); early[True] = None
            T = tr[True]
            if T['L'] is not None and not T['ok'] and b > cur.bL and C[b] > T['L']:
                T['ok'] = True; T['T'] = b; early[True] = (T['B'], T['L'], b)
            if H[b] == cur.h and cur.h > prv.h and b == cur.bH:
                lv, lb = cisdLvl(b, False); tr[False] = dict(L=lv, B=lb, ok=False, T=None); early[False] = None
            T = tr[False]
            if T['L'] is not None and not T['ok'] and b > cur.bH and C[b] < T['L']:
                T['ok'] = True; T['T'] = b; early[False] = (T['B'], T['L'], b)
        for s in fss:
            if s.phase > 0:
                bull = s.bull
                if not s.dead and ((L[b] < s.ext) if bull else (H[b] > s.ext)):
                    s.dead = True; s.deadT = t[b]
                if s.phase == 3 and not s.took and ((H[b] > s.opp) if bull else (L[b] < s.opp)):
                    s.took = True; s.tookT = t[b]
                if s.phase == 3 and ((L[b] <= s.eq) if bull else (H[b] >= s.eq)):
                    s.eqHit = True
                if not s.cisd and not s.dead and s.lvl is not None and ((C[b] > s.lvl) if bull else (C[b] < s.lvl)):
                    confirm(s, b, False)
                if s.pj is not None and not s.dead:
                    for i, y in enumerate(s.pj):
                        if not s.pjHit[i] and ((H[b] >= y) if bull else (L[b] <= y)):
                            s.pjHit[i] = True
                if not s.dead:
                    s.x2 = b
                    if s.phase == 3:
                        s.boxR = b
                if s.cisd and not s.dead and not s.pDone and b > s.cisdB:
                    if not s.pPend:
                        if (C[b] < O[b]) if bull else (C[b] > O[b]):
                            s.pPend = True; s.pA = b; s.pLvl = O[b]; s.pEx = L[b] if bull else H[b]; s.pExB = b
                    else:
                        if (L[b] < s.pEx) if bull else (H[b] > s.pEx):
                            s.pEx = L[b] if bull else H[b]; s.pExB = b
                            best = None
                            for i in range(0, min(b - s.pA, 290) + 1):
                                j = b - i
                                oppI = C[j] < O[j] if bull else C[j] > O[j]
                                if oppI or C[j] == O[j]:
                                    best = O[j] if best is None else (max(best, O[j]) if bull else min(best, O[j]))
                                else:
                                    break
                            if best is not None:
                                s.pLvl = best
                        if b > s.pExB and ((C[b] > s.pLvl) if bull else (C[b] < s.pLvl)):
                            sp, sb = None, None
                            for k in range(1, min(b - s.pA, 290) + 1):
                                j = b - k
                                sw = (L[j] <= L[j - 1] and L[j] <= L[j + 1]) if bull else (H[j] >= H[j - 1] and H[j] >= H[j + 1])
                                v = L[j] if bull else H[j]
                                if sw and (sp is None or ((v < sp) if bull else (v > sp))):
                                    sp, sb = v, j
                            if sp is not None:
                                s.pDone = True; s.pPx = sp; s.pB = sb
                                if c4_end is not None:
                                    s.pLeft = c4_end(s, b)
                            else:
                                s.pPend = False
                if s.pDone and not s.pTaken and ((L[b] < s.pPx) if s.bull else (H[b] > s.pPx)):
                    s.pTaken = True
    return dict(hcs=hcs, fss=fss, early=early, last=n - 1)
