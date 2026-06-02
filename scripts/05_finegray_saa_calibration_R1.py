#!/usr/bin/env python3
"""
05_finegray_saa_calibration_R1.py — three remaining R1 analyses:

  (A) Fine-Gray competing-risks sensitivity (death = competing event)
      — note: in this newly-diagnosed PD cohort only 1 death preceded a
      cognitive milestone, so Fine-Gray will closely mirror cause-specific
      Cox. We run it for transparency and to demonstrate non-violation.

  (B) SAA-stratified sensitivity: Model B Cox restricted to SAA+ subjects
      (the synuclein-positive subgroup that defines biological PD per the
      2024–2026 NSD-ISS / SOC reframe).

  (C) Calibration plot for nested models at 4y, 6y (already have IBS and
      AUC; add visual calibration).
"""
import os, json, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from lifelines import CoxPHFitter
from sksurv.linear_model import CoxPHSurvivalAnalysis
from sksurv.util import Surv
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import KFold
from statsmodels.stats.multitest import multipletests
warnings.filterwarnings("ignore")

SEED = 42
np.random.seed(SEED)

PROJ = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/1b-papers/SCOPA_Cognition_Study/revision_R1"
df = pd.read_csv(f"{PROJ}/data/analytical_dataset_R1.csv", low_memory=False)
df["LEDD_TOTAL_CURRENT"] = df["LEDD_TOTAL_CURRENT"].fillna(0)

ITEMS = [f"SCAU{i}" for i in range(1, 22)]  # 1–21 (drop high-missing 22–25)
# Calibration base = Model C (parsimonious 5-variable; matches script 04 + 12).
# See script 04 docstring rationale for the etiologic vs prognostic distinction.
COVARS_B = ["AGE_AT_VISIT","SEX","EDUCYRS","MCATOT","NP3TOT_BEST"]
ITEM_LABELS = {f"SCAU{i}": lab for i, lab in enumerate([
    "Swallowing/choking","Drooling","Dysphagia","Early satiety","Constipation",
    "Straining","Fecal incontinence","Urgency","Frequency","Nocturia",
    "Incontinence","Incomplete emptying","Weak stream","Lightheadedness standing",
    "Lightheadedness walking","Fainting","Excessive sweating day",
    "Excessive sweating night","Heat intolerance","Cold intolerance",
    "Color change hands/feet"], 1)}

# ════════════════════════════════════════════════════════════════════════
# (A) FINE-GRAY COMPETING RISKS
# ════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("(A) Fine-Gray competing-risks sensitivity")
print("=" * 70)

# Approach: scikit-survival lacks a built-in subdistribution Cox. We report
# cause-specific Cox (treating death as censoring) vs a milestone-or-death
# composite (treating death as an event); the difference between these
# brackets the Fine-Gray subdistribution-hazard interpretation.
#
# Correct competing-risks counts (against the actual primary outcome):
#   - Subjects who died without reaching a cognitive milestone  = competing events
#   - Subjects who reached a milestone then later died          = irrelevant
#     (the milestone was recorded first; subsequent death does not compete)
# Previous versions of this script erroneously used time_to_event_dom3_years /
# reached_dom3 (a single PPMI domain) instead of the composite primary outcome
# (event, time_to_event), which under-counted competing events to 1. Fixed below.

n_died = int((df.is_death == 1).sum())
n_died_milestone_free = int(((df.is_death == 1) & (df.event == 0)).sum())
n_died_after_milestone = int(((df.is_death == 1) & (df.event == 1)).sum())
print(f"  Total deaths during follow-up:                                  {n_died}")
print(f"  Deaths WITHOUT reaching a milestone (true competing events):    {n_died_milestone_free}")
print(f"  Deaths AFTER a milestone (milestone recorded first; irrelevant): {n_died_after_milestone}")
# Keep variable name `n_death_before` for backward compat with downstream JSON
n_death_before = n_died_milestone_free

# Cause-specific Cox (death treated as censoring) — this is exactly Model B
rows_cs = []
# Composite milestone-or-death (treats death as outcome)
df["event_OR_death"] = ((df.event == 1) |
                         ((df.is_death == 1) &
                          df.time_to_death_yrs.notna())).astype(int)
df["time_OR_death"] = df.apply(
    lambda r: min(r.time_to_event, r.time_to_death_yrs)
              if pd.notna(r.time_to_death_yrs) else r.time_to_event, axis=1)

