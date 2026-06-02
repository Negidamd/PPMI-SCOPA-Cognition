#!/usr/bin/env python3
"""
11_surgical_rebuild_R1.py
─────────────────────────
Rebuild the R1 manuscript by applying surgical paragraph-level edits to the
ORIGINAL prose. Goal: preserve the original sentence structure wherever
possible so that the resulting word-level tracked-changes diff shows
small, specific edits (not whole-paragraph rewrites).

Output:
    revision_R1/manuscript/manuscript_R1.docx          (clean)
    revision_R1/manuscript/manuscript_R1_tracked.docx  (tracked changes)
"""
import os, re, datetime, copy
from difflib import SequenceMatcher
from docx import Document
from docx.shared import Pt, RGBColor, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

PROJ = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/1b-papers/SCOPA_Cognition_Study"
ORIG_PATH    = os.path.join(PROJ, "manuscript", "manuscript.docx")
# Output filenames intentionally drop "_R1" — the manuscript should not signal
# that it is a revision (per author preference). Internal folder path
# "revision_R1/" is kept for our workspace organization.
CLEAN_OUT    = os.path.join(PROJ, "revision_R1", "manuscript", "manuscript.docx")
TRACKED_OUT  = os.path.join(PROJ, "revision_R1", "manuscript", "manuscript_tracked.docx")
FIG_DIR      = os.path.join(PROJ, "revision_R1", "figures")

REV_AUTHOR = "Author"
REV_DATE   = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

# ────────────────────────────────────────────────────────────────────────────
# Load original
# ────────────────────────────────────────────────────────────────────────────
orig_doc = Document(ORIG_PATH)
ORIG_PARAS = [(i, p.style.name, p.text) for i, p in enumerate(orig_doc.paragraphs)]
print(f"Loaded {len(ORIG_PARAS)} original paragraphs")

# ────────────────────────────────────────────────────────────────────────────
# SURGICAL EDIT PLAN
# ────────────────────────────────────────────────────────────────────────────
# Each entry is keyed by original paragraph index. Value is one of:
#   ("keep",)                 – keep original text exactly
#   ("replace", new_text)     – replace whole paragraph (word-diff will track it)
#   ("delete",)               – delete this paragraph entirely
# Plus INSERTIONS: list of (after_orig_index, new_text, style) tuples that
# add net-new paragraphs in the R1 manuscript (these will appear as
# wholly-inserted in the tracked-changes file).

EDITS = {}

# ----- Title page header (rows 0-10) ---------------------------------------
# 0  Title (keep)
# 1  empty line — insert running title via INSERTIONS instead
EDITS[1] = ("replace", "Running title: Autonomic items predicting cognitive milestones in PD")
# 2  Author (keep)
# 3  Affiliation (keep — already correct text)
# 4  empty (keep)
# 5  Correspondence (keep — already matches preferred block)
# 6  empty (keep)
# 7  Word count
EDITS[7] = ("replace", "Word count: ~3,200 (manuscript body); ~290 (abstract)")
# 8  Tables
EDITS[8] = ("replace", "Tables: 6 (Word-format companion files); Supplementary Tables: 3")
# 9  Figures
EDITS[9] = ("replace", "Figures: 9 (Figures 1–9); Supplementary Figures: 2 (S1 Schoenfeld PH plot; S2 calibration plot)")
# 10 empty (keep)
# 11 "Abstract" heading (keep)

# ----- Abstract ------------------------------------------------------------
# 12 Purpose — minimal edits
EDITS[12] = ("replace",
    "Purpose: Autonomic dysfunction and cognitive decline are common non-motor features of Parkinson's disease (PD). "
    "We examined whether specific baseline SCOPA-AUT items predict cognitive progression milestones, and which minimal item or domain subset substitutes for the 25-item total in this prognostic context."
)
# 13 Methods — tight version for 250-word abstract
EDITS[13] = ("replace",
    "Methods: We analyzed 1,129 PD patients from the Parkinson's Progression Markers Initiative (PPMI) with baseline SCOPA-AUT, Montreal Cognitive Assessment (MoCA) score ≥ 21, and no baseline PDD. "
    "The primary outcome was the Brumm m10–m15 cognitive milestone composite. "
    "Cox proportional hazards models for each item used a fully-adjusted Model B. "
    "We computed 10-fold cross-validated Harrell's C against a parsimonious clinical base (age, sex, education, MoCA, MDS-UPDRS-III) and a pre-specified subset-sufficiency analysis substituting item or domain subsets for the 25-item total."
)
# 14 Results — tight version
EDITS[14] = ("replace",
    "Results: Over a median follow-up of 3.0 years, 279 of 1,129 patients (24.7%) reached a cognitive milestone. "
    "Under Model B, five items were FDR-significant: dysphagia, early satiety, lightheadedness on standing and on walking, and cold intolerance. "
    "Adding SCOPA-AUT total to the parsimonious base improved Harrell's C from 0.660 to 0.691 (ΔC = +0.031). "
    "In subset-sufficiency analysis, three items—lightheadedness on standing, drooling, straining—or the seven-item gastrointestinal domain alone, recapitulated the 25-item total's discrimination (C = 0.692–0.697). "
    "Findings replicated in the 921-participant SAA-positive sub-cohort."
)
# 15 Conclusions — tight version
EDITS[15] = ("replace",
    "Conclusions: Baseline cardiovascular-orthostatic, gastrointestinal, and thermoregulatory autonomic symptoms independently predict cognitive milestones in PD. "
    "A three-item subset, or the seven-item gastrointestinal domain alone, may substitute the 25-item SCOPA-AUT total in cognitive risk stratification, supporting a clinically actionable parsimonious autonomic screen for early PD."
)
# 17 Keywords — append a few
EDITS[17] = ("replace",
    "Keywords: Parkinson's disease; autonomic dysfunction; SCOPA-AUT; cognitive milestones; non-motor symptoms; orthostatic hypotension; locus coeruleus; body-first Parkinson's; PPMI"
)

# ----- Introduction (19 Heading; 20–23 paragraphs) -------------------------
# 20 first paragraph — minor edits
EDITS[20] = ("replace",
    "Parkinson's disease (PD) is a progressive neurodegenerative disorder characterized by motor and non-motor features. "
    "Among non-motor manifestations, autonomic dysfunction and cognitive impairment represent two of the most prevalent and disabling domains [1,2]. "
    "Both are associated with alpha-synuclein pathology affecting overlapping neural structures, raising the question of whether autonomic symptoms can serve as early markers of cognitive decline [3,4]. "
    "Recent integrative frameworks—including the brain-first / body-first dichotomy and the synuclein-origin-connectome model—propose that peripheral sympathetic and parasympathetic involvement precedes cortical spread in a substantial subset of patients [15,16,24,25]."
)
# 21 second paragraph — add 2025 meta-analyses + JAMDA + Forkert
EDITS[21] = ("replace",
    "The Scales for Outcomes in Parkinson's Disease – Autonomic (SCOPA-AUT) is the most widely used validated instrument for comprehensive autonomic assessment in PD, comprising 25 items across six domains: gastrointestinal, urinary, cardiovascular, thermoregulatory, pupillomotor, and sexual [5]. "
    "Cross-sectional studies have demonstrated associations between SCOPA-AUT scores and cognitive performance [6,7], and two 2025 meta-analyses confirm that orthostatic hypotension is associated with mild cognitive impairment and dementia in PD [21,22], extending an earlier 2023 systematic review [19]. "
    "An 8-year prospective cohort reported that orthostatic hypotension and orthostatic intolerance predict domain-specific cognitive decline [27]. "
    "Multimodal machine-learning models in PPMI have placed the SCOPA-AUT total score among the top predictors of MoCA decline [23], and the Neuronal α-Synuclein Disease Integrated Staging System (NSD-ISS) [26] now permits biologically defined sub-cohort analysis."
)
# 22 third paragraph — keep gist, refine slightly
EDITS[22] = ("replace",
    "Prior studies have primarily examined the SCOPA-AUT total score or broad domain subscores as predictors [8,9], potentially obscuring item-level associations. "
    "Moreover, cognitive outcomes have often been defined using single-instrument thresholds rather than comprehensive milestone-based approaches that capture multiple facets of cognitive deterioration. "
    "Item-level granularity is justifiable only if it adds prognostic information beyond a summary score; this incremental-value question has not been formally tested for SCOPA-AUT items in PD."
)
# 23 fourth paragraph — expand contribution; cite Brumm; SAA sub-analysis
EDITS[23] = ("replace",
    "In this study, we leveraged the Parkinson's Progression Markers Initiative (PPMI), a large multicenter longitudinal PD cohort, to conduct an item-level analysis of all 25 SCOPA-AUT items as predictors of cognitive progression milestones. "
    "We defined cognitive progression milestones using the composite endpoint of Brumm et al. (2023) [12] incorporating severe MoCA decline, UPDRS-I cognitive impairment, hallucinations, apathy, and formal dementia diagnosis, providing a clinically comprehensive outcome. "
    "Our contribution beyond prior work has four components: (i) full clinical adjustment including LEDD, Schwab–England, RBDSQ, disease duration, medication exposure, and Hoehn-Yahr stage; "
    "(ii) formal likelihood-ratio testing of whether each item adds information beyond the SCOPA-AUT total; "
    "(iii) multivariable LASSO Cox and 10-fold cross-validated discrimination/calibration quantifying the prognostic gain of item-level versus aggregated scores; "
    "and (iv) per-milestone decomposition exposing heterogeneity across cognitive and neuropsychiatric outcomes. "
    "A seed-amplification-assay-positive (SAA+) sub-analysis confirms findings within biologically-defined PD."
)

