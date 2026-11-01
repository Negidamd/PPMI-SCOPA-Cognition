# common.R: shared definitions. Every R script sources this file.
suppressPackageStartupMessages({library(survival); library(data.table)})
set.seed(42)
args <- commandArgs(trailingOnly = FALSE)
script <- sub("--file=", "", args[grep("--file=", args)])
PROJ <- normalizePath(file.path(dirname(script), ".."))
EXPECTED_N <- 1339L
EXPECTED_EVENTS <- 349L
d <- fread(file.path(PROJ, "data", "analytical_dataset.csv"), data.table = FALSE)
stopifnot(nrow(d) == EXPECTED_N, sum(d$e_primary) == EXPECTED_EVENTS)

d$ledd100 <- d$ledd / 100
M1 <- c("age", "male", "edu", "moca", "updrs3")
M2 <- c(M1, "hy", "schwab", "dis_dur", "ledd100", "rbdsq", "gds15",
        "antihypertensive", "alpha_blocker", "anticholinergic", "genetic_enrolled")
ITEMS <- paste0("SCAU", 1:25)
CORE <- paste0("SCAU", 1:21)
LABEL <- c(
  SCAU1 = "Swallowing or choking", SCAU2 = "Saliva dribbling", SCAU3 = "Food sticking in throat",
  SCAU4 = "Early fullness", SCAU5 = "Constipation", SCAU6 = "Straining at stool",
  SCAU7 = "Fecal incontinence", SCAU8 = "Urinary urgency", SCAU9 = "Urinary incontinence",
  SCAU10 = "Incomplete emptying", SCAU11 = "Weak urinary stream", SCAU12 = "Urinary frequency",
  SCAU13 = "Nocturia", SCAU14 = "Lightheaded on standing up", SCAU15 = "Lightheaded after standing a while",
  SCAU16 = "Syncope", SCAU17 = "Sweating, day", SCAU18 = "Sweating, night",
  SCAU19 = "Oversensitive to bright light", SCAU20 = "Cold intolerance", SCAU21 = "Heat intolerance",
  SCAU22 = "Erection problems (men)", SCAU23 = "Ejaculation problems (men)",
  SCAU24 = "Vaginal dryness (women)", SCAU25 = "Orgasm problems (women)")
DOMAIN <- c(rep("Gastrointestinal", 7), rep("Urinary", 6), rep("Cardiovascular", 3),
            "Thermoregulatory", "Thermoregulatory", "Pupillomotor", "Thermoregulatory",
            "Thermoregulatory", rep("Sexual", 4))
names(DOMAIN) <- ITEMS
sex_of_item <- function(x) if (x %in% c("SCAU22", "SCAU23")) 1L else if (x %in% c("SCAU24", "SCAU25")) 0L else NA

# Fit one exposure in one Cox model. Sexual items run within the relevant sex.
fit_one <- function(x, covs, tvar, evar, data = d, weights = NULL, xname = x) {
  s <- sex_of_item(xname)
  dat <- if (!is.na(s)) data[data$male == s, ] else data
  cv <- if (!is.na(s)) setdiff(covs, "male") else covs
  f <- as.formula(sprintf("Surv(%s, %s) ~ %s + %s + strata(era2)", tvar, evar, x, paste(cv, collapse = " + ")))
  m <- coxph(f, data = dat, ties = "efron")
  cf <- summary(m)$coefficients
  ci <- summary(m)$conf.int
  data.frame(exposure = xname, HR = ci[x, "exp(coef)"], lo = ci[x, "lower .95"], hi = ci[x, "upper .95"],
             p = cf[x, "Pr(>|z|)"], N = m$n, events = m$nevent, stringsAsFactors = FALSE)
}

add_q <- function(tab) {tab$q <- p.adjust(tab$p, "BH"); tab}
out <- function(x, name) fwrite(x, file.path(PROJ, "outputs", name))
