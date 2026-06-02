#!/usr/bin/env python3
"""
16_recompute_discrimination_full_metrics.py
─────────────────────────────────────────────────────────────────────────
Recompute 10-fold CV discrimination + calibration metrics for the SIX
post-triage prognostic models (P0 / P1 / P-sig-dom / P-sig-items / P2 / P3)
and write the full result to tables/replaces_total_comparison_R1.csv
INCLUDING AUC at 4 and 6 years and the integrated Brier score.

This is the metric companion of scripts/04_lasso_and_discrimination_R1.py.
We use the SAME seed (42), the same KFold, the same StandardScaler + Cox
machinery, so estimates are directly comparable to scripts/04's M0/M1 etc.

Reason this script exists: the original 6-model CSV (created earlier in
the session) carried only c_mean/c_sd. Table 4 needs AUC + Brier as well,
which without these would render as "—" placeholders.
─────────────────────────────────────────────────────────────────────────
"""
import os, warnings
import numpy as np
import pandas as pd
from sksurv.linear_model import CoxPHSurvivalAnalysis
from sksurv.metrics import (concordance_index_censored,
                             cumulative_dynamic_auc, integrated_brier_score)
from sksurv.util import Surv
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
warnings.filterwarnings("ignore")

SEED = 42
np.random.seed(SEED)

PROJ = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/1b-papers/SCOPA_Cognition_Study/revision_R1"
df = pd.read_csv(f"{PROJ}/data/analytical_dataset_R1.csv", low_memory=False)
df["LEDD_TOTAL_CURRENT"] = df["LEDD_TOTAL_CURRENT"].fillna(0)

ITEMS    = [f"SCAU{i}" for i in range(1, 22)]        # SCAU1–21, 99–100% available
DOMAINS  = ["SCAU_GI", "SCAU_URI", "SCAU_CV", "SCAU_THERM"]
BASE     = ["AGE_AT_VISIT", "SEX", "EDUCYRS", "MCATOT", "NP3TOT_BEST"]

# Three FDR-significant domains (from Model B item-level Cox, Table 3):
SIG_DOMAINS = ["SCAU_GI", "SCAU_CV", "SCAU_THERM"]
# Five FDR-significant items (from Model B item-level Cox, Table 2):
SIG_ITEMS   = ["SCAU3", "SCAU4", "SCAU14", "SCAU15", "SCAU20"]

# Six post-triage prognostic models — same naming used in Table 4 + Figure 5
MODELS = [
    ("P0_base",       BASE),                                   # no SCOPA-AUT
    ("P1_total",      BASE + ["SCAU_TOTAL"]),                  # reference
    ("P_sig_domains", BASE + SIG_DOMAINS),                     # REPLACES total
    ("P_sig_items",   BASE + SIG_ITEMS),                       # REPLACES total
    ("P2_4_domains",  BASE + DOMAINS),                         # REPLACES total
    ("P3_21_items",   BASE + ITEMS),                           # REPLACES total
]

# Complete-case subset using the largest feature footprint (21 items + 4 domains
# + total + base). Matches the cohort scripts/04 uses for nested-model
# discrimination — keeps results directly comparable to the LASSO analysis.
need = BASE + ["SCAU_TOTAL"] + DOMAINS + ITEMS + ["time_to_event", "event"]
cc = df[need].dropna().copy()
print(f"Complete-case N for discrimination cohort: {len(cc)} "
      f"({int(cc.event.sum())} events)")

