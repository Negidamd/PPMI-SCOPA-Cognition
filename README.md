# SCOPA-AUT Items Predicting Cognitive Milestones in Parkinson's Disease

Analysis code for the study: **"Baseline Autonomic Symptoms Predict Cognitive Milestones in Parkinson's Disease: An Item-Level Analysis of SCOPA-AUT in the PPMI"**

## Study Summary

This study examines which individual SCOPA-AUT (Scales for Outcomes in Parkinson's Disease — Autonomic) items at baseline predict subsequent cognitive milestones in Parkinson's disease, using the Parkinson's Progression Markers Initiative (PPMI) dataset.

- **Cohort:** 960 de novo PD patients with baseline SCOPA-AUT and ≥2 years follow-up
- **Outcome:** Composite cognitive milestone (MoCA <21, investigator-diagnosed dementia, PD-Dementia per MDS criteria, UPDRS-I cognitive/hallucination/apathy items)
- **Primary analysis:** Item-level Cox proportional hazards models, adjusted for age, sex, education, baseline MoCA, and MDS-UPDRS Part III
- **Key finding:** 8 of 25 SCOPA-AUT items independently predicted cognitive milestones after FDR correction

## Data

This analysis uses the [PPMI dataset](https://www.ppmi-info.org/). Data access requires registration and approval from PPMI. The scripts expect:
- `../PPMI_Master_Merged.csv` — the merged PPMI master dataset (not included; see PPMI data portal)

## Scripts

Run scripts in numerical order:

| Script | Description |
|--------|-------------|
| `scripts/00_build_cohort.py` | Builds the analytical cohort (N=960) with inclusion/exclusion criteria, defines outcomes and time-to-event variables |
| `scripts/01_table1.py` | Generates Table 1: baseline characteristics by cognitive milestone status |
| `scripts/02_primary_analysis.py` | Primary analysis: item-level and domain-level Cox PH and logistic regression |
| `scripts/03_sensitivity.py` | Sensitivity analyses: 4-year follow-up cutoff, individual milestones, attrition bias |
| `scripts/04_figures.py` | Generates all figures: flow diagram, forest plots, Kaplan-Meier curves, sensitivity heatmap |

## Requirements

```
pip install -r requirements.txt
```

## Output Structure

```
├── data/
│   ├── analytical_dataset.csv      # Locked analytical dataset (N=960)
│   └── analytical_dataset_4y.csv   # 4-year minimum follow-up subset
├── tables/
│   ├── table1.csv
│   ├── cox_univariable.csv
│   ├── cox_adjusted.csv
│   ├── logistic_univariable.csv
│   ├── logistic_adjusted.csv
│   ├── cox_domain_adjusted.csv
│   └── sensitivity_*.csv
├── figures/
│   ├── figure1_flowchart.png/pdf
│   ├── figure2_forest_cox.png/pdf
│   ├── figure3_km_tertiles.png/pdf
│   ├── figure4_domain_forest.png/pdf
│   └── figure5_sensitivity_heatmap.png/pdf
└── logs/
    ├── exclusion_log.csv
    └── exclusion_log.md
```

## Citation

Negida A. Baseline Autonomic Symptoms Predict Cognitive Milestones in Parkinson's Disease: An Item-Level Analysis of SCOPA-AUT in the PPMI. *Clinical Autonomic Research*. 2025.

## License

This code is provided for research reproducibility. PPMI data is subject to its own data use agreement.
