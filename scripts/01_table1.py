#!/usr/bin/env python3
"""
01_table1.py — Table 1: Baseline characteristics by cognitive milestone status
"""
import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

BASE = "."
df = pd.read_csv(f"{BASE}/data/analytical_dataset.csv")
EXPECTED_N = 960
assert len(df) == EXPECTED_N, f"COHORT MISMATCH: {len(df)} ≠ {EXPECTED_N}"

g0 = df[df['event'] == 0]
g1 = df[df['event'] == 1]
print(f"No event: {len(g0)}, Event: {len(g1)}")

rows = []

def add_continuous(label, col, g0, g1, total):
    v0, v1, vt = g0[col].dropna(), g1[col].dropna(), total[col].dropna()
    if len(v0) < 5 or len(v1) < 5:
        return
    stat, pval = stats.mannwhitneyu(v0, v1, alternative='two-sided')
    fmt = lambda v: f"{v.median():.1f} ({v.quantile(0.25):.1f}\u2013{v.quantile(0.75):.1f})"
    n_miss = total[col].isna().sum()
    miss_str = f" [{n_miss}]" if n_miss > 0 else ""
    rows.append({
        'Variable': f"{label}{miss_str}",
        f'Total (N={EXPECTED_N})': fmt(vt),
        f'No Event (n={len(g0)})': fmt(v0),
        f'Event (n={len(g1)})': fmt(v1),
        'p-value': f"{pval:.3f}" if pval >= 0.001 else "<0.001",
    })

def add_categorical(label, col, g0, g1, total, categories=None):
    if categories is None:
        categories = sorted(total[col].dropna().unique())
    n_miss = total[col].isna().sum()
    miss_str = f" [{n_miss}]" if n_miss > 0 else ""
    ct = pd.crosstab(total[col], total['event'])
    if ct.shape[0] > 1 and ct.shape[1] > 1:
        _, pval, _, _ = stats.chi2_contingency(ct)
    else:
        pval = np.nan
    rows.append({
        'Variable': f"{label}, n (%){miss_str}",
        f'Total (N={EXPECTED_N})': '',
        f'No Event (n={len(g0)})': '',
        f'Event (n={len(g1)})': '',
        'p-value': f"{pval:.3f}" if (not np.isnan(pval) and pval >= 0.001) else ("<0.001" if not np.isnan(pval) else ""),
    })
    for cat in categories:
        n0 = (g0[col] == cat).sum()
        n1 = (g1[col] == cat).sum()
        nt = (total[col] == cat).sum()
        rows.append({
            'Variable': f"  {cat}",
            f'Total (N={EXPECTED_N})': f"{nt} ({100*nt/len(total):.1f})",
            f'No Event (n={len(g0)})': f"{n0} ({100*n0/len(g0):.1f})",
            f'Event (n={len(g1)})': f"{n1} ({100*n1/len(g1):.1f})",
            'p-value': '',
        })

# Demographics
add_continuous('Age, years', 'AGE_AT_VISIT', g0, g1, df)
df['SEX_LABEL'] = df['SEX'].map({0: 'Female', 1: 'Male'})
g0['SEX_LABEL'] = g0['SEX'].map({0: 'Female', 1: 'Male'})
g1['SEX_LABEL'] = g1['SEX'].map({0: 'Female', 1: 'Male'})
add_categorical('Sex', 'SEX_LABEL', g0, g1, df, ['Female', 'Male'])
add_continuous('Education, years', 'EDUCYRS', g0, g1, df)
add_categorical('Race', 'RACE', g0, g1, df, ['White', 'Black', 'Asian', 'Other'])

# Clinical
add_continuous('MoCA total', 'MCATOT', g0, g1, df)
add_continuous('MDS-UPDRS III (best)', 'NP3TOT_BEST', g0, g1, df)
add_continuous('Hoehn & Yahr stage', 'NHY_BEST', g0, g1, df)
add_continuous('Schwab-England ADL', 'MSEADLG', g0, g1, df)
add_continuous('LEDD, mg/day', 'LEDD_TOTAL_CURRENT', g0, g1, df)
add_continuous('UPSIT (%)', 'UPSIT_PRCNTGE', g0, g1, df)
add_continuous('RBDSQ total', 'RBDSQ_TOTAL', g0, g1, df)

# SCOPA-AUT
add_continuous('SCOPA-AUT total', 'SCAU_TOTAL', g0, g1, df)
add_continuous('  Gastrointestinal (items 1\u20137)', 'SCAU_GI', g0, g1, df)
add_continuous('  Urinary (items 8\u201313)', 'SCAU_URI', g0, g1, df)
add_continuous('  Cardiovascular (items 14\u201316)', 'SCAU_CV', g0, g1, df)
add_continuous('  Thermoregulatory (items 17\u201321)', 'SCAU_THERM', g0, g1, df)
add_continuous('  Pupillomotor (item 22)', 'SCAU_PUPIL', g0, g1, df)
add_continuous('  Sexual (items 23\u201325)', 'SCAU_SEX', g0, g1, df)

add_continuous('Follow-up / time-to-event, years', 'time_to_event', g0, g1, df)

table1 = pd.DataFrame(rows)
table1.to_csv(f"{BASE}/tables/table1.csv", index=False)
print("\nTable 1:")
print(table1.to_string(index=False))
