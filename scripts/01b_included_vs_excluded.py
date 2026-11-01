#!/usr/bin/env python3
"""01b_included_vs_excluded.py: analyzed participants against those without post-baseline assessment."""
import os
import pandas as pd
from scipy import stats

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
a = pd.read_csv(os.path.join(PROJ, "data", "analytical_dataset.csv"), low_memory=False)
e = pd.read_csv(os.path.join(PROJ, "data", "eligible_before_followup.csv"))
assert len(a) == 1339 and len(e) == 1490
x = e[~e.PATNO.isin(a.PATNO)]; i = e[e.PATNO.isin(a.PATNO)]
rows = []
for c in ["age", "edu", "moca", "updrs3", "gds15", "rbdsq", "scopa_total21"]:
    p = stats.mannwhitneyu(x[c].dropna(), i[c].dropna()).pvalue
    f = lambda s: f"{s.median():.1f} [{s.quantile(.25):.1f}, {s.quantile(.75):.1f}]"
    rows.append((c, f(i[c].dropna()), f(x[c].dropna()), p))
for c in ["male", "genetic_enrolled", "era2"]:
    p = stats.chi2_contingency(pd.crosstab(e[c], e.PATNO.isin(a.PATNO)), correction=False)[1]
    rows.append((c, f"{int(i[c].sum())} ({100 * i[c].mean():.1f})", f"{int(x[c].sum())} ({100 * x[c].mean():.1f})", p))
pd.DataFrame(rows, columns=["var", "included", "no_followup", "p"]).to_csv(os.path.join(PROJ, "outputs", "included_vs_nofollowup.csv"), index=False)