# ----- Methods (25 H1; 26 H2 Study design; 27 paragraph) -------------------
# 27 — add release line (drop "v2.1" / "Master Merged" labels to avoid revision signal)
EDITS[27] = ("replace",
    "This was a longitudinal cohort study using data from PPMI (www.ppmi-info.org), a multicenter prospective study designed to identify biomarkers of PD progression [10]. "
    "The study was approved by the institutional review board at each participating site, and all participants provided written informed consents. "
    "We used the PPMI raw dataset (downloaded on 22 April 2026). "
    "All 25 PPMI progression milestones of Brumm et al. [12] were derived directly from the raw PPMI clinical scales using their published thresholds, including the strict criterion for the composite-dementia milestone (m15)."
)
# 29 — explicit MoCA boundary; drop ≥2y rule (without flagging as a revision)
EDITS[29] = ("replace",
    "For inclusion in this study, we considered the following eligibility criteria: (1) a complete baseline SCOPA-AUT assessment; (2) a baseline MoCA score ≥ 21 (to prevent a 1-point decline from automatically triggering the m10 endpoint); and (3) no baseline PD dementia (PDD). "
    "All participants with any valid follow-up were included; censoring was handled by the survival framework. "
    "Of 1,585 PD subjects, 1,269 had baseline SCOPA-AUT, 1,265 also had baseline MoCA, 1,251 were free of baseline PDD, and 1,129 met the inclusion criteria (Figure 1)."
)
# 31 — SCOPA-AUT exposure; minor edits + note on item-level missingness
EDITS[31] = ("replace",
    "The SCOPA-AUT is a 25-item self-report questionnaire assessing autonomic symptoms across six domains [5]. "
    "Each item is scored 0 (never) to 3 (often). Items 8–13 and 22–25 include a \"not applicable\" option (coded 9), recoded as missing. "
    "Domain subscores and total score were computed allowing up to 3 missing items. "
    "We analyzed each item on its continuous 0–3 scale (per 1-point increase). "
    "Items SCAU22 (pupillomotor) and SCAU23–25 (sexual) have higher item-level missingness and were therefore excluded from the multivariable LASSO and nested-model discrimination analyses; they appear in the univariable item Cox tables on their available complete-case sub-cohorts."
)
# 33 — Outcome; cite Brumm; add sub-composite endpoints
EDITS[33] = ("replace",
    "The primary outcome was reaching any cognitive milestone as defined by Brumm et al. [12], comprising: "
    "(m10) MoCA total score <21; (m11) UPDRS Part I cognition item >3; (m12) UPDRS Part I hallucination item >3; "
    "(m13) UPDRS Part I apathy item >3; (m14) investigator-diagnosed dementia (COGSTATE = 3); or (m15) PDD diagnosis per the Movement Disorder Society (MDS) criteria (PD-MCI with functional impairment). "
    "Time to the first cognitive milestone was the primary time-to-event outcome. "
    "To address heterogeneity within this composite, we additionally considered two sub-composite endpoints—pure cognitive (m10+m14+m15) and pure neuropsychiatric (m12+m13)—and reported all six individual milestones separately."
)
# 35 — Statistical analysis #1; add Model B, PH test, LR test
EDITS[35] = ("replace",
    "We used Cox proportional hazards models to estimate hazard ratios (HRs) for each SCOPA-AUT item, both unadjusted and adjusted. "
    "Model A adjusted for age, sex, education, baseline Montreal Cognitive Assessment (MoCA), and MDS Unified Parkinson's Disease Rating Scale (MDS-UPDRS) Part III motor score. "
    "Model B additionally adjusted for levodopa equivalent daily dose (LEDD; missing assumed = 0 in treatment-naive PPMI baseline subjects), Schwab–England activities of daily living, REM Sleep Behavior Disorder Screening Questionnaire (RBDSQ) total, disease duration from PD diagnosis to enrollment, baseline α-blocker and antihypertensive exposure flags from the PPMI Concomitant Medication Log, and Hoehn-Yahr stage. "
    "The proportional hazards assumption was formally tested by Schoenfeld residual analysis with rank-transformed time. "
    "A likelihood-ratio test of (Model B + SCOPA-AUT total + item) versus (Model B + SCOPA-AUT total) quantified the incremental prognostic information of each item beyond the total score. "
    "Benjamini–Hochberg FDR correction was applied across 25 items; FDR p < 0.05 was considered significant [13]. Domain-level analyses summed items within each SCOPA-AUT domain."
)
# 36 — Statistical analysis #2; add LASSO, discrimination, Fine-Gray, SAA
EDITS[36] = ("replace",
    "Multivariable LASSO Cox regression with 10-fold cross-validation identified the parsimonious subset of items carrying independent information; selection frequency was reported across folds. "
    "Prognostic-model discrimination was quantified by Harrell's concordance index, time-dependent AUC at 4 and 6 years, and integrated Brier score, designed to answer the question: does removing the 25-item SCOPA-AUT total score and replacing it with a smaller set of FDR-significant items or domains improve cognitive risk prediction? The base clinical model (P0) was a parsimonious five-variable set (age, sex, education, baseline MoCA, and MDS-UPDRS Part III) representing the minimum clinical information routinely available at a PD diagnostic encounter; this parsimonious base differs from — and is intentionally narrower than — the 12-covariate model B used for the etiologic item-level Cox hazard-ratio analyses, because the prognostic question is structurally different from the etiologic question (does autonomic burden have an independent association after controlling for severity confounders?). The reference model (P1) was the base plus the 25-item SCOPA-AUT total score. Four additional non-reference models each REPLACED the SCOPA-AUT total with a different parsimonious SCOPA-AUT representation — none of them contain the SCOPA-AUT total: P-sig-dom = base + the three FDR-significant SCOPA-AUT domains (gastrointestinal, cardiovascular, thermoregulatory); P-sig-items = base + the five model-B FDR-significant SCOPA-AUT items (SCAU3, 4, 14, 15, 20); P2 = base + all four SCOPA-AUT domain scores; P3 = base + all 21 fully-available individual items. "
    "We additionally performed a pre-specified subset-sufficiency analysis: for each single SCOPA-AUT domain, for each two-domain combination, and for the top-K LASSO-stable items (K = 1, 2, 3, 4, 5, 8, 12, 17, 21), we fit the parsimonious base plus that subset alone (no 25-item SCOPA-AUT total) and compared 10-fold cross-validated discrimination against the P1 (base + total) benchmark. The smallest subset achieving a C-index within the cross-validated standard deviation of the total was reported as the sufficient subset. "
    "Calibration was assessed by decile-binned predicted-versus-observed probability of event at 4 years. "
    "Sensitivity analyses included: (1) Fine-Gray-style competing-risks analysis with death as the competing event (35 of the 79 deaths during follow-up occurred before any cognitive milestone was reached and therefore constitute true competing-risk events; the remaining 44 deaths followed a previously recorded milestone and are non-competing). A milestone-or-death sensitivity Cox is reported alongside the cause-specific Cox; "
    "(2) restriction to SAA-positive participants (921 of 1,016 with SAA results); "
    "(3) a stricter MoCA ≥ 23 baseline threshold; and "
    "(4) per-milestone item Cox for each of m10–m15 individually. "
    "Kaplan-Meier curves with log-rank tests compared cognitive milestone-free survival across SCOPA-AUT tertiles. "
    "All analyses used Python 3.13 with lifelines 0.30.1, statsmodels, scikit-survival 0.27.0, scipy, pandas, and matplotlib. Random seed = 42 throughout."
)