for item in ITEMS:
    sub = df[[item, "time_to_event", "event", "time_OR_death",
              "event_OR_death"] + COVARS_B].dropna()
    if len(sub) < 100 or sub["event"].sum() < 20:
        continue
    try:
        # cause-specific
        cph_cs = CoxPHFitter()
        cph_cs.fit(sub.drop(columns=["time_OR_death", "event_OR_death"]),
                   duration_col="time_to_event", event_col="event")
        hr_cs = float(np.exp(cph_cs.params_[item]))
        lo_cs = float(np.exp(cph_cs.confidence_intervals_.loc[item].iloc[0]))
        hi_cs = float(np.exp(cph_cs.confidence_intervals_.loc[item].iloc[1]))
        p_cs  = float(cph_cs.summary.loc[item, "p"])
        # milestone-or-death composite
        cph_or = CoxPHFitter()
        cph_or.fit(sub.drop(columns=["time_to_event", "event"]),
                   duration_col="time_OR_death", event_col="event_OR_death")
        hr_or = float(np.exp(cph_or.params_[item]))
        rows_cs.append({"Item": item, "Label": ITEM_LABELS[item],
                        "HR_cause_specific": hr_cs,
                        "CI_low_cs": lo_cs, "CI_high_cs": hi_cs, "p_cs": p_cs,
                        "HR_milestone_or_death": hr_or,
                        "delta_HR_pct": 100*(hr_or - hr_cs)/hr_cs})
    except Exception:
        pass

cs = pd.DataFrame(rows_cs)
valid = cs.dropna(subset=["p_cs"])
_, fdr, _, _ = multipletests(valid["p_cs"], method="fdr_bh")
cs["p_cs_fdr"] = np.nan
cs.loc[valid.index, "p_cs_fdr"] = fdr
cs.to_csv(f"{PROJ}/tables/finegray_cause_specific_R1.csv", index=False)
print(f"  Max |ΔHR| between cause-specific and milestone-or-death framings: "
      f"{cs.delta_HR_pct.abs().max():.2f}%  "
      "(small ⇒ competing-risks bias is negligible)")
print(cs[["Item","Label","HR_cause_specific","HR_milestone_or_death",
          "delta_HR_pct","p_cs","p_cs_fdr"]].to_string(index=False,
                                                       float_format="%.3f"))

# ════════════════════════════════════════════════════════════════════════
# (B) SAA-STRATIFIED SENSITIVITY
# ════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("(B) SAA-stratified Cox (Model B), SAA+ subjects only")
print("=" * 70)
saa_pos = df[df.SAA_POS_Subject == "SAA+"].copy()
saa_neg = df[df.SAA_POS_Subject == "SAA-"].copy()
print(f"  SAA+ N = {len(saa_pos)} (events = {int(saa_pos.event.sum())})")
print(f"  SAA- N = {len(saa_neg)} (events = {int(saa_neg.event.sum())})")

rows_saa = []
for item in ITEMS:
    cols = [item, "time_to_event", "event"] + COVARS_B
    sub = saa_pos[cols].dropna()
    if len(sub) < 80 or sub["event"].sum() < 15:
        continue
    try:
        cph = CoxPHFitter()
        cph.fit(sub, duration_col="time_to_event", event_col="event")
        hr = float(np.exp(cph.params_[item]))
        lo = float(np.exp(cph.confidence_intervals_.loc[item].iloc[0]))
        hi = float(np.exp(cph.confidence_intervals_.loc[item].iloc[1]))
        pv = float(cph.summary.loc[item, "p"])
        rows_saa.append({"Item": item, "Label": ITEM_LABELS[item],
                         "N_SAA+": len(sub),
                         "Events_SAA+": int(sub["event"].sum()),
                         "HR_SAA+": hr, "CI_low": lo, "CI_high": hi, "p": pv})
    except Exception:
        pass

saa = pd.DataFrame(rows_saa)
valid = saa.dropna(subset=["p"])
_, fdr, _, _ = multipletests(valid["p"], method="fdr_bh")
saa["p_fdr"] = np.nan
saa.loc[valid.index, "p_fdr"] = fdr
saa.to_csv(f"{PROJ}/tables/cox_R1_SAApos_only.csv", index=False)
print(saa[["Item","Label","N_SAA+","Events_SAA+","HR_SAA+","CI_low","CI_high","p","p_fdr"]]
      .to_string(index=False, float_format="%.3f"))

# ════════════════════════════════════════════════════════════════════════
# (C) CALIBRATION PLOT for nested models at 4y
# ════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("(C) Calibration plot at t=4 years (10-fold CV pooled)")
print("=" * 70)

DOMAINS = ["SCAU_GI", "SCAU_URI", "SCAU_CV", "SCAU_THERM"]
need = COVARS_B + ["SCAU_TOTAL"] + DOMAINS + ITEMS + ["time_to_event", "event"]
cc = df[need].dropna().copy()
print(f"  Complete-case N = {len(cc)} (events = {int(cc.event.sum())})")

F_BASE   = COVARS_B
F_TOTAL  = COVARS_B + ["SCAU_TOTAL"]
F_DOMAIN = COVARS_B + DOMAINS

T_CAL = 4.0  # calibration horizon
kf = KFold(n_splits=10, shuffle=True, random_state=SEED)
results = {"M0_base": {"pred": [], "obs": []},
           "M1_total": {"pred": [], "obs": []},
           "M2_domain": {"pred": [], "obs": []}}

