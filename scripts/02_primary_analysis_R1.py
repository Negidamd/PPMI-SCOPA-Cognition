#!/usr/bin/env python3
"""
02_primary_analysis_R1.py — R1 primary Cox PH analysis

For each SCOPA-AUT item (1-25):
  • Model A — original adjustment: age, sex, education, MoCA, UPDRS-III (NP3TOT_BEST)
  • Model B — expanded R1 adjustment: + LEDD, Schwab-England, RBDSQ, disease duration,
              alpha-blocker exposure, antihypertensive exposure, Hoehn-Yahr stage
  • Schoenfeld residual global PH test for Model B per item
  • Domain-level Cox (Model B)
  • SCAU_TOTAL Cox (Model B)
  • Outputs: tables/cox_R1_item_modelA.csv
            tables/cox_R1_item_modelB.csv
            tables/cox_R1_domain.csv
            tables/cox_R1_ph_test.csv
"""
import os, warnings, json
import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from lifelines.statistics import proportional_hazard_test
from statsmodels.stats.multitest import multipletests

warnings.filterwarnings("ignore")
SEED = 42
np.random.seed(SEED)

PROJ = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/1b-papers/SCOPA_Cognition_Study/revision_R1"
df = pd.read_csv(f"{PROJ}/data/analytical_dataset_R1.csv", low_memory=False)
N_EXPECTED = 1129
assert len(df) == N_EXPECTED, f"Expected N={N_EXPECTED}, got {len(df)}"
print(f"Loaded R1 dataset: N={len(df)}, composite events={int(df.event.sum())}")

# ── Item & domain labels ─────────────────────────────────────────────────
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
DOMAIN_LABELS = {
    "SCAU_GI":"Gastrointestinal","SCAU_URI":"Urinary",
    "SCAU_CV":"Cardiovascular","SCAU_THERM":"Thermoregulatory",
    "SCAU_PUPIL":"Pupillomotor","SCAU_SEX":"Sexual",
}
ITEMS = [f"SCAU{i}" for i in range(1, 26)]

COVARS_A = ["AGE_AT_VISIT", "SEX", "EDUCYRS", "MCATOT", "NP3TOT_BEST"]
COVARS_B = COVARS_A + ["LEDD_TOTAL_CURRENT", "MSEADLG", "RBDSQ_TOTAL",
                       "disease_duration_yrs", "bl_alpha_blocker",
                       "bl_antihypertensive", "NHY_BEST"]

# LEDD missingness: PPMI BL is largely treatment-naive — set NaN to 0 (not on
# dopaminergic therapy at baseline). Document in Methods.
df["LEDD_TOTAL_CURRENT"] = df["LEDD_TOTAL_CURRENT"].fillna(0)

# Helper to fit Cox safely
def fit_cox(data, item_col, covars, duration="time_to_event", event="event"):
    cols = [item_col, duration, event] + covars
    sub = data[cols].dropna()
    if len(sub) < 100 or sub[event].sum() < 20:
        return None, None
    try:
        cph = CoxPHFitter(penalizer=0.0)
        cph.fit(sub, duration_col=duration, event_col=event)
        return cph, sub
    except Exception:
        return None, None

def cox_row(cph, item):
    p = cph.summary
    hr = float(np.exp(cph.params_[item]))
    lo = float(np.exp(cph.confidence_intervals_.loc[item].iloc[0]))
    hi = float(np.exp(cph.confidence_intervals_.loc[item].iloc[1]))
    return hr, lo, hi, float(p.loc[item, "p"])

# ── ANALYSIS 1: Model A (original covariates, replication on R1 cohort) ──
print("\n" + "=" * 70)
print("ANALYSIS 1 — Cox item-level, Model A (original covariates)")
print("=" * 70)
rows_A = []
for item in ITEMS:
    cph, sub = fit_cox(df, item, COVARS_A)
    if cph is None:
        rows_A.append({"Item": item, "Label": ITEM_LABELS[item],
                       "N": np.nan, "Events": np.nan,
                       "HR": np.nan, "CI_low": np.nan, "CI_high": np.nan,
                       "p": np.nan})
        continue
    hr, lo, hi, pv = cox_row(cph, item)
    rows_A.append({"Item": item, "Label": ITEM_LABELS[item],
                   "N": len(sub), "Events": int(sub["event"].sum()),
                   "HR": hr, "CI_low": lo, "CI_high": hi, "p": pv})
