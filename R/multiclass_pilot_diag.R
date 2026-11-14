# Pilot of criterion E9 (docs/experiment_plan.md, section 5d): R side of the diagnosis.
#
#   Rscript R/multiclass_pilot_diag.R results/raw/04a_multiclass_pilot/diag
#
# For every model exported by python -m sharedimp_exp.multiclass_pilot check
# (cells.json, <id>.train.csv, <id>.test.csv) fit multinomial logistic
# regression exactly as the built-in "linear" learner of sharedimp does for
# three or more classes (nnet::multinom(maxit = 500)) and write the class
# probabilities of the assessment rows (<id>.prob_r.csv) and the convergence
# code (<id>.r.json).
source(file.path(Sys.getenv("SHAREDIMP_EXP_ROOT", "."), "R", "common.R"))
dir <- commandArgs(trailingOnly = TRUE)[1L]
cells <- read_json(file.path(dir, "cells.json"))$cells
for (cell in cells) {
  train <- utils::read.csv(file.path(dir, paste0(cell$id, ".train.csv")))
  test <- utils::read.csv(file.path(dir, paste0(cell$id, ".test.csv")))
  train$y <- factor(train$y)
  fit <- nnet::multinom(y ~ ., data = train, maxit = 500, trace = FALSE)
  prob <- stats::predict(fit, newdata = test, type = "probs")
  write_csv_exact(as.data.frame(prob), file.path(dir, paste0(cell$id, ".prob_r.csv")))
  writeLines(sprintf('{"convergence": %d, "iterations_limit": 500}', fit$convergence), file.path(dir, paste0(cell$id, ".r.json")))
}
writeLines(sprintf('{"cells": %d}', length(cells)), file.path(dir, "r_done.json"))
cat("[multiclass_pilot_diag]", length(cells), "model(s)\n")
