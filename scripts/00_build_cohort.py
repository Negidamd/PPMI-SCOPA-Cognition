#!/usr/bin/env python3
"""
00_build_cohort.py: build the locked analytical dataset from raw PPMI CRF files.

Uses raw files only (data/raw). No derived master file. See SAP.md.
Outputs: data/analytical_dataset.csv, data/milestone_long.csv,
         logs/exclusion_log.csv, logs/exclusion_log.md, logs/build_log.json
"""
import json, os, random, re
import numpy as np
import pandas as pd

SEED = 42
np.random.seed(SEED); random.seed(SEED)
# CATH3=1 builds the sensitivity cohort in which catheter responses score 3 instead of missing.
CATH3 = os.environ.get("CATH3") == "1"

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "data", "raw")
FREEZE = "22Apr2026"


def rd(name):
    return pd.read_csv(os.path.join(RAW, f"{name}_{FREEZE}.csv"), low_memory=False)


def month(s):
    return pd.to_datetime(s, format="%m/%Y", errors="coerce")


def years(later, earlier):
    return ((later.dt.year - earlier.dt.year) * 12 + (later.dt.month - earlier.dt.month)) / 12


BASE_EVENTS = {"SC", "BL"}
ITEMS = [f"SCAU{i}" for i in range(1, 26)]
CORE = [f"SCAU{i}" for i in range(1, 22)]
DOMAINS = {
    "dom_gi": [f"SCAU{i}" for i in range(1, 8)],
    "dom_uri": [f"SCAU{i}" for i in range(8, 14)],
    "dom_cv": ["SCAU14", "SCAU15", "SCAU16"],
    "dom_therm": ["SCAU17", "SCAU18", "SCAU20", "SCAU21"],
    "dom_pupil": ["SCAU19"],
}
URINARY = DOMAINS["dom_uri"]
log = {}
flow = []


def step(label, frame, reason_counts=None):
    n = frame.PATNO.nunique()
    prev = flow[-1]["n_after"] if flow else None
    flow.append({"step": len(flow), "criterion": label, "n_after": n,
                 "excluded": (prev - n) if prev is not None else 0,
                 "detail": json.dumps(reason_counts) if reason_counts else ""})
    print(f"{label}: {n}" + (f" (excluded {prev - n})" if prev is not None else ""))


# 1. Participants ---------------------------------------------------------
ps = rd("Participant_Status")
ps["ENROLL_DT"] = month(ps.ENROLL_DATE)
cohort = ps[ps.COHORT == 1].copy()
step("Assigned to PD cohort", cohort)

s = rd("SCOPA-AUT")
assert not s[s.EVENT_ID == "BL"].PATNO.duplicated().any()
bl = s[s.EVENT_ID == "BL"].copy()
bl["t0"] = month(bl.INFODT)
assert bl.t0.notna().all()

log["status_of_PD_cohort_with_BL_SCOPA"] = (
    cohort[cohort.PATNO.isin(bl.PATNO)].ENROLL_STATUS.value_counts().to_dict())
NOT_ENROLLED = {"Screen failed", "Excluded", "Declined", "Screened", "Screen Scheduled", "Pending"}
c1 = cohort[~cohort.ENROLL_STATUS.isin(NOT_ENROLLED)]
step("Enrolled (not screen failed, excluded, declined or pending)", c1,
     cohort[cohort.ENROLL_STATUS.isin(NOT_ENROLLED)].ENROLL_STATUS.value_counts().to_dict())

# 2. Exposure -------------------------------------------------------------
d = c1.merge(bl[["PATNO", "t0", "PTCGBOTH"] + ITEMS + ["SCAU23A", "SCAU26A", "SCAU26B", "SCAU26C", "SCAU26D"]],
             on="PATNO", how="inner")
step("Baseline SCOPA-AUT form present", d)

catheter = {c: int((d[c] == 9).sum()) for c in URINARY}
log["catheter_code_9_counts"] = catheter
log["sexual_not_applicable"] = {c: int((d[c] == 9).sum()) for c in ["SCAU22", "SCAU23", "SCAU24", "SCAU25"]}
d["catheter_any"] = (d[URINARY] == 9).any(axis=1).astype(int)
for c in URINARY:
    d[c + "_cath3"] = d[c].replace(9, 3)
if CATH3:
    d[URINARY] = d[URINARY].replace(9, 3)
d[ITEMS] = d[ITEMS].replace(9, np.nan)
for c in ITEMS:
    assert d[c].dropna().isin([0, 1, 2, 3]).all(), c