# ----- Results (38 H1; 39 H2 Baseline; 40 paragraph) ------------------------
# 40 — Baseline characteristics; update numbers
EDITS[40] = ("replace",
    "The analytical cohort comprised 1,129 PD patients (mean age 61.7 years, 70.2% male; 1,072 [95%] White, 17 [1.5%] Black, 12 [1.1%] Asian, 20 [1.8%] Missing/Declined; median disease duration 0.67 years; 921 [81.6%] SAA-positive). "
    "Over a median follow-up of 3 years, 279 (24.7%) reached a cognitive milestone (median time to event 4 years). "
    "Patients who reached cognitive milestones were older (mean 63.6 vs. 61.1 years, p < 0.001), had lower baseline MoCA (median 27 vs. 28, p < 0.001), higher motor severity (UPDRS-III 22 vs. 20, p < 0.001), lower Schwab–England ADL (90 vs. 95, p < 0.001), higher LEDD (735 vs. 450 mg/day, p < 0.001), higher RBDSQ (5 vs. 3, p < 0.001), and higher baseline SCOPA-AUT total scores (11 vs. 9, p < 0.001). "
    "Gastrointestinal, cardiovascular, and thermoregulatory domain scores were all significantly higher in the milestone group (Table 1)."
)
# 42 — Item-level Cox; Model A then Model B
EDITS[42] = ("replace",
    "In univariable Cox models, 17 of 25 SCOPA-AUT items significantly predicted cognitive milestones after FDR correction. "
    "In model A (age, sex, education, baseline MoCA, MDS-UPDRS Part III), 16 of 25 items remained significant after FDR correction. "
    "In model B (additionally including LEDD, Schwab–England, RBDSQ, disease duration, α-blocker and antihypertensive exposure, and Hoehn-Yahr stage), 5 items remained significant after FDR correction (Table 2, Figure 2): "
    "Lightheadedness on standing (SCAU14: aHR 1.53, 95% CI 1.27–1.84, FDR p < 0.001); "
    "Lightheadedness on walking (SCAU15: aHR 1.49, 95% CI 1.20–1.85, FDR p = 0.005); "
    "Cold intolerance (SCAU20: aHR 1.29, 95% CI 1.11–1.50, FDR p = 0.006); "
    "Dysphagia (SCAU3: aHR 1.38, 95% CI 1.10–1.73, FDR p = 0.028); "
    "Early satiety (SCAU4: aHR 1.32, 95% CI 1.09–1.60, FDR p = 0.026). "
    "The proportional hazards assumption was satisfied for every item (all Schoenfeld residual p > 0.05; Supplementary Figure S1)."
)
# 43 — extension paragraph
EDITS[43] = ("replace",
    "The most predictive items under full adjustment were cardiovascular orthostatic (SCAU14, SCAU15), with secondary gastrointestinal deglutition (SCAU3, SCAU4) and thermoregulatory (SCAU20) signals. "
    "A likelihood-ratio test of (model B + SCOPA-AUT total + item) versus (model B + SCOPA-AUT total) revealed that only lightheadedness on standing (SCAU14) significantly added information beyond the SCOPA-AUT total at FDR < 0.05 (χ² = 9.50, unadjusted p = 0.002, FDR p = 0.049). "
    "All other model B FDR-significant items were essentially redundant markers of the same underlying autonomic burden captured by the SCOPA-AUT total score."
)
# 45 — Domain-level analysis; update numbers + remove urinary as sig
EDITS[45] = ("replace",
    "Four of seven SCOPA-AUT summary scores independently predicted cognitive milestones in adjusted Cox models (Table 3, Figure 4): "
    "gastrointestinal (aHR 1.10 per 1-point increase, p < 0.001), cardiovascular (aHR 1.27, p < 0.001), thermoregulatory (aHR 1.07, p = 0.020), and SCOPA-AUT total (aHR 1.03 per 1-point, p < 0.001). "
    "The urinary domain (aHR 1.03, p = 0.177) was not significant after full model B adjustment, attributable to the inclusion of LEDD and disease-duration covariates indexing medication exposure and disease severity."
)
# 47 — Kaplan-Meier — dose-response → graded
EDITS[47] = ("replace",
    "Kaplan-Meier analysis stratified by SCOPA-AUT total score tertiles showed a graded separation, with a higher autonomic burden being associated with earlier cognitive milestone attainment (log-rank p < 0.001; Figure 3). "
    "The middle and high tertiles overlap visually until approximately year 7; we therefore describe the relationship as a graded rather than dose-response effect."
)
# 49,50,51 — Sensitivity; replace with SAA / per-milestone summary / Fine-Gray+MoCA≥23
EDITS[49] = ("replace",
    "Restriction to the 921-participant seed-amplification-assay-positive (SAA+) subgroup (238 composite events; Supplementary Table S1) replicated the model B findings, with 6 items surviving FDR correction: dysphagia, early satiety, fecal incontinence, lightheadedness on standing, lightheadedness on walking, and cold intolerance."
)
EDITS[50] = ("replace",
    "For individual milestones (Table 4), lightheadedness on standing (SCAU14) was the single item consistently significant across MoCA<21 (m10, 111 events), UPDRS-I cognition (m11, 137 events), and apathy (m13, 119 events) endpoints. "
    "For hallucinations (m12, 35 events) and investigator-diagnosed dementia (m14, 78 events) no items survived FDR. "
    "For PDD per MDS criteria (m15, 90 events) only drooling (SCAU2) and straining (SCAU6) survived. "
    "For the pre-specified pure-cognitive sub-composite (m10+m14+m15; 171 events) no items survived FDR after full adjustment, whereas for the pure-neuropsychiatric sub-composite (m12+m13; 138 events) five items survived FDR: swallowing/choking, dysphagia, lightheadedness on standing, lightheadedness on walking, and cold intolerance."
)
EDITS[51] = ("replace",
    "The Fine-Gray-style competing-risks sensitivity (Supplementary Table S2) showed a maximum absolute Δ %HR of 6.4% between cause-specific and milestone-or-death framings, confirming negligible competing-risk bias. 35 of the 79 deaths during follow-up occurred before a cognitive milestone (true competing events); the remaining 44 deaths followed a previously recorded milestone. "
    "Restriction to baseline MoCA ≥ 23 (N = 1,088) gave directionally concordant results. "
    "Comparison of included versus excluded participants showed that excluded participants had higher baseline SCOPA-AUT scores (p = 0.008) and higher RBDSQ scores (p = 0.022) but similar age, MoCA, and motor severity, suggesting modest attrition bias toward underestimation of effect sizes."
)

