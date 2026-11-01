# 03_sensitivity.R: pre-specified sensitivity analyses of the primary endpoint under Model 2.
args0 <- commandArgs(trailingOnly = FALSE)
source(file.path(dirname(sub("--file=", "", args0[grep("--file=", args0)])), "common.R"))
suppressPackageStartupMessages(library(mice))

EXPO <- c(ITEMS, "scopa_total21")
d$dropout <- as.integer(d$e_primary == 0 & d$ENROLL_STATUS %in% c("Withdrew", "Withdraw Deceased", "Lost to follow-up", "Baseline Withdraw"))
res <- list()
store <- function(name, tab) {
  it <- tab$exposure %in% ITEMS
  tab$q <- NA; tab$q[it] <- p.adjust(tab$p[it], "BH")
  tab$analysis <- name; res[[name]] <<- tab
  cat(sprintf("%-28s N=%d ev=%d  SCAU14 HR %.2f  total HR %.3f  q<.05: %s\n", name,
              max(tab$N), max(tab$events), tab$HR[tab$exposure == "SCAU14"], tab$HR[tab$exposure == "scopa_total21"],
              paste(tab$exposure[which(tab$q < 0.05)], collapse = " ")))
}
run_cox <- function(data = d, tv = "t_primary", ev = "e_primary", covs = M2, expo = EXPO) {
  do.call(rbind, lapply(expo, function(x) fit_one(x, covs, tv, ev, data = data)))
}

store("Main analysis", run_cox())

# 1. Fine-Gray, death competing
dd <- d
dd$st <- factor(dd$cr_status, 0:2, labels = c("cens", "event", "death"))
keep <- c("PATNO", "cr_time", "st", "era2", M2, EXPO)
fgfit <- function(x) {
  s <- sex_of_item(x)
  sub <- if (!is.na(s)) dd[dd$male == s, keep] else dd[, keep]
  cv <- if (!is.na(s)) setdiff(M2, "male") else M2
  sub <- sub[complete.cases(sub[, c(x, cv)]), ]
  fg <- finegray(Surv(cr_time, st) ~ . + strata(era2), data = sub, etype = "event", id = PATNO)
  f <- as.formula(sprintf("Surv(fgstart, fgstop, fgstatus) ~ %s + %s + strata(era2) + cluster(PATNO)", x, paste(cv, collapse = "+")))
  m <- coxph(f, data = fg, weights = fgwt, ties = "efron")
  sm <- summary(m)
  data.frame(exposure = x, HR = sm$conf.int[x, 1], lo = sm$conf.int[x, 3], hi = sm$conf.int[x, 4],
             p = sm$coefficients[x, ncol(sm$coefficients)], N = nrow(sub), events = sum(sub$st == "event"))
}
store("Fine-Gray, death competing", do.call(rbind, lapply(EXPO, fgfit)))

# 2a. Interval-censored Weibull regression on the last negative and first positive assessment
icw <- function(x) {
  s <- sex_of_item(x)
  sub <- if (!is.na(s)) d[d$male == s, ] else d
  cv <- if (!is.na(s)) setdiff(M2, "male") else M2
  sub <- sub[complete.cases(sub[, c(x, cv, "era2")]), ]
  sub$L_ <- ifelse(sub$e_primary == 1, ifelse(sub$tl_primary > 0, sub$tl_primary, NA), sub$t_primary)
  sub$R_ <- ifelse(sub$e_primary == 1, sub$t_primary, NA)
  m <- survreg(as.formula(sprintf("Surv(L_, R_, type = 'interval2') ~ %s + era2 + %s", x, paste(cv, collapse = "+"))), data = sub, dist = "weibull")
  b <- coef(m)[x]; ls <- log(m$scale); V <- vcov(m)[c(x, "Log(scale)"), c(x, "Log(scale)")]
  g <- c(-exp(-ls), b * exp(-ls)); lhr <- -b * exp(-ls); se <- sqrt(as.numeric(t(g) %*% V %*% g))
  data.frame(exposure = x, HR = exp(lhr), lo = exp(lhr - 1.96 * se), hi = exp(lhr + 1.96 * se), p = 2 * pnorm(-abs(lhr / se)), N = nrow(sub), events = sum(sub$e_primary))
}
store("Interval-censored Weibull", do.call(rbind, lapply(EXPO, icw)))

