import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'DejaVu Sans'
S, T1, T2, GR = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
C1, C2, NEU = '#2a78d6', '#eb6834', '#8a8984'
def style(ax):
    ax.set_facecolor(S); [ax.spines[s].set_visible(False) for s in ('top', 'right', 'left')]; ax.spines['bottom'].set_color(GR)
    ax.grid(axis='y', color=GR, lw=0.8); ax.set_axisbelow(True); ax.tick_params(colors=T2, labelsize=9, length=0)
# 1) reach by level: observed vs the shifted grid at the same distance
tab = pd.read_csv('reach_by_level.csv')
fig, ax = plt.subplots(figsize=(9, 4.6), dpi=150, facecolor=S); style(ax)
ax.plot(tab.f, 100 * tab.pred, color=C2, lw=2, label='Shifted grid, same distance (expected)')
ax.scatter(tab.f, 100 * tab.hit, s=34, color=C1, edgecolor=S, linewidth=1.5, zorder=3, label='Jūjishō level (observed)')
for f in (-0.5, 0.0, 0.5, 1.0, 1.5):
    r = tab[tab.f == f].iloc[0]; ax.annotate(f"{f:g}", (f, 100 * r.hit), xytext=(0, 9), textcoords='offset points', ha='center', fontsize=8, color=T2)
ax.set_xlabel('Fib level (0 = Monday\'s CE, 1 = Friday\'s CE)', color=T2, fontsize=9); ax.set_ylabel('Reached by Friday 16:59 (%)', color=T2, fontsize=9)
ax.set_ylim(45, 100); ax.legend(frameon=False, fontsize=9, labelcolor=T1, loc='lower left')
ax.set_title('Every level traded as often as a random level the same distance away', color=T1, fontsize=11, loc='left', pad=10)
fig.text(0.01, 0.01, 'NQ 2018–Oct 2026, 402 weeks. Distance-controlled logit, real vs shifted grid: p = 0.75.', color=T2, fontsize=8)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig('images/jujisho_reach_vs_shifted.png', facecolor=S); plt.close(fig)
# 2) direction state by year
W = pd.read_pickle('weeks_final.pkl')
g = W.groupby(['yr', 'dn']).bp.mean().unstack(); a = W.groupby('yr').bp.mean(); yrs = g.index.values
fig, ax = plt.subplots(figsize=(9, 4.6), dpi=150, facecolor=S); style(ax)
w = 0.36
ax.bar(yrs - w / 2 - 0.01, g[1], w, color=C1, label='Monday\'s gap below Friday\'s CE', zorder=2)
ax.bar(yrs + w / 2 + 0.01, g[0], w, color=C2, label='Monday\'s gap above Friday\'s CE', zorder=2)
ax.scatter(yrs, a, marker='_', s=260, color=T1, linewidth=2, zorder=3, label='All weeks (always long)')
ax.axhline(0, color=T2, lw=0.8)
ax.set_xticks(yrs); ax.set_xticklabels([str(y) if y < 2026 else '2026*' for y in yrs])
ax.set_ylabel('Mean rest-of-week return (bp)', color=T2, fontsize=9)
ax.legend(frameon=False, fontsize=9, labelcolor=T1, loc='lower left', ncol=1)
ax.set_title('After a down shift the rest of the week did better in 7 of 9 years', color=T1, fontsize=11, loc='left', pad=10)
fig.text(0.01, 0.01, 'From Monday\'s gap to Friday 16:59, NQ, 402 weeks. Permutation p = 0.005. *2026 to 23 Oct. Same result from prices alone (97% overlap).', color=T2, fontsize=8)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig('images/jujisho_shift_by_year.png', facecolor=S); plt.close(fig)
print('ok')
