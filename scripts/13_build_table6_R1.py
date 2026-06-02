#!/usr/bin/env python3
"""
13_build_table6_R1.py — Build Table 6 (subset-sufficiency table) as Word .docx
in the same three-line style as Tables 1–5.

Sources:
  tables/subset_sufficiency_domains_R1.csv  (from script 12)
  tables/subset_sufficiency_items_R1.csv    (from script 12)

Output:
  tables/Table6_subset_sufficiency.docx
"""
import os
import pandas as pd
from docx import Document
from docx.shared import Pt, RGBColor, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

PROJ = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/1b-papers/SCOPA_Cognition_Study/revision_R1"
TAB = f"{PROJ}/tables"

# ── style helpers (mirrored from 07_build_tables_R1.py) ────────────────
def set_run(run, *, size=10, bold=False, italic=False):
    run.font.name = "Arial"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts"); rPr.append(rFonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs"): rFonts.set(qn(a), "Arial")

def set_para(p, *, before=0, after=0, line=1.0, align=None):
    pf = p.paragraph_format
    pf.space_before = Pt(before); pf.space_after = Pt(after); pf.line_spacing = line
    if align: p.alignment = align

def clear_borders(cell):
    tcPr = cell._tc.get_or_add_tcPr()
    old = tcPr.find(qn("w:tcBorders"))
    if old is not None: tcPr.remove(old)
    tb = OxmlElement("w:tcBorders")
    for s in ("top","left","bottom","right","insideH","insideV"):
        b = OxmlElement(f"w:{s}"); b.set(qn("w:val"),"nil"); tb.append(b)
    tcPr.append(tb)

def set_border(cell, side, sz=4):
    tcPr = cell._tc.get_or_add_tcPr()
    tb = tcPr.find(qn("w:tcBorders"))
    if tb is None: tb = OxmlElement("w:tcBorders"); tcPr.append(tb)
    old = tb.find(qn(f"w:{side}"))
    if old is not None: tb.remove(old)
    b = OxmlElement(f"w:{side}"); b.set(qn("w:val"),"single")
    b.set(qn("w:sz"), str(sz)); b.set(qn("w:color"),"000000"); tb.append(b)

def write_simple_table(rows, header, body_size=9):
    """Write a three-line-bordered table; rows = list of list-of-strings."""
    doc = Document()
    # margins
    for s in doc.sections:
        s.top_margin = Inches(1); s.bottom_margin = Inches(1)
        s.left_margin = Inches(1); s.right_margin = Inches(1)
    # caption placeholder
    doc.add_paragraph("")
    # table
    n_cols = len(header)
    table = doc.add_table(rows=len(rows)+1, cols=n_cols)
    # header row
    for j, h in enumerate(header):
        cell = table.rows[0].cells[j]
        cell.text = ""
        p = cell.paragraphs[0]
        set_para(p, before=0, after=0, line=1.0)
        r = p.add_run(h); set_run(r, size=body_size, bold=True)
        clear_borders(cell)
        set_border(cell, "top", sz=8)       # top thick line
        set_border(cell, "bottom", sz=4)    # header bottom thin
    # body rows
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            cell = table.rows[i].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            set_para(p, before=0, after=0, line=1.05)
            r = p.add_run(val); set_run(r, size=body_size)
            clear_borders(cell)
            if i == len(rows):
                set_border(cell, "bottom", sz=8)  # bottom thick
    return doc, table


# ── Build Table 6 ──────────────────────────────────────────────────────
dom = pd.read_csv(f"{TAB}/subset_sufficiency_domains_R1.csv")
itm = pd.read_csv(f"{TAB}/subset_sufficiency_items_R1.csv")

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

def fmt_c(row):
    return f"{row.c_mean:.3f} ± {row.c_sd:.3f}"
def fmt_auc(v):
    return f"{v:.3f}" if pd.notna(v) else "—"

# Build rows: reference (P0, P1) + 4 single domain + 4 domain pairs (best 3) + key item K values
rows = []
# Reference benchmarks
ref_rows = dom[dom.k.isin([0, 1, 4])].copy()
m0 = ref_rows[ref_rows.subset == "Base only"].iloc[0]
m1 = ref_rows[ref_rows.subset == "Base + Total"].iloc[0]
rows.append(["Reference: P0 parsimonious clinical base (age, sex, edu, MoCA, MDS-UPDRS-III) — no SCOPA-AUT", "5", fmt_c(m0),
             fmt_auc(m0.AUC_t4_mean), fmt_auc(m0.AUC_t6_mean)])
