#!/usr/bin/env python3
"""
09_build_tracked_changes_R1.py — Word-level tracked-changes manuscript.

Builds manuscript_R1_tracked.docx using OOXML revision marks (w:ins / w:del).
For each paragraph: identifies the best-matching paragraph in the new R1
manuscript by section + similarity, then produces a word-level diff using
difflib.SequenceMatcher. Wraps inserted runs in <w:ins> and deleted runs in
<w:del> with author "AI-assisted revision" and a timestamp.
"""
import os, re, hashlib, datetime
from difflib import SequenceMatcher
from docx import Document
from docx.shared import Pt, RGBColor, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

PROJ = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/1b-papers/SCOPA_Cognition_Study/revision_R1"
ORIG = "/Users/ahmednegida/Library/Mobile Documents/com~apple~CloudDocs/1b-papers/SCOPA_Cognition_Study/manuscript/manuscript.docx"
NEW  = os.path.join(PROJ, "manuscript", "manuscript_R1.docx")
OUT  = os.path.join(PROJ, "manuscript", "manuscript_R1_tracked.docx")

AUTHOR = "R1 revision"
DATE   = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

# ── Load original and new ────────────────────────────────────────────────
orig = Document(ORIG)
new  = Document(NEW)
print(f"Original: {len(orig.paragraphs)} paragraphs")
print(f"New R1:   {len(new.paragraphs)} paragraphs")

# Helpers
def text_only(para):
    return para.text.strip()

def style_name(para):
    try:    return para.style.name
    except: return "Normal"

# Section header detection
def is_heading(para):
    return style_name(para).startswith("Heading")

# Group paragraphs by section
def group_by_section(paragraphs):
    sections, cur, cur_name = [], [], "PREAMBLE"
    for p in paragraphs:
        if is_heading(p) and style_name(p) == "Heading 1":
            if cur:
                sections.append((cur_name, cur))
            cur, cur_name = [p], text_only(p)
        else:
            cur.append(p)
    if cur:
        sections.append((cur_name, cur))
    return sections

orig_sec = group_by_section(orig.paragraphs)
new_sec  = group_by_section(new.paragraphs)
print(f"\nOriginal sections: {[s[0] for s in orig_sec]}")
print(f"New R1 sections:   {[s[0] for s in new_sec]}")

# ── Build tracked-changes document ───────────────────────────────────────
doc = Document()
section = doc.sections[0]
section.top_margin    = Cm(2.54)
section.bottom_margin = Cm(2.54)
section.left_margin   = Cm(2.54)
section.right_margin  = Cm(2.54)

# Line numbers
sectPr = section._sectPr
lnNum = OxmlElement("w:lnNumType")
lnNum.set(qn("w:countBy"), "1"); lnNum.set(qn("w:restart"), "continuous")
lnNum.set(qn("w:distance"), "284")
sectPr.append(lnNum)

# Footer page number
footer = section.footer
footer_p = footer.paragraphs[0]
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
fr = footer_p.add_run()
fr.font.name = "Arial"; fr.font.size = Pt(10)
fld_begin = OxmlElement("w:fldChar"); fld_begin.set(qn("w:fldCharType"), "begin")
instr = OxmlElement("w:instrText"); instr.text = "PAGE"
fld_end = OxmlElement("w:fldChar"); fld_end.set(qn("w:fldCharType"), "end")
fr._r.append(fld_begin); fr._r.append(instr); fr._r.append(fld_end)

# Font helpers
def make_run_xml(text, *, size=11, bold=False, italic=False):
    """Create a <w:r> element with given run properties + text."""
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rFonts = OxmlElement("w:rFonts")
    for a in ("w:ascii","w:hAnsi","w:cs"): rFonts.set(qn(a), "Arial")
    rPr.append(rFonts)
    sz = OxmlElement("w:sz"); sz.set(qn("w:val"), str(int(size*2)))
    rPr.append(sz)
    color = OxmlElement("w:color"); color.set(qn("w:val"), "000000")
    rPr.append(color)
    if bold: rPr.append(OxmlElement("w:b"))
    if italic: rPr.append(OxmlElement("w:i"))
    r.append(rPr)
    t = OxmlElement("w:t"); t.text = text
    t.set(qn("xml:space"), "preserve")
    r.append(t)
    return r