d["n_core_missing"] = d[CORE].isna().sum(axis=1)
d = d[d.n_core_missing <= 2].copy()
step("At most 2 of 21 non-sexual SCOPA-AUT items missing", d)

d["scopa_total21"] = d[CORE].mean(axis=1) * 21
for dom, items in DOMAINS.items():
    n = len(items)
    allowed = 1 if n >= 4 else 0
    ok = d[items].isna().sum(axis=1) <= allowed
    d[dom] = (d[items].mean(axis=1) * n).where(ok)

# Demographics and covariates -----------------------------------------------
dm = rd("Demographics")
assert not dm.PATNO.duplicated().any()
d = d.merge(dm[["PATNO", "SEX", "BIRTHDT", "HISPLAT", "RAASIAN", "RABLACK", "RAHAWOPI",
                "RAINDALS", "RANOS", "RAWHITE"]], on="PATNO", how="left")
# PPMI SEX: 0 female, 1 male. Verified from sex-specific SCOPA-AUT items.
assert d.loc[d.SEX == 0, "SCAU22"].notna().sum() <= 2
d["male"] = d.SEX
ra = d[["RAWHITE", "RABLACK", "RAASIAN", "RAHAWOPI", "RAINDALS"]].fillna(0).astype(int)
names = np.array(["White", "Black", "Asian", "Native Hawaiian/Pacific Islander",
                  "American Indian/Alaska Native"])
d["race"] = [("Not reported" if r.sum() == 0 else "More than one race" if r.sum() > 1
              else names[r.values.argmax()]) for _, r in ra.iterrows()]

age = rd("Age_at_visit")
age_bl = age[age.EVENT_ID == "BL"].drop_duplicates("PATNO")[["PATNO", "AGE_AT_VISIT"]].rename(
    columns={"AGE_AT_VISIT": "age"})
d = d.merge(age_bl, on="PATNO", how="left")

se = rd("Socio-Economics").sort_values("PATNO")
se["edu"] = pd.to_numeric(se.EDUCYRS, errors="coerce").where(lambda x: x < 40)
if "EDUCYRS_EQUIV" in se:
    se["edu"] = se.edu.fillna(pd.to_numeric(se.EDUCYRS_EQUIV, errors="coerce"))
edu = se[se.edu.notna()].groupby("PATNO").edu.first().reset_index()
d = d.merge(edu, on="PATNO", how="left")


def at_baseline(frame, cols, allow_sc=True):
    """Value at BL; if absent, the SC form (a pre-baseline screening assessment)."""
    f = frame[frame.EVENT_ID.isin(BASE_EVENTS if allow_sc else {"BL"})].copy()
    f["_o"] = f.EVENT_ID.map({"BL": 0, "SC": 1})
    f = f.sort_values(["PATNO", "_o"])
    return f.groupby("PATNO")[cols].first().reset_index()


mc = rd("Montreal_Cognitive_Assessment__MoCA_")
mc["MCATOT"] = pd.to_numeric(mc.MCATOT, errors="coerce")
assert mc.MCATOT.dropna().between(0, 30).all()
d = d.merge(at_baseline(mc[mc.MCATOT.notna()], ["MCATOT"]).rename(columns={"MCATOT": "moca"}),
            on="PATNO", how="left")
d = d.merge(mc[(mc.EVENT_ID == "BL") & mc.MCATOT.notna()][["PATNO"]].assign(moca_from_bl=1), on="PATNO", how="left")
d["moca_from_bl"] = d.moca_from_bl.fillna(0).astype(int)
d0 = d.copy()
d = d[d.moca.notna()].copy()
step("Baseline MoCA available", d)

# MDS-UPDRS Part III at baseline: untreated exam, else OFF, else ON
p3 = rd("MDS-UPDRS_Part_III")
p3b = p3[p3.EVENT_ID == "BL"].copy()
for c in ["NP3TOT", "NHY"]:
    p3b[c] = pd.to_numeric(p3b[c], errors="coerce")
p3b.loc[p3b.NHY > 5, "NHY"] = np.nan
p3b["_rank"] = np.select(
    [(p3b.PDTRTMNT == 0) | (p3b.PDMEDYN == 0), p3b.PDSTATE == "OFF", p3b.PDSTATE == "ON"],
    [0, 1, 2], default=3)
