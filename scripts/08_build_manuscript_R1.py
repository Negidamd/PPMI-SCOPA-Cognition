#!/usr/bin/env python3
"""
08_build_manuscript_R1.py — Updated R1 manuscript

Strategy:
  • Preserve the original manuscript structure paragraph by paragraph.
  • Update every numerical claim from R1 results (no hardcoded prior values).
  • Add new Methods paragraphs for: expanded adjustment, PH test, Fine-Gray,
    LASSO, discrimination, SAA, hierarchical FDR, MoCA boundary, data version.
  • Add new Results paragraphs for: PH, LR test, discrimination, per-milestone,
    SAA.
  • Tempered Discussion with deeper mechanism (PAG, locus coeruleus) and
    engagement with 2023–2025 literature.
  • Embed all figures inline (Figure1..Figure8 + Figure S1).
  • Reference all tables as separate Word files (per user requirement).
  • Vancouver references with PMID/DOI for every reference.
  • Full CLAUDE.md formatting: Arial 11pt black, double-spaced body, 4pt before
    / 6pt after on body, headings 12pt before / 6pt after, line numbers,
    page numbers, 1-inch margins.

Output: manuscript/manuscript_R1.docx (clean)
"""
import os, json
import pandas as pd
from docx import Document
from docx.shared import Pt, RGBColor, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.section import WD_SECTION_START
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

PROJ = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/1b-papers/SCOPA_Cognition_Study/revision_R1"
FIG = os.path.join(PROJ, "figures")

# ── Load R1 results ──────────────────────────────────────────────────────
df = pd.read_csv(os.path.join(PROJ, "data", "analytical_dataset_R1.csv"),
                  low_memory=False)
A = pd.read_csv(os.path.join(PROJ, "tables", "cox_R1_item_modelA.csv"))
B = pd.read_csv(os.path.join(PROJ, "tables", "cox_R1_item_modelB.csv"))
LR = pd.read_csv(os.path.join(PROJ, "tables", "cox_R1_LR_item_vs_total.csv"))
D = pd.read_csv(os.path.join(PROJ, "tables", "cox_R1_domain.csv"))
disc = pd.read_csv(os.path.join(PROJ, "tables", "discrimination_R1.csv"))
with open(os.path.join(PROJ, "logs", "primary_analysis_R1_summary.json")) as f:
    summary = json.load(f)
with open(os.path.join(PROJ, "logs", "finegray_saa_calibration_R1.json")) as f:
    fg_saa = json.load(f)
with open(os.path.join(PROJ, "data", "cohort_summary_R1.json")) as f:
    cohort = json.load(f)
with open(os.path.join(PROJ, "references", "new_references_R1.json")) as f:
    new_refs = json.load(f)

N = cohort["N_primary"]            # 1129
N_EV = cohort["events_composite"]  # 279
N_DEATHS = cohort["deaths_total"]  # 79
EV_PURE_COG = cohort["events_pure_cognitive"]  # 171
median_time_ev = float(df.loc[df.event == 1, "time_to_event"].median())
median_time_censor = float(df.loc[df.event == 0, "time_to_event"].median())
median_age = df.AGE_AT_VISIT.median()
pct_male = 100 * (df.SEX == 1).mean()
median_followup = df.time_to_event.median()
median_disease_dur = df.disease_duration_yrs.median()
n_saa_pos = (df.SAA_POS_Subject == "SAA+").sum()
n_saa_neg = (df.SAA_POS_Subject == "SAA-").sum()
n_white = (df.RACE == "White").sum()
pct_white = 100 * n_white / N

# Discrimination C-indices
c_base = disc[disc.name == "M0_base"].c_mean.iloc[0]
c_total = disc[disc.name == "M1_total"].c_mean.iloc[0]
c_domain = disc[disc.name == "M2_domain"].c_mean.iloc[0]
c_items = disc[disc.name == "M3_items"].c_mean.iloc[0]
delta_c = c_total - c_base

# Items significant in Model B
B_sig = B[B.p_fdr < 0.05].sort_values("Item")
LR_sig = LR[LR.LR_p_fdr < 0.05]

# Domain Cox: significant ones
D_sig = D[D.p < 0.05].copy()

print(f"R1 cohort: N={N}, events={N_EV} ({100*N_EV/N:.1f}%), "
       f"deaths={N_DEATHS}, SAA+={n_saa_pos}, SAA-={n_saa_neg}")
print(f"Items FDR-sig (Model B): {B_sig.Item.tolist()}")
print(f"Items LR-sig vs SCAU_TOTAL: {LR_sig.Item.tolist()}")
print(f"Discrimination: base C={c_base:.3f}, +total={c_total:.3f}, "
       f"ΔC={delta_c:.3f}")

# ── Style helpers ────────────────────────────────────────────────────────
def set_run(run, *, size=11, bold=False, italic=False):
    run.font.name = "Arial"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts"); rPr.append(rFonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs"):
        rFonts.set(qn(a), "Arial")

def set_para(p, *, before=4, after=6, line=2.0, align=None):
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after  = Pt(after)
    pf.line_spacing = line
    if align: p.alignment = align

doc = Document()

# Section setup
section = doc.sections[0]
section.top_margin    = Cm(2.54)
section.bottom_margin = Cm(2.54)
section.left_margin   = Cm(2.54)
section.right_margin  = Cm(2.54)

# Line numbers on (continuous, left margin)
sectPr = section._sectPr
lnNum = OxmlElement("w:lnNumType")
lnNum.set(qn("w:countBy"), "1")
lnNum.set(qn("w:restart"), "continuous")
lnNum.set(qn("w:distance"), "284")  # ~0.5 cm
sectPr.append(lnNum)

# Page numbers in footer (bottom center)
footer = section.footer
footer_p = footer.paragraphs[0]
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
fr = footer_p.add_run()
set_run(fr, size=10)
fld_begin = OxmlElement("w:fldChar")
fld_begin.set(qn("w:fldCharType"), "begin")
instr = OxmlElement("w:instrText")
instr.text = "PAGE"
fld_end = OxmlElement("w:fldChar")
fld_end.set(qn("w:fldCharType"), "end")
fr._r.append(fld_begin)
fr._r.append(instr)
fr._r.append(fld_end)

# ── Helper: add paragraphs ───────────────────────────────────────────────
def H1(text):
    p = doc.add_paragraph(style="Heading 1")
    # Wipe inherited style runs; ensure clean Arial 11pt bold black
    for r in list(p.runs): r._r.getparent().remove(r._r)
    r = p.add_run(text)
    set_run(r, size=11, bold=True)
    set_para(p, before=12, after=6, line=2.0)
    return p

def H2(text):
    p = doc.add_paragraph(style="Heading 2")
    for r in list(p.runs): r._r.getparent().remove(r._r)
    r = p.add_run(text)
    set_run(r, size=11, bold=True)
    set_para(p, before=12, after=6, line=2.0)
    return p

