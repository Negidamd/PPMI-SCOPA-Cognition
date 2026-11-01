# 04_prediction.R: out-of-sample prediction comparison. All selection and scaling occur inside folds.
args0 <- commandArgs(trailingOnly = FALSE)
source(file.path(dirname(sub("--file=", "", args0[grep("--file=", args0)])), "common.R"))
suppressPackageStartupMessages({library(glmnet); library(timeROC)})

BASE <- M1
DOMS <- c("dom_gi", "dom_uri", "dom_cv", "dom_therm", "dom_pupil")
EXT <- M2
need <- c("PATNO", "t_primary", "e_primary", EXT, "scopa_total21", DOMS, CORE)
z <- d[complete.cases(d[, need]), need]
cat("Complete-case prediction set N", nrow(z), "events", sum(z$e_primary), "\n")
N <- nrow(z); REPS <- 20; K <- 10
MODELS <- c("Base", "Base + total", "Base + 5 domains", "Base + 21 items (ridge)",
            "Base + LASSO items (1se)", "Base + LASSO items (min)", "Base + items selected by FDR",
            "Base + 3 prior items", "Base + GI domain",
            "Extended base", "Extended base + total", "Extended base + 5 domains")
TAU <- 5

# Breslow cumulative baseline hazard at t, written out so the reference point is the linear predictor itself
surv_at <- function(lp_train, y_train, lp_new, t) {
  tt <- y_train[, 1]; ev <- y_train[, 2]
  et <- sort(unique(tt[ev == 1 & tt <= t]))
  H <- sum(vapply(et, function(u) sum(ev == 1 & tt == u) / sum(exp(lp_train[tt >= u])), numeric(1)))
  exp(-H * exp(lp_new))
}

fit_predict <- function(tr, te, model) {
  ytr <- Surv(tr$t_primary, tr$e_primary)
  cox_lp <- function(vars) {
    f <- as.formula(paste("ytr ~", paste(vars, collapse = "+")))
    m <- coxph(f, data = tr, ties = "efron")
    list(tr = as.vector(as.matrix(tr[, vars]) %*% coef(m)), te = as.vector(as.matrix(te[, vars]) %*% coef(m)))
  }
  if (model == "Base") return(cox_lp(BASE))
  if (model == "Base + total") return(cox_lp(c(BASE, "scopa_total21")))
  if (model == "Base + 5 domains") return(cox_lp(c(BASE, DOMS)))
  if (model == "Base + 3 prior items") return(cox_lp(c(BASE, "SCAU14", "SCAU2", "SCAU6")))
  if (model == "Base + GI domain") return(cox_lp(c(BASE, "dom_gi")))
  if (model == "Extended base") return(cox_lp(EXT))
  if (model == "Extended base + total") return(cox_lp(c(EXT, "scopa_total21")))
  if (model == "Extended base + 5 domains") return(cox_lp(c(EXT, DOMS)))
  if (model == "Base + items selected by FDR") {
    ps <- sapply(CORE, function(x) {
      m <- coxph(as.formula(paste("ytr ~", x, "+", paste(BASE, collapse = "+"))), data = tr, ties = "efron")
      summary(m)$coefficients[x, 5]
    })
    sel <- names(ps)[p.adjust(ps, "BH") < 0.05]
    return(c(cox_lp(c(BASE, sel)), list(sel = sel)))
  }
  vars <- c(BASE, CORE)
  xt <- as.matrix(tr[, vars]); xe <- as.matrix(te[, vars])
  pf <- c(rep(0, length(BASE)), rep(1, length(CORE)))
  a <- if (grepl("ridge", model)) 0 else 1
  cv <- cv.glmnet(xt, Surv(tr$t_primary, tr$e_primary), family = "cox", alpha = a, penalty.factor = pf, nfolds = 5)
  lam <- if (a == 0 || grepl("min", model)) cv$lambda.min else cv$lambda.1se
  b <- as.vector(coef(cv, s = lam))
  out <- list(tr = as.vector(xt %*% b), te = as.vector(xe %*% b))
  if (a == 1) out$sel <- CORE[b[(length(BASE) + 1):length(b)] != 0]
  out
}

