#!/usr/bin/env python3
"""
02_primary_analysis.py — Primary analysis: SCOPA-AUT items predicting cognitive milestones
Cox PH (primary) + logistic regression
"""
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.statistics import logrank_test
import warnings
warnings.filterwarnings('ignore')

SEED = 42
np.random.seed(SEED)

BASE = "."
df = pd.read_csv(f"{BASE}/data/analytical_dataset.csv")
EXPECTED_N = 960
assert len(df) == EXPECTED_N

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

DOMAIN_LABELS = {
    'SCAU_GI': 'Gastrointestinal', 'SCAU_URI': 'Urinary',
    'SCAU_CV': 'Cardiovascular', 'SCAU_THERM': 'Thermoregulatory',
    'SCAU_PUPIL': 'Pupillomotor', 'SCAU_SEX': 'Sexual'
}

# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 1: Cox PH — item-level (PRIMARY)
# ══════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("ANALYSIS 1: Cox PH — item-level (univariable)")
print("=" * 70)

results_cox_uni = []
for item in SCOPA_ITEMS:
    cols = [item, 'time_to_event', 'event']
    sub = df[cols].dropna()
    if len(sub) < 50 or sub['event'].sum() < 10:
        continue
    try:
        cph = CoxPHFitter()
        cph.fit(sub, duration_col='time_to_event', event_col='event')
        hr = np.exp(cph.params_[item])
        ci = np.exp(cph.confidence_intervals_.loc[item])
        results_cox_uni.append({
            'Item': item, 'Label': ITEM_LABELS.get(item, item),
            'N': len(sub), 'Events': int(sub['event'].sum()),
            'HR': hr, 'CI_low': ci.iloc[0], 'CI_high': ci.iloc[1],
            'p_value': cph.summary['p'][item]
        })
    except Exception as e:
        print(f"  {item}: {e}")

cox_uni = pd.DataFrame(results_cox_uni)
if len(cox_uni) > 0:
    _, cox_uni['p_fdr'], _, _ = multipletests(cox_uni['p_value'], method='fdr_bh')

print("\nCox univariable:")
for _, r in cox_uni.iterrows():
    sig = "*" if r['p_fdr'] < 0.05 else ""
    print(f"  {r['Item']:8s} {r['Label']:30s} HR={r['HR']:.2f} ({r['CI_low']:.2f}\u2013{r['CI_high']:.2f}) "
          f"p={r['p_value']:.3f} FDR={r['p_fdr']:.3f} {sig}")

# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 2: Cox PH — item-level (adjusted)
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 2: Cox PH — item-level (adjusted)")
print("=" * 70)

results_cox_adj = []
for item in SCOPA_ITEMS:
    cols = [item, 'time_to_event', 'event'] + COVARIATES
    sub = df[cols].dropna()
    if len(sub) < 50 or sub['event'].sum() < 10:
        continue
    try:
        cph = CoxPHFitter()
        cph.fit(sub, duration_col='time_to_event', event_col='event')
        hr = np.exp(cph.params_[item])
        ci = np.exp(cph.confidence_intervals_.loc[item])
        results_cox_adj.append({
            'Item': item, 'Label': ITEM_LABELS.get(item, item),
            'N': len(sub), 'Events': int(sub['event'].sum()),
            'HR_adj': hr, 'CI_low_adj': ci.iloc[0], 'CI_high_adj': ci.iloc[1],
            'p_value_adj': cph.summary['p'][item]
        })
    except Exception as e:
        print(f"  {item}: {e}")

cox_adj = pd.DataFrame(results_cox_adj)
if len(cox_adj) > 0:
    _, cox_adj['p_fdr_adj'], _, _ = multipletests(cox_adj['p_value_adj'], method='fdr_bh')

print("\nCox adjusted:")
for _, r in cox_adj.iterrows():
    sig = "*" if r['p_fdr_adj'] < 0.05 else ""
    print(f"  {r['Item']:8s} {r['Label']:30s} aHR={r['HR_adj']:.2f} ({r['CI_low_adj']:.2f}\u2013{r['CI_high_adj']:.2f}) "
          f"p={r['p_value_adj']:.3f} FDR={r['p_fdr_adj']:.3f} {sig}")

# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 3: Logistic regression (item-level)
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 3: Logistic regression — item-level")
print("=" * 70)

results_log_uni = []
results_log_adj = []

