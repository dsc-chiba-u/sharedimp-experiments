# Run shared_importance() for every job of a job file (R side).
#
#   Rscript R/run_jobs.R config/01_smoke_jobs.json results/raw/01_environment/r
#
# For each job three files are written: <id>.importance.csv, <id>.folds.csv
# and <id>.meta.json. Any failure makes the process exit with a non-zero
# status after the remaining jobs have run; a failed job leaves a meta file
# with "status": "failed" and no result tables.

suppressPackageStartupMessages(library(sharedimp))
source(file.path(Sys.getenv("SHAREDIMP_EXP_ROOT"), "R", "common.R"))

args <- commandArgs(trailingOnly = TRUE)
jobs_file <- args[1L]
out <- args[2L]
dir.create(out, recursive = TRUE, showWarnings = FALSE)

manifest_path <- Sys.getenv("SHAREDIMP_INSTALL_MANIFEST", "")
manifest <- if (nzchar(manifest_path) && file.exists(manifest_path)) read_json(manifest_path) else list()
provenance <- list(
  jobs_file = jobs_file,
  sharedimp_version = as.character(utils::packageVersion("sharedimp")),
  sharedimp_commit = manifest$sharedimp_r$commit,
  threads = as.integer(Sys.getenv("SHAREDIMP_EXP_THREADS", "1")),
  run_at_utc = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
)

run_job <- function(job) {
  meta <- c(list(job = job, language = "r", status = "failed"), provenance)
  paths <- file.path(out, paste0(job$id, c(".importance.csv", ".folds.csv", ".meta.json")))
  caught <- character()
  result <- tryCatch(
    withCallingHandlers(
      {
        ds <- load_dataset(job$dataset)
        t0 <- proc.time()[["elapsed"]]
        res <- shared_importance(
          ds$x, ds$y,
          learner = job$learner, metric = job$metric,
          resamples = ds$fold, seed = job$seed, on_error = "error"
        )
        elapsed <- proc.time()[["elapsed"]] - t0
        list(ds = ds, res = res, elapsed = elapsed)
      },
      warning = function(w) {
        caught <<- c(caught, conditionMessage(w))
        invokeRestart("muffleWarning")
      }
    ),
    error = function(e) e
  )
  if (inherits(result, "error")) {
    meta$error <- conditionMessage(result)
    unlink(paths[1:2])
  } else {
    res <- result$res
    labels <- sort(unique(result$ds$fold))
    folds <- as.data.frame(fold_results(res))
    folds <- cbind(folds[, 1:2], fold = labels[folds$split], folds[, -(1:2)])
    write_csv_exact(res$importance, paths[1L])
    write_csv_exact(folds, paths[2L])
    meta$status <- "ok"
    meta <- c(meta, list(
      dataset_sha256 = result$ds$sha256,
      task = res$task,
      learner_description = paste(format(res$learner), collapse = " "),
      metric = paste(format(res$metric$name), collapse = " "),
      n = res$n, p = res$p, n_splits = length(labels),
      elapsed_seconds = result$elapsed,
      warnings = as.list(caught)
    ))
  }
  write_json(meta, paths[3L])
  cat(sprintf("[r] %s: %s%s\n", job$id, meta$status, if (meta$status != "ok") sprintf(" (%s)", meta$error) else ""))
  identical(meta$status, "ok")
}

ok <- vapply(read_json(jobs_file)$jobs, run_job, logical(1))
quit(status = if (all(ok)) 0L else 1L)
