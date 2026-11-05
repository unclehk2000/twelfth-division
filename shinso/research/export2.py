import numpy as np, pickle
M = pickle.load(open('/home/claude/sn/t15_models.pkl', 'rb'))
def export(gb, FE, VN, fname, doc):
    lr = gb.learning_rate; p0 = gb.init_.class_prior_[1]; init = float(np.log(p0 / (1 - p0)))
    def expr(t, node):
        if t.children_left[node] == -1: return f'{t.value[node][0][0] * lr:.5f}'
        return f'({VN[FE[t.feature[node]]]} <= {t.threshold[node]:.5f} ? {expr(t, t.children_left[node])} : {expr(t, t.children_right[node])})'
    lines = [expr(e[0].tree_, 0) for e in gb.estimators_]
    args = ', '.join(f'float {VN[f]}' for f in FE)
    return f'''// {doc}
{fname}({args}) =>
    float s = {init:.6f}
''' + '\n'.join(f'    s += {l}' for l in lines) + '\n    1.0 / (1.0 + math.exp(-s))'
P = M['pool']; R = M['race']
t1 = export(P['gb'], P['FE'], {'lz': 'fLz', 'typ': 'fTyp', 'side': 'fSd', 'r': 'fR', 'nb': 'fNb', 'cf': 'fCf', 'opp': 'fOpp', 'same': 'fSame', 'tow': 'fTow', 'ev': 'fEv', 'dow': 'fDow'}, 'poolTrees',
            f'pool model: {len(P["gb"].estimators_)} gradient-boosted trees, depth 3, trained on NQ + ES + RTY 1-minute 2018–24 (2.3 million samples)')
t2 = export(R['gb'], R['FE'], {'lb': 'fLb', 'tB': 'fTB', 'tS': 'fTS', 'nTB': 'fNTB', 'nTS': 'fNTS', 'opn': 'fOpn', 'r': 'fR'}, 'raceTrees',
            f'race model: {len(R["gb"].estimators_)} gradient-boosted trees, depth 3, trained on 2018–24 (261,109 races)')
open('/home/claude/sn/trees.pine', 'w').write(t1 + '\n\n' + t2 + '\n')
print(P['k0'], P['a0'], P['b0'], len(t1), len(t2))
