# R side of experiment B: the official R implementations and sharedimp-r in
# one R session.
#
#   Rscript R/official_umfi.R representations CONFIG SOURCES OUT_DIR
#   Rscript R/official_umfi.R identical       CONFIG SOURCES OUT.csv
#   Rscript R/official_umfi.R importance      CONFIG SOURCES DESIGNS_DIR DESIGN OUT.csv
#   Rscript R/official_umfi.R leak            CONFIG SOURCES OUT.csv
#   Rscript R/official_umfi.R structural      CONFIG SOURCES OUT.json
#   Rscript R/official_umfi.R api             CONFIG SOURCES OUT.json
#
# The official code is read from external/ at the pinned commits (see
# python/sharedimp_exp/official_fetch.py) and evaluated unmodified:
#   official_r  HydroML/UMFI: R/preprocess_lr.R and R/umfi.R are sourced.
#   original_r  joej1997/UMFI: UMFI_extended_code.R is a script that runs the
#               paper's experiments (absolute Windows paths, many packages). It
#               is parsed, and only the first top-level definitions of
#               `modifty_linreg` and `UMFI` are evaluated.

suppressPackageStartupMessages({
  library(sharedimp)
  library(ranger)
})
source(file.path(Sys.getenv("SHAREDIMP_EXP_ROOT"), "R", "common.R"))
args <- commandArgs(trailingOnly = TRUE)
mode <- args[1L]
cfg <- read_json(args[2L])
sources <- read_json(args[3L])$sources
rest <- args[-(1:3)]

official <- new.env()
for (f in c("R/preprocess_lr.R", "R/umfi.R")) {
  sys.source(file.path(exp_root(), sources$official_r$directory, f), envir = official)
}
original <- new.env()
local({
  exprs <- parse(file.path(exp_root(), sources$original_r$directory, "UMFI_extended_code.R"), keep.source = FALSE)
  for (name in c("modifty_linreg", "UMFI")) {
    hit <- Filter(function(e) {
      is.call(e) && identical(e[[1L]], as.name("<-")) && identical(e[[2L]], as.name(name)) &&
        is.call(e[[3L]]) && identical(e[[3L]][[1L]], as.name("function"))
    }, as.list(exprs))
    if (!length(hit)) stop("definition of ", name, " not found in the original script")
    eval(hit[[1L]], envir = original)
  }
})

long_rep <- function(dataset, implementation, representation, anchor, m) {
  m <- as.matrix(m)
  data.frame(
    dataset = dataset, implementation = implementation, representation = representation, anchor = anchor,
    feature = rep(colnames(m), each = nrow(m)), position = rep(seq_len(ncol(m)), each = nrow(m)),
    row = rep(seq_len(nrow(m)), ncol(m)), value = as.vector(m)
  )
}

# ---------------------------------------------------------------- B1, B2
if (mode == "representations") {
  out <- rest[1L]
  dir.create(out, recursive = TRUE, showWarnings = FALSE)
  reps <- list(); gates <- list()
  for (id in unlist(cfg$representation_datasets)) {
    ds <- load_dataset(id)
    x <- ds$x
    for (i in seq_along(x)) {
      anchor <- names(x)[i]
      set.seed(1) # only used by the official noise branches
      off <- official$preprocess_lr(x, i)
      set.seed(1)
      orig <- original$modifty_linreg(x, i)
      reps[[length(reps) + 1L]] <- long_rep(id, "official_r", "full", anchor, off)
      reps[[length(reps) + 1L]] <- long_rep(id, "original_r", "full", anchor, orig)
      b <- build_representations(as.matrix(x), as.matrix(x), anchor = anchor)
      reps[[length(reps) + 1L]] <- long_rep(id, "sharedimp_r", "full", anchor, b$full_train)
      reps[[length(reps) + 1L]] <- long_rep(id, "sharedimp_r", "reduced", anchor, b$reduced_train)
      # the two official dependence tests, recomputed independently of the official code
      for (j in setdiff(seq_along(x), i)) {
        fit <- summary(stats::lm(x[[j]] ~ x[[i]]))
        gates[[length(gates) + 1L]] <- data.frame(
          dataset = id, anchor = anchor, feature = names(x)[j], n = nrow(x),
          p_value = fit$coefficients[2L, 4L], r_squared = fit$r.squared,
          sd_anchor = stats::sd(x[[i]]), sd_feature = stats::sd(x[[j]]),
          # exact comparisons with the data as parsed by R (R and pandas can parse
          # the same decimal text to doubles that differ in the last bit)
          official_r_equals_raw = identical(as.numeric(off[[j]]), x[[j]]),
          original_r_equals_raw = identical(as.numeric(orig[[j]]), x[[j]]),
          official_r_anchor_equals_raw = identical(as.numeric(off[[i]]), x[[i]]),
          original_r_anchor_equals_raw = identical(as.numeric(orig[[i]]), x[[i]]),
          sharedimp_r_anchor_equals_raw = identical(unname(b$full_train[, i]), x[[i]])
        )
      }
    }
  }
  write_csv_exact(do.call(rbind, reps), file.path(out, "representations_r.csv"))
  write_csv_exact(do.call(rbind, gates), file.path(out, "gates.csv"))
}

