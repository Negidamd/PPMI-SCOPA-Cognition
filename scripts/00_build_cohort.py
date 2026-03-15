#!/usr/bin/env python3
"""
00_build_cohort.py — Build analytical cohort for SCOPA-AUT × Cognitive Milestones study
Outcome: PPMI cognitive domain milestones (dom3: m10-m15)
    m10: MoCA < 21
    m11: NP1COG > 3 (UPDRS-I cognitive impairment)
    m12: NP1HALL > 3 (hallucinations)
    m13: NP1APAT > 3 (apathy)
    m14: COGSTATE = 3 (investigator-diagnosed dementia)
    m15: Cognitive_Group = 3 (PD-Dementia per MDS criteria)
"""

import pandas as pd
import numpy as np
import os, json, warnings
warnings.filterwarnings('ignore')

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/3-resources/datasets/PPMI"
MASTER = os.path.join(BASE, "PPMI_Master_Merged.csv")
OUT    = os.path.join(BASE, "SCOPA_Cognition_Study", "data")
LOGS   = os.path.join(BASE, "SCOPA_Cognition_Study", "logs")
os.makedirs(OUT, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)

SEED = 42
np.random.seed(SEED)

# ── 1. Load master dataset ─────────────────────────────────────────────────
print("Loading PPMI Master Merged...")
df = pd.read_csv(MASTER, low_memory=False)
print(f"  Master: {df.shape[0]} rows, {df.shape[1]} cols, {df['PATNO'].nunique()} subjects")

# ── 2. Define SCOPA-AUT items and domains ──────────────────────────────────
SCOPA_ITEMS = [f'SCAU{i}' for i in range(1, 26)]
SCOPA_DOMAINS = {
    'SCAU_GI':    [f'SCAU{i}' for i in range(1, 8)],
    'SCAU_URI':   [f'SCAU{i}' for i in range(8, 14)],
    'SCAU_CV':    [f'SCAU{i}' for i in range(14, 17)],
    'SCAU_THERM': [f'SCAU{i}' for i in range(17, 22)],
    'SCAU_PUPIL': ['SCAU22'],
    'SCAU_SEX':   ['SCAU23', 'SCAU24', 'SCAU25'],
}

# Milestone columns
MILESTONE_COLS = ['reached_dom3', 'time_to_event_dom3_years', 'first_dom3',
                  'm10', 'm11', 'm12', 'm13', 'm14', 'm15',
                  'm10everreached', 'm11everreached', 'm12everreached',
                  'm13everreached', 'm14everreached', 'm15everreached',
                  'Cognitive_Group']

# Covariates
COVAR_COLS = ['AGE_AT_VISIT', 'SEX', 'EDUCYRS', 'MCATOT', 'NP3TOT_BEST', 'NHY_BEST',
              'MSEADLG', 'LEDD_TOTAL_CURRENT', 'APPRDX', 'COHORT',
              'COHORT_DEFINITION', 'ENROLL_DATE',
              'RBDSQ_TOTAL', 'UPSIT_PRCNTGE',
              'HISPLAT', 'RAWHITE', 'RABLACK', 'RAASIAN',
              'SCAU_TOTAL']

# ── 3. EXCLUSION CASCADE ──────────────────────────────────────────────────
log = []
def log_step(step, reason, n_subj_before, n_subj_after):
    excluded = n_subj_before - n_subj_after
    log.append({'step': step, 'reason': reason,
                'subjects_before': n_subj_before, 'subjects_after': n_subj_after,
                'subjects_excluded': excluded})
    print(f"  Step {step}: {reason}")
    print(f"    {n_subj_before} → {n_subj_after} subjects (excluded {excluded})")

# Work with BL only for subject-level filtering
bl_all = df[df['EVENT_ID'] == 'BL'].copy()
N0 = bl_all['PATNO'].nunique()
print(f"\nStarting exclusion cascade: {N0} subjects at BL")

# Step 1: Restrict to PD cohort
n_before = bl_all['PATNO'].nunique()
bl = bl_all[bl_all['COHORT'] == 1].copy()
log_step(1, "Restrict to PD cohort (COHORT=1)", n_before, bl['PATNO'].nunique())

# Step 2: Require baseline SCOPA-AUT total score
n_before = bl['PATNO'].nunique()
bl = bl[bl['SCAU_TOTAL'].notna()].copy()
log_step(2, "Require baseline SCOPA-AUT total score", n_before, bl['PATNO'].nunique())

# Step 3: Require baseline MoCA
n_before = bl['PATNO'].nunique()
bl = bl[bl['MCATOT'].notna()].copy()
log_step(3, "Require baseline MoCA", n_before, bl['PATNO'].nunique())

# Step 4: Require milestone data (time_to_event_dom3_years available)
n_before = bl['PATNO'].nunique()
bl = bl[bl['time_to_event_dom3_years'].notna()].copy()
log_step(4, "Require cognitive milestone data", n_before, bl['PATNO'].nunique())

