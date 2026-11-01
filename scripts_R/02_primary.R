# 02_primary.R: item, domain and total models for every endpoint; assumptions; item vs rest score.
args0 <- commandArgs(trailingOnly = FALSE)
source(file.path(dirname(sub("--file=", "", args0[grep("--file=", args0)])), "common.R"))

ENDPOINTS <- c("primary", "strict", "neuropsych", "m10", "m11", "m12", "m13", "m14", "m15")
cat("N", nrow(d), "events", sum(d$e_primary), "\n")

# Item models ---------------------------------------------------------------
res <- list()
for (ep in ENDPOINTS) for (mn in c("M0", "M1", "M2")) {
  covs <- switch(mn, M0 = "male", M1 = M1, M2 = M2)
  tab <- do.call(rbind, lapply(ITEMS, function(x) {
    if (mn == "M0") {
      s <- sex_of_item(x); dat <- if (!is.na(s)) d[d$male == s, ] else d
      m <- coxph(as.formula(sprintf("Surv(t_%s, e_%s) ~ %s + strata(era2)", ep, ep, x)), data = dat, ties = "efron")
      cf <- summary(m)
      return(data.frame(exposure = x, HR = cf$conf.int[1, 1], lo = cf$conf.int[1, 3], hi = cf$conf.int[1, 4],
                        p = cf$coefficients[1, 5], N = m$n, events = m$nevent))
    }
    fit_one(x, covs, paste0("t_", ep), paste0("e_", ep))
  }))
  tab <- add_q(tab); tab$endpoint <- ep; tab$model <- mn
  res[[paste(ep, mn)]] <- tab
}
items <- do.call(rbind, res)
items$label <- LABEL[items$exposure]; items$domain <- DOMAIN[items$exposure]
out(items, "cox_items_all.csv")

# Domain and total ----------------------------------------------------------
d$dom_sex_m <- rowSums(d[, c("SCAU22", "SCAU23")]); d$dom_sex_m[d$male != 1] <- NA
d$dom_sex_f <- rowSums(d[, c("SCAU24", "SCAU25")]); d$dom_sex_f[d$male != 0] <- NA
d$scopa_total23 <- ifelse(d$male == 1, d$scopa_total21 + d$dom_sex_m, d$scopa_total21 + d$dom_sex_f)
SC <- c(dom_gi = "Gastrointestinal", dom_uri = "Urinary", dom_cv = "Cardiovascular",
        dom_therm = "Thermoregulatory", dom_pupil = "Pupillomotor",
        scopa_total21 = "SCOPA-AUT total (21 items)")
dres <- list()
for (ep in ENDPOINTS) for (mn in c("M1", "M2")) {
  covs <- if (mn == "M1") M1 else M2
  rows <- list()
  for (x in names(SC)) {
    r <- fit_one(x, covs, paste0("t_", ep), paste0("e_", ep))
    sdv <- sd(d[[x]], na.rm = TRUE)
    z <- d; z$.x <- d[[x]] / sdv
    r2 <- fit_one(".x", covs, paste0("t_", ep), paste0("e_", ep), data = z)
    r$HR_sd <- r2$HR; r$lo_sd <- r2$lo; r$hi_sd <- r2$hi; r$sd <- sdv
    rows[[x]] <- r
  }
  for (x in c("dom_sex_m", "dom_sex_f")) {
    s <- ifelse(x == "dom_sex_m", 1, 0)
    z <- d[d$male == s & !is.na(d[[x]]), ]
    f <- as.formula(sprintf("Surv(t_%s, e_%s) ~ %s + %s + strata(era2)", ep, ep, x, paste(setdiff(covs, "male"), collapse = "+")))
    m <- coxph(f, data = z, ties = "efron"); sm <- summary(m)
    sdv <- sd(z[[x]])
    rows[[x]] <- data.frame(exposure = x, HR = sm$conf.int[x, 1], lo = sm$conf.int[x, 3], hi = sm$conf.int[x, 4],
                            p = sm$coefficients[x, 5], N = m$n, events = m$nevent,
                            HR_sd = sm$conf.int[x, 1]^sdv, lo_sd = sm$conf.int[x, 3]^sdv, hi_sd = sm$conf.int[x, 4]^sdv, sd = sdv)
  }
  tab <- do.call(rbind, rows)
  idx <- tab$exposure != "scopa_total21"
  tab$q <- NA; tab$q[idx] <- p.adjust(tab$p[idx], "BH")
  tab$endpoint <- ep; tab$model <- mn; dres[[paste(ep, mn)]] <- tab
}
dom <- do.call(rbind, dres)
dom$label <- ifelse(dom$exposure %in% names(SC), SC[dom$exposure], ifelse(dom$exposure == "dom_sex_m", "Sexual, men", "Sexual, women"))
out(dom, "cox_domains_all.csv")

