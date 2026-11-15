# R survey cross-check for M3 (docs/milestones/M3_estimators.md item 4).
# Usage: Rscript tests/r_survey_check.R <element.csv> <cluster.csv> <out.csv>
# element.csv columns: stratum, N_h, w, y_<p>, x_<p>; cluster.csv adds psu and uses M_h (PSUs per stratum).
suppressMessages(library(survey))
args <- commandArgs(trailingOnly = TRUE)
params <- c("OA", "UA_2", "PA_4")
run <- function(d, design_label, ids, fpc) {
  des <- svydesign(ids = ids, strata = ~stratum, fpc = fpc, weights = ~w, data = d)
  out <- NULL
  for (p in params) {
    r <- svyratio(as.formula(paste0("~y_", p)), as.formula(paste0("~x_", p)), des)
    out <- rbind(out, data.frame(design = design_label, parameter = p,
                                 estimate = as.numeric(coef(r)), se = as.numeric(SE(r))))
  }
  out
}
e <- read.csv(args[1])
c <- read.csv(args[2])
res <- rbind(run(e, "element", ~1, ~N_h), run(c, "cluster", ~psu, ~M_h))
write.csv(res, args[3], row.names = FALSE)