p3b["updrs3_state"] = np.select(
    [p3b._rank == 0, p3b._rank == 1, p3b._rank == 2], ["untreated", "OFF", "ON"], default="unspecified")
p3s = p3b[p3b.NP3TOT.notna()].sort_values(["PATNO", "_rank"]).drop_duplicates("PATNO")
d = d.merge(p3s[["PATNO", "NP3TOT", "NHY", "updrs3_state"]].rename(columns={"NP3TOT": "updrs3", "NHY": "hy"}),
            on="PATNO", how="left")

mse = rd("Modified_Schwab___England_Activities_of_Daily_Living")
mse["MSEADLG"] = pd.to_numeric(mse.MSEADLG, errors="coerce")
mse = mse[mse.MSEADLG.between(0, 100)]
d = d.merge(at_baseline(mse, ["MSEADLG"]).rename(columns={"MSEADLG": "schwab"}), on="PATNO", how="left")

# GDS-15, standard scoring (reverse keyed: SATIS, GSPIR, HAPPY, ALIVE, ENRGY)
gds = rd("Geriatric_Depression_Scale__Short_Version_")
g_pos = ["GDSDROPD", "GDSEMPTY", "GDSBORED", "GDSAFRAD", "GDSHLPLS", "GDSHOME", "GDSMEMRY", "GDSWRTLS", "GDSHOPLS", "GDSBETER"]
g_rev = ["GDSSATIS", "GDSGSPIR", "GDSHAPPY", "GDSALIVE", "GDSENRGY"]
gx = gds[g_pos + g_rev].apply(pd.to_numeric, errors="coerce").where(lambda x: x.isin([0, 1]))
gds["gds15"] = gx[g_pos].sum(axis=1, min_count=10) + (1 - gx[g_rev]).sum(axis=1, min_count=5)
gds.loc[gx.isna().any(axis=1), "gds15"] = np.nan
d = d.merge(at_baseline(gds[gds.gds15.notna()], ["gds15"]), on="PATNO", how="left")

# RBDSQ, 0-13, Stiasny-Kolster 2007
rb = rd("REM_Sleep_Behavior_Disorder_Screening_Questionnaire")
q12 = ["DRMVIVID", "DRMAGRAC", "DRMNOCTB", "SLPLMBMV", "SLPINJUR", "DRMVERBL", "DRMFIGHT",
       "DRMUMV", "DRMOBJFL", "MVAWAKEN", "DRMREMEM", "SLPDSTRB"]
q10 = ["STROKE", "HETRA", "PARKISM", "RLS", "NARCLPSY", "DEPRS", "EPILEPSY", "BRNINFM", "CNSOTH"]
rx = rb[q12].apply(pd.to_numeric, errors="coerce").where(lambda x: x.isin([0, 1]))
fx = rb[q10].apply(pd.to_numeric, errors="coerce")
rb["rbdsq"] = rx.sum(axis=1) + (fx.eq(1).any(axis=1)).astype(int)
rb.loc[rx.isna().any(axis=1), "rbdsq"] = np.nan
d = d.merge(at_baseline(rb[rb.rbdsq.notna()], ["rbdsq"]), on="PATNO", how="left")

# Disease duration at baseline
dx = rd("PD_Diagnosis_History")
dx["dxdt"] = month(dx.PDDXDT); dx["sxdt"] = month(dx.SXDT)
dx = dx.sort_values("dxdt").groupby("PATNO")[["dxdt", "sxdt"]].first().reset_index()
d = d.merge(dx, on="PATNO", how="left")
d["dis_dur"] = years(d.t0, d.dxdt).clip(lower=0)

# Baseline LEDD: dose active in the baseline month ---------------------------
led = rd("LEDD_Concomitant_Medication_Log")
led["st"] = month(led.STARTDT); led["sp"] = month(led.STOPDT)
led = led.merge(d[["PATNO", "t0"]], on="PATNO")
LD_NAME = (r"dopa|levo|sinemet|madopar|stalevo|rytary|duopa|inbrija|dhivy|crexont|parcopa|prolopa|"
           r"benserazid|nacom|isicom|duellin|lecado|syndopa|tidomet")
