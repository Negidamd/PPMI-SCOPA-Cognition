#!/usr/bin/env python3
"""
00_inspect_data.py — Inspect PPMI master + auxiliary files to confirm
availability of new covariates and competing-risk data needed for R1 revision.

Produces: logs/data_inspection_R1.json + console report.
"""
import os, json, sys
import pandas as pd
import numpy as np

PPMI = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/3-resources/datasets/PPMI"
RAW  = os.path.join(PPMI, "PPMI_April2026")
PROJ = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/1b-papers/SCOPA_Cognition_Study/revision_R1"
LOGS = os.path.join(PROJ, "logs")
os.makedirs(LOGS, exist_ok=True)

print("=" * 70)
print("R1 DATA INSPECTION")
print("=" * 70)

# -- Load master at BL only for subject-level columns ---------------------
print("\n[1/6] Loading master, baseline-only frame ...")
master = pd.read_csv(os.path.join(PPMI, "PPMI_Master_Merged.csv"), low_memory=False)
bl = master[master.EVENT_ID == "BL"].copy()
print(f"  Master rows: {len(master):,}; baseline rows: {len(bl):,}; subjects (BL): {bl.PATNO.nunique():,}")

# Subset to PD with SCOPA-AUT total and MoCA at BL (matches study population)
pd_bl = bl[(bl.COHORT == 1) & bl.SCAU_TOTAL.notna() & bl.MCATOT.notna()].copy()
print(f"  PD + BL SCOPA + BL MoCA: {pd_bl.PATNO.nunique():,}")

study_patnos = set(pd_bl.PATNO)

# -- Check availability of key covariates already in master ---------------
print("\n[2/6] Master covariate availability (PD-BL subset):")
report = {}
for col in ["LEDD_TOTAL_CURRENT", "MSEADLG", "RBDSQ_TOTAL", "NHY_BEST",
            "NP3TOT_BEST", "EDUCYRS", "AGE_AT_VISIT", "UPSIT_PRCNTGE",
            "SAA_Status_Combined", "SAA_POS", "SAA_POS_Subject",
            "Cognitive_Group", "time_to_event_dom3_years", "reached_dom3"]:
    if col not in pd_bl.columns:
        report[col] = {"exists": False}
        print(f"  {col:30s} MISSING column")
        continue
    n = pd_bl[col].notna().sum()
    pct = 100 * n / len(pd_bl)
    report[col] = {"exists": True, "n_nonmiss": int(n), "pct_nonmiss": round(pct, 1)}
    if pd.api.types.is_numeric_dtype(pd_bl[col]):
        report[col]["median"] = float(pd_bl[col].median()) if n else None
    else:
        vc = pd_bl[col].value_counts(dropna=True).head(8).to_dict()
        report[col]["top_values"] = {str(k): int(v) for k, v in vc.items()}
    print(f"  {col:30s} n={n:4d} ({pct:5.1f}%)")

# Per-milestone events
print("\n  Per-milestone events (m10–m15 everreached) in PD-BL subset:")
for m in range(10, 16):
    col = f"m{m}everreached"
    if col in pd_bl.columns:
        n = int(pd_bl[col].fillna(0).sum())
        report[col] = {"exists": True, "n_events": n}
        print(f"    {col}: {n} subjects ever reached")

# -- PDDXDT for disease duration -----------------------------------------
print("\n[3/6] Disease duration from PD_Diagnosis_History.PDDXDT ...")
dx = pd.read_csv(os.path.join(RAW, "PD_Diagnosis_History_22Apr2026.csv"))
dx_pat = dx[dx.PATNO.isin(study_patnos)].copy()
print(f"  Diagnosis records for study patients: {len(dx_pat)} rows, "
      f"{dx_pat.PATNO.nunique()} subjects")

# PDDXDT can be sparse — examine
def parse_month(s):
    try:
        return pd.to_datetime(str(s), format="%m/%Y")
    except Exception:
        try:
            return pd.to_datetime(str(s))
        except Exception:
            return pd.NaT

dx_pat["PDDXDT_dt"] = dx_pat.PDDXDT.apply(parse_month)
dx_pat["SXDT_dt"]   = dx_pat.SXDT.apply(parse_month)
# Take first non-null PDDXDT per subject
dx_first = (dx_pat.sort_values(["PATNO", "PDDXDT_dt"])
            .groupby("PATNO").agg(PDDXDT_dt=("PDDXDT_dt", "first"),
                                  SXDT_dt=("SXDT_dt", "first")).reset_index())

