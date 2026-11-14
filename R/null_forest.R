# Null-design forest study, R side (one design and one variant per call).
#
#   Rscript R/null_forest.R config/04c_null_forest.json results/raw/04c_null_forest/r null_p5 baseline
#
# Writes <out>/<design>__<variant>.csv and .meta.json with the columns of
# python/sharedimp_exp/null_forest.py. Representations come from sharedimp's
# build_representations(), fitted on the training rows of the split. ranger is
# called directly with the settings of the built-in "rand_forest" learner
# (500 trees, min.node.size = 5, mtry = floor(sqrt(q)), 1 thread), so that
# single settings can be changed.

suppressPackageStartupMessages({
  library(sharedimp)
  library(ranger)
})
source(file.path(Sys.getenv("SHAREDIMP_EXP_ROOT"), "R", "common.R"))
args <- commandArgs(trailingOnly = TRUE)
cfg <- read_json(args[1L]); out <- args[2L]; design <- args[3L]; variant <- args[4L]
dir.create(out, recursive = TRUE, showWarnings = FALSE)

s <- cfg$baseline[setdiff(names(cfg$baseline), c("r", "python", "note"))]
s$node <- cfg$baseline$r
change <- cfg$variants[[variant]]$change
for (k in names(change)) {
  if (k %in% c("r", "python")) { if (k == "r") s$node <- change[[k]] } else s[k] <- list(change[[k]])
}
mtry_of <- function(rule, q, p) switch(rule, sqrt = max(1L, floor(sqrt(q))), as_full = max(1L, floor(sqrt(p))), all = q, one = 1L)

entry <- read_json(file.path(exp_root(), "data", "null_forest", "manifest.json"))$designs[[design]]
path <- file.path(exp_root(), "data", "null_forest", entry$file)
if (!identical(sha256_file(path), entry$sha256)) stop("sha256 of the data file differs from the manifest")
data <- utils::read.csv(path)
feats <- unlist(entry$features); p <- entry$p
t0 <- proc.time()[["elapsed"]]
rows <- list()
for (d in sort(unique(data$dataset))) {
  df <- data[data$dataset == d, ]
  x <- as.matrix(df[, feats]); y <- df$y; z <- df$z; fold <- df$fold
  for (f in sort(unique(fold))) {
    tr <- fold != f; te <- fold == f
    null_mse <- mean((y[te] - mean(y[tr]))^2)
    for (a in seq_len(p)) {
      b <- build_representations(x[tr, , drop = FALSE], x[te, , drop = FALSE], anchor = feats[a])
      reps <- list(list(b$full_train, b$full_assess), list(b$reduced_train, b$reduced_assess))
      padded <- list(cbind(b$reduced_train, z = z[tr]), cbind(b$reduced_assess, z = z[te]))
      if (identical(s$representation, "padded_reduced")) reps[[2L]] <- padded
      if (identical(s$representation, "placebo_full")) reps[[1L]] <- padded
      mse <- numeric(2); cand <- integer(2)
      for (m in 1:2) {
        A <- reps[[m]][[1L]]; B <- reps[[m]][[2L]]; q <- ncol(A)
        if (identical(s$learner, "ols")) {
          cand[m] <- q
          coef <- stats::lm.fit(cbind(1, A), y[tr])$coefficients
          pred <- drop(cbind(1, B) %*% coef)
        } else {
          cand[m] <- as.integer(mtry_of(s$mtry, q, p))
          fit <- ranger(x = A, y = y[tr], num.trees = s$trees, mtry = cand[m], min.node.size = s$node[["min.node.size"]],
                        min.bucket = s$node[["min.bucket"]], max.depth = s$max_depth, replace = isTRUE(s$bootstrap), sample.fraction = 1,
                        num.threads = 1, seed = 100000 * d + 1000 * f + 10 * a + (m - 1))
          pred <- predict(fit, data = B, num.threads = 1)$predictions
        }
        mse[m] <- mean((y[te] - pred)^2)
      }
      rows[[length(rows) + 1L]] <- data.frame(
        design = design, variant = variant, dataset = d, fold = f, anchor = feats[a], columns_full = ncol(reps[[1L]][[1L]]),
        columns_reduced = ncol(reps[[2L]][[1L]]), candidates_full = cand[1L], candidates_reduced = cand[2L],
        mse_full = mse[1L], mse_reduced = mse[2L], mse_null_model = null_mse
      )
    }
  }
}
write_csv_exact(do.call(rbind, rows), file.path(out, sprintf("%s__%s.csv", design, variant)))
secs <- proc.time()[["elapsed"]] - t0
write_json(c(list(language = "r", status = "ok", design = design, variant = variant, settings = s, data_sha256 = entry$sha256, seconds = secs,
                  ranger_version = as.character(utils::packageVersion("ranger")),
                  sharedimp_version = as.character(utils::packageVersion("sharedimp")),
                  threads = as.integer(Sys.getenv("SHAREDIMP_EXP_THREADS", "1"))), provenance()),
           file.path(out, sprintf("%s__%s.meta.json", design, variant)))
cat(sprintf("[r] %s %s: %d rows, %.0f s\n", design, variant, length(rows), secs))