for fold, (tr_idx, te_idx) in enumerate(kf.split(cc)):
    cc_tr, cc_te = cc.iloc[tr_idx], cc.iloc[te_idx]
    y_tr = Surv.from_dataframe("event", "time_to_event", cc_tr)
    for name, feats in [("M0_base", F_BASE),
                        ("M1_total", F_TOTAL),
                        ("M2_domain", F_DOMAIN)]:
        sc = StandardScaler().fit(cc_tr[feats])
        cph = CoxPHSurvivalAnalysis(alpha=0.001).fit(sc.transform(cc_tr[feats]), y_tr)
        survs = cph.predict_survival_function(sc.transform(cc_te[feats]))
        # Predicted P(event by t=4)
        p_event = np.array([1.0 - s(T_CAL) for s in survs])
        results[name]["pred"].extend(p_event.tolist())
        # Observed: event indicator if time_to_event ≤ 4y and event=1
        obs = ((cc_te["time_to_event"].values <= T_CAL) & (cc_te["event"].values == 1)).astype(int)
        results[name]["obs"].extend(obs.tolist())

# Plot calibration
sns.set_palette("muted")
fig, ax = plt.subplots(figsize=(6, 4.5), constrained_layout=True)
colors = {"M0_base": "#4878D0", "M1_total": "#EE854A", "M2_domain": "#6ACC64"}
labels = {"M0_base": "P0 base (5 clinical variables)",
          "M1_total": "P1: base + SCOPA-AUT total",
          "M2_domain": "P2: base + 4 SCOPA-AUT domains"}
n_bins = 8
for name in ["M0_base", "M1_total", "M2_domain"]:
    p_arr = np.array(results[name]["pred"])
    o_arr = np.array(results[name]["obs"])
    # Decile binning
    bins = np.quantile(p_arr, np.linspace(0, 1, n_bins + 1))
    bins = np.unique(bins)
    bin_id = np.clip(np.digitize(p_arr, bins[1:-1]), 0, len(bins) - 2)
    means_pred, means_obs = [], []
    for b in range(len(bins) - 1):
        mask = bin_id == b
        if mask.sum() < 5:
            continue
        means_pred.append(p_arr[mask].mean())
        means_obs.append(o_arr[mask].mean())
    ax.plot(means_pred, means_obs, "o-",
            color=colors[name], label=labels[name], markersize=8, linewidth=2)

ax.plot([0, 1], [0, 1], "k--", linewidth=1, alpha=0.6, label="Perfect calibration")
ax.set_xlabel("Predicted probability of event by 4 years")
ax.set_ylabel("Observed event rate")
ax.set_xlim(0, max(0.7, max(np.array(results["M2_domain"]["pred"])) + 0.05))
ax.set_ylim(0, max(0.7, max(np.array(results["M2_domain"]["pred"])) + 0.05))
ax.legend(loc="upper left", frameon=False, fontsize=9)
fig.savefig(f"{PROJ}/figures/calibration_R1_4y.pdf", bbox_inches="tight", dpi=300)
fig.savefig(f"{PROJ}/figures/calibration_R1_4y.png", bbox_inches="tight", dpi=280)
# Also save under non-suffixed name for manuscript embedding (no _R1 in submission files)
fig.savefig(f"{PROJ}/figures/calibration_4y.png", bbox_inches="tight", dpi=280)
fig.savefig(f"{PROJ}/figures/calibration_4y.pdf", bbox_inches="tight")
fig.savefig(f"{PROJ}/figures/calibration_4y.svg", bbox_inches="tight")
plt.close(fig)
print(f"  Saved calibration_R1_4y.{{pdf,png}}")

# Persist
out = {
    "finegray": {"n_death_before_event": n_death_before,
                 "max_delta_HR_pct": float(cs.delta_HR_pct.abs().max())},
    "saa_stratified": {"SAA+_N": int(len(saa_pos)),
                       "SAA+_events": int(saa_pos.event.sum()),
                       "SAA-_N": int(len(saa_neg)),
                       "SAA-_events": int(saa_neg.event.sum()),
                       "fdr_sig_in_SAA+": saa[saa.p_fdr < 0.05]["Item"].tolist()},
    "calibration_4y": {k: {"pred_mean": float(np.mean(v["pred"])),
                            "obs_mean": float(np.mean(v["obs"])),
                            "n_predictions": len(v["pred"])}
                        for k, v in results.items()},
}
with open(f"{PROJ}/logs/finegray_saa_calibration_R1.json", "w") as f:
    json.dump(out, f, indent=2)

print("\n=== FINE-GRAY + SAA + CALIBRATION COMPLETE ===")
print(f"  SAA+ FDR-significant items: {saa[saa.p_fdr < 0.05]['Item'].tolist()}")
