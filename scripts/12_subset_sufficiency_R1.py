#!/usr/bin/env python3
"""
12_subset_sufficiency_R1.py — Sparse-sufficient analysis (Reviewer #2 reframe).

Asks: "Which minimal subset of SCOPA-AUT items / domains, used INSTEAD of the
25-item total, achieves the same 10-fold CV discrimination as adding the total
to the base clinical model?"

Reference benchmarks (from script 04):
  M0 base      = 0.717  (12 clinical covariates)
  M1 base+total = 0.726 (the bar to clear)

Three sub-analyses:
  A) Each single domain alone (4 models): base + GI; base + Urinary; base + CV;
     base + Thermo. Identifies which single domain matches M1.
  B) Domain pairs (6 models). Identifies smallest k-domain set matching M1.
  C) Item sufficiency curve: rank items by LASSO 10-fold selection frequency,
     then for K = 1, 2, 3, 4, 5, 8, 12, 17, 21 fit base + top-K items
     (NO total, NO domains). Report C, AUC@4y, AUC@6y per K.

Outputs:
  tables/subset_sufficiency_domains_R1.csv
  tables/subset_sufficiency_items_R1.csv
  logs/subset_sufficiency_R1.json
  figures/Figure9_subset_sufficiency.{png,pdf,svg}
"""
import os, json, warnings, itertools
import numpy as np
import pandas as pd
from sksurv.linear_model import CoxPHSurvivalAnalysis
from sksurv.metrics import concordance_index_censored, cumulative_dynamic_auc
from sksurv.util import Surv
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
warnings.filterwarnings("ignore")
import matplotlib.pyplot as plt
import seaborn as sns

SEED = 42
np.random.seed(SEED)

PROJ = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/1b-papers/SCOPA_Cognition_Study/revision_R1"
df = pd.read_csv(f"{PROJ}/data/analytical_dataset_R1.csv", low_memory=False)
df["LEDD_TOTAL_CURRENT"] = df["LEDD_TOTAL_CURRENT"].fillna(0)

ITEMS = [f"SCAU{i}" for i in range(1, 22)]                # SCAU1–21
DOMAINS = ["SCAU_GI", "SCAU_URI", "SCAU_CV", "SCAU_THERM"]
# Model C base — parsimonious clinical comparator (see scripts/04 rationale)
COVARS_BASE = ["AGE_AT_VISIT", "SEX", "EDUCYRS", "MCATOT", "NP3TOT_BEST"]

ITEM_LABELS = {
    "SCAU1": "Swallowing/choking", "SCAU2": "Drooling", "SCAU3": "Dysphagia",
    "SCAU4": "Early satiety", "SCAU5": "Constipation", "SCAU6": "Straining",
    "SCAU7": "Fecal incontinence", "SCAU8": "Urgency", "SCAU9": "Frequency",
    "SCAU10": "Nocturia", "SCAU11": "Incontinence", "SCAU12": "Incomplete emptying",
    "SCAU13": "Weak stream", "SCAU14": "Lightheadedness standing",
    "SCAU15": "Lightheadedness walking", "SCAU16": "Fainting",
    "SCAU17": "Excessive sweating day", "SCAU18": "Excessive sweating night",
    "SCAU19": "Heat intolerance", "SCAU20": "Cold intolerance",
    "SCAU21": "Color change hands/feet"}
DOMAIN_LABELS = {"SCAU_GI": "Gastrointestinal", "SCAU_URI": "Urinary",
                 "SCAU_CV": "Cardiovascular", "SCAU_THERM": "Thermoregulatory"}

need = COVARS_BASE + ["SCAU_TOTAL"] + DOMAINS + ITEMS + ["time_to_event", "event"]
cc = df[need].dropna().copy()
N, EV = len(cc), int(cc.event.sum())
print(f"Complete-case N = {N}; events = {EV}")