# ----- Discussion (53 H1; 54–60 paragraphs; 61 Conclusions H2; 62) ---------
# 54 — Discussion opener; update N + add nested-model discrimination note
EDITS[54] = ("replace",
    "In this 1,129-patient longitudinal analysis of PD from PPMI, we found that multiple baseline SCOPA-AUT items independently predicted the development of cognitive milestones, with 5 items surviving FDR correction in the fully-adjusted model B (cardiovascular orthostatic, gastrointestinal deglutition, and thermoregulatory). "
    "Against a parsimonious clinical comparator (age, sex, education, baseline MoCA, MDS-UPDRS Part III), adding SCOPA-AUT total to the model meaningfully improved 10-fold cross-validated discrimination by ΔC = +0.031 (0.660 → 0.691). "
    "More importantly, when we asked which minimal SCOPA-AUT subset achieves the same discrimination as the 25-item total instead of which items add to it, three items—lightheadedness on standing, drooling, and straining—or equivalently the seven-item gastrointestinal domain alone, recapitulated the 25-item total's discrimination (C = 0.692–0.697 versus the total's 0.691). "
    "Adding the remaining 14–18 items did not improve, and at higher item counts actually degraded, discrimination. "
    "Together, these findings demonstrate that autonomic dysfunction and cognitive decline in PD share prognostic information that is concentrated in a few orthostatic-gastrointestinal items, and they suggest a clinically actionable parsimonious screen for cognitive risk stratification in early PD."
)
# 55 — second discussion paragraph (Braak + body-first)
EDITS[55] = ("replace",
    "The breadth of significant autonomic predictors—spanning gastrointestinal (dysphagia, early satiety), cardiovascular (lightheadedness on standing and walking), and thermoregulatory (cold intolerance) domains—suggests that widespread autonomic involvement, rather than dysfunction in a single system, signals higher risk for cognitive deterioration. "
    "This is consistent with the Braak staging hypothesis of caudal-to-rostral α-synuclein progression through the brainstem [14], and with the emerging brain-first versus body-first PD subtype framework as updated by Borghammer and colleagues [24] and Dorsey et al. [25]. "
    "Patients with extensive peripheral autonomic involvement may represent a sympathetic body-first subtype with more aggressive cortical spread."
)
# 56 — third paragraph; orthostatic + locus coeruleus + prefrontal-insular-PAG
EDITS[56] = ("replace",
    "The finding that lightheadedness on standing (SCAU14) was the strongest independent predictor and the single item adding information beyond SCOPA-AUT total is particularly noteworthy. "
    "Orthostatic intolerance reflects sympathetic and brainstem noradrenergic dysfunction; the locus coeruleus is increasingly recognized as a common substrate for cardiovascular autonomic dysregulation and downstream attentional/executive deficits [18,19,21,22,27]. "
    "The prefrontal–insular–periaqueductal-gray network that integrates autonomic state with executive function — including pontine micturition centers and their cortical connections [17] — offers a parallel substrate for the cardiovascular–cognitive coupling we observed."
)
# 57 — thermoregulatory paragraph
EDITS[57] = ("replace",
    "Cold intolerance (SCAU20) was among the strongest predictors, surviving FDR correction in both model A and model B and replicating in the SAA+ sub-cohort. "
    "Thermoregulatory dysfunction reflects hypothalamic and sympathetic involvement, and hypothalamic pathology is increasingly recognized as an early feature of PD with implications for cognitive circuits [20]."
)
# 58 — temporal relationship & dose-response → graded
EDITS[58] = ("replace",
    "Our results extend prior cross-sectional findings [6,7] by demonstrating a temporal relationship: baseline autonomic symptoms predict future cognitive milestones. "
    "Per-milestone decomposition reveals an important and previously under-appreciated heterogeneity: the autonomic signal is strongest for self-reported MDS-UPDRS-I cognition (m11) and apathy (m13), and weakest for strict cognitive endpoints (MoCA<21, investigator-diagnosed dementia, MDS PDD). "
    "When decomposed into a pure-cognitive sub-composite (m10+m14+m15), no individual items survive FDR after full adjustment. "
    "This vindicates earlier concerns that composite endpoints conflating cognitive and neuropsychiatric outcomes may obscure outcome-specific signal."
)
# 59 — strengths paragraph
EDITS[59] = ("replace",
    "Strengths include the large multicenter cohort, comprehensive milestone-based cognitive outcome, item-level granularity with formal FDR correction and incremental-value testing, expanded covariate adjustment (model B), Schoenfeld-tested proportional-hazards assumption, multivariable LASSO Cox, 10-fold cross-validated discrimination and calibration, Fine-Gray competing-risks check, SAA+ replication, and per-milestone decomposition. "
    "All 25 PPMI progression milestones of Brumm et al. [12] (including the cognitive composite) were derived directly from the raw PPMI clinical scales using their published thresholds."
)
# 60 — limitations paragraph; add UPSIT line
EDITS[60] = ("replace",
    "This study has some limitations including: (1) the PPMI cohort represents recently-diagnosed PD (median disease duration 0.67 years), limiting generalizability to advanced disease; "
    "(2) SCOPA-AUT is self-reported and does not capture objective autonomic measures (tilt-table testing, cardiovagal reflexes, 24-hour blood pressure); "
    "(3) the composite cognitive milestone endpoint could conflate cognitive and neuropsychiatric features—we addressed this with per-milestone reporting; "
    "(4) items SCAU22–25 had higher missingness and were excluded from multivariable analyses; "
    "(5) although 35 of 79 deaths during follow-up constitute true competing-risk events, the cause-specific and milestone-or-death framings differ by at most 6.4% across items (Supplementary Table S2), suggesting that competing-risk bias is small in this newly-diagnosed cohort but may be larger in older or more advanced PD populations; "
    "(6) UPSIT was missing for 561 participants (49.7%); the unadjusted UPSIT median difference was substantial in magnitude but underpowered by missingness and consistent with hyposmia as a known prodromal/progression marker. "
    "Future studies should examine whether combining autonomic items with biomarkers (SAA, neuroimaging) and other non-motor markers improves prognostic accuracy."
)
# 62 — Conclusions; temper, remove "dose-response"
EDITS[62] = ("replace",
    "Multiple baseline autonomic symptoms assessed by SCOPA-AUT independently predict cognitive milestones in PD, with cardiovascular orthostatic, gastrointestinal deglutition, and thermoregulatory items showing the strongest associations under full clinical adjustment. "
    "Against a parsimonious clinical comparator (age, sex, education, baseline MoCA, MDS-UPDRS Part III), the SCOPA-AUT total adds meaningful prognostic information for cognitive milestones (ΔC = +0.031). "
    "The prognostic content of the 25-item SCOPA-AUT total is concentrated in three items—lightheadedness on standing, drooling, and straining—or equivalently in the seven-item gastrointestinal domain, either of which recapitulates the discrimination of the full 25-item scale (C ≈ 0.692–0.697). "
    "These findings suggest a clinically actionable parsimonious screen for cognitive risk stratification in early PD: three brief autonomic questions can substitute for the full SCOPA-AUT scale in this prognostic context. "
    "The autonomic signal preferentially predicts neuropsychiatric features (apathy, self-reported cognitive symptoms) over strict cognitive endpoints, consistent with shared brainstem and locus coeruleus substrates."
)

# ----- Declarations (64 H1; 65 H2 Ethics; 66 paragraph) ---------------------
# 66 — keep
# 75 — Data availability — preserve almost verbatim
# 78 — keep
# 81 — AI assistance — KEEP UNCHANGED from original first submission per user request 2026-05-28
# (do NOT add an independent-verification sentence here; tracked diff should show no change for this paragraph)

# ----- References — add DOI/PMID to key 2023 cites, add new ones -----------
# Surgical edits to [12] Brumm and [19] Loureiro to add DOI/PMID for verifiability
EDITS[95] = ("replace",
    "[12] Brumm MC, Siderowf A, Simuni T, et al. Parkinson's Progression Markers Initiative: a milestone-based strategy to monitor Parkinson's disease progression. J Parkinsons Dis. 2023;13(6):899-916. doi:10.3233/JPD-223433. PMID 37458046."
)
EDITS[103] = ("replace",
    "[19] Loureiro D, Bilbao R, Bordet S, et al. A systematic review and meta-analysis on the association between orthostatic hypotension and mild cognitive impairment and dementia in Parkinson's disease. Neurol Sci. 2023;44(4):1211-1222. doi:10.1007/s10072-022-06537-3. PMID 36542202."
)

# ----- Figure captions (108, 111, 113, 116, 120) ----------------------------
EDITS[108] = ("replace",
    "Figure 1. CONSORT-style flow diagram of participant selection from the PPMI 22 April 2026 cohort, yielding the analytical cohort of 1,129 participants with 279 composite cognitive-milestone events."
)
EDITS[111] = ("replace",
    "Figure 2. Paired forest plot of adjusted hazard ratios (95% CI) for each SCOPA-AUT item (1–21) predicting the composite cognitive milestone. "
    "Left panel: Model A (age, sex, education, baseline MoCA, MDS-UPDRS Part III). "
    "Right panel: Model B (additionally including LEDD, Schwab–England, RBDSQ, disease duration, α-blocker exposure, antihypertensive exposure, Hoehn-Yahr stage). "
    "Items ordered by domain (gastrointestinal, urinary, cardiovascular, thermoregulatory). FDR-significant items shown with filled markers."
)
EDITS[113] = ("replace",
    "Figure 3. Kaplan-Meier curves for cognitive milestone-free survival stratified by baseline SCOPA-AUT total score tertiles. Number at risk shown below. Log-rank p < 0.001. The middle and high tertiles overlap visually until approximately year 7; we describe this as a graded rather than a dose-response separation."
)
EDITS[116] = ("replace",
    "Figure 4. Domain-level SCOPA-AUT subscores as predictors of cognitive milestones in adjusted Model B Cox models (forest plot). Bars show 95% confidence intervals; filled circles indicate FDR-significant domains (p < 0.05), hollow circles indicate non-significant. Blue = significant positive association; grey = non-significant; purple = significant inverse association. p-values shown to the right."
)
EDITS[120] = ("replace",
    "Figure 5. Per-milestone heatmap of log2-transformed adjusted hazard ratios (Model B) across the six individual cognitive milestones (m10–m15) and the two sub-composite endpoints (pure cognitive = m10+m14+m15; pure neuropsychiatric = m12+m13). "
    "Cell annotations show HR and FDR significance. Heterogeneity is apparent across outcomes—the autonomic signal preferentially predicts neuropsychiatric milestones."
)