# ---------------------------------------------------------------- B3
# The official scoring rule (R/umfi.R: two ranger forests with 100 trees,
# out-of-bag R^2 floored at 0, difference, negative values set to 0) applied to
# sharedimp's representation. Same seed and same order of ranger calls as
# umfi(); the official preprocessing draws no random numbers on these data.
official_rule_on <- function(x, y, representation) {
  fi <- rep(0, ncol(x))
  for (i in seq_along(fi)) {
    newX <- representation(x, i)
    rfwith <- ranger::ranger(x = newX, y = y, num.trees = 100)
    rfwithout <- ranger::ranger(x = as.data.frame(as.matrix(newX[, -c(i)], nrow = nrow(newX))), y = y, num.trees = 100)
    fi[i] <- max(rfwith$r.squared, 0) - max(rfwithout$r.squared, 0)
  }
  fi[fi < 0] <- 0
  fi
}
sharedimp_all_rows <- function(x, i) {
  as.data.frame(build_representations(as.matrix(x), as.matrix(x), anchor = names(x)[i])$full_train)
}
if (mode == "identical") {
  ic <- cfg$identical_condition
  rows <- list()
  for (id in c(ic$dataset, ic$contrast_dataset)) {
    ds <- load_dataset(id)
    for (seed in unlist(ic$seeds)) {
      set.seed(seed); off <- official$umfi(ds$x, ds$y, mod_meth = "lr")
      set.seed(seed); orig <- original$UMFI(ds$x, ds$y, mod_meth = "lin")
      set.seed(seed); rep <- official_rule_on(ds$x, ds$y, sharedimp_all_rows)
      rows[[length(rows) + 1L]] <- data.frame(
        language = "r", dataset = id, forest = "random_forest", seed = seed, feature = names(ds$x),
        official = off, original = orig, official_rule_on_sharedimp_representation = rep
      )
    }
  }
  write_csv_exact(do.call(rbind, rows), rest[1L])
}

# ---------------------------------------------------------------- B4, B6
if (mode == "importance") {
  designs_dir <- rest[1L]; design <- rest[2L]
  manifest <- read_json(file.path(designs_dir, "manifest.json"))$datasets
  off_rows <- list(); si_rows <- list()
  for (id in names(manifest)) {
    entry <- manifest[[id]]
    if (!identical(entry$design, design)) next
    ds <- load_dataset(id, designs_dir)
    set.seed(entry$seed); off <- official$umfi(ds$x, ds$y, mod_meth = "lr")
    set.seed(entry$seed); orig <- original$UMFI(ds$x, ds$y, mod_meth = "lin")
    off_rows[[length(off_rows) + 1L]] <- data.frame(
      implementation = rep(c("official_r", "original_r"), each = ncol(ds$x)), dataset = id, design = design,
      seed = entry$seed, forest = "random_forest", feature = names(ds$x), iteration = 0L, importance = c(off, orig)
    )
    for (job in cfg$sharedimp_jobs) {
      res <- shared_importance(ds$x, ds$y, learner = job$learner, metric = job$metric,
                               resamples = ds$fold, seed = entry$seed, on_error = "error")
      si_rows[[length(si_rows) + 1L]] <- cbind(
        implementation = "sharedimp_r", dataset = id, design = design, seed = entry$seed,
        learner = job$learner, metric = job$metric, as.data.frame(res$importance)
      )
    }
    cat(sprintf("[r] %s\n", id))
  }
  write_csv_exact(do.call(rbind, off_rows), rest[3L])
  write_csv_exact(do.call(rbind, si_rows), rest[4L])
}

