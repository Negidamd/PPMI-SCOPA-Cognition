# 07_posthoc.R: checks not in the SAP, labeled post hoc in the paper.
# (a) lightheadedness on standing with measured orthostatic blood pressure in the model
# (b) stability of urinary urgency on the strict cognitive endpoint
args0 <- commandArgs(trailingOnly = FALSE)
source(file.path(dirname(sub("--file=", "", args0[grep("--file=", args0)])), "common.R"))

rows <- list()
add <- function(lbl, x, cv, tv, ev, data = d) {
  r <- fit_one(x, cv, tv, ev, data = data); r$analysis <- lbl; rows[[length(rows) + 1]] <<- r
}
z <- d[!is.na(d$sbp_drop), ]
add("Primary, Model 2, measured BP sample", "SCAU14", M2, "t_primary", "e_primary", z)
add("Primary, Model 2 + orthostatic SBP and DBP drop", "SCAU14", c(M2, "sbp_drop", "dbp_drop"), "t_primary", "e_primary", z)
add("Primary, Model 2 + orthostatic hypotension (yes/no)", "SCAU14", c(M2, "oh_bl"), "t_primary", "e_primary", z)
add("Primary, Model 2: orthostatic hypotension (yes/no) as exposure", "oh_bl", M2, "t_primary", "e_primary", z)
add("Primary, Model 2: SBP drop per 10 mmHg", "sbp10", M2, "t_primary", "e_primary", transform(z, sbp10 = sbp_drop / 10))
tab14 <- table(lightheaded = d$SCAU14 > 0, oh = d$oh_bl)
print(tab14); print(prop.table(tab14, 2), digits = 3)

ev <- "e_strict"; tv <- "t_strict"
add("Strict, Model 2", "SCAU8", M2, tv, ev)
add("Strict, Model 1", "SCAU8", M1, tv, ev)
add("Strict, without GDS-15", "SCAU8", setdiff(M2, "gds15"), tv, ev)
add("Strict, without RBDSQ", "SCAU8", setdiff(M2, "rbdsq"), tv, ev)
add("Strict, baseline MoCA >=26", "SCAU8", M2, tv, ev, d[d$moca >= 26, ])
add("Strict, de novo sporadic untreated", "SCAU8", setdiff(M2, c("ledd100", "genetic_enrolled")), tv, ev,
    d[d$genetic_enrolled == 0 & d$ledd == 0 & d$dis_dur <= 2, ])
add("Strict, SAA positive", "SCAU8", M2, tv, ev, d[which(d$saa == 1), ])
add("Strict, men", "SCAU8", setdiff(M2, "male"), tv, ev, d[d$male == 1, ])
add("Strict, women", "SCAU8", setdiff(M2, "male"), tv, ev, d[d$male == 0, ])
add("Strict, no alpha-blocker or anticholinergic", "SCAU8", setdiff(M2, c("alpha_blocker", "anticholinergic")), tv, ev,
    d[d$alpha_blocker == 0 & d$anticholinergic == 0, ])
lm2 <- d[d$t_strict > 2, ]; lm2$t_lm <- lm2$t_strict - 2
add("Strict, landmark at 2 years", "SCAU8", M2, "t_lm", ev, lm2)
add("Strict, lightheaded on standing up, Model 2", "SCAU14", M2, tv, ev)

add("Strict, no last research diagnosis other than idiopathic PD", "SCAU8", M2, tv, ev, d[which(d$last_dx_ipd == 1), ])
r <- do.call(rbind, rows); out(r, "posthoc_checks.csv")
ix <- do.call(rbind, lapply(c("male", "era2"), function(v) {
  f <- if (v == "male") sprintf("Surv(t_strict, e_strict) ~ SCAU8*male + %s + strata(era2)", paste(setdiff(M2, "male"), collapse = "+"))
       else sprintf("Surv(t_strict, e_strict) ~ SCAU8 + SCAU8:era2 + %s + strata(era2)", paste(M2, collapse = "+"))
  cf <- summary(coxph(as.formula(f), data = d))$coefficients; rn <- grep(":", rownames(cf), value = TRUE)
  data.frame(exposure = "SCAU8_strict", by = v, HR_ratio = exp(cf[rn, 1]), p = cf[rn, ncol(cf)])
}))
out(ix, "interaction_strict.csv")
print(r[, c("analysis", "exposure", "HR", "lo", "hi", "p", "N", "events")], digits = 3, row.names = FALSE)