led["isLD"] = led.LEDTRT.astype(str).str.lower().str.contains(LD_NAME, regex=True)
act = led[(led.st <= led.t0) & (led.sp.isna() | (led.sp >= led.t0))].copy()
# A row stopping in the baseline month is a dose change when a row of the same class starts that month.
new_rows = set(zip(act[act.st == act.t0].PATNO, act[act.st == act.t0].isLD))
stopped = (act.sp == act.t0) & (act.st < act.t0)
replaced = pd.Series([(pid, c) in new_rows for pid, c in zip(act.PATNO, act.isLD)], index=act.index)
log["ledd_rows_dropped_dose_change"] = int((stopped & replaced).sum())
act = act[~(stopped & replaced)].copy()
d["treated_bl"] = d.PATNO.isin(act.PATNO).astype(int)

act["L"] = pd.to_numeric(act.LEDD, errors="coerce")
act["f"] = act.LEDD.astype(str).str.extract(r"LD x ([0-9.]+)", expand=False).astype(float)
combo = act.f.notna() & act.isLD          # levodopa + COMT inhibitor in one tablet
comt = act.f.notna() & ~act.isLD          # separate COMT inhibitor, multiplies the levodopa dose
ld_c = pd.to_numeric(act.LEDDSTRMG, errors="coerce") * pd.to_numeric(act.LEDDOSE, errors="coerce") * pd.to_numeric(act.LEDDOSFRQ, errors="coerce")
act["ld"] = act.L.where(act.isLD & ~combo)
act.loc[combo, "ld"] = ld_c[combo]
act["own"] = act.L.where(~combo & ~comt)
act.loc[combo, "own"] = (ld_c * (1 + act.f))[combo]
unknown = set(act[act.own.isna() & ~comt].PATNO)   # dose not recorded, or combination tablet without strength
ld_tot = act.groupby("PATNO").ld.sum()
fac = act[comt].copy()
fac["add"] = fac.f * fac.PATNO.map(ld_tot).fillna(0)
ledd = act.groupby("PATNO").own.sum().add(fac.groupby("PATNO")["add"].sum(), fill_value=0)
d["ledd"] = d.PATNO.map(ledd).fillna(0.0)
d.loc[d.PATNO.isin(unknown), "ledd"] = np.nan
log["ledd_unknown_dose_participants"] = int(d.PATNO.isin(unknown).sum())
log["ledd_rows_without_start_date_for_cohort"] = int(led.st.isna().sum())

# Other medications active at baseline
cm = rd("Concomitant_Medication_Log")
cm["st"] = month(cm.STARTDT); cm["sp"] = month(cm.STOPDT)
cm = cm.merge(d[["PATNO", "t0"]], on="PATNO")
ongoing = pd.to_numeric(cm.ONGOING, errors="coerce").eq(1)
cma = cm[(cm.st <= cm.t0) & (cm.sp.isna() | (cm.sp >= cm.t0) | ongoing)].copy()
cma = cma[pd.to_numeric(cma.ROUTE, errors="coerce").ne(8)]   # topical preparations have no systemic effect
cma["name"] = (cma.CMTRT.fillna("") + " " + cma.WHODRUG.fillna("")).str.lower()
ALPHA = r"tamsulosin|flomax|alfuzosin|uroxatral|silodosin|rapaflo|terazosin|hytrin|doxazosin|cardura|prazosin|minipress"
HTN = (r"lisinopril|zestril|prinivil|enalapril|vasotec|renitec|ramipril|altace|tritace|benazepril|lotensin|captopril|quinapril|fosinopril|"
       r"perindopril|coversyl|trandolapril|losartan|cozaar|hyzaar|valsartan|diovan|exforge|irbesartan|avapro|aprovel|candesartan|atacand|"
       r"olmesartan|benicar|olmetec|telmisartan|micardis|azilsartan|amlodipine|amlodipin|norvasc|caduet|nifedipine|adalat|procardia|felodipine|"
       r"plendil|nisoldipine|isradipin|lercanidipine|diltiazem|cardizem|tiazac|verapamil|calan|isoptin|hydrochlorothiazide|hydrochlorthiazide|hctz|"
       r"microzide|thiazid|chlorthalidone|indapamide|natrilix|furosemide|lasix|torsemide|torasemid|demadex|bumetanide|spironolactone|aldactone|triamterene|"
       r"dyazide|maxzide|metoprolol|toprol|lopressor|beloc|atenolol|tenormin|bisoprolol|concor|zebeta|carvedilol|coreg|nebivolol|bystolic|"
       r"nebilet|labetalol|propranolol|inderal|nadolol|clonidine|catapres|hydralazine|minoxidil|methyldopa")
