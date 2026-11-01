# SCOPA-AUT items and cognition milestones in Parkinson's disease

Analysis code for **"Baseline Autonomic Symptoms and Cognitive Progression Milestones in Parkinson's Disease: An Item-Level SCOPA-AUT Analysis"**, a longitudinal cohort study in the Parkinson's Progression Markers Initiative (PPMI).

This code replaces the code for the preprint (doi:10.21203/rs.3.rs-9129721/v1). Do not use the preprint code or its results. The rebuild corrects the SCOPA-AUT item labels and domains, the timing of baseline levodopa equivalent daily dose, the time scale after year 5, the event times for individual milestones, the competing-risk model, and the exclusion of participants who answered "not applicable" to sexual items. The preprint code is kept at tag `preprint-v1`.

The analysis plan is in [SAP.md](SAP.md). It was written after an audit of the earlier versions and is not blind to their results. Departures from it are listed in the manuscript.

## Data

No PPMI data are in this repository. Access requires approval from PPMI ([ppmi-info.org](https://www.ppmi-info.org/)).

Download the raw case report form files of the 22 April 2026 freeze into `data/raw/`, keeping their file names. `data/raw_manifest_sha256.txt` lists the files with SHA-256 hashes, so you can confirm you have the same freeze. No derived or merged dataset is used.

## Run order

Run from the repository root.

```
pip install -r requirements.txt

python3 scripts/00_build_cohort.py                # cohort, milestones, covariates
CATH3=1 python3 scripts/00_build_cohort.py        # catheter sensitivity cohort
python3 scripts/01_table1.py                      # baseline table
python3 scripts/01b_included_vs_excluded.py       # analyzed vs no follow-up
Rscript scripts_R/02_primary.R                    # item, domain and total models
python3 scripts/03_verify_lifelines.py            # refit in a second implementation
Rscript scripts_R/03_sensitivity.R                # sensitivity analyses
Rscript scripts_R/05_descriptive_curves.R         # cumulative incidence, attrition
Rscript scripts_R/07_posthoc.R                    # post hoc checks
Rscript scripts_R/04_prediction.R                 # cross-validated prediction
python3 scripts/06_figures.py                     # figures
```

Scripts stop if the cohort does not match the expected N = 1,339 and 349 primary events. Results are written to `outputs/`, `logs/`, and `figures/`. The random seed is 42.

## Software

Python 3.13 with the versions in `requirements.txt`. R 4.5.2 with survival 3.8.3, glmnet 4.1.10, timeROC 0.4.1, mice 3.19.0, and data.table 1.17.0.

## Citation

The corrected manuscript is not yet published. Until then, please cite this repository.

## License

This code is provided for research reproducibility. PPMI data are subject to the PPMI data use agreement.