# 2b. Discrete-time complementary log-log, annual bins
pp <- rbindlist(lapply(seq_len(nrow(d)), function(i) {
  k <- ceiling(d$t_primary[i] * 12 / 12)
  k <- max(k, 1)
  data.table(idx = i, bin = 1:k, y = c(rep(0L, k - 1), d$e_primary[i]))
}))
pp <- cbind(pp, as.data.table(d[pp$idx, c("era2", M2, ITEMS, "scopa_total21")]))
pp$binf <- factor(pmin(pp$bin, 10))
cloglog <- function(x) {
  s <- sex_of_item(x)
  sub <- if (!is.na(s)) pp[pp$male == s, ] else pp
  cv <- if (!is.na(s)) setdiff(M2, "male") else M2
  f <- as.formula(sprintf("y ~ binf + era2 + %s + %s", x, paste(cv, collapse = "+")))
  m <- glm(f, data = sub, family = binomial("cloglog"))
  b <- coef(summary(m))[x, ]
  data.frame(exposure = x, HR = exp(b[1]), lo = exp(b[1] - 1.96 * b[2]), hi = exp(b[1] + 1.96 * b[2]), p = b[4],
             N = length(unique(sub$idx[complete.cases(as.data.frame(sub)[, c(x, cv)])])),
             events = sum(sub$y[complete.cases(as.data.frame(sub)[, c(x, cv)])]))
}
store("Discrete-time annual model", do.call(rbind, lapply(EXPO, cloglog)))

# 3. Sustained milestone
store("Sustained milestone", run_cox(tv = "t_sustained", ev = "e_sustained"))

# 4. Landmark at 2 years
lm <- d[d$t_primary > 2, ]; lm$t_lm <- lm$t_primary - 2
store("Landmark at 2 years", run_cox(data = lm, tv = "t_lm"))

# 5-6. Baseline MoCA restrictions
store("Baseline MoCA >=26", run_cox(data = d[d$moca >= 26, ]))
store("Baseline MoCA >=23", run_cox(data = d[d$moca >= 23, ]))

# 7. De novo: sporadic, untreated, diagnosed within 2 years
dn <- d[d$genetic_enrolled == 0 & d$treated_bl == 0 & d$dis_dur <= 2, ]
store("De novo sporadic untreated", run_cox(data = dn, covs = setdiff(M2, c("ledd100", "genetic_enrolled"))))

# 8. SAA positive
store("SAA positive", run_cox(data = d[which(d$saa == 1), ]))

# 9. IPCW for dropout
base <- d[complete.cases(d[, c(M2, "scopa_total21")]), ]
cf <- as.formula(sprintf("Surv(t_primary, dropout) ~ scopa_total21 + %s + strata(era2)", paste(M2, collapse = "+")))
cm <- coxph(cf, data = base, ties = "efron")
cm0 <- coxph(Surv(t_primary, dropout) ~ strata(era2), data = base, ties = "efron")
sp <- survSplit(Surv(t_primary, e_primary) ~ ., data = base, cut = 1:15, episode = "ep")
H <- function(m, centered) {
  b <- basehaz(m, centered = centered); b <- b[order(b$strata, b$time), ]
  split(b, b$strata)
}
hc <- H(cm, FALSE); h0 <- H(cm0, FALSE)
hval <- function(tb, s, t) {
  x <- tb[[paste0("era2=", s)]]
  i <- findInterval(t, x$time); ifelse(i == 0, 0, x$hazard[pmax(i, 1)])
}
lpm <- as.vector(as.matrix(sp[, names(coef(cm))]) %*% coef(cm))
sp$Hc <- 0; sp$H0 <- 0
for (s in 0:1) {
  idx <- sp$era2 == s
  sp$Hc[idx] <- hval(hc, s, sp$tstart[idx]); sp$H0[idx] <- hval(h0, s, sp$tstart[idx])
}
sp$w <- exp(-sp$H0) / exp(-sp$Hc * exp(lpm))
q <- quantile(sp$w, c(.01, .99)); sp$w <- pmin(pmax(sp$w, q[1]), q[2])
cat("IPCW weights: ", round(summary(sp$w), 3), "\n")
ipcw <- function(x) {
  s <- sex_of_item(x)
  sub <- if (!is.na(s)) sp[sp$male == s, ] else sp
  cv <- if (!is.na(s)) setdiff(M2, "male") else M2
  f <- as.formula(sprintf("Surv(tstart, t_primary, e_primary) ~ %s + %s + strata(era2) + cluster(PATNO)", x, paste(cv, collapse = "+")))
  m <- coxph(f, data = sub, weights = w, ties = "efron"); sm <- summary(m)
  data.frame(exposure = x, HR = sm$conf.int[x, 1], lo = sm$conf.int[x, 3], hi = sm$conf.int[x, 4],
             p = sm$coefficients[x, ncol(sm$coefficients)], N = length(unique(sub$PATNO[!is.na(sub[[x]])])), events = m$nevent)
}
store("IPCW for dropout", do.call(rbind, lapply(EXPO, ipcw)))