print(f"  Subjects with PDDXDT: {dx_first.PDDXDT_dt.notna().sum()} / {len(dx_first)}")
print(f"  Subjects with SXDT:   {dx_first.SXDT_dt.notna().sum()} / {len(dx_first)}")

# Enrollment date from Participant_Status
ps = pd.read_csv(os.path.join(RAW, "Participant_Status_22Apr2026.csv"))
ps = ps[ps.PATNO.isin(study_patnos)].copy()
ps["ENROLL_DT"] = ps.ENROLL_DATE.apply(parse_month)
ps_first = ps[["PATNO", "ENROLL_DT", "ENROLL_STATUS", "STATUS_DATE"]].copy()
ps_first["STATUS_DT"] = ps_first.STATUS_DATE.apply(parse_month)

merged = dx_first.merge(ps_first, on="PATNO", how="inner")
merged["disease_duration_yrs"] = (
    (merged.ENROLL_DT - merged.PDDXDT_dt).dt.days / 365.25
)
n_dd = merged.disease_duration_yrs.notna().sum()
print(f"  Subjects with computable disease duration (PDDXDT→ENROLL): "
      f"{n_dd} / {len(merged)}")
if n_dd:
    print(f"    median={merged.disease_duration_yrs.median():.2f}y, "
          f"IQR=[{merged.disease_duration_yrs.quantile(0.25):.2f}, "
          f"{merged.disease_duration_yrs.quantile(0.75):.2f}]")
report["disease_duration"] = {
    "n_subjects": int(n_dd),
    "pct": round(100 * n_dd / len(merged), 1),
    "median_yrs": float(merged.disease_duration_yrs.median()) if n_dd else None,
}

# -- Enrollment status + withdrawal ---------------------------------------
print("\n[4/6] ENROLL_STATUS distribution (PD-BL subset):")
es_counts = ps_first.ENROLL_STATUS.value_counts(dropna=False).to_dict()
for k, v in es_counts.items():
    print(f"    {k}: {v}")
report["enroll_status"] = {str(k): int(v) for k, v in es_counts.items()}

# Conclusion of study participation (for death flag)
cosp = pd.read_csv(os.path.join(RAW, "Conclusion_of_Study_Participation_22Apr2026.csv"))
cosp_pat = cosp[cosp.PATNO.isin(study_patnos)].copy()
print(f"\n  Concl of Study Participation records: {len(cosp_pat)} rows, "
      f"{cosp_pat.PATNO.nunique()} subjects")
death_n = int(cosp_pat.WDDEATH.fillna(0).astype(float).gt(0).sum())
health_n = int(cosp_pat.WDHEALTH.fillna(0).astype(float).gt(0).sum())
ltfu_n = int(cosp_pat.WDLTFU.fillna(0).astype(float).gt(0).sum())
print(f"    WDDEATH=1 (death): {death_n}")
print(f"    WDHEALTH=1 (health-related): {health_n}")
print(f"    WDLTFU=1 (lost to follow-up): {ltfu_n}")
report["withdrawal"] = {"death": death_n, "health": health_n, "ltfu": ltfu_n}

# -- Medications at baseline ----------------------------------------------
print("\n[5/6] Concomitant medications — class flags at baseline ...")
cm = pd.read_csv(os.path.join(RAW, "Concomitant_Medication_Log_22Apr2026.csv"))
cm_pat = cm[cm.PATNO.isin(study_patnos)].copy()
print(f"  Med records for study patients: {len(cm_pat):,}")

# Drug-class keyword sets (case-insensitive matching on CMTRT)
CLASSES = {
    "dopamine_agonist": ["pramipexole", "ropinirole", "rotigotine",
                          "apomorphine", "mirapex", "requip", "neupro"],
    "anticholinergic":  ["benztropine", "trihexyphenidyl", "amantadine",
                          "oxybutynin", "tolterodine", "solifenacin",
                          "darifenacin", "fesoterodine", "trospium",
                          "cogentin", "artane"],
    "alpha_blocker":    ["tamsulosin", "doxazosin", "terazosin", "alfuzosin",
                          "silodosin", "prazosin", "flomax"],
    "antihypertensive": ["lisinopril", "losartan", "valsartan", "enalapril",
                          "ramipril", "amlodipine", "metoprolol", "atenolol",
                          "carvedilol", "hydrochlorothiazide", "chlorthalidone",
                          "spironolactone", "olmesartan", "irbesartan",
                          "candesartan", "benazepril", "captopril", "diltiazem",
                          "verapamil", "bisoprolol"],
}