for item in SCOPA_ITEMS:
    # Univariable
    subset = df[[item, 'event']].dropna()
    if len(subset) < 50:
        continue
    try:
        X = sm.add_constant(subset[item])
        model = sm.Logit(subset['event'], X).fit(disp=0)
        results_log_uni.append({
            'Item': item, 'Label': ITEM_LABELS.get(item, item),
            'N': len(subset),
            'OR': np.exp(model.params[item]),
            'CI_low': np.exp(model.conf_int().loc[item, 0]),
            'CI_high': np.exp(model.conf_int().loc[item, 1]),
            'p_value': model.pvalues[item]
        })
    except:
        pass

    # Adjusted
    cols = [item, 'event'] + COVARIATES
    subset2 = df[cols].dropna()
    if len(subset2) < 50:
        continue
    try:
        X2 = sm.add_constant(subset2[[item] + COVARIATES])
        model2 = sm.Logit(subset2['event'], X2).fit(disp=0)
        results_log_adj.append({
            'Item': item, 'Label': ITEM_LABELS.get(item, item),
            'N': len(subset2),
            'OR_adj': np.exp(model2.params[item]),
            'CI_low_adj': np.exp(model2.conf_int().loc[item, 0]),
            'CI_high_adj': np.exp(model2.conf_int().loc[item, 1]),
            'p_value_adj': model2.pvalues[item]
        })
    except:
        pass

log_uni = pd.DataFrame(results_log_uni)
log_adj = pd.DataFrame(results_log_adj)
if len(log_uni) > 0:
    _, log_uni['p_fdr'], _, _ = multipletests(log_uni['p_value'], method='fdr_bh')
if len(log_adj) > 0:
    _, log_adj['p_fdr_adj'], _, _ = multipletests(log_adj['p_value_adj'], method='fdr_bh')

print("\nLogistic adjusted:")
for _, r in log_adj.iterrows():
    sig = "*" if r['p_fdr_adj'] < 0.05 else ""
    print(f"  {r['Item']:8s} {r['Label']:30s} aOR={r['OR_adj']:.2f} ({r['CI_low_adj']:.2f}\u2013{r['CI_high_adj']:.2f}) "
          f"p={r['p_value_adj']:.3f} FDR={r['p_fdr_adj']:.3f} {sig}")

# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 4: Domain-level Cox
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 4: Domain-level Cox PH (adjusted)")
print("=" * 70)

results_dom = []
for domain in list(DOMAIN_LABELS.keys()) + ['SCAU_TOTAL']:
    label = DOMAIN_LABELS.get(domain, 'SCOPA-AUT Total')
    cols = [domain, 'time_to_event', 'event'] + COVARIATES
    sub = df[cols].dropna()
    if len(sub) < 50 or sub['event'].sum() < 10:
        continue
    try:
        cph = CoxPHFitter()
        cph.fit(sub, duration_col='time_to_event', event_col='event')
        hr = np.exp(cph.params_[domain])
        ci = np.exp(cph.confidence_intervals_.loc[domain])
        results_dom.append({
            'Domain': domain, 'Label': label,
            'N': len(sub), 'Events': int(sub['event'].sum()),
            'HR_adj': hr, 'CI_low': ci.iloc[0], 'CI_high': ci.iloc[1],
            'p_value': cph.summary['p'][domain]
        })
    except Exception as e:
        print(f"  {domain}: {e}")

dom_df = pd.DataFrame(results_dom)
print("\nDomain-level Cox (adjusted):")
for _, r in dom_df.iterrows():
    print(f"  {r['Label']:25s} aHR={r['HR_adj']:.2f} ({r['CI_low']:.2f}\u2013{r['CI_high']:.2f}) p={r['p_value']:.3f}")

# ══════════════════════════════════════════════════════════════════════════
# SAVE
# ══════════════════════════════════════════════════════════════════════════
cox_uni.to_csv(f"{BASE}/tables/cox_univariable.csv", index=False)
cox_adj.to_csv(f"{BASE}/tables/cox_adjusted.csv", index=False)
log_uni.to_csv(f"{BASE}/tables/logistic_univariable.csv", index=False)
log_adj.to_csv(f"{BASE}/tables/logistic_adjusted.csv", index=False)
dom_df.to_csv(f"{BASE}/tables/cox_domain_adjusted.csv", index=False)

print("\n=== PRIMARY ANALYSIS COMPLETE ===")