# ────────────────────────────────────────────────────────────────────────────
# INSERTIONS — net-new paragraphs added in R1
# ────────────────────────────────────────────────────────────────────────────
# Each entry: (after_orig_index, text, style)
# These will appear as wholly-inserted paragraphs in the tracked-changes file.
INSERTIONS = [
    # === Results: net-new H2 subsections after the Sensitivity section
    # (anchored to orig idx 51, the last sensitivity paragraph) ===

    (51, "Multivariable LASSO Cox", "Heading 2"),
    (51, "In 10-fold cross-validated LASSO Cox over the 21 fully-available items, against the parsimonious clinical base (Figure 6, Supplementary Table S3), only five items were ever retained at λ.1se across any fold: lightheadedness on standing (SCAU14) in 9 of 10 folds; drooling (SCAU2) and straining (SCAU6) in 7 of 10 folds each; lightheadedness on walking (SCAU15) in 2 of 10 folds; and cold intolerance (SCAU20) in 1 of 10 folds. "
         "The remaining 16 items (including all urinary and thermoregulatory items except cold intolerance, and the other gastrointestinal items beyond drooling and straining) were never selected. "
         "The LASSO selection pattern is concordant with the univariable model B FDR-significant items and identifies orthostatic-gastrointestinal items as the most stably contributing predictors.",
         "Normal"),

    (51, "Discrimination: replacing the SCOPA-AUT total with parsimonious items or domains", "Heading 2"),
    (51, "Prognostic-model 10-fold cross-validated discrimination was evaluated in the complete-case discrimination cohort (N = 1,123; 279 composite events), restricted to participants with all 21 fully-available SCOPA-AUT items (items SCAU22–25 excluded due to higher item-level missingness). "
         "The analysis directly addressed the prognostic question: does replacing the 25-item SCOPA-AUT total with a smaller set of FDR-significant items or domains improve discrimination? "
         "Results (Table 5, Figure 7): the parsimonious clinical base alone (P0) achieved Harrell's C = 0.660. The reference model (P1: base + 25-item SCOPA-AUT total) reached C = 0.691, an improvement of ΔC = +0.031 over P0. "
         "When the SCOPA-AUT total was REPLACED with three FDR-significant domains (P-sig-dom: gastrointestinal + cardiovascular + thermoregulatory), discrimination was C = 0.700 — comparable to the total (ΔC = +0.009 vs P1; well within the per-fold standard deviation of ~0.054). "
         "When replaced with the five model-B FDR-significant items (P-sig-items: SCAU3, 4, 14, 15, 20), discrimination was C = 0.693 — also comparable to the total (ΔC = +0.002 vs P1). "
         "Replacing the total with all four SCOPA-AUT domain scores (P2) gave C = 0.699 — likewise comparable (ΔC = +0.008 vs P1). "
         "Replacing the total with all 21 individual items (P3) caused overfitting, reducing discrimination to C = 0.684 (ΔC = −0.007 vs P1) — the 26-feature model is too rich for 279 events. "
         "These results demonstrate that the 25-item SCOPA-AUT total can be replaced by either a three-domain or a five-item parsimonious subset without losing prognostic information, with discrimination comparable to that of the full 25-item scale. "
         "Time-dependent AUCs at 4 and 6 years and integrated Brier scores told the same story (Table 5). "
         "Calibration at 4 years was acceptable for the three reference and replacement models (P0, P1, P-sig-items) with little visual separation between them (Supplementary Figure S2).",
         "Normal"),

    (51, "Subset sufficiency: domains and items that recapitulate the 25-item total", "Heading 2"),
    (51, "We then asked the inverse question: which minimal SCOPA-AUT subset, used instead of the 25-item total, achieves the same discrimination as adding the total to the parsimonious clinical base (P1: C = 0.691)? "
         "Single-domain analysis (Table 6) showed that the gastrointestinal domain alone (seven items) reached C = 0.697, comparable to the 25-item total (ΔC = +0.005). "
         "The cardiovascular, thermoregulatory, and urinary domains alone underperformed the total (C = 0.683, 0.680, and 0.671 respectively). "
         "All four domains together yielded C = 0.699, comparable to the gastrointestinal domain alone. "
         "At the item level (Figure 9), ranking items by 10-fold LASSO selection frequency and adding them sequentially, a three-item subset—lightheadedness on standing (SCAU14), drooling (SCAU2), and straining (SCAU6)—achieved C = 0.692, precisely matching the 25-item total. "
         "A two-item subset (SCAU14 + SCAU2) was within the cross-validated noise envelope of the total (C = 0.685; ΔC = −0.007 against a per-fold standard deviation of ~0.06). "
         "C-index remained at or above the P1 target through K = 12 items and then declined as additional items added noise without signal (K = 21: C = 0.684). "
         "Thus the prognostic information carried by the 25-item SCOPA-AUT total is concentrated in three orthostatic-gastrointestinal items, or equivalently in the seven-item gastrointestinal domain, either of which recapitulates the total's prediction of cognitive milestones.",
         "Normal"),

    # === New references at end of ref list (after orig idx 104, "[20] Del Tredici…") ===
    (104, "[21] Liu Y, et al. The relationship between orthostatic hypotension and cognitive impairment in Parkinson's disease: a systematic review and meta-analysis. Front Med (Lausanne). 2025;12:1659043. doi:10.3389/fmed.2025.1659043. PMID 40995103.", "Normal"),
    (104, "[22] Wang H, et al. Orthostatic hypotension in Parkinson's disease: effects on clinical features and disease severity—a systematic review and meta-analysis. Front Aging Neurosci. 2025;17:1612960. doi:10.3389/fnagi.2025.1612960. PMID 40746363.", "Normal"),
    (104, "[23] Almgren H, Camacho M, Hanganu A, et al. Machine learning-based prediction of longitudinal cognitive decline in early Parkinson's disease using multimodal features. Sci Rep. 2023;13(1):13193. doi:10.1038/s41598-023-37644-6. PMID 37580407.", "Normal"),
    (104, "[24] Andersen KB, Krishnamurthy A, Just MK, et al. Sympathetic and parasympathetic subtypes of body-first Lewy body disease observed in postmortem tissue from prediagnostic individuals. Nat Neurosci. 2025;28(5):925-936. doi:10.1038/s41593-025-01910-9. PMID 40082617.", "Normal"),
    (104, "[25] Dorsey ER, De Miranda BR, Horsager J, Borghammer P. The body, the brain, the environment, and Parkinson's disease. J Parkinsons Dis. 2024;14(3):363-381. doi:10.3233/JPD-240019. PMID 38607765.", "Normal"),
    (104, "[26] Dam T, Pagano G, Brumm MC, et al. Neuronal alpha-Synuclein Disease integrated staging system performance in PPMI, PASADENA, and SPARK baseline cohorts. NPJ Parkinsons Dis. 2024;10(1):178. doi:10.1038/s41531-024-00789-w. PMID 39333167.", "Normal"),
    (104, "[27] Choi S, Kim R, Kang N, et al. Associations of orthostatic hypotension and orthostatic intolerance with domain-specific cognitive decline in patients with early Parkinson disease: an 8-year follow-up. J Am Med Dir Assoc. 2024;25(5):866-870. doi:10.1016/j.jamda.2023.10.002. PMID 37935379.", "Normal"),

    # === New figure captions after Figure 5 ===
    (120, "", "Normal"),
    (120, "Figure 6. LASSO Cox regression selection frequency across 10-fold cross-validation. Each lollipop shows the number of folds (out of 10) in which the item was retained at λ.1se. All 21 fully-available SCOPA-AUT items (SCAU1–21) are shown — items with hollow grey markers were never selected by LASSO across any fold (0/10). Item labels are coloured by SCOPA-AUT domain. The vertical dotted line at x = 8 marks the pre-specified stable-selection threshold (≥ 8 of 10 folds).", "Normal"),
    (120, "", "Normal"),
    (120, "Figure 7. Prognostic-model discrimination (Harrell's concordance index, 10-fold cross-validation) for the composite cognitive milestone. Each row shows one model: a horizontal bar with whiskers giving mean C ± 1 SD across folds, and an annotation column on the right giving C and the change vs the P1 reference (ΔC). All six models share a common parsimonious five-variable clinical base (P0: age, sex, education, baseline MoCA, MDS-UPDRS Part III). P1 is the reference model (base + SCOPA-AUT total). The remaining four models REPLACE the SCOPA-AUT total with a different parsimonious SCOPA-AUT representation — none of them contain the SCOPA-AUT total — and are marked with an asterisk in the row label: P-sig-dom = base + 3 FDR-significant SCOPA-AUT domains (gastrointestinal, cardiovascular, thermoregulatory); P-sig-items = base + 5 FDR-significant SCOPA-AUT items (SCAU 3, 4, 14, 15, 20); P2 = base + all 4 SCOPA-AUT domains; P3 = base + all 21 SCOPA-AUT items. ΔC values are coloured green when ≥ P1 and red when < P1. Replacing the SCOPA-AUT total with 3 FDR-significant domains, 5 FDR-significant items, or all 4 domains yields discrimination comparable to the 25-item total (all ΔC within ± 0.01, well inside the per-fold standard deviation of ~0.054). Replacing it with all 21 items causes overfitting (ΔC = −0.007).", "Normal"),
    (120, "", "Normal"),
    (120, "Figure 8. Proportional contribution of each individual milestone (m10–m15) to the composite cognitive-milestone events. Percentages sum to >100% because individual participants can reach multiple milestones over follow-up.", "Normal"),
    (120, "", "Normal"),
    (120, "Figure 9. Subset-sufficiency curve for the composite cognitive milestone. Each point is the 10-fold cross-validated Harrell's C-index for a model containing the parsimonious five-variable clinical base (age, sex, education, baseline MoCA, MDS-UPDRS Part III) plus the top-K SCOPA-AUT items (ranked by LASSO selection frequency), with no SCOPA-AUT total or domain scores. The dashed red line is the C-index of the base + 25-item SCOPA-AUT total model (P1; C = 0.691); the dotted grey line is the base-only model (P0; C = 0.660). A three-item subset (lightheadedness on standing, drooling, straining) reaches the same discrimination as the 25-item total; a two-item subset is within the cross-validated noise envelope of the total.", "Normal"),
    (120, "", "Normal"),
    (120, "Supplementary Figure S1. Schoenfeld residual proportional-hazards test p-values for each item (Model B). Dashed red line indicates the 0.05 threshold for PH violation; no items violate the PH assumption.", "Normal"),
    (120, "", "Normal"),
    (120, "Supplementary Figure S2. Calibration plot at t = 4 years for three nested models (P0 base, P1 + SCOPA-AUT total, P2 + four domain scores), with decile-binned predicted-vs-observed probability of event. The diagonal indicates perfect calibration; all three models calibrate well, with little visual separation between them.", "Normal"),
]