def fit_metrics(X_tr, y_tr, X_te, y_te, t_eval=(4.0, 6.0)):
    """Identical signature to scripts/04 — Cox PH (sksurv), 10-fold CV.
    Returns c-index on the test fold + time-dependent AUC at t_eval years
    + integrated Brier score over [0.5, min(6, t_max-0.5)]."""
    sc = StandardScaler().fit(X_tr)
    Xtr, Xte = sc.transform(X_tr), sc.transform(X_te)
    cph = CoxPHSurvivalAnalysis(alpha=0.001).fit(Xtr, y_tr)
    risk = cph.predict(Xte)
    c = concordance_index_censored(
        y_te["event"], y_te["time_to_event"], risk)[0]
    t_max = min(y_tr["time_to_event"].max(), y_te["time_to_event"].max())
    t_eval_use = tuple(t for t in t_eval if t < t_max - 0.01)
    auc_vals = {}
    if t_eval_use:
        try:
            auc, mean_auc = cumulative_dynamic_auc(
                y_tr, y_te, risk, list(t_eval_use))
            auc_vals = {f"AUC_t{int(t)}": float(a)
                        for t, a in zip(t_eval_use, auc)}
            auc_vals["AUC_mean"] = float(mean_auc)
        except Exception as e:
            print(f"    AUC failed: {e}")
    ibs = np.nan
    try:
        times = np.linspace(0.5, min(t_max - 0.5, 6.0), 20)
        survs = cph.predict_survival_function(Xte)
        surv_matrix = np.row_stack([s(times) for s in survs])
        ibs = float(integrated_brier_score(y_tr, y_te, surv_matrix, times))
    except Exception as e:
        print(f"    IBS failed: {e}")
    return {"c_index": float(c), "ibs": ibs, **auc_vals}

# ── 10-fold CV ──────────────────────────────────────────────────────────
print("\n10-fold CV discrimination + calibration for 6 prognostic models")
print("(same KFold seed=42, same scaling, same Cox(alpha=0.001) as scripts/04)\n")
kf = KFold(n_splits=10, shuffle=True, random_state=SEED)
results = {nm: [] for nm, _ in MODELS}
for fold, (tr_idx, te_idx) in enumerate(kf.split(cc)):
    cc_tr, cc_te = cc.iloc[tr_idx], cc.iloc[te_idx]
    y_tr = Surv.from_dataframe("event", "time_to_event", cc_tr)
    y_te = Surv.from_dataframe("event", "time_to_event", cc_te)
    for name, feats in MODELS:
        m = fit_metrics(cc_tr[feats], y_tr, cc_te[feats], y_te)
        results[name].append(m)

def _summary(rows):
    def col(key):
        v = [r[key] for r in rows if key in r and not np.isnan(r.get(key, np.nan))]
        return (np.mean(v), np.std(v), len(v)) if v else (np.nan, np.nan, 0)
    c_m, c_s, c_n  = col("c_index")
    ibs_m, ibs_s, _ = col("ibs")
    a4_m, a4_s, _   = col("AUC_t4")
    a6_m, a6_s, _   = col("AUC_t6")
    return {"c_mean": c_m, "c_sd": c_s, "n_folds": c_n,
            "ibs_mean": ibs_m, "ibs_sd": ibs_s,
            "AUC_t4_mean": a4_m, "AUC_t4_sd": a4_s,
            "AUC_t6_mean": a6_m, "AUC_t6_sd": a6_s}

# Build output table + preserve n_features / features columns for Figure 7 compat
rows_out = []
for name, feats in MODELS:
    s = _summary(results[name])
    s["name"] = name
    s["n_features"] = len(feats)
    s["features"]   = str(feats)
    rows_out.append(s)

out_df = pd.DataFrame(rows_out)[[
    "name", "c_mean", "c_sd", "n_folds",
    "ibs_mean", "ibs_sd",
    "AUC_t4_mean", "AUC_t4_sd",
    "AUC_t6_mean", "AUC_t6_sd",
    "n_features", "features"
]]
out_path = os.path.join(PROJ, "tables", "replaces_total_comparison_R1.csv")
out_df.to_csv(out_path, index=False)

# Console summary
print(f"\n{'MODEL':18s}  {'C':>14s}  {'AUC(4y)':>9s}  {'AUC(6y)':>9s}  {'IBS':>7s}")
print("-" * 70)
for r in rows_out:
    cs   = f"{r['c_mean']:.3f}±{r['c_sd']:.3f}"
    a4   = f"{r['AUC_t4_mean']:.3f}" if not np.isnan(r['AUC_t4_mean']) else "—"
    a6   = f"{r['AUC_t6_mean']:.3f}" if not np.isnan(r['AUC_t6_mean']) else "—"
    ibs  = f"{r['ibs_mean']:.3f}"   if not np.isnan(r['ibs_mean'])   else "—"
    print(f"{r['name']:18s}  {cs:>14s}  {a4:>9s}  {a6:>9s}  {ibs:>7s}")

print(f"\nWrote {out_path}")