# 23-item total as sensitivity
z <- d[!is.na(d$scopa_total23), ]
r23 <- fit_one("scopa_total23", M2, "t_primary", "e_primary", data = z)
r23M1 <- fit_one("scopa_total23", M1, "t_primary", "e_primary", data = z)
out(rbind(cbind(r23, model = "M2"), cbind(r23M1, model = "M1")), "cox_total23.csv")

# Item vs rest score (primary and strict) -----------------------------------
lrres <- list()
for (ep in c("primary", "strict")) {
  rows <- lapply(CORE, function(x) {
    z <- d; rest <- setdiff(CORE, x)
    z$.rest <- rowMeans(z[, rest], na.rm = TRUE) * length(rest)
    keep <- complete.cases(z[, c(x, ".rest", M2)])
    z <- z[keep, ]
    fb <- as.formula(sprintf("Surv(t_%s, e_%s) ~ .rest + %s + strata(era2)", ep, ep, paste(M2, collapse = "+")))
    m0 <- coxph(fb, data = z, ties = "efron")
    m1 <- update(m0, as.formula(sprintf(". ~ . + %s", x)))
    lr <- 2 * (m1$loglik[2] - m0$loglik[2])
    sm <- summary(m1)
    data.frame(exposure = x, LR = lr, p = pchisq(lr, 1, lower.tail = FALSE),
               HR = sm$conf.int[x, 1], lo = sm$conf.int[x, 3], hi = sm$conf.int[x, 4], N = m1$n, events = m1$nevent)
  })
  tab <- add_q(do.call(rbind, rows)); tab$endpoint <- ep; lrres[[ep]] <- tab
}
lrt <- do.call(rbind, lrres); lrt$label <- LABEL[lrt$exposure]
out(lrt, "item_vs_rest_LR.csv")

# All 21 items together -----------------------------------------------------
for (ep in c("primary", "strict")) {
  z <- d[complete.cases(d[, c(CORE, M2)]), ]
  f <- as.formula(sprintf("Surv(t_%s, e_%s) ~ %s + %s + strata(era2)", ep, ep, paste(CORE, collapse = "+"), paste(M2, collapse = "+")))
  m <- coxph(f, data = z, ties = "efron"); sm <- summary(m)
  r <- data.frame(exposure = CORE, label = LABEL[CORE], HR = sm$conf.int[CORE, 1], lo = sm$conf.int[CORE, 3],
                  hi = sm$conf.int[CORE, 4], p = sm$coefficients[CORE, 5], N = m$n, events = m$nevent)
  m0 <- coxph(as.formula(sprintf("Surv(t_%s, e_%s) ~ %s + strata(era2)", ep, ep, paste(M2, collapse = "+"))), data = z, ties = "efron")
  lr <- 2 * (m$loglik[2] - m0$loglik[2])
  cat(ep, "joint 21-item LR", round(lr, 1), "df 21 p", signif(pchisq(lr, 21, lower.tail = FALSE), 3), "\n")
  r$q <- p.adjust(r$p, "BH"); r$joint_LR <- lr; r$joint_p <- pchisq(lr, 21, lower.tail = FALSE)
  out(r, sprintf("joint_21items_%s.csv", ep))
}

# Correlation among items
cm <- cor(d[, CORE], method = "spearman", use = "pairwise.complete.obs")
out(as.data.table(cm, keep.rownames = "item"), "item_spearman.csv")

# Proportional hazards -------------------------------------------------------
ph <- do.call(rbind, lapply(ITEMS, function(x) {
  s <- sex_of_item(x); dat <- if (!is.na(s)) d[d$male == s, ] else d
  cv <- if (!is.na(s)) setdiff(M2, "male") else M2
  m <- coxph(as.formula(sprintf("Surv(t_primary, e_primary) ~ %s + %s + strata(era2)", x, paste(cv, collapse = "+"))), data = dat, ties = "efron")
  z <- cox.zph(m, transform = "km")
  data.frame(exposure = x, ph_p_item = z$table[x, "p"], ph_p_global = z$table["GLOBAL", "p"])
}))
ph$label <- LABEL[ph$exposure]
out(ph, "ph_tests.csv")