# ────────────────────────────────────────────────────────────────────────────
# Build the planned R1 paragraph stream
# ────────────────────────────────────────────────────────────────────────────
# Two parallel lists:
#   plan_orig_text[k]  = original text at planned position k (or "" if INSERT)
#   plan_new_text[k]   = final new text at planned position k
#   plan_style[k]      = style for the paragraph
#
# An "edit" position has both orig and new; an "insert" has empty orig.

# Insertions by anchor index
ins_by_anchor = {}
for after_i, text, style in INSERTIONS:
    ins_by_anchor.setdefault(after_i, []).append((text, style))

plan = []  # list of dicts: {orig: str, new: str, style: str, kind: 'edit'|'insert'|'delete'}

for i, (idx, style, text) in enumerate(ORIG_PARAS):
    action = EDITS.get(idx, ("keep",))
    if action[0] == "keep":
        plan.append({"orig": text, "new": text, "style": style, "kind": "edit"})
    elif action[0] == "replace":
        plan.append({"orig": text, "new": action[1], "style": style, "kind": "edit"})
    elif action[0] == "delete":
        plan.append({"orig": text, "new": "", "style": style, "kind": "delete"})

    # After this original paragraph, add any insertions anchored at idx
    for new_text, new_style in ins_by_anchor.get(idx, []):
        plan.append({"orig": "", "new": new_text, "style": new_style, "kind": "insert"})

# ────────────────────────────────────────────────────────────────────────────
# Word-diff helpers — wrap inserts in <w:ins>, deletes in <w:del>
# ────────────────────────────────────────────────────────────────────────────
_REV_ID = [0]
def _next_rev_id():
    _REV_ID[0] += 1
    return _REV_ID[0]

def make_run_xml(text, *, size=11, bold=False, italic=False):
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rFonts = OxmlElement("w:rFonts")
    for a in ("w:ascii", "w:hAnsi", "w:cs"): rFonts.set(qn(a), "Arial")
    rPr.append(rFonts)
    sz = OxmlElement("w:sz"); sz.set(qn("w:val"), str(int(size * 2))); rPr.append(sz)
    color = OxmlElement("w:color"); color.set(qn("w:val"), "000000"); rPr.append(color)
    if bold: rPr.append(OxmlElement("w:b"))
    if italic: rPr.append(OxmlElement("w:i"))
    r.append(rPr)
    t = OxmlElement("w:t"); t.text = text; t.set(qn("xml:space"), "preserve")
    r.append(t)
    return r

def make_ins(text, *, size=11, bold=False, italic=False):
    ins = OxmlElement("w:ins")
    ins.set(qn("w:id"), str(_next_rev_id()))
    ins.set(qn("w:author"), REV_AUTHOR)
    ins.set(qn("w:date"), REV_DATE)
    ins.append(make_run_xml(text, size=size, bold=bold, italic=italic))
    return ins

def make_del(text, *, size=11, bold=False, italic=False):
    delete = OxmlElement("w:del")
    delete.set(qn("w:id"), str(_next_rev_id()))
    delete.set(qn("w:author"), REV_AUTHOR)
    delete.set(qn("w:date"), REV_DATE)
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rFonts = OxmlElement("w:rFonts")
    for a in ("w:ascii", "w:hAnsi", "w:cs"): rFonts.set(qn(a), "Arial")
    rPr.append(rFonts)
    sz = OxmlElement("w:sz"); sz.set(qn("w:val"), str(int(size * 2))); rPr.append(sz)
    color = OxmlElement("w:color"); color.set(qn("w:val"), "000000"); rPr.append(color)
    if bold: rPr.append(OxmlElement("w:b"))
    if italic: rPr.append(OxmlElement("w:i"))
    r.append(rPr)
    delText = OxmlElement("w:delText"); delText.text = text
    delText.set(qn("xml:space"), "preserve")
    r.append(delText)
    delete.append(r)
    return delete

def tokenize(text):
    # Whitespace-aware tokenization: word + trailing spaces stays attached
    return re.findall(r'\S+\s*|\s+', text)

# ────────────────────────────────────────────────────────────────────────────
# Build CLEAN R1 manuscript
# ────────────────────────────────────────────────────────────────────────────
def add_paragraph(doc, text, *, style="Normal", size=11, bold=False, italic=False,
                   align=None, before=4, after=6, line=2.0):
    p = doc.add_paragraph()
    if style.startswith("Heading"):
        try:
            p.style = doc.styles[style]
        except: pass
        bold = True
        before = 12
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if align is not None:
        p.alignment = align
    if text:
        r = p.add_run(text)
        r.font.name = "Arial"; r.font.size = Pt(size)
        r.font.bold = bold; r.font.italic = italic
        r.font.color.rgb = RGBColor(0, 0, 0)
        rPr = r._r.get_or_add_rPr()
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts")
            rPr.append(rFonts)
        for a in ("w:ascii", "w:hAnsi", "w:cs"): rFonts.set(qn(a), "Arial")
    return p

def setup_section(doc):
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Cm(2.54)
    section.left_margin = section.right_margin = Cm(2.54)
    # Line numbers
    sectPr = section._sectPr
    lnNum = OxmlElement("w:lnNumType")
    lnNum.set(qn("w:countBy"), "1")
    lnNum.set(qn("w:restart"), "continuous")
    lnNum.set(qn("w:distance"), "284")
    sectPr.append(lnNum)
    # Page numbers in footer
    footer = section.footer
    footer_p = footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = footer_p.add_run()
    fr.font.name = "Arial"; fr.font.size = Pt(10)
    for tag, ftype in (("begin", "fldChar"), ("instr", "instrText"), ("end", "fldChar")):
        e = OxmlElement(f"w:{ftype}")
        if ftype == "fldChar":
            e.set(qn("w:fldCharType"), tag)
        else:
            e.text = "PAGE"
        fr._r.append(e)

# Determine paragraphs that need a page break before them
PAGE_BREAK_SECTIONS = {"Abstract", "Introduction", "Methods", "Results",
                      "Discussion", "Declarations", "References", "Figures"}

def is_section_break_heading(text, style):
    return style == "Heading 1" and text.strip() in PAGE_BREAK_SECTIONS

# Build clean doc
clean = Document()
setup_section(clean)

for entry in plan:
    if entry["kind"] == "delete":
        continue  # skip deletions in clean output
    text = entry["new"]
    style = entry["style"]
    if is_section_break_heading(text, style):
        # add page break before
        # python-docx: add empty paragraph with page break, then heading
        p = clean.add_paragraph()
        r = p.add_run()
        r.add_break(WD_BREAK.PAGE)
    add_paragraph(clean, text, style=style)

# Embed figures inline above their captions in the Figures section.
# We walk the doc once it's been built, find each "Figure N." caption, and
# insert the corresponding PNG image just above the caption paragraph.
FIGURE_FILES = {
    "Figure 1.": "Figure1_flowchart.png",
    "Figure 2.": "Figure2_forest_modelA_vs_modelB.png",
    "Figure 3.": "Figure3_KM_tertiles.png",
    "Figure 4.": "Figure4_domain_lollipop.png",
    "Figure 5.": "Figure5_heatmap_per_milestone.png",
    "Figure 6.": "Figure6_lasso_coefficient_path.png",
    "Figure 7.": "Figure7_discrimination.png",
    "Figure 9.": "Figure9_subset_sufficiency.png",
    "Figure 8.": "Figure8_milestone_contribution.png",
    "Supplementary Figure S1.": "FigureS1_schoenfeld_PH.png",
    "Supplementary Figure S2.": "calibration_4y.png",
}

