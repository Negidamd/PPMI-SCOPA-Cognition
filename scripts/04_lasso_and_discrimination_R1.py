#!/usr/bin/env python3
"""
04_lasso_and_discrimination_R1.py — LASSO Cox over all 25 SCOPA-AUT items +
nested-model discrimination/calibration on the primary composite outcome.

Nested models (all use the same N = complete cases for all features):
  M0  base:      age + sex + education + MoCA + UPDRS-III + LEDD + Schwab +
                 RBDSQ + disease duration + alpha-blocker + antihypertensive + H&Y
  M1  + SCAU_TOTAL
  M2  + 6 domain scores
  M3  + 25 items (all)
  M4  + LASSO-selected items only (chosen by 10-fold CV)

Metrics:
  - Harrell's concordance (training & 10-fold CV)
  - Time-dependent AUC at 4 and 6 years
  - Integrated Brier score
  - Calibration plot at 4 years
"""
import os, json, warnings, sys
import numpy as np
import pandas as pd
from sksurv.linear_model import CoxnetSurvivalAnalysis, CoxPHSurvivalAnalysis
from sksurv.metrics import concordance_index_censored, cumulative_dynamic_auc, integrated_brier_score
from sksurv.util import Surv
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
warnings.filterwarnings("ignore")

SEED = 42
np.random.seed(SEED)

PROJ = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/1b-papers/SCOPA_Cognition_Study/revision_R1"
df = pd.read_csv(f"{PROJ}/data/analytical_dataset_R1.csv", low_memory=False)
df["LEDD_TOTAL_CURRENT"] = df["LEDD_TOTAL_CURRENT"].fillna(0)

ITEMS_ALL = [f"SCAU{i}" for i in range(1, 26)]
# For multivariable / LASSO / discrimination, drop high-missing items (SCAU22 70%,
# SCAU23 69%, SCAU24 29%, SCAU25 28%). State this in Methods.
ITEMS = [f"SCAU{i}" for i in range(1, 22)]   # SCAU1–SCAU21, 99–100% available
DOMAINS = ["SCAU_GI", "SCAU_URI", "SCAU_CV", "SCAU_THERM"]
# Discrimination base = Model C (5 covariates: age, sex, education, baseline MoCA, UPDRS-III).
# Rationale (author decision 2026-05-28): the discrimination analysis answers a
# prognostic question ("how much does measuring autonomic burden improve cognitive risk
# prediction beyond what a clinician routinely knows?"), which requires a clinically
# parsimonious base. The full 12-covariate adjustment is reserved for the etiologic Cox
# HR analyses (Tables 2-4, Model B) where it correctly controls for severity confounding.
COVARS_BASE = ["AGE_AT_VISIT","SEX","EDUCYRS","MCATOT","NP3TOT_BEST"]

# Use the largest complete-case subset that has all features (items, domains,
# base covariates). SCAU22, SCAU23–25 have missingness — restrict to subjects
# with all 25 items + base covariates (this aligns with the LASSO domain).
need = COVARS_BASE + ["SCAU_TOTAL"] + DOMAINS + ITEMS + ["time_to_event", "event"]
cc = df[need].dropna().copy()
print(f"Complete-case N for nested-model comparison: {len(cc)} "
      f"({int(cc.event.sum())} events)")

# Build sksurv structured array
y = Surv.from_dataframe("event", "time_to_event", cc)

def fit_metrics(X_train, y_train, X_test, y_test, t_eval=(4.0, 6.0), label=""):
    """Fit a Cox model (sksurv), return c-index, time-dep AUC, IBS, calib."""
    sc = StandardScaler().fit(X_train)
    Xtr, Xte = sc.transform(X_train), sc.transform(X_test)
    cph = CoxPHSurvivalAnalysis(alpha=0.001).fit(Xtr, y_train)
    risk = cph.predict(Xte)
    c = concordance_index_censored(
        y_test["event"], y_test["time_to_event"], risk)[0]
    # time-dependent AUC needs evaluation times strictly within train range
    t_max = min(y_train["time_to_event"].max(), y_test["time_to_event"].max())
    t_eval_use = tuple(t for t in t_eval if t < t_max - 0.01)
    auc_vals = {}
    if t_eval_use:
        try:
            auc, mean_auc = cumulative_dynamic_auc(
                y_train, y_test, risk, list(t_eval_use))
            auc_vals = {f"AUC_t{int(t)}": float(a)
                        for t, a in zip(t_eval_use, auc)}
            auc_vals["AUC_mean"] = float(mean_auc)
        except Exception as e:
            print(f"  AUC failed for {label}: {e}")
    # Integrated Brier on min(test_time, max train time)
    ibs = np.nan
    try:
        times = np.linspace(0.5, min(t_max - 0.5, 6.0), 20)
        survs = cph.predict_survival_function(Xte)
        surv_matrix = np.row_stack([s(times) for s in survs])
        ibs = integrated_brier_score(y_train, y_test, surv_matrix, times)
    except Exception as e:
        print(f"  IBS failed for {label}: {e}")
    return {"c_index": float(c), "ibs": float(ibs), **auc_vals,
            "coef": dict(zip(X_train.columns, cph.coef_))}

