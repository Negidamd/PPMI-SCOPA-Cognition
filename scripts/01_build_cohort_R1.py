#!/usr/bin/env python3
"""
01_build_cohort_R1.py — R1 cohort rebuild (Clinical Auton. Res.)

Changes vs original:
  • MoCA boundary fix: REQUIRE baseline MCATOT ≥ 21 (the m10 endpoint is MoCA<21;
    keeping pts at MCATOT=21 lets a 1-point drop trigger event).
  • Drop "≥2y follow-up or event" rule (asymmetric; biased toward early events).
  • Add disease duration from PD_Diagnosis_History.PDDXDT.
  • Add death/withdrawal events for Fine-Gray competing-risks (from Conclusion_of_Study).
  • Add baseline medication-class flags (alpha-blocker, antihypertensive — others sparse).
  • Add SAA status (Status_Combined and POS_Subject).
  • Locked analytical dataset: data/analytical_dataset_R1.csv
  • Locked sensitivity datasets:
      - data/analytical_dataset_R1_strictMoCA23.csv (sensitivity: MCATOT≥23)
      - data/analytical_dataset_R1_v0replication.csv (replicates original ≥2y rule, MoCA≥18)
"""
import os, json, warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
SEED = 42
np.random.seed(SEED)

PPMI = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/3-resources/datasets/PPMI"
RAW  = os.path.join(PPMI, "PPMI_April2026")
PROJ = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/1b-papers/SCOPA_Cognition_Study/revision_R1"
DATA = os.path.join(PROJ, "data")
LOGS = os.path.join(PROJ, "logs")
os.makedirs(DATA, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)

# ── SCOPA-AUT items and domain groupings ─────────────────────────────────
SCOPA_ITEMS = [f"SCAU{i}" for i in range(1, 26)]
SCOPA_DOMAINS = {
    "SCAU_GI":    [f"SCAU{i}" for i in range(1, 8)],
    "SCAU_URI":   [f"SCAU{i}" for i in range(8, 14)],
    "SCAU_CV":    [f"SCAU{i}" for i in range(14, 17)],
    "SCAU_THERM": [f"SCAU{i}" for i in range(17, 22)],
    "SCAU_PUPIL": ["SCAU22"],
    "SCAU_SEX":   ["SCAU23", "SCAU24", "SCAU25"],
}

# ── 1. Load master, baseline-only ────────────────────────────────────────
print("[1/8] Loading PPMI master (v2.1, 2026-05-13) ...")
master = pd.read_csv(os.path.join(PPMI, "PPMI_Master_Merged.csv"), low_memory=False)
print(f"  rows: {len(master):,}; subjects: {master.PATNO.nunique():,}")

bl = master[master.EVENT_ID == "BL"].copy()
print(f"  baseline rows: {len(bl):,}; baseline subjects: {bl.PATNO.nunique():,}")

# ── 2. Exclusion cascade ─────────────────────────────────────────────────
flow = []
def step(num, reason, n_before, frame):
    n_after = frame.PATNO.nunique()
    excl = n_before - n_after
    flow.append({"step": num, "reason": reason,
                 "n_before": n_before, "n_after": n_after, "excluded": excl})
    print(f"  Step {num}: {reason}")
    print(f"    {n_before} → {n_after} (excluded {excl})")
    return n_after

N0 = bl.PATNO.nunique()
print(f"\n[2/8] Exclusion cascade — starting from N={N0:,} BL subjects")

n = N0
bl = bl[bl.COHORT == 1].copy()
n = step(1, "Restrict to PD cohort (COHORT=1)", n, bl)

bl = bl[bl.SCAU_TOTAL.notna()].copy()
n = step(2, "Require baseline SCOPA-AUT total score", n, bl)

bl = bl[bl.MCATOT.notna()].copy()
n = step(3, "Require baseline MoCA", n, bl)

