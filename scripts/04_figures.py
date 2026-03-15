#!/usr/bin/env python3
"""
04_figures.py — Publication-quality figures for Clinical Autonomic Research
Outcome: cognitive milestones (dom3)
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.patches as mpatches
import seaborn as sns
from lifelines import KaplanMeierFitter
from lifelines.statistics import logrank_test
import warnings
warnings.filterwarnings('ignore')

SEED = 42
np.random.seed(SEED)

BASE = "."

plt.rcParams.update({
    'font.family': 'Arial', 'font.size': 9, 'axes.linewidth': 0.8,
    'axes.spines.top': False, 'axes.spines.right': False,
})

PALETTE = sns.color_palette('muted')
DOMAIN_COLORS = {
    'Gastrointestinal': '#4C72B0', 'Urinary': '#DD8452', 'Cardiovascular': '#55A868',
    'Thermoregulatory': '#C44E52', 'Pupillomotor': '#8172B3', 'Sexual': '#937860',
}
ITEM_DOMAIN = {}
for i in range(1,8): ITEM_DOMAIN[f'SCAU{i}'] = 'Gastrointestinal'
for i in range(8,14): ITEM_DOMAIN[f'SCAU{i}'] = 'Urinary'
for i in range(14,17): ITEM_DOMAIN[f'SCAU{i}'] = 'Cardiovascular'
for i in range(17,22): ITEM_DOMAIN[f'SCAU{i}'] = 'Thermoregulatory'
ITEM_DOMAIN['SCAU22'] = 'Pupillomotor'
for i in range(23,26): ITEM_DOMAIN[f'SCAU{i}'] = 'Sexual'

ITEM_LABELS = {
    'SCAU1': 'Swallowing/choking', 'SCAU2': 'Drooling', 'SCAU3': 'Dysphagia',
    'SCAU4': 'Early satiety', 'SCAU5': 'Constipation', 'SCAU6': 'Straining',
    'SCAU7': 'Fecal incontinence', 'SCAU8': 'Urgency', 'SCAU9': 'Frequency',
    'SCAU10': 'Nocturia', 'SCAU11': 'Incontinence', 'SCAU12': 'Incomplete emptying',
    'SCAU13': 'Weak stream', 'SCAU14': 'Lightheadedness standing',
    'SCAU15': 'Lightheadedness walking', 'SCAU16': 'Fainting',
    'SCAU17': 'Excessive sweating day', 'SCAU18': 'Excessive sweating night',
    'SCAU19': 'Heat intolerance', 'SCAU20': 'Cold intolerance',
    'SCAU21': 'Color change hands/feet', 'SCAU22': 'Oversensitive to light',
    'SCAU23': 'Sexual dysfunction 1', 'SCAU24': 'Sexual dysfunction 2',
    'SCAU25': 'Sexual dysfunction 3'
}

# ══════════════════════════════════════════════════════════════════════════
# FIGURE 1: Flow diagram
# ══════════════════════════════════════════════════════════════════════════
print("Figure 1: Flow diagram...")
fig, ax = plt.subplots(figsize=(7, 8.5))
ax.set_xlim(0, 10); ax.set_ylim(0, 12); ax.axis('off')

def draw_box(ax, x, y, w, h, text, color='white', edge='black', fs=8):
    box = FancyBboxPatch((x-w/2,y-h/2), w, h, boxstyle="round,pad=0.1",
                          facecolor=color, edgecolor=edge, linewidth=1)
    ax.add_patch(box)
    ax.text(x, y, text, ha='center', va='center', fontsize=fs, wrap=True)

def draw_side(ax, x, y, w, h, text, fs=7):
    box = FancyBboxPatch((x-w/2,y-h/2), w, h, boxstyle="round,pad=0.1",
                          facecolor='#f0f0f0', edgecolor='gray', linewidth=0.8)
    ax.add_patch(box)
    ax.text(x, y, text, ha='center', va='center', fontsize=fs)

steps = [
    (5, 11.2, 'PPMI Master Dataset\n(N = 4,697 at baseline)', '#E8F4FD'),
    (5, 9.8, 'PD cohort\n(n = 1,585)', '#E8F4FD'),
    (5, 8.4, 'Baseline SCOPA-AUT available\n(n = 1,269)', '#E8F4FD'),
    (5, 7.0, 'Baseline MoCA available\n(n = 1,265)', '#E8F4FD'),
    (5, 5.6, 'No baseline PD-Dementia\n(n = 1,251)', '#E8F4FD'),
    (5, 4.2, 'Event or \u22652-year follow-up\n(n = 960)', '#E8F4FD'),
]
excl = [
    (8.5, 10.5, 'Excluded: n = 3,112\n(non-PD cohorts)'),
    (8.5, 9.1, 'Excluded: n = 316\n(missing SCOPA-AUT)'),
    (8.5, 7.7, 'Excluded: n = 4\n(missing MoCA)'),
    (8.5, 6.3, 'Excluded: n = 14\n(Cognitive_Group = 3)'),
    (8.5, 4.9, 'Excluded: n = 291\n(insufficient follow-up)'),
]

for (x,y,t,c) in steps:
    draw_box(ax, x, y, 4.5, 0.7, t, c)
for (x,y,t) in excl:
    draw_side(ax, x, y, 2.5, 0.5, t)
for i in range(len(steps)-1):
    ax.annotate('', xy=(5, steps[i+1][1]+0.35), xytext=(5, steps[i][1]-0.35),
                arrowprops=dict(arrowstyle='->', color='black', lw=1))

# Final box
draw_box(ax, 5, 2.5, 4.5, 1.2,
    'Analytical cohort: N = 960\n\nCognitive milestone reached: n = 227 (23.6%)\nNo cognitive milestone: n = 733 (76.4%)',
    '#D5E8D4', 'green', 8)
ax.annotate('', xy=(5, 3.1), xytext=(5, steps[-1][1]-0.35),
            arrowprops=dict(arrowstyle='->', color='black', lw=1))

for fmt in ['png','pdf']:
    fig.savefig(f"{BASE}/figures/figure1_flowchart.{fmt}", dpi=300, bbox_inches='tight',
                facecolor='white')
plt.close()
print("  Done")

# ══════════════════════════════════════════════════════════════════════════
# FIGURE 2: Forest plot — Adjusted HRs (Cox, PRIMARY)
# ══════════════════════════════════════════════════════════════════════════
print("Figure 2: Forest plot (adjusted Cox HRs)...")
cox = pd.read_csv(f"{BASE}/tables/cox_adjusted.csv")
cox['item_num'] = cox['Item'].str.replace('SCAU','').astype(int)
cox = cox.sort_values('item_num')

fig, ax = plt.subplots(figsize=(7, 8))
items = cox['Item'].values
hrs = cox['HR_adj'].values
ci_lo = cox['CI_low_adj'].values
ci_hi = cox['CI_high_adj'].values
pvals = cox['p_value_adj'].values
fdrs = cox['p_fdr_adj'].values
y_pos = np.arange(len(items))

for i in range(len(items)):
    domain = ITEM_DOMAIN.get(items[i], 'Other')
    color = DOMAIN_COLORS.get(domain, 'gray')
    marker = 's' if fdrs[i] < 0.05 else 'o'
    msize = 7 if fdrs[i] < 0.05 else 5
    ax.errorbar(hrs[i], y_pos[i], xerr=[[hrs[i]-ci_lo[i]], [ci_hi[i]-hrs[i]]],
                fmt=marker, color=color, markersize=msize, capsize=3, linewidth=1.2,
                markeredgecolor='black' if fdrs[i]<0.05 else color, markeredgewidth=0.5 if fdrs[i]<0.05 else 0)

ax.axvline(x=1.0, color='gray', linestyle='--', linewidth=0.8, zorder=0)
ax.set_yticks(y_pos)
ax.set_yticklabels([f"{it}  {ITEM_LABELS.get(it,'')}" for it in items], fontsize=7.5)
ax.set_xlabel('Adjusted Hazard Ratio (95% CI)', fontsize=9)
ax.invert_yaxis()

for i in range(len(items)):
    ci_str = f"{hrs[i]:.2f} ({ci_lo[i]:.2f}\u2013{ci_hi[i]:.2f})"
    p_str = f"{pvals[i]:.3f}" if pvals[i] >= 0.001 else "<0.001"
    fdr_str = f"{fdrs[i]:.3f}" if fdrs[i] >= 0.001 else "<0.001"
    bold = "**" if fdrs[i] < 0.05 else ""
    ax.text(max(ci_hi)+0.2, y_pos[i], f"{ci_str}  p={p_str}  FDR={fdr_str}",
            fontsize=6, va='center', fontweight='bold' if fdrs[i]<0.05 else 'normal')

handles = [mpatches.Patch(color=c, label=d) for d,c in DOMAIN_COLORS.items()]
ax.legend(handles=handles, loc='lower right', fontsize=7, frameon=True, fancybox=True)
ax.set_xlim(0.1, max(ci_hi)+1.5)

plt.tight_layout()
for fmt in ['png','pdf']:
    fig.savefig(f"{BASE}/figures/figure2_forest_cox.{fmt}", dpi=300, bbox_inches='tight')
plt.close()
print("  Done")

# ══════════════════════════════════════════════════════════════════════════
# FIGURE 3: Kaplan-Meier — SCOPA-AUT tertiles
# ══════════════════════════════════════════════════════════════════════════
print("Figure 3: Kaplan-Meier curves...")
df = pd.read_csv(f"{BASE}/data/analytical_dataset.csv")
assert len(df) == 960

t33 = df['SCAU_TOTAL'].quantile(0.333)
t67 = df['SCAU_TOTAL'].quantile(0.667)
df['scopa_tert'] = pd.cut(df['SCAU_TOTAL'], bins=[-1, t33, t67, 100],
                           labels=[f'Low (\u2264{t33:.0f})', f'Mid ({t33:.0f}\u2013{t67:.0f})', f'High (>{t67:.0f})'])

fig, ax = plt.subplots(figsize=(6, 5))
colors = [PALETTE[0], PALETTE[2], PALETTE[3]]
kmfs = []

for i, (tert, color) in enumerate(zip(df['scopa_tert'].cat.categories, colors)):
    sub = df[df['scopa_tert'] == tert]
    kmf = KaplanMeierFitter()
    kmf.fit(sub['time_to_event'], sub['event'], label=f'{tert} (n={len(sub)})')
    kmf.plot_survival_function(ax=ax, color=color, linewidth=1.5, ci_alpha=0.12)
    kmfs.append(kmf)

# Log-rank: low vs high
low = df[df['scopa_tert'] == df['scopa_tert'].cat.categories[0]]
high = df[df['scopa_tert'] == df['scopa_tert'].cat.categories[2]]
lr = logrank_test(low['time_to_event'], high['time_to_event'], low['event'], high['event'])

ax.text(0.95, 0.05, f'Log-rank p {"<0.001" if lr.p_value<0.001 else f"= {lr.p_value:.3f}"}',
        transform=ax.transAxes, fontsize=8, ha='right', va='bottom',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.8))

ax.set_xlabel('Years from baseline', fontsize=9)
ax.set_ylabel('Probability of cognitive milestone-free survival', fontsize=9)
ax.set_xlim(0, 10)
ax.set_ylim(0, 1.05)
ax.legend(fontsize=7.5, loc='lower left', frameon=True)

from lifelines.plotting import add_at_risk_counts
add_at_risk_counts(*kmfs, ax=ax, fontsize=6)

plt.tight_layout()
for fmt in ['png','pdf']:
    fig.savefig(f"{BASE}/figures/figure3_km_tertiles.{fmt}", dpi=300, bbox_inches='tight')
plt.close()
print("  Done")

# ══════════════════════════════════════════════════════════════════════════
# FIGURE 4: Domain-level forest plot (adjusted Cox)
# ══════════════════════════════════════════════════════════════════════════
print("Figure 4: Domain-level forest plot...")
dom = pd.read_csv(f"{BASE}/tables/cox_domain_adjusted.csv")

fig, ax = plt.subplots(figsize=(6, 3.5))
y_d = np.arange(len(dom))
for i, (_, r) in enumerate(dom.iterrows()):
    color = DOMAIN_COLORS.get(r['Label'], 'gray')
    ax.errorbar(r['HR_adj'], i, xerr=[[r['HR_adj']-r['CI_low']], [r['CI_high']-r['HR_adj']]],
                fmt='s', color=color, markersize=7, capsize=4, linewidth=1.5)
    ci_str = f"{r['HR_adj']:.2f} ({r['CI_low']:.2f}\u2013{r['CI_high']:.2f})"
    p_str = f"{r['p_value']:.3f}" if r['p_value'] >= 0.001 else "<0.001"
    ax.text(max(dom['CI_high'])+0.08, i, f"{ci_str}  p={p_str}", fontsize=7, va='center')

ax.axvline(x=1.0, color='gray', linestyle='--', linewidth=0.8)
ax.set_yticks(y_d)
ax.set_yticklabels(dom['Label'].values, fontsize=8)
ax.set_xlabel('Adjusted Hazard Ratio (95% CI)', fontsize=9)
ax.invert_yaxis()
ax.set_xlim(0.7, max(dom['CI_high'])+0.7)

plt.tight_layout()
for fmt in ['png','pdf']:
    fig.savefig(f"{BASE}/figures/figure4_domain_forest.{fmt}", dpi=300, bbox_inches='tight')
plt.close()
print("  Done")

# ══════════════════════════════════════════════════════════════════════════
# FIGURE 5: Sensitivity heatmap
# ══════════════════════════════════════════════════════════════════════════
print("Figure 5: Sensitivity heatmap...")

primary = pd.read_csv(f"{BASE}/tables/cox_adjusted.csv")
sens_4y = pd.read_csv(f"{BASE}/tables/sensitivity_4y_cox.csv")

# Try to load individual milestone files
import os
sens_files = {
    'Primary\n(dom3, 2y)': (primary, 'HR_adj', 'p_value_adj'),
    '4-year\ncutoff': (sens_4y, 'HR', 'p_value'),
}
for m in ['m10', 'm14', 'm15']:
    fpath = f"{BASE}/tables/sensitivity_{m}_cox.csv"
    if os.path.exists(fpath):
        d = pd.read_csv(fpath)
        labels_map = {'m10': 'MoCA\n<21', 'm14': 'Investigator\ndementia', 'm15': 'PD-\nDementia'}
        sens_files[labels_map[m]] = (d, 'HR', 'p_value')

items_all = [f'SCAU{i}' for i in range(1,26)]
analyses = list(sens_files.keys())

matrix = np.full((len(items_all), len(analyses)), np.nan)
pvals_matrix = np.full((len(items_all), len(analyses)), np.nan)

for j, (name, (d, hr_col, p_col)) in enumerate(sens_files.items()):
    for i, item in enumerate(items_all):
        row = d[d['Item'] == item]
        if len(row) > 0:
            matrix[i, j] = np.log(row[hr_col].values[0])
            pvals_matrix[i, j] = row[p_col].values[0]

fig, ax = plt.subplots(figsize=(6, 8))
vmax = min(max(abs(np.nanmin(matrix)), abs(np.nanmax(matrix))), 1.0)
im = ax.imshow(matrix, cmap='RdBu_r', vmin=-vmax, vmax=vmax, aspect='auto')

for i in range(len(items_all)):
    for j in range(len(analyses)):
        if not np.isnan(pvals_matrix[i,j]):
            if pvals_matrix[i,j] < 0.001: marker = '***'
            elif pvals_matrix[i,j] < 0.01: marker = '**'
            elif pvals_matrix[i,j] < 0.05: marker = '*'
            else: marker = ''
            if marker:
                ax.text(j, i, marker, ha='center', va='center', fontsize=8, fontweight='bold')

ax.set_xticks(range(len(analyses)))
ax.set_xticklabels(analyses, fontsize=7.5)
ax.set_yticks(range(len(items_all)))
ax.set_yticklabels([f"{it} {ITEM_LABELS.get(it,'')}" for it in items_all], fontsize=7)

domain_breaks = [7, 13, 16, 21, 22]
for db in domain_breaks:
    ax.axhline(y=db-0.5, color='black', linewidth=0.5)

cbar = plt.colorbar(im, ax=ax, shrink=0.6, label='log(aHR)')
cbar.ax.tick_params(labelsize=7)

plt.tight_layout()
for fmt in ['png','pdf']:
    fig.savefig(f"{BASE}/figures/figure5_sensitivity_heatmap.{fmt}", dpi=300, bbox_inches='tight')
plt.close()
print("  Done")

print("\n=== ALL FIGURES GENERATED ===")
