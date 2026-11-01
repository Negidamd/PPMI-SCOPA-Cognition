#!/usr/bin/env python3
"""
03_verify_lifelines.py: refit the primary and strict models in a second implementation.

Uses lifelines (Python) and compares against R survival output. Also explains warnings
and writes logs/verify_lifelines.md.
"""
import os, random, warnings
import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from statsmodels.stats.multitest import multipletests

warnings.filterwarnings("ignore")
SEED = 42
np.random.seed(SEED); random.seed(SEED)
EXPECTED_N, EXPECTED_EVENTS = 1339, 349
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = pd.read_csv(os.path.join(PROJ, "data", "analytical_dataset.csv"), low_memory=False)
assert len(d) == EXPECTED_N and d.e_primary.sum() == EXPECTED_EVENTS
d["ledd100"] = d.ledd / 100
M1 = ["age", "male", "edu", "moca", "updrs3"]
M2 = M1 + ["hy", "schwab", "dis_dur", "ledd100", "rbdsq", "gds15", "antihypertensive",
           "alpha_blocker", "anticholinergic", "genetic_enrolled"]
ITEMS = [f"SCAU{i}" for i in range(1, 26)]
r = pd.read_csv(os.path.join(PROJ, "outputs", "cox_items_all.csv"))


def fit(item, covs, ep):
    data = d
    if item in ("SCAU22", "SCAU23"):
        data = d[d.male == 1]; covs = [c for c in covs if c != "male"]
    if item in ("SCAU24", "SCAU25"):
        data = d[d.male == 0]; covs = [c for c in covs if c != "male"]
    sub = data[[item, f"t_{ep}", f"e_{ep}", "era2"] + covs].dropna()
    # lifelines has Efron ties and strata, as R does
    m = CoxPHFitter().fit(sub, duration_col=f"t_{ep}", event_col=f"e_{ep}", strata=["era2"])
    return np.exp(m.params_[item]), m.summary.loc[item, "p"], len(sub), int(sub[f"e_{ep}"].sum())


out = ["# Second-implementation check (lifelines vs R survival)\n"]
worst = {}
for ep, mn, covs in [("primary", "M2", M2), ("primary", "M1", M1), ("strict", "M2", M2), ("strict", "M1", M1)]:
    rows = []
    for it in ITEMS:
        hr, p, n, ev = fit(it, covs, ep)
        rows.append((it, hr, p, n, ev))
    t = pd.DataFrame(rows, columns=["exposure", "HR_py", "p_py", "N_py", "ev_py"])
    t["q_py"] = multipletests(t.p_py, method="fdr_bh")[1]
    m = t.merge(r[(r.endpoint == ep) & (r.model == mn)], on="exposure")
    m["dHR"] = (m.HR_py - m.HR).abs()
    m["dq"] = (m.q_py - m.q).abs()
    worst[(ep, mn)] = (m.dHR.max(), m.dq.max(), (m.N_py != m.N).sum(), (m.ev_py != m.events).sum())
    same = set(m[m.q < .05].exposure) == set(m[m.q_py < .05].exposure)
    out.append(f"- {ep} {mn}: max |dHR| {m.dHR.max():.5f}; max |dq| {m.dq.max():.5f}; "
               f"N mismatches {(m.N_py != m.N).sum()}; event mismatches {(m.ev_py != m.events).sum()}; "
               f"same q<0.05 set: {same}")

# Which R fits produced the convergence warning
sub = d[d.male == 0]
out.append("\nR warning source: sex-restricted fits. Women on alpha-blockers, by event:")
out.append(str(pd.crosstab(sub.alpha_blocker, sub.e_primary).to_dict()))
out.append(f"Women with alpha_blocker=1 and any strict event: {int(sub[sub.alpha_blocker == 1].e_strict.sum())}")
txt = "\n".join(out)
print(txt)
open(os.path.join(PROJ, "logs", "verify_lifelines.md"), "w").write(txt + "\n")