ACH = (r"oxybutynin|ditropan|tolterodine|detrol|solifenacin|vesicare|trospium|darifenacin|fesoterodine|toviaz|"
       r"trihexyphenidyl|artane|benztropine|cogentin|biperiden|amitriptyline|nortriptyline|imipramine|"
       r"doxepin|hydroxyzine|diphenhydramine|paroxetine")
for nm, rx_ in [("alpha_blocker", ALPHA), ("antihypertensive", HTN), ("anticholinergic", ACH)]:
    hit = set(cma[cma.name.str.contains(rx_, regex=True)].PATNO)
    d[nm] = d.PATNO.isin(hit).astype(int)

# Vital signs, descriptive
vs = rd("Vital_Signs")
for c in ["SYSSUP", "SYSSTND", "DIASUP", "DIASTND"]:
    vs[c] = pd.to_numeric(vs[c], errors="coerce")
vs["sbp_drop"] = vs.SYSSUP - vs.SYSSTND
vs["dbp_drop"] = vs.DIASUP - vs.DIASTND
d = d.merge(at_baseline(vs[vs.sbp_drop.notna()], ["sbp_drop", "dbp_drop"], allow_sc=False), on="PATNO", how="left")
d["oh_bl"] = ((d.sbp_drop >= 20) | (d.dbp_drop >= 10)).where(d.sbp_drop.notna()).astype(float)

# Era and cohort type
d["era2"] = (d.ENROLL_DT >= pd.Timestamp("2020-01-01")).astype(int)
gen = ["ENRLLRRK2", "ENRLGBA", "ENRLSNCA", "ENRLPRKN", "ENRLPINK1"]
d["genetic_enrolled"] = (d[gen].fillna(0).sum(axis=1) > 0).astype(int)

# Genetics and SAA
gc = rd("iu_genetic_consensus_20251025").drop_duplicates("PATNO")
for c in ["LRRK2", "GBA"]:
    gc[c.lower() + "_carrier"] = gc[c].astype(str).str.strip().str.upper().map(
        lambda x: np.nan if x in {"NAN", ""} else (0.0 if x in {"0", "0.0", "NO", "WT", "NEGATIVE"} else 1.0))
gc["apoe4"] = gc.APOE.astype(str).str.contains("4").astype(float).where(gc.APOE.notna())
d = d.merge(gc[["PATNO", "lrrk2_carrier", "gba_carrier", "apoe4"]], on="PATNO", how="left")
log["raw_LRRK2_values"] = gc.LRRK2.astype(str).value_counts().head(8).to_dict()
log["raw_GBA_values"] = gc.GBA.astype(str).value_counts().head(8).to_dict()

saa = rd("SAA_Biospecimen_Analysis_Results")
saa = saa[saa.CLINICAL_EVENT.isin(["BL", "SC"]) | True]
log["SAA_status_values"] = saa.SAA_Status.astype(str).value_counts().to_dict()
log["SAA_type_values"] = saa.TYPE.astype(str).value_counts().head(6).to_dict()
sb = saa[saa.CLINICAL_EVENT == "BL"].copy()
pos = sb.SAA_Status.astype(str).str.lower().str.contains("positive")
neg = sb.SAA_Status.astype(str).str.lower().str.contains("negative")
d["saa"] = np.where(d.PATNO.isin(sb[pos].PATNO), 1.0, np.where(d.PATNO.isin(sb[neg].PATNO), 0.0, np.nan))

# 3. Outcomes -------------------------------------------------------------
T0 = d.set_index("PATNO").t0
ids = set(d.PATNO)


def add_t(f, datecol="INFODT"):
    f = f[f.PATNO.isin(ids)].copy()
    f["date"] = month(f[datecol])
    f["t"] = years(f.date, f.PATNO.map(T0))
    return f


rows = []
# m10
f = add_t(mc[mc.MCATOT.notna()])
f["flag"] = (f.MCATOT < 21).astype(int); f["m"] = "m10"
rows.append(f[["PATNO", "EVENT_ID", "t", "m", "flag"]])
# m11-13
p1 = rd("MDS-UPDRS_Part_I")
for col_, m_ in [("NP1COG", "m11"), ("NP1HALL", "m12"), ("NP1APAT", "m13")]:
    f = add_t(p1)
    f[col_] = pd.to_numeric(f[col_], errors="coerce")
    f = f[f[col_].between(0, 4)]
    f["flag"] = (f[col_] >= 3).astype(int); f["m"] = m_
    rows.append(f[["PATNO", "EVENT_ID", "t", "m", "flag"]])