bl = bl[bl.MCATOT >= 21].copy()
n = step(4, "Require baseline MoCA ≥ 21 (R1 fix: m10 = MoCA<21 endpoint)", n, bl)

bl = bl[bl.time_to_event_dom3_years.notna()].copy()
n = step(5, "Require cognitive milestone follow-up data", n, bl)

bl = bl[bl.Cognitive_Group != 3].copy()
n = step(6, "Exclude baseline PD-Dementia (Cognitive_Group=3)", n, bl)

bl = bl[bl.time_to_event_dom3_years > 0].copy()
n = step(7, "Require non-zero follow-up time", n, bl)

print(f"\n  Final analytical N (R1 primary): {n}")

# ── 3. Compute / rename derived columns to match downstream expectations ─
print("\n[3/8] Computing derived columns ...")

# Best-available motor severity: prefer NP3TOT, fall back to OFF/ON
def best_np3(row):
    for c in ["NP3TOT", "NP3TOT_OFF_UNTREATED", "NP3TOT_OFF", "NP3TOT_ON"]:
        if c in row.index and pd.notna(row[c]):
            return row[c]
    return np.nan
bl["NP3TOT_BEST"] = bl.apply(best_np3, axis=1)

def best_nhy(row):
    for c in ["NHY", "NHY_OFF_UNTREATED", "NHY_OFF", "NHY_ON"]:
        if c in row.index and pd.notna(row[c]):
            return row[c]
    return np.nan
bl["NHY_BEST"] = bl.apply(best_nhy, axis=1)

bl["RBDSQ_TOTAL"] = bl["RBDSQ_13item"]

# Domain scores
for domain, items in SCOPA_DOMAINS.items():
    avail = [c for c in items if c in bl.columns]
    bl[domain] = bl[avail].sum(axis=1, min_count=max(1, len(avail)-1))

# ── 4. Race (proper PPMI 5-source + missing) ─────────────────────────────
print("\n[4/8] Race coding (proper 5-source + missing) ...")
RA_FLAGS = ["RAWHITE", "RABLACK", "RAASIAN", "RAHAWOPI", "RAINDALS"]
for c in RA_FLAGS:
    if c not in bl.columns:
        bl[c] = np.nan
ra_int = bl[RA_FLAGS].fillna(0).astype(int)
ra_sum = ra_int.sum(axis=1)

def label_race(row, total):
    if total == 0:
        return "Missing/Declined"
    if total > 1:
        return "More than one race"
    if row["RAWHITE"]   == 1: return "White"
    if row["RABLACK"]   == 1: return "Black"
    if row["RAASIAN"]   == 1: return "Asian"
    if row["RAHAWOPI"]  == 1: return "Native Hawaiian/Pacific Islander"
    if row["RAINDALS"]  == 1: return "American Indian/Alaska Native"
    return "Missing/Declined"

bl["RACE"] = [label_race(r, s) for r, s in zip(ra_int.to_dict("records"), ra_sum)]
bl["HISPLAT_LABEL"] = bl["HISPLAT"].map({0: "Not Hispanic/Latino",
                                          1: "Hispanic/Latino",
                                          2: "Declined"})

print("  RACE distribution:")
for k, v in bl.RACE.value_counts(dropna=False).items():
    print(f"    {k}: {v} ({100*v/len(bl):.1f}%)")

# Sex label
bl["SEX_LABEL"] = bl["SEX"].map({0: "Female", 1: "Male"})

# ── 5. Disease duration from PDDXDT ──────────────────────────────────────
print("\n[5/8] Disease duration from PD_Diagnosis_History.PDDXDT ...")

def parse_month(s):
    try:    return pd.to_datetime(str(s), format="%m/%Y")
    except: return pd.NaT