A = pd.DataFrame(rows_A)
A_valid = A.dropna(subset=["p"])
_, A_fdr, _, _ = multipletests(A_valid["p"], method="fdr_bh")
A["p_fdr"] = np.nan
A.loc[A_valid.index, "p_fdr"] = A_fdr
A.to_csv(f"{PROJ}/tables/cox_R1_item_modelA.csv", index=False)
print(A[["Item","Label","N","Events","HR","CI_low","CI_high","p","p_fdr"]]
      .to_string(index=False, float_format="%.3f"))

# ── ANALYSIS 2: Model B (expanded R1 adjustment) ─────────────────────────
print("\n" + "=" * 70)
print("ANALYSIS 2 — Cox item-level, Model B (R1 expanded covariates)")
print(f"Covariates: {COVARS_B}")
print("=" * 70)
rows_B = []
ph_rows = []
for item in ITEMS:
    cph, sub = fit_cox(df, item, COVARS_B)
    if cph is None:
        rows_B.append({"Item": item, "Label": ITEM_LABELS[item],
                       "N": np.nan, "Events": np.nan,
                       "HR": np.nan, "CI_low": np.nan, "CI_high": np.nan,
                       "p": np.nan})
        continue
    hr, lo, hi, pv = cox_row(cph, item)
    rows_B.append({"Item": item, "Label": ITEM_LABELS[item],
                   "N": len(sub), "Events": int(sub["event"].sum()),
                   "HR": hr, "CI_low": lo, "CI_high": hi, "p": pv})
    # Schoenfeld PH test for the item coefficient
    try:
        ph = proportional_hazard_test(cph, sub, time_transform="rank")
        ph_p_item = float(ph.summary.loc[item, "p"]) if item in ph.summary.index else np.nan
        ph_p_global = float(ph.summary["p"].min())  # most-violated covariate
    except Exception:
        ph_p_item = ph_p_global = np.nan
    ph_rows.append({"Item": item, "Label": ITEM_LABELS[item],
                    "PH_p_item": ph_p_item, "PH_p_global_min": ph_p_global})

B = pd.DataFrame(rows_B)
B_valid = B.dropna(subset=["p"])
_, B_fdr, _, _ = multipletests(B_valid["p"], method="fdr_bh")
B["p_fdr"] = np.nan
B.loc[B_valid.index, "p_fdr"] = B_fdr
B.to_csv(f"{PROJ}/tables/cox_R1_item_modelB.csv", index=False)
print(B[["Item","Label","N","Events","HR","CI_low","CI_high","p","p_fdr"]]
      .to_string(index=False, float_format="%.3f"))

PH = pd.DataFrame(ph_rows)
PH.to_csv(f"{PROJ}/tables/cox_R1_ph_test.csv", index=False)
print("\nSchoenfeld PH test summary (rank-transformed time):")
print(PH.to_string(index=False, float_format="%.3f"))

# ── ANALYSIS 3: Domain-level Cox (Model B) ───────────────────────────────
print("\n" + "=" * 70)
print("ANALYSIS 3 — Domain-level Cox, Model B (R1 expanded covariates)")
print("=" * 70)
rows_dom = []
for dom in list(DOMAIN_LABELS.keys()) + ["SCAU_TOTAL"]:
    label = DOMAIN_LABELS.get(dom, "SCOPA-AUT Total")
    cph, sub = fit_cox(df, dom, COVARS_B)
    if cph is None:
        rows_dom.append({"Domain": dom, "Label": label,
                         "N": np.nan, "Events": np.nan,
                         "HR": np.nan, "CI_low": np.nan, "CI_high": np.nan, "p": np.nan})
        continue
    hr, lo, hi, pv = cox_row(cph, dom)
    rows_dom.append({"Domain": dom, "Label": label,
                     "N": len(sub), "Events": int(sub["event"].sum()),
                     "HR": hr, "CI_low": lo, "CI_high": hi, "p": pv})