set.seed(42)
oof <- array(NA_real_, dim = c(N, length(MODELS), REPS), dimnames = list(NULL, MODELS, NULL))
risk5 <- oof
selcount <- list(lasso = setNames(numeric(21), CORE), lassomin = setNames(numeric(21), CORE), fdr = setNames(numeric(21), CORE))
nsel <- list(lasso = c(), lassomin = c(), fdr = c())
for (r in 1:REPS) {
  fold <- sample(rep(1:K, length.out = N))
  for (k in 1:K) {
    tr <- z[fold != k, ]; te <- z[fold == k, ]
    y <- Surv(tr$t_primary, tr$e_primary)
    for (m in MODELS) {
      p <- fit_predict(tr, te, m)
      oof[fold == k, m, r] <- p$te
      risk5[fold == k, m, r] <- 1 - surv_at(p$tr, y, p$te, TAU)
      if (m == "Base + LASSO items (1se)") {selcount$lasso[p$sel] <- selcount$lasso[p$sel] + 1; nsel$lasso <- c(nsel$lasso, length(p$sel))}
      if (m == "Base + LASSO items (min)") {selcount$lassomin[p$sel] <- selcount$lassomin[p$sel] + 1; nsel$lassomin <- c(nsel$lassomin, length(p$sel))}
      if (m == "Base + items selected by FDR") {selcount$fdr[p$sel] <- selcount$fdr[p$sel] + 1; nsel$fdr <- c(nsel$fdr, length(p$sel))}
    }
  }
  cat("repeat", r, "\n")
}

Y <- Surv(z$t_primary, z$e_primary)
harrell <- function(lp, idx = seq_len(N)) concordance(Y[idx] ~ lp[idx], reverse = TRUE)$concordance
uno <- function(lp, idx = seq_len(N)) concordance(Y[idx] ~ lp[idx], reverse = TRUE, timewt = "n/G2", ymax = TAU)$concordance
G <- survfit(Surv(z$t_primary, 1 - z$e_primary) ~ 1)
Gf <- stepfun(G$time, c(1, G$surv))
Gat <- function(t) Gf(pmin(t, max(G$time)))
brier <- function(risk) {
  surv <- 1 - risk
  ev <- z$t_primary <= TAU & z$e_primary == 1
  alive <- z$t_primary > TAU
  w <- numeric(N)
  w[ev] <- 1 / Gat(z$t_primary[ev]); w[alive] <- 1 / Gat(TAU)
  mean(w * ((as.numeric(alive) - surv)^2))
}
metrics <- list()
for (m in MODELS) for (r in 1:REPS) {
  lp <- oof[, m, r]
  tr3 <- timeROC(z$t_primary, z$e_primary, lp, cause = 1, times = c(3, 5), iid = FALSE, weighting = "marginal")
  metrics[[length(metrics) + 1]] <- data.frame(
    model = m, rep = r, harrell = harrell(lp), uno = uno(lp), auc3 = tr3$AUC[1], auc5 = tr3$AUC[2],
    brier5 = brier(risk5[, m, r]), slope = coef(coxph(Y ~ lp))[1])
}
mt <- rbindlist(metrics)
sumtab <- mt[, .(harrell = mean(harrell), uno = mean(uno), auc3 = mean(auc3), auc5 = mean(auc5),
                 brier5 = mean(brier5), slope = mean(slope)), by = model]
out(mt, "prediction_metrics_reps.csv")
print(sumtab, digits = 4)

