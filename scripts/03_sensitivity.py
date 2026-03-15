#!/usr/bin/env python3
"""
03_sensitivity.py — Sensitivity analyses:
  1. 4-year minimum follow-up
  2. Individual milestones (m10=MoCA<21, m14=dementia, m15=PDD)
  3. Completers vs dropout comparison
  4. SCOPA-AUT total tertiles Cox
"""
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from lifelines import CoxPHFitter
import warnings
warnings.filterwarnings('ignore')

SEED = 42
np.random.seed(SEED)

BASE = "."
SCOPA_ITEMS = [f'SCAU{i}' for i in range(1, 26)]
COVARIATES = ['AGE_AT_VISIT', 'SEX', 'EDUCYRS', 'MCATOT', 'NP3TOT_BEST']
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

def run_cox_items(data, items, covariates, event_col='event', time_col='time_to_event'):
    results = []
    for item in items:
        cols = [item, time_col, event_col] + covariates
        sub = data[cols].dropna()
        if len(sub) < 50 or sub[event_col].sum() < 10:
            continue
        try:
            cph = CoxPHFitter()
            cph.fit(sub, duration_col=time_col, event_col=event_col)
            hr = np.exp(cph.params_[item])
            ci = np.exp(cph.confidence_intervals_.loc[item])
            results.append({
                'Item': item, 'Label': ITEM_LABELS.get(item, item),
                'N': len(sub), 'Events': int(sub[event_col].sum()),
                'HR': hr, 'CI_low': ci.iloc[0], 'CI_high': ci.iloc[1],
                'p_value': cph.summary['p'][item]
            })
        except:
            pass
    rdf = pd.DataFrame(results)
    if len(rdf) > 0:
        _, rdf['p_fdr'], _, _ = multipletests(rdf['p_value'], method='fdr_bh')
    return rdf

# ══════════════════════════════════════════════════════════════════════════
# SENSITIVITY 1: 4-year minimum follow-up
# ══════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("SENSITIVITY 1: 4-year minimum follow-up")
print("=" * 70)

df4 = pd.read_csv(f"{BASE}/data/analytical_dataset_4y.csv")
print(f"N={len(df4)}, Events: {df4['event'].sum()} ({100*df4['event'].mean():.1f}%)")

s1 = run_cox_items(df4, SCOPA_ITEMS, COVARIATES)
s1.to_csv(f"{BASE}/tables/sensitivity_4y_cox.csv", index=False)

print("\n4-year Cox (adjusted):")
for _, r in s1.iterrows():
    sig = "*" if r['p_fdr'] < 0.05 else ""
    print(f"  {r['Item']:8s} {r['Label']:30s} aHR={r['HR']:.2f} ({r['CI_low']:.2f}\u2013{r['CI_high']:.2f}) "
          f"p={r['p_value']:.3f} FDR={r['p_fdr']:.3f} {sig}")

# ══════════════════════════════════════════════════════════════════════════
# SENSITIVITY 2: Individual cognitive milestones
# ══════════════════════════════════════════════════════════════════════════
df = pd.read_csv(f"{BASE}/data/analytical_dataset.csv")
EXPECTED_N = 960
assert len(df) == EXPECTED_N

milestone_defs = {
    'm10': 'MoCA < 21',
    'm14': 'Investigator-diagnosed dementia',
    'm15': 'PD-Dementia (MDS criteria)',
}

for m, desc in milestone_defs.items():
    print(f"\n{'=' * 70}")
    print(f"SENSITIVITY 2{m}: Individual milestone {m} ({desc})")
    print(f"{'=' * 70}")

    event_col = f'event_{m}'
    n_events = df[event_col].sum()
    print(f"N={len(df)}, Events: {n_events} ({100*n_events/len(df):.1f}%)")

    if n_events < 20:
        print("  Too few events for item-level Cox. Skipping.")
        continue

    sm_res = run_cox_items(df, SCOPA_ITEMS, COVARIATES, event_col=event_col)
    sm_res.to_csv(f"{BASE}/tables/sensitivity_{m}_cox.csv", index=False)

    print(f"\n{m} Cox (adjusted):")
    for _, r in sm_res.iterrows():
        sig = "*" if r['p_fdr'] < 0.05 else ""
        print(f"  {r['Item']:8s} {r['Label']:30s} aHR={r['HR']:.2f} ({r['CI_low']:.2f}\u2013{r['CI_high']:.2f}) "
              f"p={r['p_value']:.3f} FDR={r['p_fdr']:.3f} {sig}")

# ══════════════════════════════════════════════════════════════════════════
# SENSITIVITY 3: Completers vs dropouts
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 70}")
print("SENSITIVITY 3: Completers vs Dropouts (attrition bias)")
print("=" * 70)

master = pd.read_csv("../PPMI_Master_Merged.csv",
                     usecols=['PATNO','EVENT_ID','COHORT','MCATOT','AGE_AT_VISIT','SEX','EDUCYRS',
                              'SCAU_TOTAL','NP3TOT_BEST','NHY_BEST','MSEADLG','RBDSQ_TOTAL'], low_memory=False)
pd_bl = master[(master['COHORT']==1) & (master['EVENT_ID']=='BL') & (master['SCAU_TOTAL'].notna())].copy()
included = set(df['PATNO'].unique())
pd_bl['included'] = pd_bl['PATNO'].isin(included).astype(int)

print(f"Total PD with BL SCOPA-AUT: {len(pd_bl)}")
print(f"Included: {pd_bl['included'].sum()}, Excluded: {(~pd_bl['included'].astype(bool)).sum()}")

compare_vars = ['AGE_AT_VISIT','SEX','EDUCYRS','MCATOT','SCAU_TOTAL','NP3TOT_BEST','RBDSQ_TOTAL','MSEADLG']
print(f"\n{'Variable':25s} {'Included':>20s} {'Excluded':>20s} {'p':>8s}")
print("-" * 78)

for var in compare_vars:
    inc = pd_bl.loc[pd_bl['included']==1, var].dropna()
    exc = pd_bl.loc[pd_bl['included']==0, var].dropna()
    if len(inc) > 5 and len(exc) > 5:
        _, pval = stats.mannwhitneyu(inc, exc, alternative='two-sided')
        inc_str = f"{inc.median():.1f} ({inc.quantile(0.25):.1f}\u2013{inc.quantile(0.75):.1f})"
        exc_str = f"{exc.median():.1f} ({exc.quantile(0.25):.1f}\u2013{exc.quantile(0.75):.1f})"
        print(f"{var:25s} {inc_str:>20s} {exc_str:>20s} {pval:>8.3f}")

print("\n=== SENSITIVITY ANALYSES COMPLETE ===")
