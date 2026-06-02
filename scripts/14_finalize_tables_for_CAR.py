"""
14_finalize_tables_for_CAR.py
─────────────────────────────────────────────────────────────────────────
Apply the CAR (Clinical Autonomic Research) figure/table triage to the
standalone table .docx files in /tables/.

Renumbering (combined first- + second-pass CAR triage):
  Table 3 (domain Cox)               → Supplementary Table S5  (NEW, second pass)
  Table 4 (per-milestone item Cox)   → Supplementary Table S4
  Table 5 (discrimination)           → Table 3                  (promoted +1)
  Table 6 (subset sufficiency)       → Table 4                  (promoted +1)

For each source file we:
  (a) load the docx,
  (b) rewrite the "Table N." caption text to the new label,
  (c) save under the new filename,
  (d) delete the source file (so /tables/ doesn't carry both numberings).

Existing Supp Tables S1, S2, S3 are not touched.

Idempotent: re-running after a successful pass is a no-op (sources missing).
─────────────────────────────────────────────────────────────────────────
"""
import os, re
from docx import Document

PROJ = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/1b-papers/SCOPA_Cognition_Study/revision_R1"
TAB  = os.path.join(PROJ, "tables")

# Each entry: (src_filename, dst_filename, old_label, new_label).
# We keep TWO entries for Table 4 → Supp S4 because both the R1-suffixed and
# the cleaned versions may coexist in /tables/.
RENAMES = [
    # Second-pass: domain Cox (was main Table 3) → Supplementary Table S5
    ("Table3_R1_domain.docx",          "SuppTableS5_domain.docx",
     "Table 3.", "Supplementary Table S5."),
    ("Table3_domain.docx",             "SuppTableS5_domain.docx",
     "Table 3.", "Supplementary Table S5."),
    # First-pass: per-milestone Cox (was main Table 4) → Supplementary Table S4
    ("Table4_R1_per_milestone.docx",   "SuppTableS4_per_milestone.docx",
     "Table 4.", "Supplementary Table S4."),
    ("Table4_per_milestone.docx",      "SuppTableS4_per_milestone.docx",
     "Table 4.", "Supplementary Table S4."),
    # Promotions (now shifted up to fill Table 3 gap)
    ("Table5_R1_discrimination.docx",  "Table3_discrimination.docx",
     "Table 5.", "Table 3."),
    ("Table5_discrimination.docx",     "Table3_discrimination.docx",
     "Table 5.", "Table 3."),
    ("Table6_subset_sufficiency.docx", "Table4_subset_sufficiency.docx",
     "Table 6.", "Table 4."),
]

def _rewrite_caption(doc, old_label, new_label):
    """Walk every text run in the document and replace the leading caption
    label. Handles 'Table N.' (the caption convention) plus any in-text
    cross-reference such as '(Table N)' inside footnotes or abbreviations
    blocks. Word boundaries kept so 'Table 4' doesn't match 'Table 40'."""
    pat_caption = re.compile(r"^" + re.escape(old_label))
    pat_inline  = re.compile(r"\b" + re.escape(old_label.rstrip('.')) + r"\b")
    n = 0
    for p in doc.paragraphs:
        for run in p.runs:
            if not run.text: continue
            t = run.text
            # First try caption-position match (start of run)
            t2, k = pat_caption.subn(new_label, t)
            if k:
                run.text = t2; n += k; continue
            # Then any in-text refs in this run
            t2, k = pat_inline.subn(new_label.rstrip('.'), t)
            if k:
                run.text = t2; n += k
    # Also walk table cells (footnotes/abbreviations rows)
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for run in p.runs:
                        if not run.text: continue
                        t = run.text
                        t2, k = pat_caption.subn(new_label, t)
                        if k: run.text = t2; n += k; continue
                        t2, k = pat_inline.subn(new_label.rstrip('.'), t)
                        if k: run.text = t2; n += k
    return n

def main():
    renamed, skipped = [], []
    for src, dst, old_lbl, new_lbl in RENAMES:
        src_path = os.path.join(TAB, src)
        dst_path = os.path.join(TAB, dst)
        if not os.path.exists(src_path):
            skipped.append(src); continue
        # If destination already exists from a prior run, replace it
        # (the new file from this pass supersedes).
        doc = Document(src_path)
        n = _rewrite_caption(doc, old_lbl, new_lbl)
        doc.save(dst_path)
        os.remove(src_path)
        renamed.append((src, dst, n))
        print(f"  {src:42s} -> {dst:42s}   ({n} caption/ref edits)")
    if skipped:
        print(f"  Skipped (not present): {', '.join(skipped)}")
    print(f"\nDone. {len(renamed)} renames applied.")

if __name__ == "__main__":
    main()