def fit_metrics(X_train, y_train, X_test, y_test):
    sc = StandardScaler().fit(X_train)
    Xtr = sc.transform(X_train); Xte = sc.transform(X_test)
    cph = CoxPHSurvivalAnalysis(alpha=0.001).fit(Xtr, y_train)
    risk = cph.predict(Xte)
    c = concordance_index_censored(
        y_test["event"], y_test["time_to_event"], risk)[0]
    t_max = min(y_train["time_to_event"].max(),
                y_test["time_to_event"].max())
    t_eval = [t for t in (4.0, 6.0) if t < t_max - 0.01]
    aucs = {}
    if t_eval:
        try:
            auc, _ = cumulative_dynamic_auc(y_train, y_test, risk, t_eval)
            for t, a in zip(t_eval, auc):
                aucs[f"AUC_t{int(t)}"] = float(a)
        except Exception:
            pass
    return {"c_index": float(c), **aucs}


def cv_evaluate(features, n_splits=10, seed=SEED, label=""):
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    rows = []
    for tr, te in kf.split(cc):
        cc_tr, cc_te = cc.iloc[tr], cc.iloc[te]
        y_tr = Surv.from_dataframe("event", "time_to_event", cc_tr)
        y_te = Surv.from_dataframe("event", "time_to_event", cc_te)
        m = fit_metrics(cc_tr[features], y_tr, cc_te[features], y_te)
        rows.append(m)
    cs = np.array([r["c_index"] for r in rows])
    out = {"label": label, "n_features_total": len(features),
           "c_mean": float(cs.mean()), "c_sd": float(cs.std())}
    for k in ("AUC_t4", "AUC_t6"):
        vals = [r[k] for r in rows if k in r]
        if vals:
            out[f"{k}_mean"] = float(np.mean(vals))
            out[f"{k}_sd"] = float(np.std(vals))
    return out

# ───────────────────────────────────────────────────────────────
# Benchmarks: M0 (base) and M1 (base + total)
# ───────────────────────────────────────────────────────────────
print("\n=== Benchmark models ===")
M0 = cv_evaluate(COVARS_BASE, label="M0 base")
M1 = cv_evaluate(COVARS_BASE + ["SCAU_TOTAL"], label="M1 base+total")
print(f"  {M0['label']:25s} C = {M0['c_mean']:.3f} ± {M0['c_sd']:.3f}")
print(f"  {M1['label']:25s} C = {M1['c_mean']:.3f} ± {M1['c_sd']:.3f}")
TARGET_C = M1["c_mean"]
print(f"  TARGET C (M1) = {TARGET_C:.3f}\n")

# ───────────────────────────────────────────────────────────────
# A) Each single domain alone
# ───────────────────────────────────────────────────────────────
print("=== Single-domain sufficiency ===")
domain_rows = [{"subset": "Base only", "k": 0, "features": "",
                **{k: M0[k] for k in M0 if k != "label"}}]
domain_rows.append({"subset": "Base + Total", "k": 1, "features": "SCAU_TOTAL",
                    **{k: M1[k] for k in M1 if k != "label"}})
for dom in DOMAINS:
    r = cv_evaluate(COVARS_BASE + [dom], label=f"Base + {DOMAIN_LABELS[dom]}")
    domain_rows.append({"subset": f"Base + {DOMAIN_LABELS[dom]}", "k": 1,
                        "features": dom, **{k: r[k] for k in r if k != "label"}})
    print(f"  Base + {DOMAIN_LABELS[dom]:18s} C = {r['c_mean']:.3f} ± {r['c_sd']:.3f}  "
          f"vs target {TARGET_C:.3f}  Δ = {r['c_mean']-TARGET_C:+.4f}")

# ───────────────────────────────────────────────────────────────
# B) Domain pairs
# ───────────────────────────────────────────────────────────────
print("\n=== Two-domain sufficiency ===")
for pair in itertools.combinations(DOMAINS, 2):
    r = cv_evaluate(COVARS_BASE + list(pair),
                    label=f"Base + {'+'.join(DOMAIN_LABELS[d] for d in pair)}")
    pair_label = " + ".join(DOMAIN_LABELS[d] for d in pair)
    domain_rows.append({"subset": f"Base + {pair_label}", "k": 2,
                        "features": "|".join(pair),
                        **{k: r[k] for k in r if k != "label"}})
    print(f"  {r['label']:60s} C = {r['c_mean']:.3f}  Δ = {r['c_mean']-TARGET_C:+.4f}")

