#!/usr/bin/env python3
"""
07_build_tables_R1.py — Submission-ready Word-format tables for R1 revision.

Per CLAUDE.md: Arial throughout, 9-10pt body, three-line borders (top + header
bottom + bottom), no vertical lines, no interior horizontals, zero paragraph
spacing inside cells, abbreviations footnote below each table.

Tables produced:
  Table 1 — Baseline characteristics (corrected race coding)
  Table 2 — Item-level Cox: Model A vs Model B + PH + LR test
  Table 3 — Domain-level Cox
  Table 4 — Per-milestone item-level Cox (8 outcomes)
  Table 5 — Nested-model discrimination
  Supp S1 — SAA+ stratified
  Supp S2 — Strict MoCA≥23 sensitivity
  Supp S3 — Fine-Gray cause-specific vs milestone-or-death
  Supp S4 — LASSO selection frequency
  Supp S5 — v0 (Jan-2026 PPMI freeze) replication
"""
import os, json
import numpy as np
import pandas as pd
from docx import Document
from docx.shared import Pt, RGBColor, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

PROJ = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/1b-papers/SCOPA_Cognition_Study/revision_R1"
TAB_OUT = os.path.join(PROJ, "tables")
os.makedirs(TAB_OUT, exist_ok=True)

# ── Style helpers ─────────────────────────────────────────────────────
def set_run(run, *, size=10, bold=False, italic=False):
    run.font.name = "Arial"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        rFonts.set(qn(attr), "Arial")

def set_para(para, *, before=0, after=0, line=1.0, align=None):
    pf = para.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after  = Pt(after)
    pf.line_spacing = line
    if align: para.alignment = align

