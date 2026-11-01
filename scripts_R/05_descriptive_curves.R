# 05_descriptive_curves.R: cumulative incidence by tertile, numbers at risk, attrition table.
args0 <- commandArgs(trailingOnly = FALSE)
source(file.path(dirname(sub("--file=", "", args0[grep("--file=", args0)])), "common.R"))

cuts <- quantile(d$scopa_total21, c(1 / 3, 2 / 3))
d$tert <- cut(d$scopa_total21, c(-Inf, cuts, Inf), labels = c("Low", "Middle", "High"))
print(cuts); print(table(d$tert))
print(tapply(d$scopa_total21, d$tert, range))

# Aalen-Johansen with death as competing event
d$st <- factor(d$cr_status, 0:2, labels = c("c", "ev", "dth"))
f <- survfit(Surv(cr_time, st) ~ tert, data = d)
s <- summary(f, times = seq(0, 12, by = 0.25), extend = TRUE)
j <- which(f$states == "ev")
cur <- data.frame(tert = sub("tert=", "", s$strata), t = s$time, cif = s$pstate[, j], lo = s$lower[, j], hi = s$upper[, j])
risk <- do.call(rbind, lapply(levels(d$tert), function(g) {
  z <- d[d$tert == g, ]
  data.frame(tert = g, t = 0:12, n = sapply(0:12, function(u) sum(z$cr_time >= u & !(z$cr_time == u & u == 0 & FALSE))))
}))
out(cur, "cif_by_tertile.csv"); out(risk, "risk_by_tertile.csv")
s5 <- summary(f, times = c(5, 8), extend = TRUE)
pt <- data.frame(tert = sub("tert=", "", s5$strata), t = s5$time, cif = s5$pstate[, j], lo = s5$lower[, j], hi = s5$upper[, j])
out(pt, "cif_tertile_points.csv"); print(pt, digits = 3)

# Gray-type comparison through Fine-Gray on tertile
fg <- finegray(Surv(cr_time, st) ~ tert + era2 + PATNO, data = d, etype = "ev", id = PATNO)
m <- coxph(Surv(fgstart, fgstop, fgstatus) ~ tert + strata(era2) + cluster(PATNO), data = fg, weights = fgwt)
sm <- summary(m); print(sm$conf.int, digits = 3)
lrt <- coxph(Surv(t_primary, e_primary) ~ tert + strata(era2), data = d)
ptrend <- summary(lrt)$logtest
res <- data.frame(term = rownames(sm$conf.int), sHR = sm$conf.int[, 1], lo = sm$conf.int[, 3], hi = sm$conf.int[, 4])
out(res, "tertile_shr.csv")
sl <- survdiff(Surv(t_primary, e_primary) ~ tert + strata(era2), data = d)
out(data.frame(chisq = sl$chisq, df = 2, p = pchisq(sl$chisq, 2, lower.tail = FALSE)), "tertile_logrank.csv")

# Follow-up table
tt <- 0:12
att <- data.frame(year = tt,
  at_risk = sapply(tt, function(u) sum(d$t_primary >= u)),
  assessed_any_after = sapply(tt, function(u) sum(d$t_last >= u)),
  cum_events = sapply(tt, function(u) sum(d$e_primary == 1 & d$t_primary <= u)),
  cum_censored = sapply(tt, function(u) sum(d$e_primary == 0 & d$t_primary <= u)))
att$lost_pct <- round(100 * att$cum_censored / nrow(d), 1)
out(att, "attrition_by_year.csv"); print(att)

# Era-specific hazard check and event rates
ep <- c(`0` = "Before 2020", `1` = "2020 onward")
print(aggregate(cbind(e_primary, t_primary) ~ era2, d, function(x) round(sum(x), 1)))
rate <- aggregate(cbind(e_primary, t_primary) ~ era2, d, sum)
rate$per100py <- 100 * rate$e_primary / rate$t_primary
out(rate, "rate_by_era.csv")

# Effect modification by sex and by era for the leading items (exploratory)
ex <- do.call(rbind, lapply(c("SCAU14", "SCAU8", "scopa_total21"), function(x) {
  do.call(rbind, lapply(c("male", "era2"), function(v) {
    f <- as.formula(sprintf("Surv(t_primary, e_primary) ~ %s*%s + %s + strata(era2)", x, v, paste(setdiff(M2, v), collapse = "+")))
    if (v == "era2") f <- as.formula(sprintf("Surv(t_primary, e_primary) ~ %s + %s:era2 + %s + strata(era2)", x, x, paste(M2, collapse = "+")))
    m <- coxph(f, data = d); cf <- summary(m)$coefficients
    rn <- grep(":", rownames(cf), value = TRUE)
    data.frame(exposure = x, by = v, HR_ratio = exp(cf[rn, 1]), p = cf[rn, ncol(cf)])
  }))
}))
out(ex, "interaction_exploratory.csv"); print(ex, digits = 3)
