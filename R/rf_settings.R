# Random-forest settings study, R side (ranger). See config/02b_rf_settings.json.
#
#   Rscript R/rf_settings.R config/02b_rf_settings.json results/raw/02b_rf_settings/r
#
# Writes single_tree.csv, single_tree_predictions.csv, bootstrap_counting.csv, forest.csv,
# forest_importance.csv and meta.json.

suppressPackageStartupMessages({
  library(sharedimp)
  library(ranger)
  library(parsnip)
})
source(file.path(Sys.getenv("SHAREDIMP_EXP_ROOT"), "R", "common.R"))
args <- commandArgs(trailingOnly = TRUE)
cfg <- read_json(args[1L])
out <- args[2L]
dir.create(out, recursive = TRUE, showWarnings = FALSE)
threads <- as.integer(Sys.getenv("SHAREDIMP_EXP_THREADS", "1"))

# leaves and depth of every tree of a ranger forest (root has depth 0)
tree_shape <- function(forest) {
  t(vapply(forest$child.nodeIDs, function(ch) {
    left <- ch[[1L]]; right <- ch[[2L]]
    depth <- integer(length(left))
    for (node in seq_along(left)) {            # children always have larger ids
      if (left[node] != 0L) depth[c(left[node], right[node]) + 1L] <- depth[node] + 1L
    }
    c(leaves = sum(left == 0L), depth = max(depth))
  }, numeric(2)))
}

fit_ranger <- function(x, y, setting, task, ...) {
  ranger(
    x = x, y = y, min.node.size = setting[["min.node.size"]], min.bucket = setting[["min.bucket"]],
    probability = task != "regression", num.threads = threads, ...
  )
}
predict_value <- function(fit, x, task) {
  p <- predict(fit, data = x)$predictions
  if (task == "regression") p else p[, "b"]
}

tree_rows <- list(); pred_rows <- list(); count_rows <- list(); forest_rows <- list(); imp_rows <- list()
for (id in unlist(cfg$datasets)) {
  ds <- load_dataset(id)
  task <- if (is.factor(ds$y)) "classification" else "regression"
  test <- ds$fold == cfg$test_fold
  xtr <- ds$x[!test, , drop = FALSE]; ytr <- ds$y[!test]; xte <- ds$x[test, , drop = FALSE]; yte <- ds$y[test]

  # Part 1: one deterministic tree (all rows once, every feature a candidate)
  for (name in names(cfg$single_tree$r)) {
    fit <- fit_ranger(xtr, ytr, cfg$single_tree$r[[name]], task,
                      num.trees = 1, mtry = ncol(xtr), replace = FALSE, sample.fraction = 1, seed = 1)
    shape <- tree_shape(fit$forest)
    tree_rows[[length(tree_rows) + 1L]] <- data.frame(dataset = id, setting = name, leaves = shape[1L, "leaves"], depth = shape[1L, "depth"])
    pred_rows[[length(pred_rows) + 1L]] <- data.frame(
      dataset = id, setting = name, part = rep(c("train", "test"), c(sum(!test), sum(test))),
      row = c(which(!test), which(test)), prediction = c(predict_value(fit, xtr, task), predict_value(fit, xte, task))
    )
  }

  # Part 2: how is the terminal-node minimum counted under bootstrap sampling?
  bc <- cfg$bootstrap_counting
  fit <- fit_ranger(xtr, ytr, bc$r, task, num.trees = bc$trees, seed = bc$seed, keep.inbag = TRUE)
  nodes <- predict(fit, data = xtr, type = "terminalNodes")$predictions
  per_tree <- t(vapply(seq_len(bc$trees), function(k) {
    inbag <- fit$inbag.counts[[k]]
    c(draws = min(tapply(inbag[inbag > 0], nodes[inbag > 0, k], sum)), distinct = min(table(nodes[inbag > 0, k])))
  }, numeric(2)))
  count_rows[[length(count_rows) + 1L]] <- data.frame(
    dataset = id, trees = bc$trees, smallest_leaf_in_draws = min(per_tree[, "draws"]),
    smallest_leaf_in_distinct_rows = min(per_tree[, "distinct"])
  )

  # Part 3: forests as used
  for (name in names(cfg$forest$r)) {
    setting <- cfg$forest$r[[name]]
    spec <- set_engine(
      rand_forest(mode = task, trees = cfg$forest$trees, min_n = setting[["min.node.size"]]),
      "ranger", min.bucket = setting[["min.bucket"]]
    )
    for (seed in unlist(cfg$forest$seeds)) {
      fit <- fit_ranger(xtr, ytr, setting, task, num.trees = cfg$forest$trees, seed = seed)
      shape <- tree_shape(fit$forest)
      p <- predict_value(fit, xte, task)
      score <- if (task == "regression") mean((yte - p)^2) else {
        q <- pmin(pmax(p, 1e-15), 1 - 1e-15); -mean(ifelse(yte == "b", log(q), log(1 - q)))
      }
      t0 <- proc.time()[["elapsed"]]
      res <- shared_importance(ds$x, ds$y, learner = spec, metric = cfg$forest$metric[[task]],
                               resamples = ds$fold, seed = seed, on_error = "error")
      forest_rows[[length(forest_rows) + 1L]] <- data.frame(
        dataset = id, setting = name, seed = seed, mtry = fit$mtry,
        mean_leaves = mean(shape[, "leaves"]), mean_depth = mean(shape[, "depth"]), max_depth = max(shape[, "depth"]),
        test_metric = cfg$forest$metric[[task]], test_score = score,
        importance_seconds = proc.time()[["elapsed"]] - t0
      )
      imp_rows[[length(imp_rows) + 1L]] <- cbind(dataset = id, setting = name, seed = seed, as.data.frame(res$importance))
      cat(sprintf("[r] %s %s seed %d\n", id, name, seed))
    }
  }
}
write_csv_exact(do.call(rbind, tree_rows), file.path(out, "single_tree.csv"))
write_csv_exact(do.call(rbind, pred_rows), file.path(out, "single_tree_predictions.csv"))
write_csv_exact(do.call(rbind, count_rows), file.path(out, "bootstrap_counting.csv"))
write_csv_exact(do.call(rbind, forest_rows), file.path(out, "forest.csv"))
write_csv_exact(do.call(rbind, imp_rows), file.path(out, "forest_importance.csv"))
write_json(c(list(language = "r", status = "ok", config = args[1L],
                  ranger_version = as.character(utils::packageVersion("ranger")),
                  parsnip_version = as.character(utils::packageVersion("parsnip")),
                  sharedimp_version = as.character(utils::packageVersion("sharedimp")),
                  threads = threads), provenance()), file.path(out, "meta.json"))