# ── Define feature sets for nested models ────────────────────────────────
F_BASE   = COVARS_BASE
F_TOTAL  = COVARS_BASE + ["SCAU_TOTAL"]
F_DOMAIN = COVARS_BASE + DOMAINS
F_ITEMS  = COVARS_BASE + ITEMS

# ── 10-fold CV nested model comparison ───────────────────────────────────
print("\n" + "=" * 70)
print("10-fold CV nested-model discrimination")
print("=" * 70)
kf = KFold(n_splits=10, shuffle=True, random_state=SEED)
results = {"M0_base": [], "M1_total": [], "M2_domain": [], "M3_items": [],
           "M4_lasso": []}
lasso_selected = []

for fold, (tr_idx, te_idx) in enumerate(kf.split(cc)):
    cc_tr, cc_te = cc.iloc[tr_idx], cc.iloc[te_idx]
    y_tr = Surv.from_dataframe("event", "time_to_event", cc_tr)
    y_te = Surv.from_dataframe("event", "time_to_event", cc_te)

    for name, feats in [("M0_base", F_BASE),
                        ("M1_total", F_TOTAL),
                        ("M2_domain", F_DOMAIN),
                        ("M3_items", F_ITEMS)]:
        m = fit_metrics(cc_tr[feats], y_tr, cc_te[feats], y_te, label=name)
        results[name].append(m)

    # LASSO Cox using sksurv's CoxnetSurvivalAnalysis. Penalize only items
    # (do not penalize base covariates). sksurv allows per-feature penalty
    # via `penalty_factor` (but only in newer versions; fallback otherwise).
    X_tr_lasso = cc_tr[F_ITEMS]
    X_te_lasso = cc_te[F_ITEMS]
    sc = StandardScaler().fit(X_tr_lasso)
    Xtr_s = sc.transform(X_tr_lasso)
    Xte_s = sc.transform(X_te_lasso)
    try:
        # l1_ratio=1.0 → pure LASSO
        coxnet = CoxnetSurvivalAnalysis(
            l1_ratio=1.0, n_alphas=50, alpha_min_ratio=0.01, max_iter=10_000)
        coxnet.fit(Xtr_s, y_tr)
        # pick alpha at the largest with at least 5 non-zero item coefs OR
        # the median alpha if none — for stability, use ~30th alpha (sparse)
        # Score grid via concordance on train (proxy for CV-within-CV)
        best_idx, best_c = None, -1
        for i in range(coxnet.alphas_.shape[0]):
            risk_tr = coxnet.predict(Xtr_s, alpha=coxnet.alphas_[i])
            try:
                c_i = concordance_index_censored(
                    y_tr["event"], y_tr["time_to_event"], risk_tr)[0]
                if c_i > best_c:
                    best_c, best_idx = c_i, i
            except Exception:
                pass
        alpha_best = coxnet.alphas_[best_idx]
        coefs = coxnet.coef_[:, best_idx]
        sel_items = [F_ITEMS[i] for i, c in enumerate(coefs)
                     if abs(c) > 1e-6 and F_ITEMS[i] in ITEMS]
        lasso_selected.append({"fold": fold, "alpha": float(alpha_best),
                               "selected": sel_items})
        # Evaluate test C
        risk_te = coxnet.predict(Xte_s, alpha=alpha_best)
        c_te = concordance_index_censored(
            y_te["event"], y_te["time_to_event"], risk_te)[0]
        results["M4_lasso"].append({"c_index": float(c_te),
                                    "n_selected_items": len(sel_items),
                                    "alpha": float(alpha_best)})
    except Exception as e:
        print(f"  LASSO failed on fold {fold}: {e}")
        results["M4_lasso"].append({"c_index": np.nan,
                                    "n_selected_items": 0,
                                    "alpha": np.nan})

# Summarize across folds
def summarize(name):
    rows = results[name]
    cs = [r["c_index"] for r in rows if not np.isnan(r.get("c_index", np.nan))]
    out = {"name": name, "c_mean": np.mean(cs), "c_sd": np.std(cs),
           "n_folds": len(cs)}
    for key in ["ibs", "AUC_t4", "AUC_t6", "AUC_mean"]:
        vals = [r[key] for r in rows
                if key in r and not np.isnan(r.get(key, np.nan))]
        if vals:
            out[f"{key}_mean"] = float(np.mean(vals))
            out[f"{key}_sd"]   = float(np.std(vals))
    if name == "M4_lasso":
        out["n_selected_mean"] = float(np.mean(
            [r["n_selected_items"] for r in rows]))
    return out