# m14
cc = rd("Cognitive_Categorization")
f = add_t(cc)
f["COGSTATE"] = pd.to_numeric(f.COGSTATE, errors="coerce")
f = f[f.COGSTATE.notna()]
f["flag"] = (f.COGSTATE == 3).astype(int); f["m"] = "m14"
rows.append(f[["PATNO", "EVENT_ID", "t", "m", "flag"]])
# m15: visits with investigator functional rating, joined to cognitive tests at the same visit
hv = rd("Hopkins_Verbal_Learning_Test_-_Revised")[["PATNO", "EVENT_ID", "DVT_TOTAL_RECALL", "DVT_RECOG_DISC_INDEX"]]
jl = rd("Benton_Judgement_of_Line_Orientation")[["PATNO", "EVENT_ID", "DVS_JLO_MSSAE"]]
sd = rd("Symbol_Digit_Modalities_Test")[["PATNO", "EVENT_ID", "DVT_SDM"]]
ln = rd("Letter_-_Number_Sequencing")[["PATNO", "EVENT_ID", "DVS_LNS"]]
sf = rd("Modified_Semantic_Fluency")[["PATNO", "EVENT_ID", "DVT_SFTANIM"]]
np_ = hv
for x in [jl, sd, ln, sf]:
    np_ = np_.merge(x.drop_duplicates(["PATNO", "EVENT_ID"]), on=["PATNO", "EVENT_ID"], how="outer")
np_ = np_.drop_duplicates(["PATNO", "EVENT_ID"])
for c in np_.columns[2:]:
    np_[c] = pd.to_numeric(np_[c], errors="coerce")
np_["dom_mem"] = (np_.DVT_TOTAL_RECALL <= 35) | (np_.DVT_RECOG_DISC_INDEX <= 35)
np_["dom_vis"] = np_.DVS_JLO_MSSAE <= 5.5
np_["dom_spd"] = np_.DVT_SDM <= 35
np_["dom_exe"] = (np_.DVS_LNS <= 5.5) | (np_.DVT_SFTANIM <= 35)
np_["n_dom"] = np_[["dom_mem", "dom_vis", "dom_spd", "dom_exe"]].sum(axis=1)
f = add_t(cc)
f["FNCDTCOG"] = pd.to_numeric(f.FNCDTCOG, errors="coerce")
f = f[f.FNCDTCOG.notna()].merge(np_[["PATNO", "EVENT_ID", "n_dom"]], on=["PATNO", "EVENT_ID"], how="left")
f["flag"] = ((f.n_dom >= 2) & (f.FNCDTCOG == 1)).astype(int); f["m"] = "m15"
rows.append(f[["PATNO", "EVENT_ID", "t", "m", "flag"]])

L = pd.concat(rows, ignore_index=True)
log["outcome_rows_missing_date"] = int(L.t.isna().sum())

# Rows with no INFODT: use AGE_AT_VISIT difference
ageL = age.merge(age_bl, on="PATNO")
ageL["t_age"] = ageL.AGE_AT_VISIT - ageL.age
L = L.merge(ageL[["PATNO", "EVENT_ID", "t_age"]].drop_duplicates(["PATNO", "EVENT_ID"]), on=["PATNO", "EVENT_ID"], how="left")
log["t_vs_age_abs_diff_q50_q99"] = [float(L.dropna(subset=["t", "t_age"]).eval("abs(t-t_age)").quantile(q)) for q in (.5, .99)]
L["t"] = L.t.fillna(L.t_age)
L["is_base"] = L.EVENT_ID.isin(BASE_EVENTS)
L["post"] = (~L.is_base) & (L.t > 0)
log["nonbase_rows_on_or_before_t0"] = int(((~L.is_base) & (L.t <= 0)).sum())
SCHEDULED = re.compile(r"^(V\d\d|R\d\d)$")
L["scheduled"] = L.EVENT_ID.astype(str).map(lambda x: bool(SCHEDULED.match(x)))
if not CATH3:
    L.to_csv(os.path.join(PROJ, "data", "milestone_long.csv"), index=False)

MS = ["m10", "m11", "m12", "m13", "m14", "m15"]
prev = L[L.is_base & (L.flag == 1)].groupby("m").PATNO.apply(set).to_dict()
for m in MS:
    d[f"bl_{m}"] = d.PATNO.isin(prev.get(m, set())).astype(int)