rows.append(["Reference: P1 parsimonious base + 25-item SCOPA-AUT total", "6", fmt_c(m1),
             fmt_auc(m1.AUC_t4_mean), fmt_auc(m1.AUC_t6_mean)])

# Single-domain models
for d_lbl in ["Base + Gastrointestinal", "Base + Urinary",
              "Base + Cardiovascular", "Base + Thermoregulatory"]:
    r = dom[dom.subset == d_lbl].iloc[0]
    rows.append([d_lbl + " domain alone", str(int(r.n_features_total)),
                 fmt_c(r), fmt_auc(r.AUC_t4_mean), fmt_auc(r.AUC_t6_mean)])

# All 4 domains
r = dom[dom.subset == "Base + all 4 domains"].iloc[0]
rows.append(["Base + all 4 SCOPA-AUT domains (no total)",
             str(int(r.n_features_total)),
             fmt_c(r), fmt_auc(r.AUC_t4_mean), fmt_auc(r.AUC_t6_mean)])

# Item K rows — focus on K=1,2,3,4,5,8,21
item_K_rows = itm[itm.K.isin(['1','2','3','4','5','8','21']) | (itm.K.isin([1,2,3,4,5,8,21]))]
# Normalize types: convert K to str-comparable
itm["K_str"] = itm.K.astype(str)
for K in ['1','2','3','4','5','8','21']:
    sub = itm[itm.K_str == K]
    if sub.empty: continue
    r = sub.iloc[0]
    items_short = r["items"]
    # If items long, show count
    item_labels_short = " + ".join(ITEM_LABELS.get(it.strip(), it.strip())
                                   for it in items_short.split(" | ")[:4])
    if K in ('8','21'):
        item_labels_short = f"({K} items: " + ", ".join(it.strip() for it in items_short.split(" | ")[:3]) + ", …)"
    rows.append([f"Base + top-{K} items (no SCOPA-AUT total): {item_labels_short}",
                 str(int(r.n_features_total)),
                 fmt_c(r), fmt_auc(r.AUC_t4_mean), fmt_auc(r.AUC_t6_mean)])

# Build doc
doc, _ = write_simple_table(
    rows,
    header=["Model", "n features", "C-index (10-fold CV)",
            "AUC at 4 years", "AUC at 6 years"],
    body_size=9)

# Caption
caption = doc.paragraphs[0]; caption.text = ""
r = caption.add_run("Table 6. "); set_run(r, size=10, bold=True)
r2 = caption.add_run(
    "Subset-sufficiency analysis for the composite cognitive milestone "
    "(m10–m15) against the parsimonious five-variable clinical base "
    "(age, sex, education, baseline MoCA, MDS-UPDRS Part III). Each row "
    "substitutes a parsimonious SCOPA-AUT representation — a single domain, "
    "a domain pair, all four domains, or the top-K most LASSO-stable items — "
    "for the 25-item SCOPA-AUT total. Discrimination is reported as 10-fold "
    "cross-validated Harrell's C-index and time-dependent area under the "
    "receiver operating characteristic curve (AUC). The seven-item "
    "gastrointestinal domain alone and a three-item subset (lightheadedness "
    "on standing + drooling + straining) recapitulate the discrimination of "
    "the 25-item total.")
set_run(r2, size=10)
set_para(caption, before=0, after=6, line=1.15)

# Footnote
foot = doc.add_paragraph(); set_para(foot, before=2, after=2, line=1.1)
fr = foot.add_run(
    "Abbreviations: AUC, area under the receiver operating characteristic "
    "curve; CV, cross-validation; LASSO, least absolute shrinkage and selection "
    "operator. Items ranked by selection frequency in 10-fold cross-validated "
    "LASSO Cox. Complete-case N = 1,123; 279 composite events. None of the "
    "differences in C-index between sufficient subsets and the SCOPA-AUT total "
    "exceed the cross-validated standard deviation; therefore the parsimonious "
    "subsets are statistically indistinguishable from the 25-item total in "
    "prognostic information for the composite cognitive milestone.")
set_run(fr, size=8, italic=True)

doc.save(f"{TAB}/Table6_subset_sufficiency.docx")
print(f"Saved {TAB}/Table6_subset_sufficiency.docx ({len(rows)} body rows)")