dx = pd.read_csv(os.path.join(RAW, "PD_Diagnosis_History_22Apr2026.csv"))
dx["PDDXDT_dt"] = dx.PDDXDT.apply(parse_month)
dx["SXDT_dt"]   = dx.SXDT.apply(parse_month)
dx_first = (dx.sort_values(["PATNO", "PDDXDT_dt"])
            .groupby("PATNO").agg(PDDXDT_dt=("PDDXDT_dt", "first"),
                                  SXDT_dt=("SXDT_dt", "first")).reset_index())

ps = pd.read_csv(os.path.join(RAW, "Participant_Status_22Apr2026.csv"))
ps["ENROLL_DT"] = ps.ENROLL_DATE.apply(parse_month)
ps["STATUS_DT"] = ps.STATUS_DATE.apply(parse_month)
ps = ps[["PATNO", "ENROLL_DT", "ENROLL_STATUS", "STATUS_DT"]]

bl = bl.merge(dx_first, on="PATNO", how="left")
bl = bl.merge(ps,       on="PATNO", how="left")

bl["disease_duration_yrs"] = ((bl.ENROLL_DT - bl.PDDXDT_dt).dt.days / 365.25)
bl["sx_duration_yrs"]      = ((bl.ENROLL_DT - bl.SXDT_dt).dt.days / 365.25)

n_dd = bl.disease_duration_yrs.notna().sum()
print(f"  Disease duration computable: {n_dd}/{len(bl)} ({100*n_dd/len(bl):.1f}%)")
print(f"    median: {bl.disease_duration_yrs.median():.2f}y, "
      f"IQR: [{bl.disease_duration_yrs.quantile(0.25):.2f}, "
      f"{bl.disease_duration_yrs.quantile(0.75):.2f}]")

# ── 6. Competing-risk event: death (Fine-Gray) ───────────────────────────
print("\n[6/8] Death / withdrawal events (Fine-Gray) ...")
cosp = pd.read_csv(os.path.join(RAW, "Conclusion_of_Study_Participation_22Apr2026.csv"))
cosp["WDDT_dt"] = cosp.WDDT.apply(parse_month)
# Per-subject death flag and date
cosp["is_death"] = cosp.WDDEATH.fillna(0).astype(float).gt(0).astype(int)
death_per_subj = (cosp.sort_values(["PATNO", "WDDT_dt"])
                  .groupby("PATNO")
                  .agg(WDDT_dt=("WDDT_dt", "first"),
                       is_death=("is_death", "max")).reset_index())
bl = bl.merge(death_per_subj, on="PATNO", how="left")
bl["is_death"] = bl["is_death"].fillna(0).astype(int)
bl["time_to_death_yrs"] = ((bl.WDDT_dt - bl.ENROLL_DT).dt.days / 365.25)
n_death = int(bl.is_death.sum())
n_death_dated = int(bl.loc[bl.is_death == 1, "time_to_death_yrs"].notna().sum())
print(f"  Deaths in cohort: {n_death} (dated: {n_death_dated})")

# Build competing-risk event variable for Fine-Gray:
#   0 = censored, 1 = cognitive milestone (primary), 2 = death before milestone
bl["fg_event"] = 0
bl.loc[bl.reached_dom3 == 1, "fg_event"] = 1
# subjects who died (is_death=1) before reaching milestone:
#   if time_to_death < time_to_event_dom3_years, then death is the competing event
death_before_event = (
    (bl.is_death == 1) & bl.time_to_death_yrs.notna() &
    (bl.time_to_death_yrs < bl.time_to_event_dom3_years) &
    (bl.reached_dom3 != 1)
)
bl.loc[death_before_event, "fg_event"] = 2
# adjust time for competing-risk frame
bl["fg_time"] = bl.time_to_event_dom3_years.copy()
bl.loc[death_before_event, "fg_time"] = bl.loc[death_before_event, "time_to_death_yrs"]

fg_counts = bl.fg_event.value_counts().sort_index().to_dict()
print(f"  Fine-Gray event distribution: {fg_counts}  "
      "(0=censored, 1=milestone, 2=death before milestone)")