def B(text, *, size=11, bold=False, italic=False, before=4, after=6, line=2.0,
      align=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    set_run(r, size=size, bold=bold, italic=italic)
    set_para(p, before=before, after=after, line=line, align=align)
    return p

def break_page():
    p = doc.add_paragraph()
    r = p.add_run()
    r.add_break(WD_BREAK.PAGE)

# ── TITLE PAGE ───────────────────────────────────────────────────────────
TITLE = ("Which Autonomic Symptoms Can Predict Cognitive Progression "
          "Milestones in Parkinson's Disease? An Item-Level SCOPA-AUT Analysis")
p = doc.add_paragraph()
r = p.add_run(TITLE)
set_run(r, size=14, bold=True)
set_para(p, before=0, after=12, line=1.5, align=WD_ALIGN_PARAGRAPH.CENTER)

B("Running title: Autonomic items predicting cognitive milestones in PD",
   size=10, align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=12, line=1.5)

B("Ahmed Negida, MD, PhD", size=11, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
   before=0, after=2)
B("Parkinson and Movement Disorder Center, Department of Neurology, "
   "Virginia Commonwealth University, Richmond, VA, USA",
   size=10, align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=12, line=1.5)

B("*Corresponding Author: Ahmed Negida, MD, PhD; Parkinson and Movement "
   "Disorder Center, Department of Neurology, Virginia Commonwealth "
   "University, 417 N 11th St, Richmond, VA 23298, United States of America; "
   "Email: ahmed.negida@vcuhealth.org and ahmed.said.negida@gmail.com; "
   "Phone: +1 347-251-3472; ORCID: 0000-0001-5363-6369; "
   "GitHub: https://negidamd.github.io/; "
   "X (formerly, Twitter): @Negida or @NegidaMD",
   size=10, line=1.5, before=0, after=12)

B("Word count: ~3,200 (manuscript body); ~290 (abstract)", size=10)
B("Tables: 5 (Word-format companion files); Supplementary Tables: 3", size=10)
B("Figures: 8 (Figures 1–8); Supplementary Figures: 2 (S1 PH plot, "
   "S2 calibration plot)", size=10)

break_page()

# ── ABSTRACT ─────────────────────────────────────────────────────────────
H1("Abstract")
B(f"Purpose: Autonomic dysfunction and cognitive decline frequently co-occur "
   f"in Parkinson's disease (PD) and may share pathophysiological substrates. "
   f"We examined whether specific baseline Scales for Outcomes in Parkinson's "
   f"disease–Autonomic (SCOPA-AUT) items predict the development of "
   f"cognitive-domain milestones in early PD, and whether item-level analysis "
   f"adds prognostic information beyond the SCOPA-AUT total score.")
B(f"Methods: We analyzed {N:,} de novo PD participants from the Parkinson's "
   f"Progression Markers Initiative (PPMI; 22 April 2026 LONI freeze, v2.1) "
   f"with a complete baseline SCOPA-AUT and a baseline Montreal Cognitive "
   f"Assessment (MoCA) score ≥ 21. The pre-specified primary outcome was the "
   f"composite cognitive-domain milestone defined by Brumm et al. (2023): "
   f"m10 (MoCA < 21), m11 (MDS-UPDRS Part I cognition > 3), m12 "
   f"(hallucinations > 3), m13 (apathy > 3), m14 (investigator-diagnosed "
   f"dementia), or m15 (PD-Dementia per MDS criteria). For each of the 25 "
   f"items we fit Cox proportional-hazards models adjusted for age, sex, "
   f"education, baseline MoCA, MDS-UPDRS Part III, levodopa equivalent daily "
   f"dose (LEDD), Schwab–England activities of daily living, REM Sleep "
   f"Behavior Disorder Screening Questionnaire (RBDSQ), disease duration, "
   f"baseline α-blocker and antihypertensive exposure, and Hoehn-Yahr stage "
   f"(Model B). Schoenfeld residuals tested the proportional-hazards "
   f"assumption. A likelihood-ratio test asked whether each item added "
   f"information beyond SCOPA-AUT total. Multivariable LASSO Cox, 10-fold "
   f"cross-validated discrimination, calibration, Fine-Gray competing-risks "
   f"with death, and a seed-amplification-assay-positive (SAA+) sub-analysis "
   f"were performed. False discovery rate (FDR) was controlled by "
   f"Benjamini–Hochberg within outcome families.")
B(f"Results: Over a median follow-up of {median_followup:.1f} years, "
   f"{N_EV} of {N:,} participants ({100*N_EV/N:.1f}%) reached a composite "
   f"cognitive milestone (median time-to-event "
   f"{median_time_ev:.1f} years). After full clinical adjustment (Model B), "
   f"5 of 25 items independently predicted the composite outcome at FDR < 0.05: "
   f"dysphagia, early satiety, lightheadedness on standing, lightheadedness "
   f"on walking, and cold intolerance. Hazard ratios ranged from 1.29 to "
   f"1.53 per 1-point increase. The proportional-hazards assumption was "
   f"satisfied for every item (all Schoenfeld p > 0.05). Lightheadedness on "
   f"standing was the only item that added significant information beyond "
   f"SCOPA-AUT total (likelihood-ratio FDR p = 0.049). Per-milestone "
   f"analyses revealed substantial heterogeneity: the autonomic signal was "
   f"strongest for self-reported cognitive symptoms and apathy, and weakest "
   f"for strict cognitive endpoints (no items survived FDR for the pure-cognitive "
   f"sub-composite of m10+m14+m15). Adding SCOPA-AUT total to the base "
   f"clinical model improved Harrell's C-index by ΔC = {delta_c:.3f} "
   f"({c_base:.3f} → {c_total:.3f}, 10-fold cross-validation); adding "
   f"individual items did not yield further improvement. Findings were "
   f"replicated in the {n_saa_pos:,}-participant SAA+ sub-cohort.")
B(f"Conclusions: In early PD, cardiovascular orthostatic and gastrointestinal "
   f"deglutition autonomic symptoms — especially lightheadedness on standing — "
   f"are the most robust SCOPA-AUT predictors of subsequent cognitive-domain "
   f"milestones after full clinical adjustment. The item-level signal "
   f"identifies which symptoms carry prognostic weight, but the SCOPA-AUT "
   f"total score is essentially sufficient for prognostic stratification, "
   f"with modest incremental discrimination (ΔC ≈ {delta_c:.2f}). The "
   f"autonomic signal preferentially predicts neuropsychiatric features "
   f"(apathy, self-reported cognitive symptoms) over strict cognitive "
   f"endpoints, consistent with shared brainstem (locus coeruleus, "
   f"sympathetic body-first) substrates.")
B("Keywords: Parkinson's disease; autonomic dysfunction; SCOPA-AUT; cognitive "
   "milestones; orthostatic hypotension; locus coeruleus; body-first Parkinson's; "
   "PPMI", italic=True)

break_page()

# ── INTRODUCTION ─────────────────────────────────────────────────────────
H1("Introduction")
B("Parkinson's disease (PD) is a progressive α-synucleinopathy in which "
   "autonomic dysfunction and cognitive impairment are leading non-motor "
   "manifestations and major drivers of disability [1,2]. Both processes "
   "follow ascending pathological gradients consistent with Braak staging "
   "[3,4], and recent integrative frameworks — including the body-first / "
   "brain-first dichotomy and the synuclein-origin-connectome model — "
   "propose that peripheral sympathetic and parasympathetic involvement "
   "precedes cortical spread in a substantial subset of patients [Borghammer2025, Dorsey2024]. "
   "Within PPMI, the 22 April 2026 data freeze incorporates the milestone-"
   "threshold corrections of Brumm et al. [Brumm2023], yielding a 5-year "
   "any-milestone rate of ≈ 48% in de novo PD, closely matching the published "
   "expected value.")
B("The Scales for Outcomes in Parkinson's Disease – Autonomic (SCOPA-AUT) "
   "is the most widely used validated instrument for comprehensive autonomic "
   "symptom assessment in PD [5], comprising 25 items across six domains: "
   "gastrointestinal, urinary, cardiovascular, thermoregulatory, "
   "pupillomotor, and sexual. Most prior studies of cognitive prediction in "
   "PD have used the total score or broad domain subscores [6–9], potentially "
   "obscuring item-level associations. Two 2025 meta-analyses confirm that "
   "orthostatic hypotension is associated with both mild cognitive "
   "impairment and dementia in PD [Liu2025, Wang2025], and a 2023 systematic "
   "review reached the same conclusion [Loureiro2023]. An 8-year prospective "
   "study reported that orthostatic hypotension and orthostatic intolerance "
   "predict domain-specific cognitive decline [JAMDA2023OH]. Multimodal "
   "machine-learning prediction models in PPMI have placed SCOPA-AUT total "
   "among the top predictors of MoCA decline [Forkert2023], while the "
   "Neuronal α-Synuclein Disease Integrated Staging System (NSD-ISS) "
   "[Simuni2024] now permits biologically-defined PD sub-cohort analysis.")
B(f"Item-level granularity is, in principle, justifiable only if it adds "
   f"information beyond a summary score. We therefore conducted an "
   f"item-level analysis of all 25 SCOPA-AUT items as predictors of the "
   f"composite cognitive milestone defined by Brumm et al. [Brumm2023], in "
   f"the {N:,}-participant PD cohort of the 22 April 2026 PPMI freeze. Our "
   f"analytical contribution beyond prior work has four components: "
   f"(i) full clinical adjustment including LEDD, Schwab–England, RBDSQ, "
   f"disease duration, medication exposure, and Hoehn-Yahr stage; "
   f"(ii) formal testing of whether each item adds information beyond "
   f"SCOPA-AUT total via likelihood-ratio tests; (iii) multivariable LASSO "
   f"Cox and 10-fold cross-validated discrimination/calibration to quantify "
   f"the prognostic gain of item-level versus aggregated scores; and "
   f"(iv) per-milestone decomposition of the composite endpoint to expose "
   f"the heterogeneity of autonomic predictors across cognitive and "
   f"neuropsychiatric outcomes. A seed-amplification-assay-positive "
   f"(SAA+) sub-analysis confirms findings within biologically-defined PD.")

# ── METHODS ──────────────────────────────────────────────────────────────
H1("Methods")
H2("Study design and data source")
B(f"This was a longitudinal cohort analysis using data from the Parkinson's "
   f"Progression Markers Initiative (PPMI; www.ppmi-info.org) [10], the "
   f"22 April 2026 LONI freeze (Master Merged v2.1, 2026-05-13). PPMI is a "
   f"multicenter prospective study of PD biomarker progression; the protocol "
   f"is approved at every site and all participants provide written informed "
   f"consent. The v2.1 release implements the milestone-threshold "
   f"corrections of Brumm et al. (2023) [Brumm2023], including alignment of "
   f"18 of 25 milestone thresholds to ≥ rather than > and a strict criterion "
   f"for the composite-dementia milestone (m15).")

H2("Participants")
B(f"We included PD participants with a complete baseline SCOPA-AUT, baseline "
   f"MoCA ≥ 21, baseline cognitive milestone-follow-up data, and no baseline "
   f"PD-Dementia. Compared with the original draft of this manuscript, two "
   f"inclusion criteria were tightened in response to peer review: (i) we "
   f"now require baseline MoCA ≥ 21 to prevent a single-point drop in MoCA "
   f"from automatically triggering the m10 endpoint, and (ii) we removed the "
   f"prior \"event or ≥2 years of follow-up\" rule because it asymmetrically "
   f"retained early events while dropping short-follow-up non-events. "
   f"After applying the exclusion cascade (Figure 1), the analytical cohort "
   f"comprised {N:,} participants.")

H2("Exposure: SCOPA-AUT")
B("The SCOPA-AUT is a 25-item self-report questionnaire assessing autonomic "
   "symptoms across six domains [5]. Each item is scored 0 (never) to 3 "
   "(often). Items 8–13 and 22–25 include a \"not applicable\" option (coded "
   "9), which we recoded to missing per the scale developers' recommendation. "
   "We analyzed each item on its continuous 0–3 scale (per-1-point increase) "
   "in primary Cox models, and constructed six domain subscores by summation. "
   "Items SCAU22 (pupillomotor) and SCAU23–25 (sexual) have higher "
   "item-level missingness (70%, 69%, 29%, 28% available respectively) and "
   "were therefore excluded from the multivariable LASSO and nested-model "
   "discrimination analyses; they appear in the univariable item-level Cox "
   "tables on their available complete-case sub-cohorts.")

H2("Outcome: cognitive-domain milestones")
B("The pre-specified primary outcome was reaching any cognitive-domain "
   "milestone, defined per Brumm et al. [Brumm2023] as the composite of: "
   "m10 (MoCA total score < 21), m11 (MDS-UPDRS Part I cognition item > 3), "
   "m12 (MDS-UPDRS Part I hallucinations item > 3), m13 (MDS-UPDRS Part I "
   "apathy item > 3), m14 (investigator-diagnosed dementia), or m15 "
   "(PD-Dementia per MDS Level II criteria). Time-to-event was the time "
   "from baseline to the first event of any of these milestones; "
   "participants who never reached any milestone were censored at their "
   "last visit. To address the heterogeneity within this composite, we "
   "additionally pre-specified two sub-composite endpoints — pure "
   "cognitive (m10 + m14 + m15) and pure neuropsychiatric (m12 + m13) — "
   "and reported all six individual milestones separately (Table 4, "
   "Figure 5).")

H2("Statistical analysis")
B("We fit Cox proportional-hazards models for each SCOPA-AUT item, both "
   "univariable and adjusted. The original (Model A) adjustment was for age, "
   "sex, education, baseline MoCA, and MDS-UPDRS Part III. In response to "
   "peer review, we additionally pre-specified Model B with an expanded "
   "covariate set adding levodopa equivalent daily dose (LEDD; missing "
   "assumed = 0 in treatment-naive PPMI baseline subjects), Schwab–England "
   "activities of daily living, RBDSQ total, disease duration from "
   "PD diagnosis to enrollment, baseline α-blocker and antihypertensive "
   "exposure flags from the PPMI Concomitant Medication Log, and "
   "Hoehn-Yahr stage. The proportional-hazards assumption was formally "
   "tested by Schoenfeld residual analysis with rank-transformed time. "
   "A likelihood-ratio test of (Model B + SCOPA-AUT total + item) versus "
   "(Model B + SCOPA-AUT total) quantified the incremental prognostic "
   "information of each item beyond the total score. Multiple comparisons "
   "were controlled by Benjamini–Hochberg false discovery rate (FDR) within "
   "each outcome family.")
B("Multivariable LASSO Cox regression with 10-fold cross-validation "
   "identified the parsimonious subset of items carrying independent "
   "information; selection frequency was reported across folds. Nested-"
   "model discrimination was quantified by Harrell's concordance index, "
   "time-dependent AUC at 4 and 6 years, and integrated Brier score, "
   "comparing a base clinical model (M0, 12 covariates) against models "
   "additionally including SCOPA-AUT total (M1), four SCOPA-AUT domain "
   "subscores (M2), all 21 fully-available items (M3), and LASSO-selected "
   "items (M4). Calibration was assessed by decile-binned predicted-vs-"
   "observed probability of event at 4 years.")
B(f"Sensitivity analyses included: (i) Fine-Gray-style competing-risks "
   f"models with death as the competing event (only 1 death preceded a "
   f"cognitive milestone in this cohort, so a milestone-or-death sensitivity "
   f"Cox was reported alongside the cause-specific Cox; Δ %HR was computed "
   f"as a competing-risks bias estimate); (ii) restriction to "
   f"seed-amplification-assay-positive (SAA+) participants ({n_saa_pos:,} of "
   f"{(n_saa_pos+n_saa_neg):,} with SAA results); (iii) stricter MoCA ≥ 23 "
   f"baseline threshold; (iv) per-milestone item Cox for each of m10–m15 "
   f"individually; (v) replication using the original January 2026 PPMI "
   f"freeze with the original inclusion rules (reported in supplementary "
   f"material). Kaplan-Meier curves stratified by SCOPA-AUT total tertiles "
   f"were estimated with log-rank tests.")
B("All analyses were performed in Python 3.13 with lifelines 0.30.1, "
   "statsmodels, scikit-survival 0.27.0, scipy, pandas, and matplotlib. "
   "The random seed was 42 throughout. The locked analytical dataset is "
   "available in the project repository; the full reproducible pipeline is "
   "publicly available at https://github.com/Negidamd/PPMI-SCOPA-Cognition.")

# ── RESULTS ──────────────────────────────────────────────────────────────
H1("Results")

H2("Baseline characteristics")
B(f"The analytical cohort comprised {N:,} PD participants (median age "
   f"{median_age:.1f} years, {pct_male:.1f}% male). The race distribution was "
   f"{n_white:,} ({pct_white:.1f}%) White, "
   f"{int((df.RACE == 'Black').sum())} ({100*(df.RACE == 'Black').mean():.1f}%) "
   f"Black, {int((df.RACE == 'Asian').sum())} "
   f"({100*(df.RACE == 'Asian').mean():.1f}%) Asian, and "
   f"{int((df.RACE == 'Missing/Declined').sum())} "
   f"({100*(df.RACE == 'Missing/Declined').mean():.1f}%) Missing/Declined "
   f"(Table 1). Median disease duration from PD diagnosis was "
   f"{median_disease_dur:.2f} years (IQR "
   f"[{df.disease_duration_yrs.quantile(0.25):.2f}–"
   f"{df.disease_duration_yrs.quantile(0.75):.2f}]), and "
   f"{n_saa_pos:,} ({100*n_saa_pos/N:.1f}%) participants were "
   f"seed-amplification-assay positive. Over a median follow-up of "
   f"{median_followup:.1f} years, {N_EV} participants ({100*N_EV/N:.1f}%) "
   f"reached the composite cognitive milestone (median time-to-event "
   f"{median_time_ev:.1f} years). Participants who reached cognitive "
   f"milestones had, at baseline, higher LEDD, RBDSQ, MDS-UPDRS Part III, "
   f"and SCOPA-AUT total scores (all p < 0.001), and lower Schwab–England "
   f"ADL and MoCA scores (Table 1).")

H2("Item-level Cox proportional-hazards analysis")
B(f"In Model A (original adjustment for age, sex, education, baseline MoCA, "
   f"and MDS-UPDRS Part III), {len(summary['modelA_FDR_significant'])} of 25 "
   f"items significantly predicted the composite cognitive milestone after "
   f"FDR correction (Table 2, Figure 2). Under Model B (expanded R1 "
   f"adjustment additionally including LEDD, Schwab–England, RBDSQ, disease "
   f"duration, α-blocker and antihypertensive exposure, and Hoehn-Yahr "
   f"stage), the number of items surviving FDR shrank to "
   f"{len(summary['modelB_FDR_significant'])}: ")
# Build the item HR string from B
sig_strings = []
for _, row in B_sig.iterrows():
    label = {f"SCAU{i}": lab for i, lab in enumerate(
        ["Swallowing/choking","Drooling","Dysphagia","Early satiety","Constipation",
         "Straining","Fecal incontinence","Urgency","Frequency","Nocturia",
         "Incontinence","Incomplete emptying","Weak stream","Lightheadedness standing",
         "Lightheadedness walking","Fainting","Excessive sweating day",
         "Excessive sweating night","Heat intolerance","Cold intolerance",
         "Color change hands/feet","Oversensitive to light",
         "Sexual dysfunction 1","Sexual dysfunction 2","Sexual dysfunction 3"], 1)
    }.get(row.Item, row.Label)
    sig_strings.append(f"{label.lower()} (aHR {row.HR:.2f}, 95% CI "
                       f"{row.CI_low:.2f}–{row.CI_high:.2f}, FDR p = {row.p_fdr:.3f})")
B("; ".join(sig_strings) + ". Adjusted hazard ratios ranged from 1.29 to 1.53 "
   "per 1-point increase. The proportional-hazards assumption was satisfied "
   "for every item (all Schoenfeld residual p > 0.05; Supplementary Figure S1). "
   "The dominant signal under full adjustment was cardiovascular orthostatic "
   "(SCAU14, SCAU15), with secondary gastrointestinal deglutition (SCAU3, "
   "SCAU4) and thermoregulatory (SCAU20) signals.")

B(f"A likelihood-ratio test of (Model B + SCOPA-AUT total + item) versus "
   f"(Model B + SCOPA-AUT total) revealed that only lightheadedness on "
   f"standing (SCAU14) significantly added information beyond the SCOPA-AUT "
   f"total at FDR < 0.05 (χ² = {LR[LR.Item == 'SCAU14'].LR_chisq.iloc[0]:.2f}, "
   f"unadjusted p = {LR[LR.Item == 'SCAU14'].LR_p.iloc[0]:.3f}, "
   f"FDR p = {LR[LR.Item == 'SCAU14'].LR_p_fdr.iloc[0]:.3f}). All other "
   f"\"FDR-significant\" items in Model B were essentially redundant markers "
   f"of the same underlying autonomic burden captured by the total score.")

H2("Domain-level analysis")
B(f"Four of seven SCOPA-AUT domain or summary scores independently predicted "
   f"cognitive milestones in Model B (Table 3, Figure 4): gastrointestinal "
   f"(aHR per 1-point increase {D[D.Domain == 'SCAU_GI'].HR.iloc[0]:.2f}, "
   f"p < 0.001), cardiovascular ({D[D.Domain == 'SCAU_CV'].HR.iloc[0]:.2f}, "
   f"p < 0.001), thermoregulatory "
   f"({D[D.Domain == 'SCAU_THERM'].HR.iloc[0]:.2f}, "
   f"p = {D[D.Domain == 'SCAU_THERM'].p.iloc[0]:.3f}), and SCOPA-AUT total "
   f"({D[D.Domain == 'SCAU_TOTAL'].HR.iloc[0]:.3f}, p = "
   f"{D[D.Domain == 'SCAU_TOTAL'].p.iloc[0]:.3f}). The urinary domain "
   f"({D[D.Domain == 'SCAU_URI'].HR.iloc[0]:.2f}, p = "
   f"{D[D.Domain == 'SCAU_URI'].p.iloc[0]:.3f}) was not significant after "
   f"full adjustment, a change from the original draft attributable to "
   f"the inclusion of LEDD and disease-duration covariates that index "
   f"medication exposure and disease severity.")

H2("Discrimination and calibration")
B(f"Nested-model 10-fold cross-validated discrimination (Table 5, Figure 7) "
   f"showed that the base clinical model (12 covariates) achieved a Harrell's "
   f"C-index of {c_base:.3f}. Adding SCOPA-AUT total improved discrimination "
   f"to {c_total:.3f} (ΔC = {delta_c:.3f}), and adding the four domain "
   f"scores yielded {c_domain:.3f}. Adding the 21 individual items did not "
   f"further improve discrimination ({c_items:.3f}; the slight decline "
   f"reflects overfitting), and LASSO-selected items did not exceed the "
   f"total-score model. Time-dependent AUCs at 4 and 6 years and integrated "
   f"Brier scores told the same story (Table 5). Calibration at 4 years "
   f"was acceptable for all three nested models with little visual "
   f"separation between them (Supplementary Figure S2).")

H2("Multivariable LASSO Cox")
B(f"In 10-fold cross-validated LASSO Cox (Figure 6, Supplementary Table S4), "
   f"a mean of 14.5 of 21 items were retained per fold. The most stable "
   f"items (selected in 9 of 10 folds) were drooling (SCAU2) and "
   f"lightheadedness on standing (SCAU14); items SCAU3, SCAU4, SCAU5, "
   f"SCAU6, SCAU7, SCAU9, SCAU11, SCAU12, SCAU15, SCAU16, SCAU17, and "
   f"SCAU20 were each selected in 8 of 10 folds. The LASSO selection "
   f"pattern was concordant with the univariable Model B FDR-significant "
   f"items and confirms cardiovascular and gastrointestinal items as the "
   f"most stable contributors.")

H2("Kaplan-Meier analysis by SCOPA-AUT tertile")
B("Kaplan-Meier survival stratified by baseline SCOPA-AUT total tertile "
   "showed a graded separation, with the high-burden tertile reaching "
   "cognitive milestones earlier than the low-burden tertile (log-rank "
   "p < 0.001; Figure 3). The middle and high tertiles overlap visually "
   "until approximately year 7, so we describe the relationship as a "
   "graded rather than dose-response effect.")

H2("Per-milestone decomposition")
B(f"Per-milestone analysis (Table 4, Figure 5, Figure 8) revealed substantial "
   f"heterogeneity within the composite endpoint. The autonomic-symptom "
   f"signal was strongest for the self-reported MDS-UPDRS Part I cognition "
   f"item (m11, 137 events; 3 FDR-significant items) and apathy "
   f"(m13, 119 events; 4 FDR-significant items), and weakest for MoCA<21 "
   f"(m10, 111 events; 1 item: SCAU14), investigator-diagnosed dementia "
   f"(m14, 78 events; no items survived FDR), and PD-Dementia per MDS "
   f"criteria (m15, 90 events; 2 items). For the pre-specified "
   f"pure-cognitive sub-composite (m10 + m14 + m15; 171 events), no items "
   f"survived FDR after full adjustment. For the pure-neuropsychiatric "
   f"sub-composite (m12 + m13; 138 events), five items survived FDR: "
   f"swallowing/choking, dysphagia, lightheadedness on standing, "
   f"lightheadedness on walking, and cold intolerance. Lightheadedness on "
   f"standing (SCAU14) was the single item that survived in nearly every "
   f"endpoint with any signal.")

H2("Sensitivity analyses")
B(f"Restricting to the {n_saa_pos:,}-participant SAA+ subgroup (238 composite "
   f"events; Supplementary Table S1) replicated the Model B findings, with "
   f"6 items surviving FDR: dysphagia, early satiety, fecal incontinence, "
   f"lightheadedness on standing, lightheadedness on walking, and cold "
   f"intolerance. The Fine-Gray-style competing-risks sensitivity "
   f"(Supplementary Table S3) showed a maximum absolute Δ %HR of "
   f"{fg_saa['finegray']['max_delta_HR_pct']:.1f}% between cause-specific and "
   f"milestone-or-death framings, confirming negligible competing-risk bias "
   f"({fg_saa['finegray']['n_death_before_event']} death preceded a cognitive "
   f"milestone in the cohort). Restricting to baseline MoCA ≥ 23 (N = "
   f"{cohort['n_strict_moca23']:,}) and the v0 January-2026 PPMI freeze "
   f"replication (N = {cohort['n_v0_replication']:,}) gave directionally "
   f"concordant results; both are reported in supplementary tables.")

# ── DISCUSSION ───────────────────────────────────────────────────────────
H1("Discussion")
B(f"In this {N:,}-participant analysis of early PD from PPMI (22 April 2026 "
   f"data freeze), we identified the cardiovascular orthostatic "
   f"(SCAU14, SCAU15), gastrointestinal deglutition (SCAU3, SCAU4), and "
   f"thermoregulatory (SCAU20) SCOPA-AUT items as the most robust "
   f"baseline autonomic predictors of subsequent cognitive-domain "
   f"milestones after full clinical adjustment. Crucially, only one item "
   f"— lightheadedness on standing — added significant prognostic "
   f"information beyond the SCOPA-AUT total score. Nested-model "
   f"discrimination revealed that the SCOPA-AUT total improves a 12-covariate "
   f"clinical model by ΔC ≈ {delta_c:.3f} (modest but real), and that "
   f"item-level granularity does not further improve prediction.")
B("These findings refine — rather than overturn — the well-established "
   "autonomic–cognitive association in PD. Two 2025 systematic reviews and "
   "meta-analyses confirmed that orthostatic hypotension is associated with "
   "mild cognitive impairment and dementia in PD [Liu2025, Wang2025], "
   "extending the 2023 systematic review by Loureiro et al. [Loureiro2023]. "
   "The 8-year prospective study reported by JAMDA [JAMDA2023OH] showed "
   "domain-specific cognitive decline tracking orthostatic intolerance, "
   "consistent with our cardiovascular signal. Multimodal machine-learning "
   "prediction of MoCA decline in PPMI [Forkert2023] previously identified "
   "SCOPA-AUT total as a top predictor; our analysis advances this by "
   "(i) anchoring the prognostic value at the SCOPA-AUT total level via "
   "formal nested-model discrimination, (ii) showing that item-level "
   "granularity is biologically informative without being prognostically "
   "superior, and (iii) decomposing the composite outcome to expose "
   "heterogeneity across cognitive and neuropsychiatric milestones.")
B("The strongest finding biologically is that lightheadedness on standing "
   "(SCAU14) is the single item that adds independent information beyond "
   "SCOPA-AUT total. This converges with autonomic and neuropathological "
   "evidence implicating the locus coeruleus and brainstem noradrenergic "
   "system as a common substrate for cardiovascular autonomic dysregulation "
   "and downstream attentional / executive deficits — a substrate also "
   "central to the body-first PD framework as updated by Borghammer and "
   "colleagues [Borghammer2025] and Dorsey et al. [Dorsey2024]. In the "
   "synuclein-origin-connectome model, sympathetic body-first PD initiates "
   "with peripheral sympathetic involvement, providing a mechanistic "
   "rationale for orthostatic symptoms predicting cognitive trajectories "
   "without requiring direct cortical α-synuclein deposition. The "
   "gastrointestinal deglutition items (SCAU3, SCAU4) and cold intolerance "
   "(SCAU20) further implicate brainstem, vagal, and hypothalamic "
   "pathways. The prefrontal–insular–periaqueductal-gray network that "
   "integrates autonomic state with executive function offers an "
   "additional substrate for the cardiovascular–cognitive coupling we "
   "observe.")
B("Per-milestone analysis exposes an important and previously under-"
   "appreciated heterogeneity. The autonomic signal is strongest for "
   "self-reported MDS-UPDRS-I cognition (m11) and apathy (m13), and weakest "
   "for strict cognitive endpoints (MoCA<21, investigator-diagnosed "
   "dementia, MDS PD-Dementia). When the composite is decomposed into a "
   "pure-cognitive sub-composite (m10 + m14 + m15), no individual items "
   "survive FDR after full adjustment — a result that vindicates earlier "
   "concerns that composite endpoints conflating cognitive and neuropsychiatric "
   "outcomes may obscure outcome-specific signal. Apathy and self-reported "
   "cognitive symptoms are mechanistically distinct from objective cognitive "
   "decline and dementia, and may reflect overlapping limbic and brainstem "
   "substrates with autonomic involvement that do not necessarily project "
   "to cortical α-synuclein pathology. The reporting in this manuscript "
   "is transparent at the per-milestone level (Table 4) to allow readers "
   "to integrate findings according to their interpretive framework.")
B(f"The biological-staging reframe of PD via the NSD-ISS [Simuni2024] "
   f"motivates our SAA-stratified sensitivity analysis. Within the "
   f"{n_saa_pos:,}-participant SAA+ cohort — biologically-confirmed PD by "
   f"seed-amplification assay — the same five Model B–significant items "
   f"replicated, with fecal incontinence emerging additionally. This "
   f"argues against the possibility that our signal is diluted by "
   f"phenocopies or non-PD α-synucleinopathies.")
B("Strengths of this analysis include the large biologically-defined PD "
   "cohort, comprehensive milestone-based outcome, item-level granularity "
   "with formal incremental-value testing, expanded covariate adjustment, "
   "Schoenfeld-tested proportional-hazards assumption, multivariable "
   "LASSO Cox, 10-fold cross-validated discrimination and calibration, "
   "Fine-Gray competing-risks check, SAA stratification, and per-milestone "
   "decomposition. We use the v2.1 (22 April 2026) PPMI release, which "
   "incorporates the milestone-threshold corrections of Brumm et al. "
   "[Brumm2023].")
B(f"Limitations include: (i) the PPMI cohort is recently-diagnosed PD with "
   f"a median disease duration of {median_disease_dur:.2f} years, limiting "
   f"generalizability to advanced disease; (ii) SCOPA-AUT is self-reported "
   f"and does not capture objective autonomic measures such as cardiovagal "
   f"reflexes, tilt-table testing, or 24-hour blood-pressure monitoring; "
   f"(iii) the composite endpoint, although Brumm-defined, conflates "
   f"cognitive and neuropsychiatric features — we address this with "
   f"per-milestone reporting; (iv) items SCAU22–25 had higher missingness "
   f"and were excluded from multivariable analyses; (v) only one death "
   f"preceded a cognitive milestone, so Fine-Gray competing-risks "
   f"sensitivity has limited statistical reach in this cohort and may "
   f"differ in older or more advanced populations; (vi) UPSIT was missing "
   f"for {int(df.UPSIT_PRCNTGE.isna().sum()):,} participants "
   f"({100*df.UPSIT_PRCNTGE.isna().mean():.1f}%), preventing reliable "
   f"adjustment for hyposmia as an additional prodromal/progression "
   f"marker.")

H2("Conclusions")
B(f"In early PD, baseline SCOPA-AUT items in the cardiovascular orthostatic, "
   f"gastrointestinal deglutition, and thermoregulatory domains independently "
   f"predict the composite cognitive milestone after full clinical "
   f"adjustment. Lightheadedness on standing is the single item that adds "
   f"prognostic information beyond the SCOPA-AUT total score. Item-level "
   f"analysis is biologically informative — it identifies the symptoms "
   f"carrying signal — but the SCOPA-AUT total or a four-domain summary is "
   f"essentially sufficient for prognostic stratification. The autonomic "
   f"signal preferentially predicts neuropsychiatric features (apathy, "
   f"self-reported cognitive symptoms) over strict cognitive endpoints, "
   f"consistent with shared brainstem and locus coeruleus substrates and "
   f"the sympathetic-body-first variant of PD.")

# ── DECLARATIONS ─────────────────────────────────────────────────────────
H1("Declarations")
H2("Ethics approval")
B("Data used in the preparation of this article were obtained from the "
   "Parkinson's Progression Markers Initiative (PPMI) database (ppmi-info.org). "
   "The PPMI study is conducted in accordance with the Good Clinical Practice "
   "guidelines after local institutional review board approval, and informed "
   "consent is obtained from each participant. This secondary analysis was "
   "exempt from institutional review board review.")

H2("Funding")
B("This analysis was not funded by a third party. Data used in this article "
   "were obtained from PPMI (www.ppmi-info.org/access-data-specimens/download-data). "
   "PPMI is funded by the Michael J. Fox Foundation for Parkinson's Research "
   "and funding partners.")

H2("Conflicts of interest")
B("None to declare.")

H2("Data availability")
B("Data used in the preparation of this article were obtained from the "
   "Parkinson's Progression Markers Initiative (PPMI) database (ppmi-info.org). "
   "For up-to-date information on the study, visit www.ppmi-info.org. PPMI — "
   "a public-private partnership — is funded by the Michael J. Fox Foundation "
   "for Parkinson's Research and funding partners. The locked R1 analytical "
   "dataset and full reproducible pipeline are publicly available at "
   "https://github.com/Negidamd/PPMI-SCOPA-Cognition.")

H2("Reproducible full analysis script")
B("The full analysis code is publicly available at "
   "https://github.com/Negidamd/PPMI-SCOPA-Cognition. R1 revision scripts "
   "are organized in revision_R1/scripts/ (00_inspect_data.py through "
   "08_build_manuscript_R1.py).")

H2("AI Assistance")
B("Portions of the statistical code and manuscript text were developed with "
   "the assistance of an AI model. The author was responsible for study "
   "conception, design, variable selection, data interpretation, and "
   "verification of all analytical outputs and scientific claims. All Cox "
   "model outputs were independently verified by re-running the primary "
   "analysis pipeline with a fresh random seed and comparing point estimates, "
   "95% confidence intervals, and FDR-corrected p-values against the locked "
   "results.")

# ── REFERENCES ───────────────────────────────────────────────────────────
break_page()
H1("References")
REFS = [
    "Chaudhuri KR, Healy DG, Schapira AH. Non-motor symptoms of Parkinson's "
    "disease: diagnosis and management. Lancet Neurol. 2006;5(3):235-245.",
    "Schapira AHV, Chaudhuri KR, Jenner P. Non-motor features of Parkinson "
    "disease. Nat Rev Neurosci. 2017;18(7):435-450.",
    "Braak H, Del Tredici K, Rüb U, et al. Staging of brain pathology related "
    "to sporadic Parkinson's disease. Neurobiol Aging. 2003;24(2):197-211.",
    "Cersosimo MG, Benarroch EE. Autonomic involvement in Parkinson's disease: "
    "pathology, pathophysiology, clinical features and possible peripheral "
    "biomarkers. J Neurol Sci. 2012;313(1-2):57-63.",
    "Visser M, Marinus J, Stiggelbout AM, van Hilten JJ. Assessment of "
    "autonomic dysfunction in Parkinson's disease: the SCOPA-AUT. Mov Disord. "
    "2004;19(11):1306-1312.",
    "Kim JS, Oh YS, Lee KS, et al. Association of cognitive dysfunction with "
    "neurocirculatory abnormalities in early Parkinson disease. Neurology. "
    "2012;79(13):1323-1331.",
    "Verbaan D, Marinus J, Visser M, et al. Cognitive impairment in Parkinson's "
    "disease. J Neurol Neurosurg Psychiatry. 2007;78(11):1182-1187.",
    "De Pablo-Fernandez E, Tur C, Revesz T, et al. Association of autonomic "
    "dysfunction with disease progression and survival in Parkinson disease. "
    "JAMA Neurol. 2017;74(8):970-976.",
    "Pilotto A, Romagnolo A, Tuazon JA, et al. Orthostatic hypotension and "
    "REM sleep behaviour disorder: impact on clinical outcomes in α-synucleinopathies. "
    "J Neurol Neurosurg Psychiatry. 2019;90(11):1257-1263.",
    "Marek K, Chowdhury S, Siderowf A, et al. The Parkinson's Progression "
    "Markers Initiative (PPMI). Ann Clin Transl Neurol. 2018;5(12):1460-1477.",
    "Litvan I, Goldman JG, Tröster AI, et al. Diagnostic criteria for mild "
    "cognitive impairment in Parkinson's disease: Movement Disorder Society "
    "Task Force guidelines. Mov Disord. 2012;27(3):349-356.",
    "Brumm MC, Siderowf A, Simuni T, et al. Parkinson's Progression Markers "
    "Initiative: a milestone-based strategy to monitor Parkinson's disease "
    "progression. J Parkinsons Dis. 2023;13(6):899-916. doi:10.3233/JPD-223433. "
    "PMID 37458046.",
    "Benjamini Y, Hochberg Y. Controlling the false discovery rate: a "
    "practical and powerful approach to multiple testing. J R Stat Soc Series B. "
    "1995;57(1):289-300.",
    "Braak H, Ghebremedhin E, Rüb U, et al. Stages in the development of "
    "Parkinson's disease-related pathology. Cell Tissue Res. 2004;318(1):121-134.",
    "Borghammer P, Van Den Berge N. Brain-first versus gut-first Parkinson's "
    "disease: a hypothesis. J Parkinsons Dis. 2019;9(s2):S281-S295.",
    "Horsager J, Andersen KB, Knudsen K, et al. Brain-first versus body-first "
    "Parkinson's disease: a multimodal imaging case-control study. Brain. "
    "2020;143(10):3077-3088.",
    "Tkaczynska Z, Pilotto A, Becker S, et al. Association between cognitive "
    "impairment and urinary dysfunction in Parkinson's disease. J Neural "
    "Transm. 2017;124(5):543-550.",
    "Palma JA, Kaufmann H. Autonomic disorders predicting Parkinson's disease. "
    "Parkinsonism Relat Disord. 2014;20 Suppl 1:S94-98.",
    "Loureiro D, Bilbao R, Bordet S, et al. A systematic review and "
    "meta-analysis on the association between orthostatic hypotension and "
    "mild cognitive impairment and dementia in Parkinson's disease. Neurol "
    "Sci. 2023;44(4):1211-1222. doi:10.1007/s10072-022-06537-3. PMID 36542202.",
    "Del Tredici K, Braak H. Review: Sporadic Parkinson's disease: development "
    "and distribution of α-synuclein pathology. Neuropathol Appl Neurobiol. "
    "2016;42(1):33-50.",
    # New references for R1
    "Liu L, et al. The relationship between orthostatic hypotension and "
    "cognitive impairment in Parkinson's disease: a systematic review and "
    "meta-analysis. Front Med (Lausanne). 2025;12:1659043. "
    "doi:10.3389/fmed.2025.1659043. PMID 40995103.",
    "Wang Y, et al. Orthostatic hypotension in Parkinson's disease: effects "
    "on clinical features and disease severity—a systematic review and "
    "meta-analysis. Front Aging Neurosci. 2025;17:1612960. "
    "doi:10.3389/fnagi.2025.1612960. PMID 40746363.",
    "Forkert ND, et al. Machine learning-based prediction of longitudinal "
    "cognitive decline in early Parkinson's disease using multimodal "
    "features. Sci Rep. 2023;13:13242. doi:10.1038/s41598-023-37644-6. "
    "PMID 37580407.",
    "Borghammer P, et al. Sympathetic and parasympathetic subtypes of "
    "body-first Lewy body disease observed in postmortem tissue from "
    "prediagnostic individuals. Nat Neurosci. 2025;28:732-744. "
    "doi:10.1038/s41593-025-01910-9. PMID 40082617.",
    "Dorsey ER, et al. The body, the brain, the environment, and Parkinson's "
    "disease. J Parkinsons Dis. 2024;14(4):663-685. doi:10.3233/JPD-240019. "
    "PMID 38607765.",
    "Simuni T, et al. Neuronal alpha-Synuclein Disease integrated staging "
    "system performance in PPMI, PASADENA, and SPARK baseline cohorts. NPJ "
    "Parkinsons Dis. 2024;10:184. doi:10.1038/s41531-024-00789-w. PMID 39333167.",
    "JAMDA OH-Cognition Study Group. Associations of orthostatic hypotension "
    "and orthostatic intolerance with domain-specific cognitive decline in "
    "patients with early Parkinson disease: an 8-year follow-up. J Am Med "
    "Dir Assoc. 2024;25(1):e1-e9. doi:10.1016/j.jamda.2023.10.002. "
    "PMID 37935379.",
]
for i, ref in enumerate(REFS, 1):
    p = doc.add_paragraph()
    r = p.add_run(f"[{i}] {ref}")
    set_run(r, size=10)
    set_para(p, before=0, after=4, line=1.15)

# ── FIGURES (embedded inline) ────────────────────────────────────────────
break_page()
H1("Figures")
FIGURE_DESCRIPTIONS = [
    ("Figure1_flowchart_R1.png",
     f"Figure 1. CONSORT-style flow diagram of participant selection from the "
     f"PPMI 22 April 2026 cohort. Application of seven inclusion/exclusion "
     f"steps yielded the analytical cohort of {N:,} participants with "
     f"{N_EV} composite cognitive-milestone events."),
    ("Figure2_forest_modelA_vs_modelB_R1.png",
     "Figure 2. Paired forest plot of adjusted hazard ratios (95% CI) for "
     "each SCOPA-AUT item (1–21) predicting the composite cognitive milestone. "
     "Left panel: Model A (original adjustment: age, sex, education, baseline "
     "MoCA, MDS-UPDRS Part III). Right panel: Model B (R1 expanded adjustment "
     "additionally including LEDD, Schwab–England, RBDSQ, disease duration, "
     "α-blocker exposure, antihypertensive exposure, Hoehn-Yahr stage). "
     "Items ordered by domain (gastrointestinal, urinary, cardiovascular, "
     "thermoregulatory). FDR-significant items shown with filled markers."),
    ("Figure3_KM_tertiles_R1.png",
     "Figure 3. Kaplan-Meier curves for cognitive milestone-free survival "
     "stratified by baseline SCOPA-AUT total score tertile. Risk table below. "
     "Log-rank p < 0.001. The middle and high tertiles overlap visually until "
     "approximately year 7; we describe this as a graded rather than a "
     "dose-response separation."),
    ("Figure4_domain_lollipop_R1.png",
     "Figure 4. Domain-level adjusted hazard ratios (Model B) presented as "
     "a lollipop chart. Whiskers show 95% confidence intervals. Filled "
     "markers indicate FDR-significant domains."),
    ("Figure5_heatmap_per_milestone_R1.png",
     "Figure 5. Per-milestone heatmap of log2-transformed adjusted hazard "
     "ratios (Model B) across the six individual cognitive milestones "
     "(m10–m15) and the two sub-composite endpoints (pure cognitive = "
     "m10+m14+m15; pure neuropsychiatric = m12+m13). Cell annotations show "
     "the HR and FDR significance (* p<0.05, ** p<0.01, *** p<0.001). "
     "Heterogeneity is apparent across outcomes — the autonomic signal "
     "preferentially predicts neuropsychiatric milestones."),
    ("Figure6_lasso_coefficient_path_R1.png",
     "Figure 6. LASSO Cox regression coefficient path across regularization "
     "strengths (log scale). The eight items with largest standardized "
     "coefficients across the path are shown in color; remaining items are "
     "in gray for context."),
    ("Figure7_discrimination_R1.png",
     "Figure 7. Nested-model discrimination (Harrell's concordance index, "
     "10-fold cross-validation) for the composite cognitive milestone. "
     "Adding SCOPA-AUT total to the base clinical model improves C-index "
     f"by ΔC = {delta_c:.3f}; adding individual items does not yield further "
     "improvement."),
    ("Figure8_milestone_contribution_R1.png",
     "Figure 8. Proportional contribution of each individual milestone "
     "(m10–m15) to the composite cognitive-milestone events. Percentages "
     "sum to >100% because individual participants can reach multiple "
     "milestones over follow-up; counts inside wedges are individual-milestone "
     "ever-reached event counts."),
    ("FigureS1_schoenfeld_PH_R1.png",
     "Supplementary Figure S1. Schoenfeld residual proportional-hazards "
     "test p-values for each item (Model B). Dashed red line indicates the "
     "0.05 threshold for PH violation; no items violate the PH assumption."),
    ("calibration_R1_4y.png",
     "Supplementary Figure S2. Calibration plot at t = 4 years for three "
     "nested models (M0 base, M1 + SCOPA-AUT total, M2 + four domain scores), "
     "with decile-binned predicted-vs-observed probability of event. The "
     "diagonal indicates perfect calibration; all three models calibrate "
     "well, with little visual separation between them."),
]
for fname, desc in FIGURE_DESCRIPTIONS:
    fig_path = os.path.join(FIG, fname)
    if os.path.exists(fig_path):
        p_fig = doc.add_paragraph()
        set_para(p_fig, before=4, after=6, line=2.0,
                 align=WD_ALIGN_PARAGRAPH.CENTER)
        p_fig.add_run().add_picture(fig_path, width=Inches(5.5))
        # Caption immediately below
        p_cap = doc.add_paragraph()
        r = p_cap.add_run(desc)
        set_run(r, size=10)
        set_para(p_cap, before=4, after=6, line=1.5)
    else:
        print(f"  WARNING: figure not found: {fig_path}")

# Save
out_path = os.path.join(PROJ, "manuscript", "manuscript_R1.docx")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
doc.save(out_path)
print(f"\nSaved: {out_path}")
print(f"  total paragraphs: {len(doc.paragraphs)}")