# Period-specific HR at 3 years for items with PH p<0.05
vi <- ph$exposure[ph$ph_p_item < 0.05]
if (length(vi)) {
  sp <- survSplit(Surv(t_primary, e_primary) ~ ., data = d, cut = 3, episode = "per")
  rows <- lapply(vi, function(x) {
    s <- sex_of_item(x); dat <- if (!is.na(s)) sp[sp$male == s, ] else sp
    cv <- if (!is.na(s)) setdiff(M2, "male") else M2
    f <- as.formula(sprintf("Surv(tstart, t_primary, e_primary) ~ %s:strata(per) + %s + strata(era2)", x, paste(cv, collapse = "+")))
    m <- coxph(f, data = dat, ties = "efron"); sm <- summary(m)
    rn <- grep(x, rownames(sm$conf.int), value = TRUE)
    data.frame(exposure = x, period = c("<3 y", ">=3 y"), HR = sm$conf.int[rn, 1], lo = sm$conf.int[rn, 3], hi = sm$conf.int[rn, 4])
  })
  out(do.call(rbind, rows), "ph_period_hrs.csv")
}

# Linearity: item categories 0, 1, 2 or 3
catres <- list()
for (ep in c("primary", "strict")) for (x in ITEMS) {
  sx <- sex_of_item(x); z <- if (!is.na(sx)) d[d$male == sx, ] else d
  cv <- if (!is.na(sx)) setdiff(M2, "male") else M2
  z$.c <- factor(ifelse(z[[x]] >= 2, 2, z[[x]]), levels = 0:2, labels = c("0", "1", "2or3"))
  m <- coxph(as.formula(sprintf("Surv(t_%s, e_%s) ~ .c + %s + strata(era2)", ep, ep, paste(cv, collapse = "+"))), data = z, ties = "efron")
  sm <- summary(m)
  catres[[paste(ep, x)]] <- data.frame(endpoint = ep, exposure = x, n1 = sum(z$.c == "1", na.rm = TRUE), n2 = sum(z$.c == "2or3", na.rm = TRUE),
    HR1 = sm$conf.int[".c1", 1], lo1 = sm$conf.int[".c1", 3], hi1 = sm$conf.int[".c1", 4],
    HR2 = sm$conf.int[".c2or3", 1], lo2 = sm$conf.int[".c2or3", 3], hi2 = sm$conf.int[".c2or3", 4])
}
out(do.call(rbind, catres), "item_categories.csv")

# Baseline follow-up summaries
rkm <- survfit(Surv(t_last, 1 - e_primary) ~ 1, data = d)
fu <- data.frame(median_fu_reverse_km = summary(rkm)$table["median"], q1 = summary(rkm)$table["0.95LCL"], q3 = summary(rkm)$table["0.95UCL"])
qs <- quantile(rkm, probs = c(.25, .5, .75))
fu2 <- data.frame(p25 = qs$quantile[1], p50 = qs$quantile[2], p75 = qs$quantile[3], max_t = max(d$t_last))
out(fu2, "followup.csv")
fu_era <- do.call(rbind, lapply(0:1, function(e) {
  z <- d[d$era2 == e, ]; q <- quantile(survfit(Surv(t_last, 1 - e_primary) ~ 1, data = z), probs = c(.25, .5, .75))
  data.frame(era2 = e, p25 = q$quantile[1], p50 = q$quantile[2], p75 = q$quantile[3])
}))
out(fu_era, "followup_by_era.csv")
km <- survfit(Surv(t_primary, e_primary) ~ 1, data = d)
s <- summary(km, times = c(1, 3, 5, 8, 10), extend = TRUE)
out(data.frame(t = s$time, cuminc = 1 - s$surv, lo = 1 - s$upper, hi = 1 - s$lower, n_risk = s$n.risk), "km_overall.csv")

cat("\nPrimary, Model 2, q<0.05:\n")
p <- items[items$endpoint == "primary" & items$model == "M2", ]
print(p[order(p$p), c("exposure", "label", "HR", "lo", "hi", "p", "q", "N", "events")], digits = 3, row.names = FALSE)
cat("\nStrict, Model 2:\n")
p <- items[items$endpoint == "strict" & items$model == "M2", ]
print(p[order(p$p), c("exposure", "label", "HR", "lo", "hi", "p", "q", "N", "events")][1:10, ], digits = 3, row.names = FALSE)
cat("\nDomains, primary Model 2:\n")
print(dom[dom$endpoint == "primary" & dom$model == "M2", c("label", "HR", "lo", "hi", "HR_sd", "p", "q", "N", "events")], digits = 3, row.names = FALSE)
print(lrt[lrt$endpoint == "primary", c("exposure", "label", "LR", "p", "q")][order(lrt$p[lrt$endpoint == "primary"])[1:6], ], digits = 3, row.names = FALSE)
print(ph[ph$ph_p_item < 0.05, ], digits = 3)
print(fu2)
sessionInfo()