# ── 7. Baseline medication-class flags ───────────────────────────────────
print("\n[7/8] Baseline medication-class flags ...")
med_path = os.path.join(PROJ, "data", "bl_medication_flags.csv")
if os.path.exists(med_path):
    med_flags = pd.read_csv(med_path)
    bl = bl.merge(med_flags, on="PATNO", how="left")
    for c in ["bl_dopamine_agonist", "bl_anticholinergic",
              "bl_alpha_blocker", "bl_antihypertensive"]:
        if c in bl.columns:
            bl[c] = bl[c].fillna(False).astype(int)
            print(f"  {c}: {bl[c].sum()} ({100*bl[c].mean():.1f}%)")
else:
    print(f"  WARNING: {med_path} not found — re-run 00_inspect_data.py")

# ── 8. Outcome columns ───────────────────────────────────────────────────
print("\n[8/8] Outcome columns ...")
bl["event"]         = bl["reached_dom3"].astype(int)
bl["time_to_event"] = bl["time_to_event_dom3_years"]

for m in [10, 11, 12, 13, 14, 15]:
    bl[f"event_m{m}"] = bl[f"m{m}everreached"].fillna(0).astype(int)

# Pure-cognitive sub-composite (secondary endpoint requested by R#2)
bl["event_pure_cognitive"] = (
    (bl.event_m10 == 1) | (bl.event_m14 == 1) | (bl.event_m15 == 1)
).astype(int)
# Time-to-first among m10/m14/m15: approximate using the existing dom3 time
# when any of m10/m14/m15 fired (dom3 covers all m10-m15 first-event time).
# For now, use time_to_event_dom3_years as a proxy — refine later if needed.
bl["time_to_pure_cognitive"] = bl.time_to_event

print(f"  Composite (m10–m15) events: {int(bl.event.sum())} / {len(bl)} "
      f"({100*bl.event.mean():.1f}%)")
print(f"  Pure-cognitive (m10+m14+m15) events: {int(bl.event_pure_cognitive.sum())} / {len(bl)} "
      f"({100*bl.event_pure_cognitive.mean():.1f}%)")
for m in [10, 11, 12, 13, 14, 15]:
    n = int(bl[f"event_m{m}"].sum())
    print(f"  m{m}everreached: {n} ({100*n/len(bl):.1f}%)")

# ── 9. Save ──────────────────────────────────────────────────────────────
out = os.path.join(DATA, "analytical_dataset_R1.csv")
bl.to_csv(out, index=False)
print(f"\nSaved primary: {out}  ({len(bl)} subjects, {bl.shape[1]} cols)")

# Sensitivity: stricter MoCA threshold (≥23, excluding subjective cognitive complaints)
bl_strict = bl[bl.MCATOT >= 23].copy()
bl_strict.to_csv(os.path.join(DATA, "analytical_dataset_R1_strictMoCA23.csv"),
                 index=False)
print(f"Saved strict-MoCA23 sensitivity: {len(bl_strict)} subjects, "
      f"{int(bl_strict.event.sum())} events")

# Sensitivity: replicate original (≥2y rule, no MoCA threshold) for direct
# comparability with the original Table 2.
master_replication = master[master.EVENT_ID == "BL"].copy()
master_replication = master_replication[master_replication.COHORT == 1]
master_replication = master_replication[master_replication.SCAU_TOTAL.notna()]
master_replication = master_replication[master_replication.MCATOT.notna()]
master_replication = master_replication[master_replication.time_to_event_dom3_years.notna()]
master_replication = master_replication[master_replication.Cognitive_Group != 3]
master_replication = master_replication[
    (master_replication.reached_dom3 == 1) |
    (master_replication.time_to_event_dom3_years >= 2)
]
# Add the same derived columns for compatibility
master_replication["NP3TOT_BEST"] = master_replication.apply(best_np3, axis=1)
master_replication["NHY_BEST"]    = master_replication.apply(best_nhy, axis=1)
master_replication["RBDSQ_TOTAL"] = master_replication["RBDSQ_13item"]
for domain, items in SCOPA_DOMAINS.items():
    avail = [c for c in items if c in master_replication.columns]
    master_replication[domain] = master_replication[avail].sum(
        axis=1, min_count=max(1, len(avail)-1))