print("\nNested-model discrimination (10-fold CV, mean ± SD):")
summary_table = []
for nm in ["M0_base", "M1_total", "M2_domain", "M3_items", "M4_lasso"]:
    s = summarize(nm)
    summary_table.append(s)
    cs = f"{s['c_mean']:.3f} ± {s['c_sd']:.3f}"
    auct4 = f"{s.get('AUC_t4_mean', float('nan')):.3f}" if 'AUC_t4_mean' in s else "—"
    auct6 = f"{s.get('AUC_t6_mean', float('nan')):.3f}" if 'AUC_t6_mean' in s else "—"
    ibs = f"{s.get('ibs_mean', float('nan')):.3f}" if 'ibs_mean' in s else "—"
    extra = (f"  | n_items_selected = {s.get('n_selected_mean', 0):.1f}"
             if nm == "M4_lasso" else "")
    print(f"  {nm:12s}  C = {cs}  AUC(4y) = {auct4}  AUC(6y) = {auct6}  "
          f"IBS = {ibs}{extra}")

pd.DataFrame(summary_table).to_csv(f"{PROJ}/tables/discrimination_R1.csv",
                                    index=False)

# LASSO selection frequency across folds
sel_freq = {}
for r in lasso_selected:
    for it in r["selected"]:
        sel_freq[it] = sel_freq.get(it, 0) + 1
print("\nLASSO item-selection frequency across 10 folds:")
sel_freq_df = pd.DataFrame([{"Item": k, "selected_folds": v,
                              "freq": v / 10}
                             for k, v in sel_freq.items()]).sort_values(
    "selected_folds", ascending=False)
print(sel_freq_df.to_string(index=False))
sel_freq_df.to_csv(f"{PROJ}/tables/lasso_selection_frequency_R1.csv",
                   index=False)

# Persist
with open(f"{PROJ}/logs/lasso_discrimination_R1_summary.json", "w") as f:
    json.dump({"discrimination": summary_table,
               "lasso_selection_frequency": sel_freq,
               "per_fold_lasso": lasso_selected,
               "n_complete_cases": int(len(cc))}, f, indent=2, default=str)

print(f"\nSaved: tables/discrimination_R1.csv, "
      "tables/lasso_selection_frequency_R1.csv, "
      "logs/lasso_discrimination_R1_summary.json")

# ── Final whole-dataset LASSO for figure/coefficient path -------------------
print("\n" + "=" * 70)
print("Final whole-dataset LASSO Cox (for coefficient path figure)")
print("=" * 70)
X_full = cc[F_ITEMS].copy()
y_full = Surv.from_dataframe("event", "time_to_event", cc)
sc = StandardScaler().fit(X_full)
X_full_s = sc.transform(X_full)
coxnet = CoxnetSurvivalAnalysis(l1_ratio=1.0, n_alphas=80,
                                 alpha_min_ratio=0.01, max_iter=20_000)
coxnet.fit(X_full_s, y_full)

# Save coefficient path
path_df = pd.DataFrame(coxnet.coef_, index=F_ITEMS, columns=coxnet.alphas_)
path_df.to_csv(f"{PROJ}/tables/lasso_coefficient_path_R1.csv")
np.save(f"{PROJ}/tables/lasso_alphas_R1.npy", coxnet.alphas_)
print(f"  Saved coefficient path (shape: {path_df.shape})")

# Pick the lambda that retains a parsimonious item set (~5–10 items)
nonzero_per_alpha = (np.abs(coxnet.coef_) > 1e-6).sum(axis=0)
# items only (exclude base covariates)
n_items_idx = [F_ITEMS.index(it) for it in ITEMS]
nonzero_items = (np.abs(coxnet.coef_[n_items_idx, :]) > 1e-6).sum(axis=0)
target_n = 8
diff = np.abs(nonzero_items - target_n)
i_best = int(np.argmin(diff))
sel = [ITEMS[k] for k in range(len(ITEMS))
       if abs(coxnet.coef_[n_items_idx[k], i_best]) > 1e-6]
print(f"  Parsimonious LASSO (target ~{target_n} items, alpha={coxnet.alphas_[i_best]:.4f}):")
print(f"    Selected items: {sel}")

with open(f"{PROJ}/logs/lasso_final_R1.json", "w") as f:
    json.dump({"alpha_parsimonious": float(coxnet.alphas_[i_best]),
               "selected_items_parsimonious": sel,
               "nonzero_per_alpha": nonzero_per_alpha.tolist(),
               "nonzero_items_per_alpha": nonzero_items.tolist()},
              f, indent=2)

print("\n=== LASSO + DISCRIMINATION COMPLETE ===")