def remove_all_borders(cell):
    """Strip every border from a cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    for tag in ("tcBorders",):
        existing = tcPr.find(qn(f"w:{tag}"))
        if existing is not None: tcPr.remove(existing)
    tcBorders = OxmlElement("w:tcBorders")
    for side in ("top","left","bottom","right","insideH","insideV"):
        b = OxmlElement(f"w:{side}")
        b.set(qn("w:val"), "nil")
        tcBorders.append(b)
    tcPr.append(tcBorders)

def set_cell_border(cell, side, sz=4, color="000000"):
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = tcPr.find(qn("w:tcBorders"))
    if tcBorders is None:
        tcBorders = OxmlElement("w:tcBorders")
        tcPr.append(tcBorders)
    existing = tcBorders.find(qn(f"w:{side}"))
    if existing is not None: tcBorders.remove(existing)
    b = OxmlElement(f"w:{side}")
    b.set(qn("w:val"), "single")
    b.set(qn("w:sz"), str(sz))
    b.set(qn("w:color"), color)
    tcBorders.append(b)

def style_table_threeline(tbl, *, header_size=10, body_size=10):
    """Apply three-line borders: top (full row above), header-bottom, bottom (full row below)."""
    n_rows = len(tbl.rows); n_cols = len(tbl.columns)
    for r_idx, row in enumerate(tbl.rows):
        for c_idx, cell in enumerate(row.cells):
            remove_all_borders(cell)
            # Cell-level paragraph spacing zero, line 1.05, font Arial 9-10pt
            for p in cell.paragraphs:
                set_para(p, before=0, after=0, line=1.1)
                for run in p.runs:
                    set_run(run, size=body_size if r_idx > 0 else header_size,
                             bold=(r_idx == 0))
            # Add borders only on first row top, header bottom, last row bottom
            if r_idx == 0:
                set_cell_border(cell, "top", sz=12)
                set_cell_border(cell, "bottom", sz=6)
            if r_idx == n_rows - 1:
                set_cell_border(cell, "bottom", sz=12)

def add_table_legend(doc, label, text, size=9):
    """Title above table; full caption above table per CLAUDE.md."""
    p = doc.add_paragraph()
    set_para(p, before=6, after=4, line=1.15)
    r = p.add_run(label + ". ")
    set_run(r, size=size, bold=True)
    r2 = p.add_run(text)
    set_run(r2, size=size, bold=False)
    return p

def add_abbreviations_footnote(doc, text, size=8):
    p = doc.add_paragraph()
    set_para(p, before=2, after=8, line=1.1)
    r = p.add_run("Abbreviations: ")
    set_run(r, size=size, italic=True, bold=True)
    r2 = p.add_run(text)
    set_run(r2, size=size, italic=True)
    return p

def write_simple_table(rows, *, header, col_widths=None, body_size=9):
    """Build a python-docx Document containing one styled three-line table.
    Caption goes ABOVE the table per CLAUDE.md; we add an empty caption
    paragraph the caller fills."""
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)
    # Caption placeholder paragraph above the table
    doc.add_paragraph()
    tbl = doc.add_table(rows=1 + len(rows), cols=len(header))
    tbl.autofit = False
    if col_widths:
        for col, w in zip(tbl.columns, col_widths):
            for cell in col.cells:
                cell.width = w
    # Header
    for i, h in enumerate(header):
        c = tbl.rows[0].cells[i]
        c.text = ""
        p = c.paragraphs[0]
        r = p.add_run(h)
        set_run(r, size=body_size + 0.5, bold=True)
        set_para(p, before=0, after=0, line=1.1,
                 align=WD_ALIGN_PARAGRAPH.LEFT)
    # Body
    for r_i, row in enumerate(rows, start=1):
        for c_i, val in enumerate(row):
            c = tbl.rows[r_i].cells[c_i]
            c.text = ""
            p = c.paragraphs[0]
            r = p.add_run("" if pd.isna(val) else str(val))
            set_run(r, size=body_size)
            set_para(p, before=0, after=0, line=1.1,
                     align=WD_ALIGN_PARAGRAPH.LEFT)
    style_table_threeline(tbl, header_size=body_size + 0.5,
                          body_size=body_size)
    return doc, tbl

ITEM_LABELS = {f"SCAU{i}": lab for i, lab in enumerate([
    "Swallowing/choking","Drooling","Dysphagia","Early satiety","Constipation",
    "Straining","Fecal incontinence","Urgency","Frequency","Nocturia",
    "Incontinence","Incomplete emptying","Weak stream","Lightheadedness standing",
    "Lightheadedness walking","Fainting","Excessive sweating day",
    "Excessive sweating night","Heat intolerance","Cold intolerance",
    "Color change hands/feet","Oversensitive to light",
    "Sexual dysfunction 1","Sexual dysfunction 2","Sexual dysfunction 3"], 1)}

# ════════════════════════════════════════════════════════════════════════
# TABLE 1 — Baseline characteristics
# ════════════════════════════════════════════════════════════════════════
print("Building Table 1 — Baseline characteristics ...")
df = pd.read_csv(os.path.join(PROJ, "data", "analytical_dataset_R1.csv"),
                  low_memory=False)

def mean_sd(series, dec=1):
    s = series.dropna()
    return f"{s.mean():.{dec}f} ({s.std():.{dec}f})"

def median_iqr(series, dec=1):
    s = series.dropna()
    return f"{s.median():.{dec}f} [{s.quantile(0.25):.{dec}f}–{s.quantile(0.75):.{dec}f}]"

def npct(n, total):
    return f"{int(n)} ({100*n/total:.1f})"

from scipy import stats
def chi2_p(a, b):
    tab = pd.crosstab(a, b)
    try:    return stats.chi2_contingency(tab)[1]
    except: return np.nan

def ttest_p(a, b):
    try:    return stats.ttest_ind(a.dropna(), b.dropna(), equal_var=False).pvalue
    except: return np.nan

def mwu_p(a, b):
    try:    return stats.mannwhitneyu(a.dropna(), b.dropna()).pvalue
    except: return np.nan

ev = df[df.event == 1]
nv = df[df.event == 0]
N, Nev, Nnv = len(df), len(ev), len(nv)

def p_format(p):
    if pd.isna(p): return "—"
    if p < 0.001:  return "<0.001"
    return f"{p:.3f}"

rows1 = []
# Demographics
rows1.append(("Age at baseline, years, mean (SD)",
              mean_sd(df.AGE_AT_VISIT), mean_sd(ev.AGE_AT_VISIT),
              mean_sd(nv.AGE_AT_VISIT),
              p_format(ttest_p(ev.AGE_AT_VISIT, nv.AGE_AT_VISIT))))
rows1.append(("Sex, male, n (%)",
              npct((df.SEX == 1).sum(), N),
              npct((ev.SEX == 1).sum(), Nev),
              npct((nv.SEX == 1).sum(), Nnv),
              p_format(chi2_p(df.SEX, df.event))))
rows1.append(("Education, years, median [IQR]",
              median_iqr(df.EDUCYRS), median_iqr(ev.EDUCYRS),
              median_iqr(nv.EDUCYRS),
              p_format(mwu_p(ev.EDUCYRS, nv.EDUCYRS))))
# Race (CORRECTED coding). Parent row carries the omnibus chi-square
# p-value across all categories; subcategory rows inherit it (blank cell,
# standard publication convention). Categories with n=0 are excluded from
# the omnibus test so the chi-square doesn't fail on empty cells.
race_present = [r for r in ["White", "Black", "Asian",
                             "American Indian/Alaska Native",
                             "Native Hawaiian/Pacific Islander",
                             "More than one race", "Missing/Declined"]
                if (df.RACE == r).sum() > 0]
# Build a 2×k contingency table (event × race) restricted to present categories
_race_in_present = df.RACE.isin(race_present)
race_omnibus_p = chi2_p(df.loc[_race_in_present, "RACE"],
                         df.loc[_race_in_present, "event"])
rows1.append(("Race, n (%)", "", "", "", p_format(race_omnibus_p)))
for race_label in race_present:
    n_all = (df.RACE == race_label).sum()
    n_ev = (ev.RACE == race_label).sum()
    n_nv = (nv.RACE == race_label).sum()
    rows1.append((f"  {race_label}",
                  npct(n_all, N), npct(n_ev, Nev), npct(n_nv, Nnv), ""))
# Hispanic/Latino
n_hisp = (df.HISPLAT == 1).sum()
rows1.append(("Hispanic or Latino, n (%)",
              npct(n_hisp, N),
              npct((ev.HISPLAT == 1).sum(), Nev),
              npct((nv.HISPLAT == 1).sum(), Nnv),
              p_format(chi2_p(df.HISPLAT, df.event))))
# Disease characteristics
rows1.append(("Disease duration from PD diagnosis, years, median [IQR]",
              median_iqr(df.disease_duration_yrs, dec=2),
              median_iqr(ev.disease_duration_yrs, dec=2),
              median_iqr(nv.disease_duration_yrs, dec=2),
              p_format(mwu_p(ev.disease_duration_yrs, nv.disease_duration_yrs))))
rows1.append(("MDS-UPDRS Part III, median [IQR]",
              median_iqr(df.NP3TOT_BEST),
              median_iqr(ev.NP3TOT_BEST),
              median_iqr(nv.NP3TOT_BEST),
              p_format(mwu_p(ev.NP3TOT_BEST, nv.NP3TOT_BEST))))
rows1.append(("Hoehn-Yahr stage, median [IQR]",
              median_iqr(df.NHY_BEST, dec=1),
              median_iqr(ev.NHY_BEST, dec=1),
              median_iqr(nv.NHY_BEST, dec=1),
              p_format(mwu_p(ev.NHY_BEST, nv.NHY_BEST))))
rows1.append(("Schwab–England ADL, median [IQR]",
              median_iqr(df.MSEADLG, dec=0),
              median_iqr(ev.MSEADLG, dec=0),
              median_iqr(nv.MSEADLG, dec=0),
              p_format(mwu_p(ev.MSEADLG, nv.MSEADLG))))
rows1.append(("LEDD at baseline, mg/day, median [IQR]",
              median_iqr(df.LEDD_TOTAL_CURRENT, dec=0),
              median_iqr(ev.LEDD_TOTAL_CURRENT, dec=0),
              median_iqr(nv.LEDD_TOTAL_CURRENT, dec=0),
              p_format(mwu_p(ev.LEDD_TOTAL_CURRENT, nv.LEDD_TOTAL_CURRENT))))
rows1.append(("Baseline MoCA, median [IQR]",
              median_iqr(df.MCATOT, dec=0),
              median_iqr(ev.MCATOT, dec=0),
              median_iqr(nv.MCATOT, dec=0),
              p_format(mwu_p(ev.MCATOT, nv.MCATOT))))
rows1.append(("RBDSQ total, median [IQR]",
              median_iqr(df.RBDSQ_TOTAL),
              median_iqr(ev.RBDSQ_TOTAL),
              median_iqr(nv.RBDSQ_TOTAL),
              p_format(mwu_p(ev.RBDSQ_TOTAL, nv.RBDSQ_TOTAL))))
rows1.append(("UPSIT percentile, median [IQR]",
              median_iqr(df.UPSIT_PRCNTGE),
              median_iqr(ev.UPSIT_PRCNTGE),
              median_iqr(nv.UPSIT_PRCNTGE),
              p_format(mwu_p(ev.UPSIT_PRCNTGE, nv.UPSIT_PRCNTGE))))
rows1.append(("SCOPA-AUT total, median [IQR]",
              median_iqr(df.SCAU_TOTAL),
              median_iqr(ev.SCAU_TOTAL),
              median_iqr(nv.SCAU_TOTAL),
              p_format(mwu_p(ev.SCAU_TOTAL, nv.SCAU_TOTAL))))
# Concomitant medications
for cls, label in [("bl_alpha_blocker", "α-Blocker exposure, n (%)"),
                    ("bl_antihypertensive", "Antihypertensive exposure, n (%)")]:
    rows1.append((label,
                  npct(df[cls].sum(), N),
                  npct(ev[cls].sum(), Nev),
                  npct(nv[cls].sum(), Nnv),
                  p_format(chi2_p(df[cls], df.event))))
# SAA
rows1.append(("Synuclein SAA positive, n (%)",
              npct((df.SAA_POS_Subject == "SAA+").sum(), N),
              npct((ev.SAA_POS_Subject == "SAA+").sum(), Nev),
              npct((nv.SAA_POS_Subject == "SAA+").sum(), Nnv),
              p_format(chi2_p(df.SAA_POS_Subject, df.event))))
# Follow-up
rows1.append(("Follow-up time, years, median [IQR]",
              median_iqr(df.time_to_event),
              median_iqr(ev.time_to_event),
              median_iqr(nv.time_to_event),
              p_format(mwu_p(ev.time_to_event, nv.time_to_event))))

doc1, _ = write_simple_table(
    rows1,
    header=["Characteristic", f"All (N = {N})",
             f"Events (n = {Nev})", f"No events (n = {Nnv})", "p-value"],
    body_size=9)
# Prepend caption
caption = doc1.paragraphs[0]
caption_text = ("Baseline characteristics of the analytical cohort, stratified "
                "by composite cognitive-milestone status (m10–m15) over the "
                "follow-up period.")
caption.text = ""
r = caption.add_run("Table 1. ")
set_run(r, size=10, bold=True)
r2 = caption.add_run(caption_text)
set_run(r2, size=10)
set_para(caption, before=0, after=6, line=1.15)
# Move caption above the table (python-docx adds it before by default since
# it's the first paragraph; ensure the order)
# Footnote
foot = doc1.add_paragraph()
set_para(foot, before=2, after=2, line=1.1)
fr = foot.add_run(
    "Abbreviations: ADL, activities of daily living; IQR, interquartile range; "
    "LEDD, levodopa equivalent daily dose; MoCA, Montreal Cognitive Assessment; "
    "MDS-UPDRS, Movement Disorder Society–Unified Parkinson's Disease Rating "
    "Scale; PD, Parkinson's disease; RBDSQ, REM Sleep Behavior Disorder "
    "Screening Questionnaire; SAA, seed amplification assay; SCOPA-AUT, "
    "Scales for Outcomes in Parkinson's disease–Autonomic; SD, standard "
    "deviation; UPSIT, University of Pennsylvania Smell Identification Test. "
    "Continuous variables compared via Welch's t test (means) or Mann–Whitney "
    "U test (medians); categorical via χ². "
    "Note: cohort uses PPMI v2.1 (22 Apr 2026 LONI freeze).")
set_run(fr, size=8, italic=True)
doc1.save(os.path.join(TAB_OUT, "Table1_baseline.docx"))
print(f"  Saved Table1_baseline.docx  ({len(rows1)} rows)")

# ════════════════════════════════════════════════════════════════════════
# TABLE 2 — Item-level Cox: Model A vs Model B + PH + LR
# ════════════════════════════════════════════════════════════════════════
print("Building Table 2 — Item-level Cox (Models A and B + PH + LR) ...")
A = pd.read_csv(os.path.join(TAB_OUT, "cox_R1_item_modelA.csv"))
B = pd.read_csv(os.path.join(TAB_OUT, "cox_R1_item_modelB.csv"))
PH = pd.read_csv(os.path.join(TAB_OUT, "cox_R1_ph_test.csv"))
LR = pd.read_csv(os.path.join(TAB_OUT, "cox_R1_LR_item_vs_total.csv"))

T2 = A.merge(B, on=["Item", "Label"], suffixes=("_A", "_B"))
T2 = T2.merge(PH[["Item", "PH_p_item"]], on="Item", how="left")
T2 = T2.merge(LR[["Item", "LR_p_fdr"]], on="Item", how="left")
T2["scau_num"] = T2.Item.str.replace("SCAU", "").astype(int)
T2 = T2.sort_values("scau_num").reset_index(drop=True)

def fmt_hr(hr, lo, hi):
    if pd.isna(hr): return "—"
    return f"{hr:.2f} ({lo:.2f}–{hi:.2f})"

def fmt_p(p):
    if pd.isna(p): return "—"
    if p < 0.001:  return "<0.001"
    return f"{p:.3f}"

rows2 = []
for _, r in T2.iterrows():
    nev_a = "—" if pd.isna(r.Events_A) else f"{int(r.N_A)}/{int(r.Events_A)}"
    rows2.append([r.Item,
                   ITEM_LABELS.get(r.Item, r.Label),
                   nev_a,
                   fmt_hr(r.HR_A, r.CI_low_A, r.CI_high_A),
                   fmt_p(r.p_fdr_A),
                   fmt_hr(r.HR_B, r.CI_low_B, r.CI_high_B),
                   fmt_p(r.p_fdr_B),
                   fmt_p(r.PH_p_item),
                   fmt_p(r.LR_p_fdr)])

doc2, _ = write_simple_table(
    rows2,
    header=["Item", "Symptom", "N / events",
             "Model A aHR (95% CI)", "Model A FDR p",
             "Model B aHR (95% CI)", "Model B FDR p",
             "PH p", "LR p (FDR)"],
    body_size=8)
caption = doc2.paragraphs[0]
caption.text = ""
r = caption.add_run("Table 2. ")
set_run(r, size=10, bold=True)
r2 = caption.add_run(
    "Item-level Cox proportional-hazards models predicting the composite "
    "cognitive milestone (m10–m15) for each SCOPA-AUT item. Model A uses "
    "the original adjustment set (age, sex, education, baseline MoCA, "
    "MDS-UPDRS Part III); Model B adds LEDD, Schwab–England ADL, RBDSQ "
    "total, disease duration, baseline α-blocker exposure, baseline "
    "antihypertensive exposure, and Hoehn-Yahr stage. PH p = Schoenfeld "
    "residual proportional-hazards test on the item coefficient (Model B). "
    "LR p (FDR) = likelihood-ratio test of whether the item adds information "
    "beyond SCOPA-AUT total in Model B (FDR-corrected across items).")
set_run(r2, size=10)
set_para(caption, before=0, after=6, line=1.15)

foot = doc2.add_paragraph()
set_para(foot, before=2, after=2, line=1.1)
fr = foot.add_run(
    "Abbreviations: aHR, adjusted hazard ratio; CI, confidence interval; "
    "FDR, false discovery rate (Benjamini–Hochberg); LEDD, levodopa "
    "equivalent daily dose; LR, likelihood ratio; MoCA, Montreal Cognitive "
    "Assessment; PH, proportional hazards. SCAU24 (Sexual dysfunction 2; "
    "female-specific item) had insufficient complete cases for stable "
    "model estimation and is not reported. ")
set_run(fr, size=8, italic=True)
doc2.save(os.path.join(TAB_OUT, "Table2_item_cox.docx"))
print(f"  Saved Table2_item_cox.docx  ({len(rows2)} rows)")

# ════════════════════════════════════════════════════════════════════════
# TABLE 3 — Domain-level Cox (Model B)
# ════════════════════════════════════════════════════════════════════════
print("Building Table 3 — Domain-level Cox ...")
D = pd.read_csv(os.path.join(TAB_OUT, "cox_R1_domain.csv"))
DOMAIN_LABEL_FULL = {"SCAU_GI": "Gastrointestinal",
                     "SCAU_URI": "Urinary",
                     "SCAU_CV": "Cardiovascular",
                     "SCAU_THERM": "Thermoregulatory",
                     "SCAU_PUPIL": "Pupillomotor (SCAU22 only)",
                     "SCAU_SEX": "Sexual (SCAU23–25)",
                     "SCAU_TOTAL": "SCOPA-AUT total (all 25 items)"}
DOMAIN_NITEMS = {"SCAU_GI": "7", "SCAU_URI": "6", "SCAU_CV": "3",
                 "SCAU_THERM": "5", "SCAU_PUPIL": "1", "SCAU_SEX": "3",
                 "SCAU_TOTAL": "25"}
rows3 = []
for _, r in D.iterrows():
    rows3.append([DOMAIN_LABEL_FULL.get(r.Domain, r.Domain),
                   DOMAIN_NITEMS.get(r.Domain, ""),
                   f"{int(r.N)}/{int(r.Events)}",
                   fmt_hr(r.HR, r.CI_low, r.CI_high),
                   fmt_p(r.p)])
doc3, _ = write_simple_table(
    rows3,
    header=["Domain", "Items (n)", "N / events",
             "aHR per 1-unit increase (95% CI)", "p-value"],
    body_size=9)
caption = doc3.paragraphs[0]
caption.text = ""
r = caption.add_run("Table 3. ")
set_run(r, size=10, bold=True)
r2 = caption.add_run(
    "Domain-level Cox proportional-hazards models for SCOPA-AUT domain "
    "subscores predicting the composite cognitive milestone (m10–m15). "
    "All models use Model B covariates (age, sex, education, baseline "
    "MoCA, MDS-UPDRS Part III, LEDD, Schwab–England ADL, RBDSQ, disease "
    "duration, α-blocker exposure, antihypertensive exposure, Hoehn-Yahr).")
set_run(r2, size=10)
set_para(caption, before=0, after=6, line=1.15)
foot = doc3.add_paragraph()
set_para(foot, before=2, after=2, line=1.1)
fr = foot.add_run(
    "Abbreviations: aHR, adjusted hazard ratio; CI, confidence interval; "
    "LEDD, levodopa equivalent daily dose; MoCA, Montreal Cognitive "
    "Assessment; MDS-UPDRS, Movement Disorder Society–Unified Parkinson's "
    "Disease Rating Scale; RBDSQ, REM Sleep Behavior Disorder Screening "
    "Questionnaire; SCOPA-AUT, Scales for Outcomes in Parkinson's "
    "disease–Autonomic. Pupillomotor and sexual sub-cohorts have smaller "
    "complete-case N because items SCAU22 and SCAU23–25 have higher "
    "missingness; cross-domain HR comparisons within these reduced "
    "cohorts should be interpreted cautiously.")
set_run(fr, size=8, italic=True)
doc3.save(os.path.join(TAB_OUT, "Table3_domain.docx"))
print(f"  Saved Table3_domain.docx  ({len(rows3)} rows)")

# ════════════════════════════════════════════════════════════════════════
# TABLE 4 — Per-milestone item-level Cox (8 outcomes, wide format)
# ════════════════════════════════════════════════════════════════════════
print("Building Table 4 — Per-milestone item-level Cox ...")
master = pd.read_csv(os.path.join(TAB_OUT, "cox_R1_per_milestone_master.csv"))
master = master[master.Item.str.match(r"SCAU([1-9]|1[0-9]|2[01])$")].copy()
master["scau_num"] = master.Item.str.replace("SCAU", "").astype(int)
master = master.sort_values(["scau_num", "Outcome"])

# Wide: rows=item, cols=outcome with formatted HR (FDR)
def cell(row):
    if pd.isna(row.HR): return "—"
    star = ""
    if pd.notna(row.p_fdr):
        if row.p_fdr < 0.001: star = "***"
        elif row.p_fdr < 0.01: star = "**"
        elif row.p_fdr < 0.05: star = "*"
    return f"{row.HR:.2f}{star}"

master["cell"] = master.apply(cell, axis=1)
wide = master.pivot(index=["Item","scau_num"], columns="Outcome",
                     values="cell").reset_index()
wide = wide.sort_values("scau_num").reset_index(drop=True)
outcomes_order = ["m10", "m11", "m12", "m13", "m14", "m15",
                   "pure_cognitive", "pure_neuropsych"]
outcomes_label = {"m10":"m10 (MoCA<21)", "m11":"m11 (UPDRS-I cog)",
                  "m12":"m12 (halluc.)", "m13":"m13 (apathy)",
                  "m14":"m14 (inv. dem.)", "m15":"m15 (MDS-PDD)",
                  "pure_cognitive":"Pure cog (m10+14+15)",
                  "pure_neuropsych":"Pure NP (m12+13)"}
rows4 = []
for _, r in wide.iterrows():
    line = [r.Item, ITEM_LABELS.get(r.Item, "")]
    for o in outcomes_order:
        line.append(r[o] if o in wide.columns else "—")
    rows4.append(line)
doc4, _ = write_simple_table(
    rows4,
    header=["Item","Symptom"] + [outcomes_label[o] for o in outcomes_order],
    body_size=7.5)
caption = doc4.paragraphs[0]; caption.text = ""
r = caption.add_run("Table 4. ")
set_run(r, size=10, bold=True)
r2 = caption.add_run(
    "Per-milestone item-level Cox proportional-hazards models, Model B "
    "(R1 expanded adjustment). Cells show the adjusted hazard ratio per "
    "1-point increase in the SCOPA-AUT item, with FDR significance "
    "(*p<0.05, **p<0.01, ***p<0.001 after Benjamini–Hochberg correction "
    "within each outcome). Pure cognitive composite = m10 + m14 + m15 "
    "(MoCA<21, investigator-diagnosed dementia, MDS PD-Dementia); pure "
    "neuropsychiatric composite = m12 + m13 (hallucinations, apathy).")
set_run(r2, size=10)
set_para(caption, before=0, after=6, line=1.15)
foot = doc4.add_paragraph()
set_para(foot, before=2, after=2, line=1.1)
fr = foot.add_run(
    "Abbreviations: FDR, false discovery rate; HR, hazard ratio; MDS-PDD, "
    "Movement Disorder Society Parkinson's Disease Dementia; MoCA, Montreal "
    "Cognitive Assessment; UPDRS-I, MDS-UPDRS Part I.")
set_run(fr, size=8, italic=True)
doc4.save(os.path.join(TAB_OUT, "Table4_per_milestone.docx"))
print(f"  Saved Table4_per_milestone.docx  ({len(rows4)} rows)")

# ════════════════════════════════════════════════════════════════════════
# TABLE 5 — Nested-model discrimination
# ════════════════════════════════════════════════════════════════════════
print("Building Table 5 — Prognostic-model discrimination (REPLACES-total framing) ...")
# Use the 6-model "REPLACES total" comparison (script 04 generates the source CSV).
disc = pd.read_csv(os.path.join(TAB_OUT, "replaces_total_comparison_R1.csv"))
model_labels = {
    "P0_base":       "P0 — Parsimonious clinical base only (age, sex, education, baseline MoCA, MDS-UPDRS Part III) — no SCOPA-AUT",
    "P1_total":      "P1 — Base + 25-item SCOPA-AUT total score (reference)",
    "P_sig_domains": "P-sig-dom — Base + 3 FDR-significant SCOPA-AUT domains (gastrointestinal, cardiovascular, thermoregulatory) — REPLACES total",
    "P_sig_items":   "P-sig-items — Base + 5 FDR-significant SCOPA-AUT items (SCAU3, 4, 14, 15, 20) — REPLACES total",
    "P2_4_domains":  "P2 — Base + all 4 SCOPA-AUT domain scores — REPLACES total",
    "P3_21_items":   "P3 — Base + all 21 fully-available SCOPA-AUT items — REPLACES total",
}
order = ["P0_base", "P1_total", "P_sig_domains", "P_sig_items",
         "P2_4_domains", "P3_21_items"]
disc_o = disc.set_index("name").reindex(order).reset_index()
rows5 = []
for _, r in disc_o.iterrows():
    rows5.append([
        model_labels[r["name"]],
        f"{r.c_mean:.3f} ± {r.c_sd:.3f}",
        f"{r.get('AUC_t4_mean', np.nan):.3f}" if pd.notna(r.get("AUC_t4_mean", np.nan)) else "—",
        f"{r.get('AUC_t6_mean', np.nan):.3f}" if pd.notna(r.get("AUC_t6_mean", np.nan)) else "—",
        f"{r.get('ibs_mean', np.nan):.3f}" if pd.notna(r.get("ibs_mean", np.nan)) else "—",
    ])
doc5, _ = write_simple_table(
    rows5,
    header=["Model", "C-index (10-fold CV)", "AUC at 4 years",
             "AUC at 6 years", "Integrated Brier score"],
    body_size=9)
caption = doc5.paragraphs[0]; caption.text = ""
r = caption.add_run("Table 5. ")
set_run(r, size=10, bold=True)
r2 = caption.add_run(
    "Prognostic-model discrimination for the composite cognitive milestone "
    "(m10–m15) at 10-fold cross-validation, designed to answer the question: "
    "does removing the 25-item SCOPA-AUT total score and replacing it with "
    "FDR-significant items or domains improve discrimination? The "
    "parsimonious clinical base model (P0) comprises the five clinical "
    "variables routinely available at a PD diagnostic encounter (age, sex, "
    "education, baseline MoCA, MDS-UPDRS Part III motor score). P1 is the "
    "reference model (base + 25-item SCOPA-AUT total). The remaining four "
    "models REPLACE the total with a different parsimonious SCOPA-AUT "
    "representation — none of them contain the SCOPA-AUT total. Higher "
    "C-index and AUC indicate better discrimination.")
set_run(r2, size=10)
set_para(caption, before=0, after=6, line=1.15)
foot = doc5.add_paragraph()
set_para(foot, before=2, after=2, line=1.1)
fr = foot.add_run(
    "Abbreviations: AUC, area under the receiver operating characteristic "
    "curve; CV, cross-validation; MoCA, Montreal Cognitive Assessment; "
    "MDS-UPDRS, Movement Disorder Society Unified Parkinson's Disease "
    "Rating Scale. Complete-case N = 1,123 (279 composite events). Items "
    "SCAU22–25 excluded from the nested-model comparison due to higher "
    "item-level missingness. The parsimonious clinical base is intentionally "
    "narrower than the 12-covariate Model B used for the etiologic item-level "
    "Cox hazard-ratio analyses (Tables 2–4), because the prognostic question "
    "(how much does measuring autonomic burden improve cognitive risk "
    "prediction beyond what a clinician routinely knows?) is structurally "
    "different from the etiologic question (does autonomic burden have an "
    "independent association after controlling for severity confounders?). "
    "LASSO Cox selection frequency across folds is reported in Figure 6 "
    "and Supplementary Table S3.")
set_run(fr, size=8, italic=True)
doc5.save(os.path.join(TAB_OUT, "Table5_discrimination.docx"))
print(f"  Saved Table5_discrimination.docx")

# ════════════════════════════════════════════════════════════════════════
# Supplementary Tables S1–S5
# ════════════════════════════════════════════════════════════════════════
print("Building Supplementary Tables ...")

# S1 — SAA+ stratified Cox
saa = pd.read_csv(os.path.join(TAB_OUT, "cox_R1_SAApos_only.csv"))
saa["scau_num"] = saa.Item.str.replace("SCAU", "").astype(int)
saa = saa.sort_values("scau_num").reset_index(drop=True)
rows_s1 = []
for _, r in saa.iterrows():
    rows_s1.append([r.Item, ITEM_LABELS.get(r.Item, r.Label),
                     f"{int(r['N_SAA+'])}/{int(r['Events_SAA+'])}",
                     fmt_hr(r['HR_SAA+'], r.CI_low, r.CI_high),
                     fmt_p(r.p_fdr)])
doc_s1, _ = write_simple_table(
    rows_s1, header=["Item","Symptom","N/events","aHR (95% CI)","FDR p"],
    body_size=8)
caption = doc_s1.paragraphs[0]; caption.text = ""
r = caption.add_run("Supplementary Table S1. ")
set_run(r, size=10, bold=True)
r2 = caption.add_run(
    "Item-level Cox proportional-hazards models restricted to the "
    "seed-amplification-assay-positive (SAA+) subgroup (N=921; 238 events). "
    "Model B covariates applied.")
set_run(r2, size=10)
set_para(caption, before=0, after=6, line=1.15)
foot = doc_s1.add_paragraph()
set_para(foot, before=2, after=2, line=1.1)
fr = foot.add_run(
    "Abbreviations: aHR, adjusted hazard ratio; CI, confidence interval; "
    "FDR, false discovery rate; SAA, seed amplification assay.")
set_run(fr, size=8, italic=True)
doc_s1.save(os.path.join(TAB_OUT, "SuppTableS1_SAApos.docx"))

# S3 — Fine-Gray cause-specific vs milestone-or-death
fg = pd.read_csv(os.path.join(TAB_OUT, "finegray_cause_specific_R1.csv"))
fg["scau_num"] = fg.Item.str.replace("SCAU", "").astype(int)
fg = fg.sort_values("scau_num").reset_index(drop=True)
rows_s3 = []
for _, r in fg.iterrows():
    rows_s3.append([r.Item, ITEM_LABELS.get(r.Item, r.Label),
                     f"{r.HR_cause_specific:.3f}",
                     f"{r.HR_milestone_or_death:.3f}",
                     f"{r.delta_HR_pct:+.2f}%",
                     fmt_p(r.p_cs_fdr)])
doc_s3, _ = write_simple_table(
    rows_s3, header=["Item","Symptom","aHR cause-specific",
                       "aHR milestone-or-death","Δ %","Cause-specific FDR p"],
    body_size=8)
caption = doc_s3.paragraphs[0]; caption.text = ""
r = caption.add_run("Supplementary Table S2. ")
set_run(r, size=10, bold=True)
r2 = caption.add_run(
    "Fine-Gray-style competing-risks sensitivity. The cause-specific Cox "
    "treats death as non-informative censoring; the milestone-or-death Cox "
    "treats death as an outcome event. 35 of 79 deaths during follow-up "
    "preceded a cognitive milestone (true competing events); the negligible "
    "Δ %HR confirms competing-risk bias is small. Model B covariates applied.")
set_run(r2, size=10)
set_para(caption, before=0, after=6, line=1.15)
foot = doc_s3.add_paragraph()
set_para(foot, before=2, after=2, line=1.1)
fr = foot.add_run(
    "Abbreviations: aHR, adjusted hazard ratio; FDR, false discovery rate.")
set_run(fr, size=8, italic=True)
doc_s3.save(os.path.join(TAB_OUT, "SuppTableS2_competing_risks.docx"))

# S3 — LASSO selection frequency (post-CAR triage: this is now Supp Table S3)
# scripts/04 only writes items that were selected ≥1 fold. We pad with 0/10
# entries for the 16 never-selected items so the manuscript's "only five items
# were ever retained" claim is visible by contrast (16 rows showing 0 of 10).
ls = pd.read_csv(os.path.join(TAB_OUT, "lasso_selection_frequency_R1.csv"))
selected_set = set(ls["Item"].tolist())
all_items = [f"SCAU{i}" for i in range(1, 22)]   # SCAU1–SCAU21 (fully-available)
missing = [it for it in all_items if it not in selected_set]
pad = pd.DataFrame([{"Item": it, "selected_folds": 0, "freq": 0.0}
                     for it in missing])
ls_full = pd.concat([ls, pad], ignore_index=True)
ls_full["scau_num"] = ls_full.Item.str.replace("SCAU", "").astype(int)
# Sort: most frequently selected first, then by SCAU number for ties (incl. zeros)
ls_full = ls_full.sort_values(
    ["selected_folds", "scau_num"], ascending=[False, True]
).reset_index(drop=True)
rows_s4 = []
for _, r in ls_full.iterrows():
    rows_s4.append([r.Item, ITEM_LABELS.get(r.Item, ""),
                     f"{int(r.selected_folds)}", f"{r.freq:.2f}"])
doc_s4, _ = write_simple_table(
    rows_s4, header=["Item","Symptom","Folds selected (of 10)","Frequency"],
    body_size=9)
caption = doc_s4.paragraphs[0]; caption.text = ""
r = caption.add_run("Supplementary Table S3. ")
set_run(r, size=10, bold=True)
r2 = caption.add_run(
    "LASSO Cox item selection frequency across 10 cross-validation folds. "
    "Each row reports the number of folds (out of 10) in which the item's "
    "coefficient was non-zero at the cross-validated optimal regularization "
    "strength. Stable items selected in ≥8/10 folds.")
set_run(r2, size=10)
set_para(caption, before=0, after=6, line=1.15)
foot = doc_s4.add_paragraph()
set_para(foot, before=2, after=2, line=1.1)
fr = foot.add_run(
    "Abbreviations: LASSO, least absolute shrinkage and selection operator.")
set_run(fr, size=8, italic=True)
doc_s4.save(os.path.join(TAB_OUT, "SuppTableS3_lasso_frequency.docx"))

print("\n=== ALL TABLES BUILT (post-CAR triage numbering) ===")
print("  Primary:        Table1_baseline, Table2_item_cox, Table3_domain,")
print("                  Table4_per_milestone (→ demoted to SuppTableS4 by scripts/14),")
print("                  Table5_discrimination (→ promoted to Table4 by scripts/14)")
print("  Supplementary:  SuppTableS1_SAApos, SuppTableS2_competing_risks,")
print("                  SuppTableS3_lasso_frequency")
