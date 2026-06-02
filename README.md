# SCOPA-AUT Items Predicting Cognitive Milestones in Parkinson's Disease

Analysis code for **"Baseline Autonomic Symptoms Predict Cognitive Milestones in Parkinson's Disease: An Item-Level Analysis of SCOPA-AUT in the PPMI"** — currently under revision (R1) at *Clinical Autonomic Research* (Springer; ms ID AUTR-D-26-00087).

> **Branch status.** The `main` branch contains the v0 analysis from the original submission. This `r1-revision` branch contains the expanded R1 pipeline. The two will be merged into `main` upon paper acceptance.

---

## Study summary (R1 revision)

| | |
|---|---|
| Data freeze | PPMI v2.1 (22 April 2026) |
| Analytical cohort | **N = 1,129** de novo PD patients with baseline SCOPA-AUT and ≥ 1 follow-up visit |
| Outcome | Composite cognitive milestone m10–m15 per Brumm et al. 2023 (MoCA < 21; investigator dementia; PD-D per MDS criteria; UPDRS-I cognitive / hallucination items) |
| Events | **279** composite events (24.7 %) over median 3.0 y follow-up |
| Primary analysis | Item-level Cox PH, two adjustment sets (Model A: 5 covariates; Model B: 12 covariates with LEDD, Schwab–England, RBDSQ, disease duration, α-blocker, antihypertensive, Hoehn–Yahr) |
| Multiple testing | Benjamini–Hochberg FDR over 25 items / 4 domains / 6 milestones |
| Sensitivity analyses | SAA+ subgroup (N = 921); Fine-Gray competing risks (35 / 79 deaths preceded a milestone); LASSO Cox (10-fold CV selection frequency); subset-sufficiency analysis |
| Discrimination | Harrell's *C*, time-dependent AUC at 4 y and 6 y, integrated Brier score; 10-fold CV |
| Key finding | 5 of 21 fully-available items survive FDR correction under Model B (dysphagia, early satiety, lightheadedness on standing, lightheadedness on walking, cold intolerance); domain-level (GI, cardiovascular, thermoregulatory) and subset-sufficient signals replicate the result |

---

## Data

This analysis uses the [PPMI dataset](https://www.ppmi-info.org/). Data access requires registration and approval from PPMI; raw data **are not** included in this repository.

Scripts expect the merged PPMI master at `data/PPMI_Master_Merged_2026-04-22.csv` (the 22 April 2026 freeze; v2.1). `00_inspect_data.py` documents the columns the pipeline expects.

---

## Pipeline — run scripts in numerical order

```
00_inspect_data.py                          # column inventory + sanity checks
01_build_cohort_R1.py                       # inclusion/exclusion, m10–m15 events, locked analytical_dataset_R1.csv
02_primary_analysis_R1.py                   # item-level Cox (Model A + Model B), Schoenfeld PH, LR vs total
03_per_milestone_and_pure_cog_R1.py         # per-milestone item-level Cox (m10–m15) + pure-cog / pure-NP sub-composites
04_lasso_and_discrimination_R1.py           # LASSO Cox selection frequency + nested-model discrimination (C, AUC, IBS)
05_finegray_saa_calibration_R1.py           # Fine-Gray competing risks + SAA+ stratification + calibration
06_build_figures_R1.py                      # publication figures (matplotlib; PDF + PNG + SVG)
07_build_tables_R1.py                       # analytical tables exported as Word .docx
12_subset_sufficiency_R1.py                 # iterative subset-sufficiency Cox sweep
13_build_table6_R1.py                       # subset-sufficiency table
16_recompute_discrimination_full_metrics.py # AUC + Brier for the 6 prognostic models (companion to 04)
```

> This repository contains **analysis code only**. Manuscript assembly, tracked-changes rendering, response-letter generation, and journal-format triage are author-side build glue and are intentionally not included here.

---

## Environment

```bash
pip install -r requirements.txt
```

Python ≥ 3.9. Tested on 3.9 and 3.11.

---

## Reproducibility notes

- **Locked analytical dataset.** Step `01_build_cohort_R1.py` produces `data/analytical_dataset_R1.csv`. All downstream scripts read **only** from that file. No script reloads raw PPMI tables once the analytical dataset is locked.
- **Seed.** `np.random.seed(42)` and `KFold(random_state=42)` everywhere CV occurs.
- **Workflow log.** Every patient-filter step, variable choice, and analytical decision is documented in `manuscript/Workflow_Decisions.docx` (not in this repo — it lives with the manuscript).
- **No silent data drift.** The R1 cohort (Apr 2026 freeze, N = 1,129) differs from the original submission (Jan 2026 freeze, N = 960). The change is disclosed in the manuscript Methods and response letter.

---

## Citation

If you use code from this repository, please cite:

> Negida A. *Baseline autonomic symptoms predict cognitive milestones in Parkinson's disease: an item-level analysis of SCOPA-AUT in the PPMI.* (Under revision, *Clinical Autonomic Research*, 2026.)

PPMI data citation per the [PPMI Data Use Agreement](https://www.ppmi-info.org/access-data-specimens/download-data).

---

## License

MIT — see `LICENSE`.

---

## Contact

Ahmed Negida, MD, PhD — Parkinson and Movement Disorder Center, Department of Neurology, Virginia Commonwealth University
[ahmed.negida@vcuhealth.org](mailto:ahmed.negida@vcuhealth.org) · ORCID [0000-0001-5363-6369](https://orcid.org/0000-0001-5363-6369) · [negidamd.github.io](https://negidamd.github.io/)