# ---------------------------------------------------------------- B5b
# OLS + MSE, step by step. `representation(x, train, assess, i)` returns the
# Full representation of the training and of the assessment rows.
manual_importance <- function(x, y, fold, representation) {
  x <- as.matrix(x)
  labels <- sort(unique(fold))
  imp <- matrix(NA_real_, length(labels), ncol(x), dimnames = list(NULL, colnames(x)))
  ols_mse <- function(xtr, ytr, xte, yte) {
    beta <- stats::lm.fit(cbind(1, xtr), ytr)$coefficients
    beta[is.na(beta)] <- 0
    mean((yte - drop(cbind(1, xte) %*% beta))^2)
  }
  for (k in seq_along(labels)) {
    assess <- fold == labels[k]
    for (i in seq_len(ncol(x))) {
      r <- representation(x, !assess, assess, i)
      full <- ols_mse(r$train, y[!assess], r$assess, y[assess])
      reduced <- ols_mse(r$train[, -i, drop = FALSE], y[!assess], r$assess[, -i, drop = FALSE], y[assess])
      imp[k, i] <- reduced - full # score = -MSE, importance = score_full - score_reduced
    }
  }
  colMeans(imp)
}
rep_fold_internal <- function(x, train, assess, i) {
  b <- build_representations(x[train, , drop = FALSE], x[assess, , drop = FALSE], anchor = colnames(x)[i])
  list(train = b$full_train, assess = b$full_assess)
}
rep_all_rows <- function(x, train, assess, i) {
  full <- build_representations(x, x, anchor = colnames(x)[i])$full_train
  list(train = full[train, , drop = FALSE], assess = full[assess, , drop = FALSE])
}
rep_official <- function(x, train, assess, i) {
  full <- as.matrix(official$preprocess_lr(as.data.frame(x), i))
  list(train = full[train, , drop = FALSE], assess = full[assess, , drop = FALSE])
}
if (mode == "leak") {
  lk <- cfg$leak
  rows <- list()
  for (n in unlist(lk$n)) {
    for (seed in seq_len(lk$seeds)) {
      set.seed(1000L * n + seed)
      x1 <- rnorm(n); x2 <- 0.8 * x1 + 0.6 * rnorm(n); x3 <- rnorm(n); x4 <- rnorm(n); x5 <- x3 + 0.1 * rnorm(n)
      y <- 2 * x1 + x3 + rnorm(n)
      x <- cbind(x1 = x1, x2 = x2, x3 = x3, x4 = x4, x5 = x5)
      fold <- sample(rep(seq_len(lk$folds), length.out = n))
      pkg <- shared_importance(x, y, learner = lk$learner, metric = lk$metric, resamples = fold, seed = 1, on_error = "error")
      rows[[length(rows) + 1L]] <- data.frame(
        n = n, seed = seed, feature = colnames(x),
        package = pkg$importance$importance[match(colnames(x), pkg$importance$feature)],
        fold_internal = manual_importance(x, y, fold, rep_fold_internal),
        all_rows = manual_importance(x, y, fold, rep_all_rows),
        all_rows_official_gate = manual_importance(x, y, fold, rep_official)
      )
    }
    cat(sprintf("[r] leak n = %d\n", n))
  }
  write_csv_exact(do.call(rbind, rows), rest[1L])
}

# ---------------------------------------------------------------- B5a
if (mode == "structural") {
  st <- cfg$structural
  ds <- load_dataset(st$dataset)
  x <- as.matrix(ds$x); y <- ds$y
  n <- nrow(x); k <- st$assessment_rows
  assess <- seq_len(n) <= k
  fold <- ifelse(assess, 1L, 2L)
  xp <- x; xp[assess, ] <- 100 * x[assess, ] + 7
  recorded <- function(data) {
    seen <- list()
    lrn <- sharedimp_learner(
      fit = function(x, y) { seen[[length(seen) + 1L]] <<- x; stats::lm.fit(cbind(1, x), y) },
      predict = function(model, x) { b <- model$coefficients; b[is.na(b)] <- 0; drop(cbind(1, x) %*% b) },
      label = "recording OLS"
    )
    shared_importance(data, y, learner = lrn, metric = "mse", resamples = fold, seed = 1, on_error = "error")
    Filter(function(m) nrow(m) == n - k, seen) # fits of the split whose assessment rows were perturbed
  }
  a <- recorded(x); b <- recorded(xp)
  same_layout <- length(a) == length(b) && all(mapply(function(u, v) identical(dim(u), dim(v)), a, b))
  d_sharedimp <- if (same_layout) max(mapply(function(u, v) max(abs(u - v)), a, b)) else NA_real_
  # the same question for the official preprocessing (all rows)
  d_official <- max(vapply(seq_len(ncol(x)), function(i) {
    max(abs(as.matrix(official$preprocess_lr(as.data.frame(x), i))[!assess, -i] -
            as.matrix(official$preprocess_lr(as.data.frame(xp), i))[!assess, -i]))
  }, numeric(1)))
  write_json(list(
    language = "r", dataset = st$dataset, perturbation = st$perturbation, n_train = n - k, n_assessment = k,
    sharedimp_r = list(learner_fits_compared = length(a), same_layout = same_layout,
                       max_abs_diff_training_representation = d_sharedimp,
                       bit_identical = same_layout && all(mapply(identical, a, b))),
    official_r = list(max_abs_diff_training_rows_of_representation = d_official,
                      note = "preprocess_lr() is given all rows, so the residuals of the training rows depend on the assessment rows")
  ), rest[1L])
}

# ---------------------------------------------------------------- B7
if (mode == "api") {
  sig <- function(f) paste(deparse(args(f)), collapse = " ")
  write_json(c(list(
    signatures = list(
      official_r = list(umfi = sig(official$umfi), umfi_par = sig(official$umfi_par), preprocess_lr = sig(official$preprocess_lr)),
      original_r = list(UMFI = sig(original$UMFI), modifty_linreg = sig(original$modifty_linreg)),
      sharedimp_r = list(shared_importance = sig(shared_importance), residualize_fit = sig(residualize_fit),
                         build_representations = sig(build_representations), sharedimp_learner = sig(sharedimp_learner))
    ),
    versions = list(R = R.version.string, ranger = as.character(utils::packageVersion("ranger")),
                    sharedimp = as.character(utils::packageVersion("sharedimp")))
  ), provenance()), rest[1L])
}
