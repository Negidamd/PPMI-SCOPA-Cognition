"""
15_assemble_submission_package.py
─────────────────────────────────────────────────────────────────────────
Build the /revised_to_submit folder for the Clinical Autonomic Research R1
revision submission.

Subfolders:
    1_cover_letter/
    2_response_to_reviewers/
    3_manuscript/                  (clean + tracked-changes versions)
    4_figures/                     (renamed Figure_1..5 + Supp S1..S6, PDF+PNG)
    5_tables/                      (Table_1..5 + Supp_Table_S1..S4)

All file copies use the post-triage CAR-clean numbering. PDFs are the
submission-grade vector originals; PNGs are included as previewable copies.

Idempotent: re-running overwrites the destination cleanly.
─────────────────────────────────────────────────────────────────────────
"""
import os, shutil

PROJ = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/1b-papers/SCOPA_Cognition_Study/revision_R1"
DEST = os.path.join(PROJ, "revised_to_submit")

# Wipe + recreate
if os.path.exists(DEST):
    shutil.rmtree(DEST)
for sub in ["1_cover_letter", "2_response_to_reviewers", "3_manuscript",
            "4_figures", "5_tables"]:
    os.makedirs(os.path.join(DEST, sub), exist_ok=True)

def cp(src, dst):
    src_abs = os.path.join(PROJ, src)
    dst_abs = os.path.join(DEST, dst)
    if not os.path.exists(src_abs):
        print(f"  MISSING: {src}")
        return False
    shutil.copy2(src_abs, dst_abs)
    print(f"  {src:60s} -> {dst}")
    return True

# ── 1. Cover letter ─────────────────────────────────────────────────────
print("\n[1] Cover letter")
cp("cover_letter/cover_letter_R1.docx", "1_cover_letter/Cover_Letter.docx")

# ── 2. Response to reviewers ────────────────────────────────────────────
print("\n[2] Response to reviewers")
cp("response_to_reviewers/Response_to_Reviewers_R1.docx",
   "2_response_to_reviewers/Response_to_Reviewers.docx")

# ── 3. Manuscript ───────────────────────────────────────────────────────
print("\n[3] Manuscript")
cp("manuscript/manuscript.docx",         "3_manuscript/Manuscript_Clean.docx")
cp("manuscript/manuscript_tracked.docx", "3_manuscript/Manuscript_Tracked_Changes.docx")

# ── 4. Figures (renamed to CAR submission numbering) ────────────────────
print("\n[4] Figures")
# Map: source basename → submission basename. Keep BOTH PDF (vector,
# submission-grade) and PNG (previewable) for every figure.
FIG_MAP = [
    # Main figures (1–5)
    ("Figure1_flowchart",                "Figure_1_Flowchart"),
    ("Figure2_forest_modelA_vs_modelB",  "Figure_2_Forest_ModelA_vs_ModelB"),
    ("Figure3_KM_tertiles",              "Figure_3_KaplanMeier_SCOPA_tertiles"),
    ("Figure4_domain_lollipop",          "Figure_4_Domain_forest"),
    ("Figure7_discrimination",           "Figure_5_Prognostic_discrimination"),
    # Supplementary figures (S1–S6)
    ("FigureS1_schoenfeld_PH",           "Supplementary_Figure_S1_Schoenfeld_PH"),
    ("calibration_4y",                   "Supplementary_Figure_S2_Calibration_4y"),
    ("Figure5_heatmap_per_milestone",    "Supplementary_Figure_S3_Per_milestone_heatmap"),
    ("Figure6_lasso_coefficient_path",   "Supplementary_Figure_S4_LASSO_selection_frequency"),
    ("Figure8_milestone_contribution",   "Supplementary_Figure_S5_Milestone_contribution"),
    ("Figure9_subset_sufficiency",       "Supplementary_Figure_S6_Subset_sufficiency"),
]
for src_base, dst_base in FIG_MAP:
    for ext in ("pdf", "png"):
        cp(f"figures/{src_base}.{ext}", f"4_figures/{dst_base}.{ext}")