# C) All 4 domains together (already approximate M2 from script 04, repeat for completeness)
r = cv_evaluate(COVARS_BASE + DOMAINS, label="Base + all 4 domains")
domain_rows.append({"subset": "Base + all 4 domains", "k": 4,
                    "features": "|".join(DOMAINS),
                    **{k: r[k] for k in r if k != "label"}})
print(f"  Base + all 4 domains{'':40s} C = {r['c_mean']:.3f}  Δ = {r['c_mean']-TARGET_C:+.4f}")

domain_df = pd.DataFrame(domain_rows)
domain_df.to_csv(f"{PROJ}/tables/subset_sufficiency_domains_R1.csv", index=False)
print(f"\nSaved tables/subset_sufficiency_domains_R1.csv")

# ───────────────────────────────────────────────────────────────
# C) Item sufficiency curve: ranked by LASSO selection frequency
# ───────────────────────────────────────────────────────────────
print("\n=== Item sufficiency curve (by LASSO selection frequency) ===")
sel = pd.read_csv(f"{PROJ}/tables/lasso_selection_frequency_R1.csv")
sel = sel[sel.Item.isin(ITEMS)].sort_values("selected_folds", ascending=False)
# Items not selected by LASSO at all — append at end (they ranked 0/10)
ranked = list(sel.Item)
missing = [it for it in ITEMS if it not in ranked]
ranked += missing
print(f"  Item rank (LASSO selection freq): {ranked}")

K_GRID = [1, 2, 3, 4, 5, 8, 12, 17, 21]
item_rows = []
for K in K_GRID:
    top_k = ranked[:K]
    r = cv_evaluate(COVARS_BASE + top_k, label=f"Base + top-{K} items")
    item_rows.append({"K": K, "items": " | ".join(top_k),
                      "n_features_total": len(COVARS_BASE) + K,
                      **{k: r[k] for k in r if k != "label"}})
    delta = r["c_mean"] - TARGET_C
    auc4 = r.get("AUC_t4_mean", float("nan"))
    print(f"  K = {K:2d}  C = {r['c_mean']:.3f} ± {r['c_sd']:.3f}  "
          f"Δ vs M1 = {delta:+.4f}  AUC(4y) = {auc4:.3f}")

# Include reference rows
item_rows_full = [
    {"K": 0, "items": "(base only)",
     "n_features_total": len(COVARS_BASE),
     **{k: M0[k] for k in M0 if k != "label"}},
    {"K": "total", "items": "SCAU_TOTAL",
     "n_features_total": len(COVARS_BASE) + 1,
     **{k: M1[k] for k in M1 if k != "label"}},
] + item_rows

item_df = pd.DataFrame(item_rows_full)
item_df.to_csv(f"{PROJ}/tables/subset_sufficiency_items_R1.csv", index=False)
print(f"\nSaved tables/subset_sufficiency_items_R1.csv")

# ───────────────────────────────────────────────────────────────
# Find smallest sufficient subset
# ───────────────────────────────────────────────────────────────
sufficient_K = None
for row in item_rows:
    if row["c_mean"] >= TARGET_C - 0.002:   # within 0.002 = noise tolerance
        sufficient_K = row["K"]
        break

print(f"\n=== Smallest sufficient item subset (C ≥ M1 − 0.002 = {TARGET_C-0.002:.3f}): "
      f"K = {sufficient_K} ===")
if sufficient_K is not None:
    sufficient_items = ranked[:sufficient_K]
    print(f"  Items: {sufficient_items}")
    print(f"  Labels: {[ITEM_LABELS[it] for it in sufficient_items]}")

# Same for single domain
sufficient_domain = None
single_doms = [r for r in domain_rows if r["k"] == 1 and r["features"] in DOMAINS]
for r in sorted(single_doms, key=lambda x: -x["c_mean"]):
    if r["c_mean"] >= TARGET_C - 0.002:
        sufficient_domain = r["features"]; break