d["bl_any"] = d[[f"bl_{m}" for m in MS]].max(axis=1)
reasons = {m: int(d[f"bl_{m}"].sum()) for m in MS}
log["cog_rating_available_at_baseline"] = int(d.PATNO.isin(L[L.is_base & L.m.eq("m14")].PATNO).sum())
d = d[d.bl_any == 0].copy()
step("Free of all cognition milestones at baseline", d, reasons)
if not CATH3:
    d[["PATNO", "age", "male", "edu", "moca", "updrs3", "hy", "gds15", "rbdsq", "scopa_total21", "ledd",
       "genetic_enrolled", "era2", "ENROLL_STATUS"]].to_csv(
        os.path.join(PROJ, "data", "eligible_before_followup.csv"), index=False)

P = L[L.post & L.PATNO.isin(set(d.PATNO))]
last = P.groupby("PATNO").t.max().rename("t_last")
d["t_last"] = d.PATNO.map(last)
d = d[d.t_last.notna()].copy()
step("At least one post-baseline outcome assessment", d)
P = P[P.PATNO.isin(set(d.PATNO))]


def endpoint(name, ms, frame=P, base=d):
    sub = frame[frame.m.isin(ms)]
    ev = sub[sub.flag == 1].groupby("PATNO").t.min()
    cen = sub.groupby("PATNO").t.max()
    base[f"e_{name}"] = base.PATNO.map(ev).notna().astype(int)
    base[f"t_{name}"] = base.PATNO.map(ev).fillna(base.PATNO.map(cen))
    # time of the last negative assessment, for interval censoring
    tmp = sub.merge(ev.rename("tev"), on="PATNO", how="left")
    lastneg = tmp[(tmp.tev.isna() | (tmp.t < tmp.tev))].groupby("PATNO").t.max()
    base[f"tl_{name}"] = base.PATNO.map(lastneg).fillna(0.0)


endpoint("primary", MS)
endpoint("strict", ["m10", "m14", "m15"])
endpoint("neuropsych", ["m12", "m13"])
for m in MS:
    endpoint(m, [m])

# Scheduled-visit-only version of the primary
endpoint("primary_sched", MS, frame=P[P.scheduled])

# Sustained: met again at the next assessment of the same milestone, or last assessment for it
sus = []
for (pid, m), g in P[P.m.isin(MS)].sort_values("t").groupby(["PATNO", "m"]):
    v = g.flag.values; t = g.t.values
    for i in range(len(v)):
        if v[i] == 1 and (i == len(v) - 1 or v[i + 1] == 1):
            sus.append((pid, t[i])); break
sus = pd.DataFrame(sus, columns=["PATNO", "t"]).groupby("PATNO").t.min()
d["e_sustained"] = d.PATNO.map(sus).notna().astype(int)
d["t_sustained"] = d.PATNO.map(sus).fillna(d.t_last)

d["first_ms"] = ""
for pid, g in P[(P.flag == 1)].sort_values("t").groupby("PATNO"):
    tmin = g.t.min()
    d.loc[d.PATNO == pid, "first_ms"] = "+".join(sorted(g[g.t == tmin].m.unique()))
d["first_ms"] = d.first_ms.where(d.e_primary == 1, "")

# Death ---------------------------------------------------------------------
cs = rd("Conclusion_of_Study_Participation")
cs["wddt"] = month(cs.WDDT)
csd = cs[pd.to_numeric(cs.WDDEATH, errors="coerce").eq(1)].sort_values("wddt").drop_duplicates("PATNO")
d = d.merge(csd[["PATNO", "wddt"]].rename(columns={"wddt": "death_dt"}), on="PATNO", how="left")
ps2 = ps.set_index("PATNO")
d["status_deceased"] = d.PATNO.map(ps2.ENROLL_STATUS).eq("Withdraw Deceased").astype(int)
d["STATUS_DT"] = d.PATNO.map(month(ps2.STATUS_DATE))
d["died"] = ((d.status_deceased == 1) | d.death_dt.notna()).astype(int)
d["death_dt"] = d.death_dt.fillna(d.STATUS_DT.where(d.died == 1))
d["t_death"] = years(d.death_dt, d.t0).where(d.died == 1)
d["withdrawn"] = d.ENROLL_STATUS.isin(["Withdrew", "Withdraw Deceased", "Lost to follow-up", "Baseline Withdraw", "Complete"]).astype(int)
log["death_status_vs_form"] = {
    "status_deceased": int(d.status_deceased.sum()), "form_death": int((d.PATNO.isin(csd.PATNO)).sum()),
    "died_any": int(d.died.sum()), "died_no_date": int((d.died.eq(1) & d.t_death.isna()).sum()),
}
d["t_death_before_t0"] = d.t_death.lt(0).astype(int)