# 10. Multiple imputation of covariates
d$na_haz <- nelsonaalen(d, t_primary, e_primary)
mv <- c(M2, "scopa_total21", "e_primary", "na_haz")
imp <- mice(d[, mv], m = 20, maxit = 10, method = "pmm", seed = 42, printFlag = FALSE)
miff <- function(x) {
  s <- sex_of_item(x)
  cv <- if (!is.na(s)) setdiff(M2, "male") else M2
  bs <- vs <- numeric(20); n <- ev <- 0
  for (i in 1:20) {
    z <- cbind(complete(imp, i)[, M2], d[, c("t_primary", "e_primary", "era2", ITEMS)])
    if (x == "scopa_total21") z$scopa_total21 <- d$scopa_total21
    if (!is.na(s)) z <- z[d$male == s, ]
    m <- coxph(as.formula(sprintf("Surv(t_primary, e_primary) ~ %s + %s + strata(era2)", x, paste(cv, collapse = "+"))), data = z, ties = "efron")
    bs[i] <- coef(m)[x]; vs[i] <- vcov(m)[x, x]; n <- m$n; ev <- m$nevent
  }
  qb <- mean(bs); u <- mean(vs); b <- var(bs); tv <- u + (1 + 1 / 20) * b
  z <- qb / sqrt(tv)
  data.frame(exposure = x, HR = exp(qb), lo = exp(qb - 1.96 * sqrt(tv)), hi = exp(qb + 1.96 * sqrt(tv)), p = 2 * pnorm(-abs(z)), N = n, events = ev)
}
store("Multiple imputation", do.call(rbind, lapply(EXPO, miff)))

# 11. Genetics
store("Added LRRK2, GBA, APOE e4", run_cox(covs = c(M2, "lrrk2_carrier", "gba_carrier", "apoe4")))

# 12. Baseline MDS-UPDRS 1.1, 1.2, 1.5
store("Added baseline UPDRS 1.1, 1.2, 1.5", run_cox(covs = c(M2, "np1cog_bl", "np1hall_bl", "np1apat_bl")))

# 13. Scheduled visits only
store("Scheduled visits only", run_cox(tv = "t_primary_sched", ev = "e_primary_sched"))

# 14. Catheter scored 3
z <- fread(file.path(PROJ, "data", "analytical_dataset_cath3.csv"), data.table = FALSE)
z$ledd100 <- z$ledd / 100
cat("Catheter cohort N", nrow(z), "catheter users", sum(z$catheter_any), "\n")
store("Catheter scored 3", run_cox(data = z))

# 14b. Last research diagnosis idiopathic PD
store("Last research diagnosis idiopathic PD", run_cox(data = d[which(d$last_dx_ipd == 1), ]))

# 15. Any vs none
z <- d
for (x in ITEMS) z[[x]] <- as.integer(z[[x]] > 0)
z$scopa_total21 <- d$scopa_total21
store("Any vs none", run_cox(data = z))

# Extra requested by the audit: Model 2 without GDS-15, and without each adjustment block
store("Model 2 without GDS-15", run_cox(covs = setdiff(M2, "gds15")))
store("Model 2 without RBDSQ", run_cox(covs = setdiff(M2, "rbdsq")))
store("Model 2 without function (H&Y, S&E)", run_cox(covs = setdiff(M2, c("hy", "schwab"))))

all <- do.call(rbind, res)
all$label <- ifelse(all$exposure == "scopa_total21", "SCOPA-AUT total (21 items)", LABEL[all$exposure])
out(all, "sensitivity_all.csv")

# Cumulative incidence with death as competing event, overall and by tertile
fit <- survfit(Surv(cr_time, factor(cr_status, 0:2, labels = c("c", "ev", "dth"))) ~ 1, data = d)
sm <- summary(fit, times = c(3, 5, 8, 10), extend = TRUE)
cif <- data.frame(t = sm$time, cif_event = sm$pstate[, which(fit$states == "ev")], lo = sm$lower[, which(fit$states == "ev")],
                  hi = sm$upper[, which(fit$states == "ev")], cif_death = sm$pstate[, which(fit$states == "dth")])
out(cif, "cif_overall.csv")
print(cif, digits = 3)
print(table(d$cr_status))