master_replication["event"] = master_replication["reached_dom3"].astype(int)
master_replication["time_to_event"] = master_replication["time_to_event_dom3_years"]
master_replication.to_csv(os.path.join(DATA, "analytical_dataset_R1_v0replication.csv"),
                          index=False)
print(f"Saved v0 replication: {master_replication.PATNO.nunique()} subjects, "
      f"{int(master_replication.event.sum())} events")

# ── 10. Persist exclusion log ────────────────────────────────────────────
log_df = pd.DataFrame(flow)
log_df.to_csv(os.path.join(LOGS, "exclusion_log_R1.csv"), index=False)

with open(os.path.join(LOGS, "exclusion_log_R1.md"), "w") as f:
    f.write("# Exclusion Cascade — R1 Revision\n\n")
    f.write(f"Source: PPMI Master Merged v2.1 (2026-05-13)\n\n")
    f.write("| Step | Criterion | Before | After | Excluded |\n")
    f.write("|------|-----------|-------:|------:|---------:|\n")
    for _, r in log_df.iterrows():
        f.write(f"| {r.step} | {r.reason} | {r.n_before} | {r.n_after} | {r.excluded} |\n")
    f.write(f"\n**Final R1 primary cohort:** N = {len(bl)}, "
            f"composite events = {int(bl.event.sum())} "
            f"({100*bl.event.mean():.1f}%)\n\n")
    f.write(f"**Sensitivity cohorts:**\n")
    f.write(f"- strict MoCA ≥ 23: N = {len(bl_strict)}, "
            f"events = {int(bl_strict.event.sum())}\n")
    f.write(f"- v0 replication (≥2y rule, no MoCA threshold): "
            f"N = {master_replication.PATNO.nunique()}, "
            f"events = {int(master_replication.event.sum())}\n")

# Summary JSON
summary = {
    "N_primary": int(len(bl)),
    "events_composite": int(bl.event.sum()),
    "events_pure_cognitive": int(bl.event_pure_cognitive.sum()),
    "events_per_milestone": {f"m{m}": int(bl[f"event_m{m}"].sum()) for m in range(10, 16)},
    "fg_event_counts": fg_counts,
    "deaths_total": n_death,
    "race_distribution": bl.RACE.value_counts().to_dict(),
    "disease_duration_median_yrs": float(bl.disease_duration_yrs.median()),
    "ledd_nonmiss": int(bl.LEDD_TOTAL_CURRENT.notna().sum()),
    "ledd_median_nonmiss": float(bl.LEDD_TOTAL_CURRENT.median()),
    "saa_pos_subjects": int(bl.SAA_POS_Subject.eq("SAA+").sum()),
    "saa_neg_subjects": int(bl.SAA_POS_Subject.eq("SAA-").sum()),
    "n_strict_moca23": int(len(bl_strict)),
    "n_v0_replication": int(master_replication.PATNO.nunique()),
    "seed": SEED,
}
with open(os.path.join(DATA, "cohort_summary_R1.json"), "w") as f:
    json.dump(summary, f, indent=2, default=str)

print("\n=== R1 COHORT BUILD COMPLETE ===")
print(f"  Primary cohort N = {len(bl)}, events = {int(bl.event.sum())}")
print(f"  Sensitivity (strict MoCA≥23) N = {len(bl_strict)}")
print(f"  Sensitivity (v0 replication) N = {master_replication.PATNO.nunique()}")