# Baseline sub-threshold ratings of the MDS-UPDRS milestone items (sensitivity 12)
pb = p1[p1.EVENT_ID == "BL"].drop_duplicates("PATNO").set_index("PATNO")
for src, dst in [("NP1COG", "np1cog_bl"), ("NP1HALL", "np1hall_bl"), ("NP1APAT", "np1apat_bl")]:
    d[dst] = d.PATNO.map(pd.to_numeric(pb[src], errors="coerce"))

# Last recorded research diagnosis (sensitivity: idiopathic PD only)
rdx = rd("Primary_Research_Diagnosis")
rdx["dt"] = month(rdx.INFODT)
rdx = rdx[rdx.PATNO.isin(set(d.PATNO)) & pd.to_numeric(rdx.PRIMDIAG, errors="coerce").notna()].sort_values(["PATNO", "dt"])
last_dx = rdx.groupby("PATNO").PRIMDIAG.last()
d["last_dx_ipd"] = pd.to_numeric(d.PATNO.map(last_dx), errors="coerce").eq(1).astype(float).where(d.PATNO.isin(last_dx.index))
log["last_research_dx_not_idiopathic_PD"] = int(d.last_dx_ipd.eq(0).sum())

# Competing-risk coding: 1 milestone, 2 death before milestone, 0 censored
d["cr_status"] = d.e_primary
d["cr_time"] = d.t_primary
dth = (d.e_primary == 0) & (d.died == 1) & d.t_death.notna()
# Death after the last outcome assessment still competes: follow to the death date
d.loc[dth, "cr_status"] = 2
d.loc[dth, "cr_time"] = d.loc[dth, ["t_death", "t_primary"]].max(axis=1)

# 4. Save ---------------------------------------------------------------
d = d.drop(columns=["ENROLL_DT", "t0", "dxdt", "sxdt", "death_dt", "STATUS_DT"], errors="ignore")
keep_first = ["PATNO", "e_primary", "t_primary"]
d = d[keep_first + [c for c in d.columns if c not in keep_first]]
out = os.path.join(PROJ, "data", "analytical_dataset_cath3.csv" if CATH3 else "analytical_dataset.csv")
d.to_csv(out, index=False)
if CATH3:
    print(f"catheter sensitivity cohort: N={len(d)}, events={int(d.e_primary.sum())}")
    raise SystemExit

fl = pd.DataFrame(flow)
fl.to_csv(os.path.join(PROJ, "logs", "exclusion_log.csv"), index=False)
with open(os.path.join(PROJ, "logs", "exclusion_log.md"), "w") as fh:
    fh.write("# Exclusion cascade\n\n| Step | Criterion | Remaining | Excluded | Detail |\n|---|---|---:|---:|---|\n")
    for _, r in fl.iterrows():
        fh.write(f"| {r.step} | {r.criterion} | {r.n_after} | {r.excluded} | {r.detail} |\n")
    fh.write(f"\nFinal N = {len(d)}, primary events = {int(d.e_primary.sum())}\n")

log.update({
    "N": int(len(d)),
    "events": {k: int(d[f"e_{k}"].sum()) for k in ["primary", "strict", "neuropsych", "sustained"] + MS},
    "first_ms_counts": d.first_ms.value_counts().to_dict(),
    "median_t_last": float(d.t_last.median()),
    "max_t_last": float(d.t_last.max()),
    "ledd_treated": int(d.treated_bl.sum()),
    "n_moca_from_screening": int((d.moca_from_bl == 0).sum()),
    "era2": int(d.era2.sum()),
    "genetic_enrolled": int(d.genetic_enrolled.sum()),
    "race": d.race.value_counts().to_dict(),
    "missing": {c: int(d[c].isna().sum()) for c in ["age", "male", "edu", "moca", "updrs3", "hy", "schwab", "dis_dur", "ledd", "rbdsq", "gds15", "saa"]},
    "updrs3_state": d.updrs3_state.value_counts(dropna=False).to_dict(),
    "cr_status": d.cr_status.value_counts().to_dict(),
    "seed": SEED,
})
with open(os.path.join(PROJ, "logs", "build_log.json"), "w") as fh:
    json.dump(log, fh, indent=2, default=str)
print(json.dumps(log, indent=1, default=str))
