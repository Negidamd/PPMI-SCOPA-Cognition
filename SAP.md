# Statistical analysis plan (rebuild)

Fixed on 2026-10-31 before any rebuilt model was fit. This plan is **not blind**: the author and analyst have seen earlier results from the same cohort (preprint and R1). The paper must say so. This is a corrected reanalysis, not a preregistered study.

## Question
Which baseline SCOPA-AUT symptoms are associated with time to first cognition-domain progression milestone in PD, and does item-level information predict better than the total score?

## Data
PPMI, freeze 22 April 2026, raw CRF files only (`data/raw`, SHA-256 in `data/raw_manifest_sha256.txt`). No derived master file is used. `DataPrep_April2026_v2_timefix` is used only as an independent cross-check.

## Cohort
Assigned to the PD cohort, enrolled, with a baseline visit. Baseline SCOPA-AUT with at most 2 of 21 non-sexual items missing. Baseline MoCA (BL, or SC when BL absent). Free of all six cognition milestones at baseline. At least one post-baseline outcome assessment. Every exclusion is logged with its reason. Exclusions never use sexual items.

## Time
Time zero is the baseline SCOPA-AUT month. Time is calendar months from INFODT divided by 12, checked against AGE_AT_VISIT differences. Censoring is at the last assessment of any outcome instrument. Each single milestone uses the last assessment of its own instrument.

## Exposure
SCAU1-25, 0-3, per 1-point higher. Labels and domains per Visser 2004:
GI 1-7; urinary 8-13; cardiovascular 14-16; thermoregulatory 17, 18, 20, 21; pupillomotor 19; sexual 22-23 (men), 24-25 (women).
Code 9: "use catheter" on urinary items is missing (sensitivity: scored 3); "not applicable" on sexual items is missing.
Sexual items are modeled in the relevant sex only, among those who answered.
Primary total: SCAU1-21, 0-63, prorated when 1-2 items are missing. Domain scores prorated when at most one item is missing and the domain has at least 4 items, otherwise complete. Domains are also reported per 1 SD so they can be compared.

## Outcomes (Brumm 2023, Table 1)
m10 MoCA <21; m11 MDS-UPDRS 1.1 >=3; m12 1.2 >=3; m13 1.5 >=3; m14 investigator PD dementia (COGSTATE=3); m15 impairment in >=2 of 4 cognitive domains (test >=1.5 SD below norm: T <=35, scaled <=5.5; a domain is impaired if any test in it is impaired) and investigator-reported functional impairment (FNCDTCOG=1).
Domains: memory (HVLT-R total recall, recognition discrimination), visuospatial (JLO), processing speed (SDMT), executive/working memory (LNS, semantic fluency).
- **Primary:** first of m10-m15 (Ahmed's recorded choice on 2026-05-14).
- **Key secondary:** strict cognitive endpoint, first of m10, m14, m15, with its own time.
- **Secondary:** each milestone alone, own time, own at-risk set. Neuropsychiatric endpoint m12 or m13.

## Models
Cox, Efron ties, stratified by era (enrolled before 2020 vs 2020 onward) because visit schedules differ. One model per item.
- **Model 1 (basic):** age, sex, education, MoCA, MDS-UPDRS III.
- **Model 2 (primary):** Model 1 + H&Y, Schwab-England, disease duration, baseline LEDD (dose active at the baseline month), RBDSQ, GDS-15, antihypertensive, alpha-blocker, anticholinergic, genetic-cohort enrollment.
Sex is dropped in sex-restricted models. MDS-UPDRS III: untreated exam, else OFF, else ON (state recorded).
BH-FDR across the 25 items, within each endpoint and model. Significance q<0.05. A result is "supported" only if q<0.05 in Model 2; Model 1 is reported beside it.
Item vs total: LR test of item added to Model 2 + rest score (total minus that item). BH across 21 items.
Domain and total: Model 2.
Item overlap: Spearman matrix, and all 21 items entered jointly in one model with Model 2 covariates.
Assumptions: Schoenfeld tests (Model 2), and for any item with p<0.05, HR by follow-up period. Linearity: item categories (0, 1, >=2).
Missing covariates: complete case; 20-fold MI (chained equations with event and cumulative hazard) as sensitivity.

## Prediction
Base prognostic model: age, sex, education, MoCA, MDS-UPDRS III. Added: total; 5 domains; 21 items (ridge); LASSO items. Repeated 10-fold CV (20 repeats), all selection and scaling inside folds. Metrics: Harrell C, Uno C, time-dependent AUC at 3 and 5 y, Brier at 5 y, calibration slope and observed vs predicted at 5 y using Kaplan-Meier within groups. Paired difference with percentile interval across a 500-replicate bootstrap (optimism-corrected). LASSO selection frequency across 500 bootstraps.

## Sensitivity (primary endpoint, Model 2)
1. Fine-Gray with death as competing event (R `cmprsk`/`survival::finegray`).
2. Interval-censored, discrete-time cloglog model with the same covariates.
3. Sustained milestone: met again at next assessment, or last assessment.
4. Events in the first 2 years excluded (landmark, reverse causation).
5. Baseline MoCA >=26. 6. Baseline MoCA >=23.
7. De novo: sporadic, untreated at baseline, disease duration <=2 y.
8. SAA-positive.
9. IPCW for dropout.
10. MI for covariates.
11. Added genetics (LRRK2, GBA, APOE e4).
12. Added baseline MDS-UPDRS 1.1, 1.2, 1.5.
13. Annual and scheduled-visit outcomes only.
14. Catheter scored 3.
15. Any vs none for each item.
Included vs excluded participants compared.

## Verification
Primary estimates fit in both Python (lifelines) and R (survival). Cohort and milestone flags compared participant by participant with the independent timefix build. Each discrepancy explained. Every number in the manuscript traced to an output file by script.