_rev_counter = [0]
def next_rev_id():
    _rev_counter[0] += 1
    return _rev_counter[0]

def make_ins(text, *, size=11, bold=False, italic=False):
    ins = OxmlElement("w:ins")
    ins.set(qn("w:id"), str(next_rev_id()))
    ins.set(qn("w:author"), AUTHOR)
    ins.set(qn("w:date"), DATE)
    r = make_run_xml(text, size=size, bold=bold, italic=italic)
    ins.append(r)
    return ins

def make_del(text, *, size=11, bold=False, italic=False):
    delete = OxmlElement("w:del")
    delete.set(qn("w:id"), str(next_rev_id()))
    delete.set(qn("w:author"), AUTHOR)
    delete.set(qn("w:date"), DATE)
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rFonts = OxmlElement("w:rFonts")
    for a in ("w:ascii","w:hAnsi","w:cs"): rFonts.set(qn(a), "Arial")
    rPr.append(rFonts)
    sz = OxmlElement("w:sz"); sz.set(qn("w:val"), str(int(size*2)))
    rPr.append(sz)
    color = OxmlElement("w:color"); color.set(qn("w:val"), "000000")
    rPr.append(color)
    if bold: rPr.append(OxmlElement("w:b"))
    if italic: rPr.append(OxmlElement("w:i"))
    r.append(rPr)
    delText = OxmlElement("w:delText"); delText.text = text
    delText.set(qn("xml:space"), "preserve")
    r.append(delText)
    delete.append(r)
    return delete

def add_para_with_tracked_diff(orig_text, new_text, *, size=11, bold=False,
                                italic=False, before=4, after=6, line=2.0,
                                style="Normal"):
    """Add a paragraph whose runs contain word-level OOXML tracked changes."""
    p = doc.add_paragraph()
    if style == "Heading 1" or style == "Heading 2":
        try: p.style = doc.styles["Heading 1"] if style == "Heading 1" else doc.styles["Heading 2"]
        except: pass
        bold = True
    pf = p.paragraph_format
    pf.space_before = Pt(before); pf.space_after = Pt(after); pf.line_spacing = line

    if orig_text == new_text:
        if new_text.strip():
            r = p.add_run(new_text)
            r.font.name = "Arial"; r.font.size = Pt(size)
            r.font.bold = bold; r.font.italic = italic
            r.font.color.rgb = RGBColor(0, 0, 0)
            rPr = r._r.get_or_add_rPr()
            rFonts = rPr.find(qn("w:rFonts")) or OxmlElement("w:rFonts")
            for a in ("w:ascii","w:hAnsi","w:cs"): rFonts.set(qn(a), "Arial")
            if rFonts not in list(rPr): rPr.append(rFonts)
        return p

    # Tokenize at whitespace, keeping spaces attached to following word
    orig_tokens = re.findall(r'\S+\s*|\s+', orig_text)
    new_tokens  = re.findall(r'\S+\s*|\s+', new_text)
    matcher = SequenceMatcher(None, orig_tokens, new_tokens)

    p_xml = p._p
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            txt = "".join(new_tokens[j1:j2])
            if txt:
                r = make_run_xml(txt, size=size, bold=bold, italic=italic)
                p_xml.append(r)
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

def add_inserted_paragraph(text, *, size=11, bold=False, italic=False,
                            before=4, after=6, line=2.0, style="Normal"):
    """Add an entire paragraph as inserted content (used for net-new R1 paragraphs)."""
    return add_para_with_tracked_diff("", text, size=size, bold=bold,
                                       italic=italic, before=before, after=after,
                                       line=line, style=style)