# Match medications active at baseline:
# treat as "active at baseline" if STARTDT <= ENROLL_DATE AND (STOPDT is null OR STOPDT >= ENROLL_DATE)
cm_pat["STARTDT_dt"] = cm_pat.STARTDT.apply(parse_month)
cm_pat["STOPDT_dt"]  = cm_pat.STOPDT.apply(parse_month)
cm_pat = cm_pat.merge(ps_first[["PATNO", "ENROLL_DT"]], on="PATNO", how="left")
cm_pat["active_at_bl"] = (
    (cm_pat.STARTDT_dt <= cm_pat.ENROLL_DT) &
    (cm_pat.STOPDT_dt.isna() | (cm_pat.STOPDT_dt >= cm_pat.ENROLL_DT))
).fillna(False)

cm_pat["CMTRT_lower"] = cm_pat.CMTRT.fillna("").str.lower()
med_class_counts = {}
class_flags = pd.DataFrame({"PATNO": list(study_patnos)})
for cls, kws in CLASSES.items():
    cm_pat[f"is_{cls}"] = cm_pat.CMTRT_lower.apply(
        lambda s: any(k in s for k in kws))
    flag = (cm_pat[cm_pat.active_at_bl & cm_pat[f"is_{cls}"]]
            .groupby("PATNO").size().gt(0).rename(f"bl_{cls}"))
    flag = flag.reindex(class_flags.PATNO, fill_value=False).reset_index(drop=True)
    class_flags[f"bl_{cls}"] = flag.values
    med_class_counts[cls] = int(class_flags[f"bl_{cls}"].sum())
    pct = 100 * med_class_counts[cls] / len(class_flags)
    print(f"  {cls:20s} at BL: {med_class_counts[cls]:4d} ({pct:5.1f}%)")

report["medication_classes_at_bl"] = med_class_counts

# Save class flags for cohort build
class_flags.to_csv(os.path.join(PROJ, "data", "bl_medication_flags.csv"),
                   index=False)
print(f"  Saved bl_medication_flags.csv ({len(class_flags)} subjects)")

# -- Race coding deep-dive ------------------------------------------------
print("\n[6/6] Race coding deep-dive:")
RA_COLS = ["RAWHITE", "RABLACK", "RAASIAN", "RAHAWOPI", "RAINDALS", "HISPLAT"]
for c in RA_COLS:
    if c in pd_bl.columns:
        vc = pd_bl[c].value_counts(dropna=False).to_dict()
        print(f"  {c}: {vc}")
        report[f"race_{c}"] = {str(k): int(v) for k, v in vc.items()}

# Multi-race / mixed
race_flags_only = pd_bl[RA_COLS[:-1]].fillna(0).astype(int)  # exclude HISPLAT for race
race_flags_only["sum_race"] = race_flags_only.sum(axis=1)
print(f"\n  Race-flag sum distribution (count of race indicators per subject):")
print(f"    {race_flags_only.sum_race.value_counts().sort_index().to_dict()}")
report["race_flag_sum"] = race_flags_only.sum_race.value_counts().sort_index().to_dict()

# -- SAA distribution -----------------------------------------------------
print("\n[bonus] SAA status distribution:")
if "SAA_Status_Combined" in pd_bl.columns:
    print(f"    {pd_bl.SAA_Status_Combined.value_counts(dropna=False).to_dict()}")
if "SAA_POS_Subject" in pd_bl.columns:
    print(f"    SAA_POS_Subject: {pd_bl.SAA_POS_Subject.value_counts(dropna=False).to_dict()}")

# -- Persist report -------------------------------------------------------
with open(os.path.join(LOGS, "data_inspection_R1.json"), "w") as f:
    json.dump(report, f, indent=2, default=str)
print(f"\nSaved {LOGS}/data_inspection_R1.json")

print("\n=== INSPECTION COMPLETE ===")