D = pd.DataFrame(rows_dom)
D.to_csv(f"{PROJ}/tables/cox_R1_domain.csv", index=False)
print(D.to_string(index=False, float_format="%.3f"))

# ── ANALYSIS 4: Likelihood-ratio test — item-level adds beyond total? ────
# For each item in Model B, fit (i) base model with COVARS_B + SCAU_TOTAL,
# and (ii) Model B + SCAU_TOTAL + item. LR test on the item's added information.
print("\n" + "=" * 70)
print("ANALYSIS 4 — LR test: does item add information beyond SCAU_TOTAL?")
print("=" * 70)
def ll(cph): return float(cph.log_likelihood_)
rows_lr = []
base_cols = ["time_to_event", "event"] + COVARS_B + ["SCAU_TOTAL"]
for item in ITEMS:
    cols = base_cols + [item]
    sub = df[cols].dropna()
    if len(sub) < 100 or sub["event"].sum() < 20:
        rows_lr.append({"Item": item, "Label": ITEM_LABELS[item],
                        "LR_chisq": np.nan, "LR_p": np.nan})
        continue
    try:
        cph0 = CoxPHFitter().fit(sub.drop(columns=[item]),
                                 duration_col="time_to_event", event_col="event")
        cph1 = CoxPHFitter().fit(sub, duration_col="time_to_event",
                                 event_col="event")
        chi = 2 * (ll(cph1) - ll(cph0))
        from scipy.stats import chi2
        pv = float(1 - chi2.cdf(chi, df=1))
        rows_lr.append({"Item": item, "Label": ITEM_LABELS[item],
                        "LR_chisq": chi, "LR_p": pv})
    except Exception:
        rows_lr.append({"Item": item, "Label": ITEM_LABELS[item],
                        "LR_chisq": np.nan, "LR_p": np.nan})
LR = pd.DataFrame(rows_lr)
LR_valid = LR.dropna(subset=["LR_p"])
_, LR_fdr, _, _ = multipletests(LR_valid["LR_p"], method="fdr_bh")
LR["LR_p_fdr"] = np.nan
LR.loc[LR_valid.index, "LR_p_fdr"] = LR_fdr
LR.to_csv(f"{PROJ}/tables/cox_R1_LR_item_vs_total.csv", index=False)
print(LR.to_string(index=False, float_format="%.4f"))

# ── Persist summary ──────────────────────────────────────────────────────
summary = {
    "N": int(len(df)), "events": int(df.event.sum()),
    "covars_A": COVARS_A, "covars_B": COVARS_B,
    "modelA_FDR_significant": A[A.p_fdr < 0.05]["Item"].tolist(),
    "modelB_FDR_significant": B[B.p_fdr < 0.05]["Item"].tolist(),
    "LR_FDR_significant_items_beyond_total": LR[LR.LR_p_fdr < 0.05]["Item"].tolist(),
    "PH_violations_p_lt_05_item": PH[PH.PH_p_item < 0.05]["Item"].tolist(),
}
with open(f"{PROJ}/logs/primary_analysis_R1_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print("\n=== R1 PRIMARY ANALYSIS COMPLETE ===")
print(f"Model A FDR-significant items: {summary['modelA_FDR_significant']}")
print(f"Model B FDR-significant items: {summary['modelB_FDR_significant']}")
print(f"Items significant beyond SCAU_TOTAL (LR FDR<0.05): "
      f"{summary['LR_FDR_significant_items_beyond_total']}")
print(f"PH-test violations (item-level p<0.05): "
      f"{summary['PH_violations_p_lt_05_item']}")