# ── 5. Tables (Word .docx, already correctly numbered) ──────────────────
print("\n[5] Tables")
TAB_MAP = [
    # Main tables (1–4 after second-pass triage)
    ("Table1_baseline.docx",            "Table_1_Baseline_characteristics.docx"),
    ("Table2_item_cox.docx",            "Table_2_Item_level_Cox_models.docx"),
    ("Table3_discrimination.docx",      "Table_3_Prognostic_discrimination.docx"),
    ("Table4_subset_sufficiency.docx",  "Table_4_Subset_sufficiency.docx"),
    # Supplementary tables (S1–S5)
    ("SuppTableS1_SAApos.docx",         "Supplementary_Table_S1_SAA_positive_subgroup.docx"),
    ("SuppTableS2_competing_risks.docx","Supplementary_Table_S2_Competing_risks_FineGray.docx"),
    ("SuppTableS3_lasso_frequency.docx","Supplementary_Table_S3_LASSO_selection_frequency.docx"),
    ("SuppTableS4_per_milestone.docx",  "Supplementary_Table_S4_Per_milestone_Cox_models.docx"),
    ("SuppTableS5_domain.docx",         "Supplementary_Table_S5_Domain_level_Cox_models.docx"),
]
for src, dst in TAB_MAP:
    cp(f"tables/{src}", f"5_tables/{dst}")

# ── Manifest ────────────────────────────────────────────────────────────
print("\n[6] Submission manifest")
manifest_path = os.path.join(DEST, "SUBMISSION_MANIFEST.txt")
with open(manifest_path, "w") as f:
    f.write("CLINICAL AUTONOMIC RESEARCH — R1 REVISION SUBMISSION PACKAGE\n")
    f.write("=" * 70 + "\n\n")
    f.write("Manuscript ID: AUTR-D-26-00087\n")
    f.write("Corresponding author: Ahmed Negida, MD, PhD\n\n")
    f.write("CONTENTS\n")
    f.write("-" * 70 + "\n\n")
    f.write("1_cover_letter/\n")
    f.write("    Cover_Letter.docx\n\n")
    f.write("2_response_to_reviewers/\n")
    f.write("    Response_to_Reviewers.docx          (point-by-point)\n\n")
    f.write("3_manuscript/\n")
    f.write("    Manuscript_Clean.docx               (submit this as the main MS)\n")
    f.write("    Manuscript_Tracked_Changes.docx     (revision audit trail)\n\n")
    f.write("4_figures/  (5 main + 6 supplementary; PDF=vector, PNG=preview)\n")
    f.write("    Figure_1_Flowchart.{pdf,png}\n")
    f.write("    Figure_2_Forest_ModelA_vs_ModelB.{pdf,png}\n")
    f.write("    Figure_3_KaplanMeier_SCOPA_tertiles.{pdf,png}\n")
    f.write("    Figure_4_Domain_forest.{pdf,png}\n")
    f.write("    Figure_5_Prognostic_discrimination.{pdf,png}\n")
    f.write("    Supplementary_Figure_S1_Schoenfeld_PH.{pdf,png}\n")
    f.write("    Supplementary_Figure_S2_Calibration_4y.{pdf,png}\n")
    f.write("    Supplementary_Figure_S3_Per_milestone_heatmap.{pdf,png}\n")
    f.write("    Supplementary_Figure_S4_LASSO_selection_frequency.{pdf,png}\n")
    f.write("    Supplementary_Figure_S5_Milestone_contribution.{pdf,png}\n")
    f.write("    Supplementary_Figure_S6_Subset_sufficiency.{pdf,png}\n\n")
    f.write("5_tables/  (4 main + 5 supplementary; Word .docx)\n")
    f.write("    Table_1_Baseline_characteristics.docx\n")
    f.write("    Table_2_Item_level_Cox_models.docx\n")
    f.write("    Table_3_Prognostic_discrimination.docx\n")
    f.write("    Table_4_Subset_sufficiency.docx\n")
    f.write("    Supplementary_Table_S1_SAA_positive_subgroup.docx\n")
    f.write("    Supplementary_Table_S2_Competing_risks_FineGray.docx\n")
    f.write("    Supplementary_Table_S3_LASSO_selection_frequency.docx\n")
    f.write("    Supplementary_Table_S4_Per_milestone_Cox_models.docx\n")
    f.write("    Supplementary_Table_S5_Domain_level_Cox_models.docx\n\n")
    f.write("DISPLAY-ITEM COUNT\n")
    f.write("-" * 70 + "\n")
    f.write("    Main figures:        5  (within CAR norm of 4–6)\n")
    f.write("    Main tables:         4  (within CAR norm of 3–5)\n")
    f.write("    Supplementary figs:  6\n")
    f.write("    Supplementary tabs:  5\n\n")
    f.write("REVISION SUMMARY\n")
    f.write("-" * 70 + "\n")
    f.write("    Original data freeze:  PPMI 26-Jan-2026  (N=960; 227 events)\n")
    f.write("    R1 revision data:      PPMI 22-Apr-2026 v2.1  (N=1,129; 279 events)\n")
    f.write("    Cohort change disclosed in Methods + cover letter.\n\n")
print(f"  Wrote {manifest_path}")

print("\n" + "=" * 70)
print(f"Submission package assembled at: {DEST}")
print("=" * 70)