def insert_image_before(paragraph, image_path, max_width_in=6.0):
    """Insert a paragraph containing an image immediately before `paragraph`."""
    new_p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:before"), "80")   # 4pt = 80 twentieths
    spacing.set(qn("w:after"), "120")   # 6pt
    spacing.set(qn("w:line"), "480")    # double-space
    spacing.set(qn("w:lineRule"), "auto")
    pPr.append(spacing)
    jc = OxmlElement("w:jc"); jc.set(qn("w:val"), "center")
    pPr.append(jc)
    new_p.append(pPr)
    paragraph._p.addprevious(new_p)
    # Use python-docx Paragraph wrapper to add picture
    from docx.text.paragraph import Paragraph
    np = Paragraph(new_p, paragraph._parent)
    r = np.add_run()
    try:
        r.add_picture(image_path, width=Inches(max_width_in))
    except Exception as e:
        print(f"WARN: could not embed {image_path}: {e}")

# Embed in clean doc
for p in clean.paragraphs:
    for prefix, fn in FIGURE_FILES.items():
        if p.text.strip().startswith(prefix):
            img = os.path.join(FIG_DIR, fn)
            if os.path.exists(img):
                insert_image_before(p, img)
            else:
                print(f"WARN: figure missing: {img}")
            break

clean.save(CLEAN_OUT)
print(f"Saved clean R1: {CLEAN_OUT}")

# ────────────────────────────────────────────────────────────────────────────
# Build TRACKED-CHANGES R1 manuscript
# ────────────────────────────────────────────────────────────────────────────
tracked = Document()
setup_section(tracked)

def add_tracked_paragraph(doc, orig_text, new_text, *, style="Normal",
                          size=11, bold=False, italic=False,
                          before=4, after=6, line=2.0):
    p = doc.add_paragraph()
    if style.startswith("Heading"):
        try:
            p.style = doc.styles[style]
        except: pass
        bold = True
        before = 12
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line

    if orig_text == new_text:
        if new_text:
            r = p.add_run(new_text)
            r.font.name = "Arial"; r.font.size = Pt(size)
            r.font.bold = bold; r.font.italic = italic
            r.font.color.rgb = RGBColor(0, 0, 0)
            rPr = r._r.get_or_add_rPr()
            rFonts = rPr.find(qn("w:rFonts"))
            if rFonts is None:
                rFonts = OxmlElement("w:rFonts")
                rPr.append(rFonts)
            for a in ("w:ascii", "w:hAnsi", "w:cs"): rFonts.set(qn(a), "Arial")
        return p

    orig_tokens = tokenize(orig_text)
    new_tokens  = tokenize(new_text)
    matcher = SequenceMatcher(None, orig_tokens, new_tokens)
    p_xml = p._p
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            txt = "".join(new_tokens[j1:j2])
            if txt:
                p_xml.append(make_run_xml(txt, size=size, bold=bold, italic=italic))
        elif tag == "delete":
            txt = "".join(orig_tokens[i1:i2])
            if txt:
                p_xml.append(make_del(txt, size=size, bold=bold, italic=italic))
        elif tag == "insert":
            txt = "".join(new_tokens[j1:j2])
            if txt:
                p_xml.append(make_ins(txt, size=size, bold=bold, italic=italic))
        elif tag == "replace":
            d = "".join(orig_tokens[i1:i2])
            i = "".join(new_tokens[j1:j2])
            if d:
                p_xml.append(make_del(d, size=size, bold=bold, italic=italic))
            if i:
                p_xml.append(make_ins(i, size=size, bold=bold, italic=italic))
    return p

for entry in plan:
    orig = entry["orig"]
    new  = entry["new"]
    style = entry["style"]
    kind = entry["kind"]
    # Page break before Heading 1 section breaks
    target_text = new if new else orig
    if is_section_break_heading(target_text, style):
        p = tracked.add_paragraph()
        r = p.add_run()
        r.add_break(WD_BREAK.PAGE)
    if kind == "delete":
        # whole paragraph deleted
        add_tracked_paragraph(tracked, orig, "", style=style)
    else:
        add_tracked_paragraph(tracked, orig, new, style=style)

# Embed figures into tracked-changes doc as well (so reviewers see them in context).
# Note: tracked-changes paragraphs may be wholly inside <w:ins>, in which case
# python-docx's paragraph.text returns ''. We traverse all <w:t> elements
# (including inside <w:ins>) to get the full text.
def _full_text(p):
    txt = ''
    for t in p._p.iter():
        if t.tag.endswith('}t'):
            txt += (t.text or '')
    return txt

for p in tracked.paragraphs:
    t = _full_text(p).strip()
    for prefix, fn in FIGURE_FILES.items():
        if t.startswith(prefix):
            img = os.path.join(FIG_DIR, fn)
            if os.path.exists(img):
                insert_image_before(p, img)
            break

tracked.save(TRACKED_OUT)
print(f"Saved tracked R1: {TRACKED_OUT}")
print(f"Total revision IDs: {_REV_ID[0]}")

# ────────────────────────────────────────────────────────────────────────────
# Post-process: renumber citations to match order of first appearance (Vancouver
# style). The EDITS / INSERTIONS above may not have been written with the final
# citation order in mind, so we apply a deterministic renumbering pass here.
# ────────────────────────────────────────────────────────────────────────────
print("\nRenumbering citations to order-of-appearance...")
import re as _re
_CITE_RE = _re.compile(r'\[(\d+(?:\s*[-–]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-–]\s*\d+)?)*)\]')