# Bootstrap on participants, using the cross-validated predictions averaged across repeats
avg <- apply(oof, c(1, 2), mean)
avg_r <- apply(risk5, c(1, 2), mean)
set.seed(42)
B <- 500
boot <- matrix(NA_real_, B, length(MODELS), dimnames = list(NULL, MODELS))
bootU <- boot
for (b in 1:B) {
  i <- sample.int(N, N, TRUE)
  for (m in MODELS) {boot[b, m] <- harrell(avg[, m], i); bootU[b, m] <- uno(avg[, m], i)}
}
ci <- function(v) quantile(v, c(.025, .975))
ctab <- rbindlist(lapply(MODELS, function(m) {
  ref <- if (grepl("^Extended", m)) "Extended base" else "Base"
  rt <- if (grepl("^Extended", m)) "Extended base + total" else "Base + total"
  dh <- boot[, m] - boot[, ref]; dt <- boot[, m] - boot[, rt]
  data.table(model = m,
             C = harrell(avg[, m]), C_lo = ci(boot[, m])[1], C_hi = ci(boot[, m])[2],
             Uno = uno(avg[, m]), Uno_lo = ci(bootU[, m])[1], Uno_hi = ci(bootU[, m])[2],
             dC_base = harrell(avg[, m]) - harrell(avg[, ref]), dC_lo = ci(dh)[1], dC_hi = ci(dh)[2],
             dC_total = harrell(avg[, m]) - harrell(avg[, rt]), dCt_lo = ci(dt)[1], dCt_hi = ci(dt)[2])
}))
out(ctab, "prediction_C_bootstrap.csv")
print(ctab, digits = 3)

# Calibration at 5 years, quintiles, observed by Kaplan-Meier
cal <- rbindlist(lapply(c("Base", "Base + total", "Base + 5 domains", "Base + 21 items (ridge)", "Extended base + total"), function(m) {
  p <- avg_r[, m]; g <- cut(p, quantile(p, 0:5 / 5), include.lowest = TRUE, labels = FALSE)
  rbindlist(lapply(1:5, function(k) {
    i <- g == k; f <- survfit(Y[i] ~ 1); s <- summary(f, times = TAU, extend = TRUE)
    data.table(model = m, group = k, n = sum(i), pred = mean(p[i]), obs = 1 - s$surv, lo = 1 - s$upper, hi = 1 - s$lower)
  }))
}))
out(cal, "calibration_5y.csv")
print(cal, digits = 3)

selfreq <- data.table(item = CORE, label = LABEL[CORE], lasso1se_cv_pct = 100 * selcount$lasso / (REPS * K),
                      lassomin_cv_pct = 100 * selcount$lassomin / (REPS * K), fdr_cv_pct = 100 * selcount$fdr / (REPS * K))
nselt <- data.table(method = c("lasso_1se", "lasso_min", "fdr"), mean = c(mean(nsel$lasso), mean(nsel$lassomin), mean(nsel$fdr)),
                    min = c(min(nsel$lasso), min(nsel$lassomin), min(nsel$fdr)), max = c(max(nsel$lasso), max(nsel$lassomin), max(nsel$fdr)))
out(nselt, "n_items_selected.csv"); print(nselt)

# LASSO stability on 500 bootstraps of the full data
set.seed(42)
vars <- c(BASE, CORE); X <- as.matrix(z[, vars]); pf <- c(rep(0, 5), rep(1, 21))
hits <- setNames(numeric(21), CORE); signs <- hits
for (b in 1:500) {
  i <- sample.int(N, N, TRUE)
  cv <- cv.glmnet(X[i, ], Y[i], family = "cox", alpha = 1, penalty.factor = pf, nfolds = 5)
  bb <- as.vector(coef(cv, s = "lambda.min"))[6:26]
  hits <- hits + (bb != 0); signs <- signs + sign(bb)
  if (b %% 100 == 0) cat("boot", b, "\n")
}
selfreq$lasso_boot_pct <- 100 * hits / 500
selfreq$lasso_boot_positive_pct <- ifelse(hits > 0, 100 * (signs + hits) / (2 * hits), NA)
out(selfreq[order(-lasso_boot_pct)], "lasso_selection.csv")
print(selfreq[order(-lasso_boot_pct)], digits = 3)
