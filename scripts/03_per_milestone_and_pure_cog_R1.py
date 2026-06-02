#!/usr/bin/env python3
"""
03_per_milestone_and_pure_cog_R1.py — item-level Cox for each milestone
(m10–m15 separately) and the pure-cognitive sub-composite (m10+m14+m15).
Uses Model B (R1 expanded adjustment).
"""
import os, json, warnings
import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from statsmodels.stats.multitest import multipletests

warnings.filterwarnings("ignore")
SEED = 42
np.random.seed(SEED)

PROJ = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/1b-papers/SCOPA_Cognition_Study/revision_R1"
df = pd.read_csv(f"{PROJ}/data/analytical_dataset_R1.csv", low_memory=False)
df["LEDD_TOTAL_CURRENT"] = df["LEDD_TOTAL_CURRENT"].fillna(0)

ITEMS = [f"SCAU{i}" for i in range(1, 26)]
ITEM_LABELS = {
    "SCAU1":"Swallowing/choking","SCAU2":"Drooling","SCAU3":"Dysphagia",
    "SCAU4":"Early satiety","SCAU5":"Constipation","SCAU6":"Straining",
    "SCAU7":"Fecal incontinence","SCAU8":"Urgency","SCAU9":"Frequency",
    "SCAU10":"Nocturia","SCAU11":"Incontinence","SCAU12":"Incomplete emptying",
    "SCAU13":"Weak stream","SCAU14":"Lightheadedness standing",
    "SCAU15":"Lightheadedness walking","SCAU16":"Fainting",
    "SCAU17":"Excessive sweating day","SCAU18":"Excessive sweating night",
    "SCAU19":"Heat intolerance","SCAU20":"Cold intolerance",
    "SCAU21":"Color change hands/feet","SCAU22":"Oversensitive to light",
    "SCAU23":"Sexual dysfunction 1","SCAU24":"Sexual dysfunction 2",
    "SCAU25":"Sexual dysfunction 3",
}
COVARS_B = ["AGE_AT_VISIT","SEX","EDUCYRS","MCATOT","NP3TOT_BEST",
            "LEDD_TOTAL_CURRENT","MSEADLG","RBDSQ_TOTAL",
            "disease_duration_yrs","bl_alpha_blocker",
            "bl_antihypertensive","NHY_BEST"]

# For per-milestone time-to-event, the master has only the composite dom3 time.
# We use composite time for each milestone outcome: this gives time-to-first-of-dom3
# but the indicator is whether that subject ever reached the SPECIFIC milestone.
# This is the same approach as the original paper's Table 4 sensitivity.
def run_for_outcome(outcome_col, outcome_label):
    rows = []
    for item in ITEMS:
        cols = [item, "time_to_event", outcome_col] + COVARS_B
        sub = df[cols].dropna()
        if len(sub) < 100 or sub[outcome_col].sum() < 15:
            rows.append({"Item": item, "Label": ITEM_LABELS[item],
                         "Outcome": outcome_label,
                         "N": len(sub), "Events": int(sub[outcome_col].sum()),
                         "HR": np.nan, "CI_low": np.nan, "CI_high": np.nan,
                         "p": np.nan})
            continue
        try:
            cph = CoxPHFitter()
            cph.fit(sub.rename(columns={outcome_col: "event"}),
                    duration_col="time_to_event", event_col="event")
            hr = float(np.exp(cph.params_[item]))
            lo = float(np.exp(cph.confidence_intervals_.loc[item].iloc[0]))
            hi = float(np.exp(cph.confidence_intervals_.loc[item].iloc[1]))
            pv = float(cph.summary.loc[item, "p"])
            rows.append({"Item": item, "Label": ITEM_LABELS[item],
                         "Outcome": outcome_label,
                         "N": len(sub), "Events": int(sub[outcome_col].sum()),
                         "HR": hr, "CI_low": lo, "CI_high": hi, "p": pv})
        except Exception as e:
            rows.append({"Item": item, "Label": ITEM_LABELS[item],
                         "Outcome": outcome_label,
                         "N": len(sub), "Events": int(sub[outcome_col].sum()),
                         "HR": np.nan, "CI_low": np.nan, "CI_high": np.nan,
                         "p": np.nan})
    df_out = pd.DataFrame(rows)
    valid = df_out.dropna(subset=["p"])
    if len(valid):
        _, fdr, _, _ = multipletests(valid["p"], method="fdr_bh")
        df_out["p_fdr"] = np.nan
        df_out.loc[valid.index, "p_fdr"] = fdr
    return df_out