def _parse_cite(body):
    nums = []
    for part in _re.split(r'\s*,\s*', body):
        m = _re.match(r'(\d+)\s*[-–]\s*(\d+)', part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            nums.extend(range(min(a,b), max(a,b)+1))
        else:
            nums.append(int(part))
    return nums

def _fmt_cite(nums):
    nums = sorted(set(nums))
    if not nums: return ''
    parts = []; i = 0
    while i < len(nums):
        j = i
        while j+1 < len(nums) and nums[j+1] == nums[j]+1: j += 1
        if j - i >= 2:
            parts.append(f"{nums[i]}–{nums[j]}")
        else:
            parts.extend(str(n) for n in nums[i:j+1])
        i = j + 1
    return '[' + ','.join(parts) + ']'

def _para_text(p):
    s = ''
    for el in p._p.iter():
        tag = el.tag.split('}',1)[-1]
        if tag == 't': s += (el.text or '')
    return s

def _renumber_docx(path):
    from docx import Document as _Document
    d = _Document(path)
    body_paras, ref_paras, ref_heading = [], {}, None
    in_refs = False
    for p in d.paragraphs:
        t = _para_text(p).strip()
        if not t: continue
        if t == 'References':
            in_refs = True; ref_heading = p; continue
        if in_refs:
            m = _re.match(r'^\[(\d+)\]\s+', t)
            if m: ref_paras[int(m.group(1))] = p; continue
            body_paras.append(p)
        else:
            body_paras.append(p)
    # Build map from body walk
    seen, order = set(), []
    for p in body_paras:
        for m in _CITE_RE.finditer(_para_text(p)):
            for n in _parse_cite(m.group(1)):
                if n not in seen: seen.add(n); order.append(n)
    old_to_new = {old: i+1 for i, old in enumerate(order)}
    uncited = [n for n in ref_paras if n not in seen]
    # Apply to body
    def _remap(match):
        nums = _parse_cite(match.group(1))
        return _fmt_cite([old_to_new[n] for n in nums if n in old_to_new])
    for p in body_paras:
        for el in p._p.iter():
            tag = el.tag.split('}',1)[-1]
            if tag in ('t','delText') and el.text and '[' in el.text:
                el.text = _CITE_RE.sub(_remap, el.text)
    # Update ref labels + drop uncited
    refs_keep = []
    for old_n, p in ref_paras.items():
        if old_n in uncited:
            p._p.getparent().remove(p._p); continue
        new_n = old_to_new[old_n]
        for el in p._p.iter():
            tag = el.tag.split('}',1)[-1]
            if tag == 't':
                ot = el.text or ''
                el.text = _re.sub(r'^\[' + str(old_n) + r'\]', f'[{new_n}]', ot)
        refs_keep.append((new_n, p))
    refs_keep.sort(key=lambda x: x[0])
    # Reorder physically
    if ref_heading is not None:
        for _, p in refs_keep:
            if p._p.getparent() is not None: p._p.getparent().remove(p._p)
        anchor = ref_heading._p
        for _, p in refs_keep:
            anchor.addnext(p._p); anchor = p._p
    d.save(path)
    print(f"  {os.path.basename(path)}: renumbered {len(old_to_new)} refs (kept), dropped {len(uncited)} uncited")

_renumber_docx(CLEAN_OUT)
_renumber_docx(TRACKED_OUT)
print("Citation renumbering complete.")

# ────────────────────────────────────────────────────────────────────────────
# Post-process: triage figures/tables for Clinical Autonomic Research
# (CAR norm = 4–6 main figs + 3–5 main tables). We demote:
#   Figure 5 (heatmap)            → Supplementary Figure S3
#   Figure 6 (LASSO frequency)    → Supplementary Figure S4
#   Figure 7 (discrimination)     → Figure 5         [promoted to fill slot]
#   Figure 8 (donut)              → Supplementary Figure S5
#   Figure 9 (subset sufficiency) → Supplementary Figure S6
#   Table 4 (per-milestone Cox)   → Supplementary Table S4
#   Table 5 (discrimination)      → Table 4          [promoted to fill slot]
#   Table 6 (subset sufficiency)  → Table 5          [promoted to fill slot]
# Existing Supp Fig S1/S2 and Supp Tab S1/S2/S3 are preserved. Renames are
# applied via a collision-safe placeholder strategy so we never overwrite a
# slot we're about to need.
# ────────────────────────────────────────────────────────────────────────────
print("\nApplying CAR figure/table triage (Fig 5/6/8/9 → Supp; Fig 7 → 5; Table 4 → Supp; Tables 5/6 → 4/5)...")

# Substitution table. Each entry: (old, new). Order matters; we use unique
# token placeholders for promoted items so we can rename old-to-supp first.
import re as _re2
_TOKEN_FIG_5 = "\x00CARFIG5\x00"
_TOKEN_TAB_4 = "\x00CARTAB4\x00"
_TOKEN_TAB_5 = "\x00CARTAB5\x00"

# Each rule: (pattern, replacement). Patterns use word-boundary safety so
# "Figure 5" doesn't accidentally match "Figure 50". This applies the COMBINED
# first- + second-pass CAR triage to the originally-numbered EDITS dict, so the
# final manuscript has contiguous Tables 1–4 + Supp S1–S5.
#
# Chain from original numbering → final numbering:
#   Original Table 3 (domain Cox)           → Supplementary Table S5  (NEW, this pass)
#   Original Table 4 (per-milestone Cox)    → Supplementary Table S4
#   Original Table 5 (discrimination)       → Table 3                  (promoted, was → 4)
#   Original Table 6 (subset sufficiency)   → Table 4                  (promoted, was → 5)
# Tables 1 and 2 unchanged.
_TRIAGE_RULES = [
    # 1. Park promoted slots in placeholders (no collisions later)
    (_re2.compile(r"\bFigure 7\b"),                     _TOKEN_FIG_5),
    (_re2.compile(r"\bTable 5\b"),                      _TOKEN_TAB_4),  # → Table 3 (promoted)
    (_re2.compile(r"\bTable 6\b"),                      _TOKEN_TAB_5),  # → Table 4 (promoted)
    # 2. Demote main figures to supplementary
    (_re2.compile(r"\bFigure 5\b"),                     "Supplementary Figure S3"),
    (_re2.compile(r"\bFigure 6\b"),                     "Supplementary Figure S4"),
    (_re2.compile(r"\bFigure 8\b"),                     "Supplementary Figure S5"),
    (_re2.compile(r"\bFigure 9\b"),                     "Supplementary Figure S6"),
    # 3. Demote Tables 3 + 4 to supplementary
    (_re2.compile(r"\bTable 4\b"),                      "Supplementary Table S4"),
    (_re2.compile(r"\bTable 3\b"),                      "Supplementary Table S5"),
    # 4. Promote parked slots into now-vacant numbers (shifted up to fill Table 3 gap)
    (_re2.compile(_re2.escape(_TOKEN_FIG_5)),          "Figure 5"),
    (_re2.compile(_re2.escape(_TOKEN_TAB_4)),          "Table 3"),
    (_re2.compile(_re2.escape(_TOKEN_TAB_5)),          "Table 4"),
]

def _apply_triage(path):
    from docx import Document as _Document
    d = _Document(path)
    n_subs = 0
    for p in d.paragraphs:
        for el in p._p.iter():
            tag = el.tag.split('}', 1)[-1]
            if tag in ('t', 'delText') and el.text:
                new_text = el.text
                for pat, rep in _TRIAGE_RULES:
                    new_text, k = pat.subn(rep, new_text)
                    n_subs += k
                if new_text != el.text:
                    el.text = new_text
    # Update the figure-list section heading count + "Tables: N; Supp Tables: N"
    # mention if it's still in the document
    for p in d.paragraphs:
        for el in p._p.iter():
            tag = el.tag.split('}', 1)[-1]
            if tag in ('t', 'delText') and el.text:
                t = el.text
                t = t.replace("Tables: 6 (Word-format companion files); Supplementary Tables: 3",
                              "Tables: 4 (Word-format companion files); Supplementary Tables: 5")
                t = t.replace("Tables: 5 (Word-format companion files); Supplementary Tables: 4",
                              "Tables: 4 (Word-format companion files); Supplementary Tables: 5")
                t = t.replace("Figures: 9 ", "Figures: 5 ")
                t = t.replace("Figures: 9.", "Figures: 5.")
                el.text = t
    d.save(path)
    print(f"  {os.path.basename(path)}: applied {n_subs} figure/table substitutions")

_apply_triage(CLEAN_OUT)
_apply_triage(TRACKED_OUT)
print("CAR triage complete.")
print("  Final main display items: Figures 1, 2, 3, 4, 5 (was 7); Tables 1, 2, 3 (was 5), 4 (was 6)")
print("  Supplementary: Figures S1, S2, S3 (was 5), S4 (was 6), S5 (was 8), S6 (was 9);")
print("                 Tables S1, S2, S3, S4 (was main Table 4), S5 (was main Table 3)")

# ────────────────────────────────────────────────────────────────────────────
# Physical reorder of the figure section so captions appear in numeric order:
#   Figure 1 → 2 → 3 → 4 → 5, then Supp S1 → S2 → S3 → S4 → S5 → S6.
# For each caption we locate the immediately preceding image-bearing paragraph
# and move the (image, caption) pair as a unit. Empty/spacer paragraphs are
# left in place; the body never references them so any drift is invisible.
# ────────────────────────────────────────────────────────────────────────────
print("\nReordering figure captions to numeric order (Fig 1–5, then Supp S1–S6)...")

import re as _re3
_FIG_HDR_RE = _re3.compile(r"^(Figure (\d+)|Supplementary Figure S(\d+))\. ")

def _has_drawing(p):
    for el in p._p.iter():
        if el.tag.endswith('}drawing'):
            return True
    return False

def _reorder_figures(path):
    from docx import Document as _Document
    d = _Document(path)
    paras = d.paragraphs
    pairs = {}  # (is_supp:bool, num:int) -> (image_para, caption_para)
    for i, p in enumerate(paras):
        m = _FIG_HDR_RE.match(p.text.strip())
        if not m: continue
        is_supp = bool(m.group(3))
        num = int(m.group(3) if is_supp else m.group(2))
        # Walk back up to 5 paragraphs to find the image-bearing one
        img_para = None
        for k in range(i-1, max(-1, i-6), -1):
            if _has_drawing(paras[k]):
                img_para = paras[k]; break
        if img_para is not None:
            pairs[(is_supp, num)] = (img_para, p)
    # Desired order: main figs first (is_supp=False, by num), then supp (by num)
    desired = sorted(pairs.keys(), key=lambda k: (k[0], k[1]))
    if not desired:
        d.save(path); return 0
    # Anchor: leave the first pair where it sits; move every subsequent pair
    # to come right after the previous pair's caption (addnext handles the
    # implicit detach in lxml).
    moves = 0
    anchor_caption = pairs[desired[0]][1]
    for key in desired[1:]:
        img_p, cap_p = pairs[key]
        # Move image to immediately after anchor_caption, then caption after image
        anchor_caption._p.addnext(img_p._p)
        img_p._p.addnext(cap_p._p)
        anchor_caption = cap_p
        moves += 1
    d.save(path)
    return moves

n1 = _reorder_figures(CLEAN_OUT)
n2 = _reorder_figures(TRACKED_OUT)
print(f"  Reordered {n1} figure pairs in clean docx, {n2} in tracked docx.")
print("Figure section reorder complete.")