print(f"=== Smallest sufficient domain subset: {sufficient_domain or 'none (no single domain matches M1)'} ===")

# ───────────────────────────────────────────────────────────────
# Persist JSON
# ───────────────────────────────────────────────────────────────
with open(f"{PROJ}/logs/subset_sufficiency_R1.json", "w") as f:
    json.dump({
        "n_complete_cases": N, "n_events": EV,
        "M0_base": M0, "M1_total": M1, "target_C": TARGET_C,
        "ranked_items_by_lasso_freq": ranked,
        "domain_rows": domain_rows,
        "item_rows": item_rows,
        "smallest_sufficient_K_items": sufficient_K,
        "smallest_sufficient_items": ranked[:sufficient_K] if sufficient_K else None,
        "smallest_sufficient_domain": sufficient_domain,
    }, f, indent=2, default=str)
print(f"Saved logs/subset_sufficiency_R1.json")

# ───────────────────────────────────────────────────────────────
# Figure 9: sufficiency curve
# ───────────────────────────────────────────────────────────────
print("\nBuilding Figure 9 (subset sufficiency curve)...")
Ks = [r["K"] for r in item_rows]
Cs = [r["c_mean"] for r in item_rows]
Csd = [r["c_sd"] for r in item_rows]

# Figsize: 6 x 4.2, DPI 290 → 1740 × 1218 (longest <= 1800)
fig, ax = plt.subplots(figsize=(6, 4.2), constrained_layout=True)
palette = sns.color_palette("muted", 4)
ax.errorbar(Ks, Cs, yerr=Csd, marker="o", color=palette[0],
            linewidth=1.5, capsize=3,
            markersize=6, markerfacecolor=palette[0],
            markeredgecolor="black", markeredgewidth=0.4,
            label="Base + top-K items (no SCOPA-AUT total)")
# Reference lines
ax.axhline(M0["c_mean"], color="#666666", linestyle=":", linewidth=1,
           label=f"M0 base (C = {M0['c_mean']:.3f})")
ax.axhline(M1["c_mean"], color=palette[3], linestyle="--", linewidth=1.2,
           label=f"M1 base + SCOPA-AUT total (C = {M1['c_mean']:.3f})")
# M0/M1 confidence bands (±SD)
ax.fill_between(Ks, M0["c_mean"]-M0["c_sd"], M0["c_mean"]+M0["c_sd"],
                color="#666666", alpha=0.08)
ax.fill_between(Ks, M1["c_mean"]-M1["c_sd"], M1["c_mean"]+M1["c_sd"],
                color=palette[3], alpha=0.10)
# Annotate sufficient K if found
if sufficient_K is not None:
    ax.annotate(f"K = {sufficient_K}\nreaches M1",
                xy=(sufficient_K, [r["c_mean"] for r in item_rows
                                    if r["K"] == sufficient_K][0]),
                xytext=(sufficient_K + 2,
                         [r["c_mean"] for r in item_rows
                          if r["K"] == sufficient_K][0] - 0.012),
                fontsize=8, color="black",
                arrowprops=dict(arrowstyle="->", color="black", lw=0.5))

ax.set_xlabel("Number of SCOPA-AUT items in model (ranked by LASSO selection frequency)")
ax.set_ylabel("Harrell's C-index (10-fold CV)")
ax.set_xticks(Ks)
ax.set_ylim(M0["c_mean"]-M0["c_sd"]-0.005,
            max(M1["c_mean"]+M1["c_sd"], max(Cs)+max(Csd))+0.005)
ax.legend(loc="lower right", fontsize=7.5, frameon=False)

FIG = f"{PROJ}/figures"
for ext in ("png", "pdf", "svg"):
    out = f"{FIG}/Figure9_subset_sufficiency.{ext}"
    if ext == "png":
        fig.savefig(out, bbox_inches="tight", dpi=290)
    else:
        fig.savefig(out, bbox_inches="tight")
    print(f"  Saved {out}")
plt.close(fig)
print("\nDone.")
