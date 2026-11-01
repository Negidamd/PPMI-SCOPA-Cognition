#!/usr/bin/env python3
"""
01_table1.py: baseline table by primary event status, included vs excluded comparison,
and item prevalence. Writes CSV to outputs/.
"""
import os, json, random
import numpy as np
import pandas as pd
from scipy import stats

SEED = 42
np.random.seed(SEED); random.seed(SEED)
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED_N, EXPECTED_EVENTS = 1339, 349
d = pd.read_csv(os.path.join(PROJ, "data", "analytical_dataset.csv"), low_memory=False)
assert len(d) == EXPECTED_N and d.e_primary.sum() == EXPECTED_EVENTS


def medq(x):
    x = x.dropna()
    return f"{x.median():.1f} [{x.quantile(.25):.1f}, {x.quantile(.75):.1f}]"


def np_(x):
    return f"{int(x.sum())} ({100 * x.mean():.1f})"


def p_fmt(p):
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


CONT = [("Age, y", "age"), ("Education, y", "edu"), ("Disease duration, y", "dis_dur"),
        ("MoCA", "moca"), ("MDS-UPDRS Part III", "updrs3"), ("Hoehn and Yahr stage", "hy"),
        ("Schwab and England ADL, %", "schwab"), ("RBDSQ", "rbdsq"), ("GDS-15", "gds15"),
        ("SCOPA-AUT total (21 items)", "scopa_total21"), ("Gastrointestinal, 0-21", "dom_gi"),
        ("Urinary, 0-18", "dom_uri"), ("Cardiovascular, 0-9", "dom_cv"),
        ("Thermoregulatory, 0-12", "dom_therm"), ("Pupillomotor, 0-3", "dom_pupil")]
BIN = [("Male", "male"), ("Treated at baseline", "treated_bl"),
       ("Genetic cohort enrollment", "genetic_enrolled"), ("Enrolled 2020 onward", "era2"),
       ("Antihypertensive", "antihypertensive"), ("Alpha-blocker", "alpha_blocker"),
       ("Anticholinergic", "anticholinergic")]
ev = d[d.e_primary == 1]; ne = d[d.e_primary == 0]
rows = []
for lab, c in CONT:
    p = stats.mannwhitneyu(ev[c].dropna(), ne[c].dropna()).pvalue
    rows.append((lab, medq(d[c]), medq(ne[c]), medq(ev[c]), p_fmt(p), int(d[c].isna().sum())))
for lab, c in BIN:
    t = pd.crosstab(d[c], d.e_primary)
    p = stats.chi2_contingency(t, correction=False)[1]
    rows.append((lab + ", n (%)", np_(d[c]), np_(ne[c]), np_(ev[c]), p_fmt(p), int(d[c].isna().sum())))
tr = d[d.ledd > 0]
rows.append(("LEDD among treated, mg/day", medq(tr.ledd), medq(tr[tr.e_primary == 0].ledd), medq(tr[tr.e_primary == 1].ledd),
             p_fmt(stats.mannwhitneyu(tr[tr.e_primary == 1].ledd, tr[tr.e_primary == 0].ledd).pvalue), int(d.ledd.isna().sum())))
for lab, c in [("SAA positive, n (%) of tested", "saa"), ("Orthostatic hypotension, n (%) of measured", "oh_bl")]:
    z = d[d[c].notna()]
    t = pd.crosstab(z[c], z.e_primary)
    rows.append((lab, np_(z[c]), np_(z[z.e_primary == 0][c]), np_(z[z.e_primary == 1][c]),
                 p_fmt(stats.chi2_contingency(t, correction=False)[1]), int(d[c].isna().sum())))
for r_ in ["White", "Black", "Asian", "More than one race", "American Indian/Alaska Native", "Not reported"]:
    rows.append((f"Race: {r_}, n (%)", np_(d.race == r_), np_(ne.race == r_), np_(ev.race == r_), "", 0))
fu = (d.t_last)
rows.append(("Last assessment, y", medq(d.t_last), medq(ne.t_last), medq(ev.t_last), "", 0))
T = pd.DataFrame(rows, columns=["Characteristic", "All", "No milestone", "Milestone", "p", "Missing"])
T.to_csv(os.path.join(PROJ, "outputs", "table1.csv"), index=False)
print(T.to_string())
print(f"Columns: all {len(d)}, no milestone {len(ne)}, milestone {len(ev)}")

# Item prevalence ---------------------------------------------------------
ITEMS = [f"SCAU{i}" for i in range(1, 26)]
prev = pd.DataFrame({"exposure": ITEMS,
                     "n_answered": [int(d[c].notna().sum()) for c in ITEMS],
                     "any_pct": [100 * (d[c].dropna() > 0).mean() for c in ITEMS],
                     "ge2_pct": [100 * (d[c].dropna() >= 2).mean() for c in ITEMS],
                     "mean": [d[c].mean() for c in ITEMS]})
prev.to_csv(os.path.join(PROJ, "outputs", "item_prevalence.csv"), index=False)

# Those excluded for lack of follow-up ---------------------------------------
print(d.groupby("era2").e_primary.agg(["size", "sum"]))
print("Follow-up by era: ", d.groupby("era2").t_last.median().round(2).to_dict())
print("First milestone distribution among events:", d[d.e_primary == 1].first_ms.str.split("+").explode().value_counts().to_dict())
print("Single first milestone:", int((~d[d.e_primary == 1].first_ms.str.contains(r"\+")).sum()))
print("Women in cohort", int((d.male == 0).sum()), "SCAU22 answered (men)", int(d.SCAU22.notna().sum()), "of", int((d.male == 1).sum()),
      "; SCAU24 answered (women)", int(d.SCAU24.notna().sum()), "of", int((d.male == 0).sum()))
ext = {"tertiles": d.scopa_total21.quantile([1 / 3, 2 / 3]).round(2).tolist()}
json.dump(ext, open(os.path.join(PROJ, "outputs", "tertiles.json"), "w"))

# Included vs eligible without follow-up ---------------------------------------
cu = pd.read_csv(os.path.join(PROJ, "logs", "exclusion_log.csv"))
print(cu[["criterion", "n_after", "excluded"]].to_string())