all_out = {}
print("=" * 70)
print("Per-milestone item-level Cox (Model B) — for transparency")
print("=" * 70)
for m in [10, 11, 12, 13, 14, 15]:
    print(f"\n— m{m} (events = {int(df[f'event_m{m}'].sum())}) —")
    o = run_for_outcome(f"event_m{m}", f"m{m}")
    o.to_csv(f"{PROJ}/tables/cox_R1_per_milestone_m{m}.csv", index=False)
    all_out[f"m{m}"] = o
    sig = o[o.p_fdr < 0.05][["Item", "Label", "HR", "CI_low", "CI_high", "p_fdr"]]
    if len(sig):
        print(sig.to_string(index=False, float_format="%.3f"))
    else:
        print("  (no items FDR-significant)")

# Pure-cognitive composite (R#2's preferred narrower endpoint)
print(f"\n— pure_cognitive (m10+m14+m15, events = {int(df.event_pure_cognitive.sum())}) —")
pc = run_for_outcome("event_pure_cognitive", "pure_cognitive")
pc.to_csv(f"{PROJ}/tables/cox_R1_pure_cognitive.csv", index=False)
all_out["pure_cognitive"] = pc
sig = pc[pc.p_fdr < 0.05][["Item", "Label", "HR", "CI_low", "CI_high", "p_fdr"]]
print(sig.to_string(index=False, float_format="%.3f") if len(sig) else "  (no items FDR-significant)")

# Pure-neuropsychiatric (m12+m13)
df["event_pure_neuropsych"] = ((df.event_m12 == 1) | (df.event_m13 == 1)).astype(int)
print(f"\n— pure_neuropsych (m12+m13, events = {int(df.event_pure_neuropsych.sum())}) —")
np2 = run_for_outcome("event_pure_neuropsych", "pure_neuropsych")
np2.to_csv(f"{PROJ}/tables/cox_R1_pure_neuropsych.csv", index=False)
all_out["pure_neuropsych"] = np2
sig = np2[np2.p_fdr < 0.05][["Item", "Label", "HR", "CI_low", "CI_high", "p_fdr"]]
print(sig.to_string(index=False, float_format="%.3f") if len(sig) else "  (no items FDR-significant)")

# Combined wide-format master
master_long = pd.concat(all_out.values(), ignore_index=True)
master_long.to_csv(f"{PROJ}/tables/cox_R1_per_milestone_master.csv", index=False)

# Heatmap-friendly wide format: rows=items, cols=outcomes, cells=HR
hr_wide = master_long.pivot(index="Item", columns="Outcome", values="HR")
p_wide  = master_long.pivot(index="Item", columns="Outcome", values="p_fdr")
hr_wide.to_csv(f"{PROJ}/tables/cox_R1_heatmap_HR.csv")
p_wide.to_csv(f"{PROJ}/tables/cox_R1_heatmap_p_fdr.csv")

# Summary
summary = {}
for k, v in all_out.items():
    sig = v.dropna(subset=["p_fdr"])
    summary[k] = {
        "events": int(df[f"event_{k}"].sum()) if f"event_{k}" in df.columns else int(v["Events"].max()),
        "fdr_sig": sig[sig.p_fdr < 0.05]["Item"].tolist(),
    }
with open(f"{PROJ}/logs/per_milestone_R1_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print("\n=== PER-MILESTONE + PURE-COG ANALYSIS COMPLETE ===")
for k, v in summary.items():
    print(f"  {k}: {v['events']} events  FDR-sig items: {v['fdr_sig']}")