def add_deleted_paragraph(text, *, size=11, bold=False, italic=False,
                           before=4, after=6, line=2.0, style="Normal"):
    """Add an entire paragraph as deleted content (used for orig paragraphs without R1 match)."""
    return add_para_with_tracked_diff(text, "", size=size, bold=bold,
                                       italic=italic, before=before, after=after,
                                       line=line, style=style)

# ── Section alignment: pair sections by name (Abstract/Introduction/etc.) ─
NAME_MAP = {  # original section name → R1 section name
    "Abstract": "Abstract",
    "Introduction": "Introduction",
    "Methods": "Methods",
    "Results": "Results",
    "Discussion": "Discussion",
    "Declarations": "Declarations",
    "References": "References",
    "Figures": "Figures",
    "PREAMBLE": "PREAMBLE",
}
new_by_name = {sec[0]: sec[1] for sec in new_sec}
orig_by_name = {sec[0]: sec[1] for sec in orig_sec}

# Match: within each shared section, pair paragraphs by best similarity
def best_match(target_text, candidates):
    """Return index of best-matching candidate (≥ threshold), else None."""
    if not target_text.strip(): return None
    best_idx, best_score = None, 0.0
    for i, c in enumerate(candidates):
        ctext = text_only(c)
        if not ctext: continue
        score = SequenceMatcher(None, target_text[:200], ctext[:200]).ratio()
        if score > best_score:
            best_score, best_idx = score, i
    return best_idx if best_score > 0.30 else None

# Process each section in NEW order (this is the "delivery" order)
print("\nGenerating tracked-changes manuscript paragraph-by-paragraph ...")
used_orig_idxs = {sec_name: set() for sec_name in orig_by_name}

for new_sec_name, new_paras in new_sec:
    orig_paras = orig_by_name.get(NAME_MAP.get(new_sec_name, new_sec_name), [])
    for np_ in new_paras:
        new_text = text_only(np_)
        new_style = style_name(np_)
        is_head = is_heading(np_)
        # Find best matching original paragraph in same section
        match_idx = None
        if orig_paras:
            unused = [(i, c) for i, c in enumerate(orig_paras)
                      if i not in used_orig_idxs[NAME_MAP.get(new_sec_name, new_sec_name)]]
            if unused:
                candidates_text = [text_only(c) for _, c in unused]
                idx_in_unused = best_match(new_text, [c for _, c in unused])
                if idx_in_unused is not None:
                    match_idx = unused[idx_in_unused][0]
        # Determine formatting
        size = 11
        bold = is_head or new_style in ("Heading 1", "Heading 2")
        italic = False
        if match_idx is not None:
            orig_text = text_only(orig_paras[match_idx])
            used_orig_idxs[NAME_MAP.get(new_sec_name, new_sec_name)].add(match_idx)
            add_para_with_tracked_diff(
                orig_text, new_text, size=size, bold=bold, italic=italic,
                before=12 if is_head else 4,
                after=6,
                line=2.0,
                style=new_style)
        else:
            # Net-new paragraph in R1 — mark wholly inserted
            if new_text.strip():
                add_inserted_paragraph(
                    new_text, size=size, bold=bold, italic=italic,
                    before=12 if is_head else 4,
                    after=6, line=2.0, style=new_style)
            else:
                doc.add_paragraph()

# Append any original paragraphs that weren't matched (wholly deleted)
print("\nMarking unmatched original paragraphs as deleted (in order)...")
for orig_sec_name, orig_paras in orig_sec:
    unmatched = [c for i, c in enumerate(orig_paras)
                 if i not in used_orig_idxs.get(orig_sec_name, set())]
    for c in unmatched:
        txt = text_only(c)
        if not txt: continue
        is_head = is_heading(c)
        bold = is_head
        # Skip if the original heading was already covered (we will already
        # have the R1 heading version inserted)
        if is_head and txt in [sn[0] for sn in new_sec]: continue
        add_deleted_paragraph(
            txt, size=11, bold=bold,
            before=12 if is_head else 4, after=6, line=2.0)

doc.save(OUT)
print(f"\nSaved: {OUT}")
print(f"  total revision IDs assigned: {_rev_counter[0]}")