# Step 5: Exclude baseline dementia (Cognitive_Group = 3)
n_before = bl['PATNO'].nunique()
bl = bl[bl['Cognitive_Group'] != 3].copy()
log_step(5, "Exclude baseline PD-Dementia (Cognitive_Group=3)", n_before, bl['PATNO'].nunique())

# Step 6: Require minimum 2-year follow-up or event before 2 years
# For survival analysis: include all subjects. Those with events before 2 years still count.
# But we want adequate follow-up for censored subjects.
# Keep subjects who: (a) reached milestone at any time, OR (b) censored at ≥2 years
n_before = bl['PATNO'].nunique()
bl = bl[(bl['reached_dom3'] == 1) | (bl['time_to_event_dom3_years'] >= 2)].copy()
log_step(6, "Require event or ≥2 years follow-up (censored)", n_before, bl['PATNO'].nunique())

print(f"\nFinal analytical cohort: {bl['PATNO'].nunique()} subjects")

# ── 4. Compute derived variables ──────────────────────────────────────────
# Domain subscores at baseline
for domain, items in SCOPA_DOMAINS.items():
    avail = [c for c in items if c in bl.columns]
    bl[domain] = bl[avail].sum(axis=1, min_count=max(1, len(avail)-1))

# Race
bl['RACE'] = 'Other'
bl.loc[bl['RAWHITE'] == 1, 'RACE'] = 'White'
bl.loc[bl['RABLACK'] == 1, 'RACE'] = 'Black'
bl.loc[bl['RAASIAN'] == 1, 'RACE'] = 'Asian'

# Sex label
bl['SEX_LABEL'] = bl['SEX'].map({0: 'Female', 1: 'Male'})

# H&Y stage categories
bl['HY_STAGE'] = pd.cut(bl['NHY_BEST'], bins=[-0.1, 1.5, 2.5, 5],
                         labels=['1-1.5', '2-2.5', '3+'])

# Rename outcome columns for clarity
bl['event'] = bl['reached_dom3'].astype(int)
bl['time_to_event'] = bl['time_to_event_dom3_years']

# Also create individual milestone outcomes
for m in [10, 11, 12, 13, 14, 15]:
    bl[f'event_m{m}'] = bl[f'm{m}everreached'].fillna(0).astype(int)

N = len(bl)
n_events = bl['event'].sum()
print(f"\nOutcome (cognitive milestone dom3):")
print(f"  Events: {n_events} / {N} ({100*n_events/N:.1f}%)")
print(f"  Median time to event: {bl.loc[bl['event']==1, 'time_to_event'].median():.1f} years")
print(f"  Median censoring time: {bl.loc[bl['event']==0, 'time_to_event'].median():.1f} years")
print(f"\nIndividual milestones ever reached:")
for m in [10, 11, 12, 13, 14, 15]:
    n = bl[f'event_m{m}'].sum()
    print(f"  m{m}: {n} ({100*n/N:.1f}%)")

# ── 5. Save ────────────────────────────────────────────────────────────────
analytical = bl.copy()
analytical.to_csv(os.path.join(OUT, 'analytical_dataset.csv'), index=False)
print(f"\nSaved: analytical_dataset.csv ({len(analytical)} subjects, {analytical.shape[1]} cols)")

# 4-year sensitivity cohort
bl_4y = bl[(bl['event'] == 1) | (bl['time_to_event'] >= 4)].copy()
bl_4y.to_csv(os.path.join(OUT, 'analytical_dataset_4y.csv'), index=False)
print(f"Saved: analytical_dataset_4y.csv ({len(bl_4y)} subjects, {bl_4y['event'].sum()} events)")

# Exclusion log
log_df = pd.DataFrame(log)
log_df.to_csv(os.path.join(LOGS, 'exclusion_log.csv'), index=False)

with open(os.path.join(LOGS, 'exclusion_log.md'), 'w') as f:
    f.write("# Exclusion Cascade\n\n")
    f.write(f"Data source: PPMI Master Merged\n\n")
    f.write("| Step | Criterion | Before | After | Excluded |\n")
    f.write("|------|-----------|-------:|------:|---------:|\n")
    for _, row in log_df.iterrows():
        f.write(f"| {row['step']} | {row['reason']} | {row['subjects_before']} | "
                f"{row['subjects_after']} | {row['subjects_excluded']} |\n")
    f.write(f"\n**Final: N = {N}, Events = {n_events} ({100*n_events/N:.1f}%)**\n")

# Summary
summary = {
    'N': N, 'n_events': int(n_events),
    'event_rate': float(n_events/N),
    'median_event_time': float(bl.loc[bl['event']==1, 'time_to_event'].median()),
    'median_censor_time': float(bl.loc[bl['event']==0, 'time_to_event'].median()),
    'N_4y': len(bl_4y), 'n_events_4y': int(bl_4y['event'].sum()),
    'seed': SEED
}
with open(os.path.join(OUT, 'cohort_summary.json'), 'w') as f:
    json.dump(summary, f, indent=2)

print("\n=== COHORT BUILD COMPLETE ===")
