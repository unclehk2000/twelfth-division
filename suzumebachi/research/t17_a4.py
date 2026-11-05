"""Discovery → confirmation scan. Discovered: |t| > 2 on ES + YM 2018–24. Confirmed: the same sign with t > 2 on 2025–26 of all four
markets pooled (the only data independent in time), and the same sign on NQ + RTY 2018–24. One context at a time, every sensitivity."""
import numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/claude/lr'); from lib import cse, D2025
X = pd.read_pickle('/home/claude/sz/t17_evx2.pkl')
X['g4'] = np.where(X.td >= D2025, 'H', np.where(X.sym.isin(['ES', 'YM']), 'T', 'O1'))
X['smt1'] = np.where(X.sw_sw == 1, np.where(X.p_sw == 0, 'SMT', 'no SMT'), 'no raid')
X['raid'] = np.select([X.f_pw == 1, X.f_pd == 1, (X.f_as == 1) | (X.f_lo == 1), X.f_day == 1, X.sw_sw == 1], ['fresh PW', 'fresh PD', 'fresh session', 'new day extreme', 'swing only'], 'no raid')
X['mo'] = np.where(X.xMO.isna(), 'before 00:00', np.where(X.xMO > 0, 'ICT side of midnight open', 'wrong side of MO'))
X['dop'] = np.where(X.xDO > 0, 'ICT side of 18:00 open', 'wrong side of 18:00')
X['wop'] = np.where(X.xWO > 0, 'ICT side of week open', 'wrong side of week open')
X['bigb'] = pd.cut(X.body, [-1, 0.75, 1.5, 99], labels=['body <0.75', 'body 0.75-1.5', 'body >1.5'])
X['rAb'] = pd.cut(X.rA, [0, 1.5, 2.5, 4, 99], labels=['risk <1.5', 'risk 1.5-2.5', 'risk 2.5-4', 'risk >4'])
X['kz'] = pd.cut(X.rel, [-1, 120, 360, 480, 660, 810, 930, 1050, 1170, 1320, 1440], labels=['18-20', 'Asia 20-00', '00-02', 'London 02-05', '05-07:30', '07:30-09:30', 'NY AM 09:30-11:30', 'lunch', 'NY PM 13:30-16', '16-17'])
X['oct'] = np.clip(np.floor(X.pdx * 4), -1, 4).map({-1: 'PD range: other side', 0: 'PD q1 (wrong)', 1: 'PD q2', 2: 'PD q3', 3: 'PD q4 (ICT)', 4: 'PD beyond (ICT)'})
X['hq'] = np.clip(np.floor(X.hdx * 4), -1, 4).map({-1: '1H DR: other side', 0: '1H q1 (wrong)', 1: '1H q2', 2: '1H q3', 3: '1H q4 (ICT)', 4: '1H beyond (ICT)'})
X['h1'] = X.tr1.map({1: 'with 1H trend', -1: 'against 1H trend', 0: '1H none'}); X['dd'] = X.trd.map({1: 'with daily trend', -1: 'against daily trend', 0: 'daily none'})
X['fv'] = X.fvg.map({1: 'FVG in leg', 0: 'no FVG'}); X['side'] = X.dir.map({1: 'long', -1: 'short'})
X['speed'] = pd.cut(X.bars_x, [-1, 2, 6, 999], labels=['break ≤2 bars after extreme', 'break 3-6 bars', 'break >6 bars'])
X.to_pickle('/home/claude/sz/t17_evx3.pkl')
CTX = ['side', 'raid', 'smt1', 'fv', 'bigb', 'rAb', 'kz', 'oct', 'hq', 'h1', 'dd', 'mo', 'dop', 'wop', 'speed']
def st(g):
    mu, se, n = cse(g.R1.values / 2, g.td.values); return mu, se, n
if __name__ == '__main__':
    res = []
    for (u, k), A in X.groupby(['u', 'k']):
        for fam in [1, 0]:
            B = A[A.mss == fam]
            for c in CTX:
                for v, g in B.groupby(c, observed=True):
                    mT, sT, nT = st(g[g.g4 == 'T']); mH, sH, nH = st(g[g.g4 == 'H']); mO, sO, nO = st(g[g.g4 == 'O1'])
                    if nT < 300: continue
                    sy = ''.join('+' if g[(g.sym == q) & (g.g4 == 'H')].R1.mean() > 0 else '−' for q in ['ES', 'YM', 'NQ', 'RTY'])
                    res.append(dict(cfg=f'{u}m k{k}', fam='MSS' if fam else 'BOS', ctx=c, val=str(v), T=50 + 100 * mT, tT=mT / sT, H=50 + 100 * mH, tH=mH / sH if sH > 0 else 0, nH=nH, O1=50 + 100 * mO, tO=mO / sO, nT=nT, sy=sy))
    R = pd.DataFrame(res)
    R['disc'] = R.tT.abs() > 2; R['conf'] = R.disc & (np.sign(R.tH) == np.sign(R.tT)) & (R.tH.abs() > 2) & (np.sign(R.tO) == np.sign(R.tT))
    R.to_pickle('/home/claude/sz/a4.pkl')
    print(f'tests {len(R)}, discovered {R.disc.sum()}, confirmed {R.conf.sum()}  (by chance ≈ {0.025 * R.disc.sum():.1f} of the discovered)')
    pd.set_option('display.width', 250)
    print(R[R.conf].sort_values(['ctx', 'cfg']).round(1).to_string(index=False))
