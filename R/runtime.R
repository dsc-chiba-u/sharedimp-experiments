# Runtime benchmark, R side: one process per learner (experiment D).
#
#   Rscript R/runtime.R config/05_runtime.json <plan.csv> <out dir> <learner> <pilot|main>
#
# Reads the rows of the plan for language "r" and the learner and writes
#   <out>/r_<learner>.runs.csv        one row per run (warm-up and timed)
#   <out>/r_<learner>.cells.csv       one row per cell: status, reason
#   <out>/r_<learner>.importance.csv  importances of the last timed run of every measured cell
#   <out>/r_<learner>.meta.json       versions, BLAS, CPU, threads, container, wall time
# Timed region: the shared_importance() call only. Timer: proc.time() elapsed
# (resolution 1 ms on this system).

suppressPackageStartupMessages(library(sharedimp))
source(file.path(Sys.getenv("SHAREDIMP_EXP_ROOT"), "R", "common.R"))
args <- commandArgs(trailingOnly = TRUE)
cfg <- read_json(args[1L]); plan <- utils::read.csv(args[2L], stringsAsFactors = FALSE)
out <- args[3L]; learner <- args[4L]; mode <- args[5L]
dir.create(out, recursive = TRUE, showWarnings = FALSE)
started <- proc.time()[["elapsed"]]
started_utc <- format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
plan <- plan[plan$language == "r" & plan$learner == learner, ]
plan <- plan[order(plan$predicted_seconds, plan$n, plan$p, plan$v), ]
if (!nrow(plan)) stop(sprintf("no cells for r/%s in %s", learner, args[2L]))
manifest <- read_json(file.path(exp_root(), "data", "runtime", "manifest.json"))$files
loadavg <- function() as.numeric(strsplit(readLines("/proc/loadavg", n = 1L), " ")[[1L]][1L])

load_cell <- function(row) {
  entry <- manifest[[row$data]]
  path <- file.path(exp_root(), "data", "runtime", entry$file)
  digest <- sha256_file(path)
  if (!identical(digest, entry$sha256)) stop(sprintf("%s: sha256 differs from the manifest", path))
  df <- utils::read.csv(path)
  list(x = df[, unlist(entry$features), drop = FALSE], y = df$y, fold = as.integer(df[[row$fold_column]]), sha256 = digest)
}
timed_call <- function(d, lrn = learner) {
  invisible(gc(FALSE))
  t0 <- proc.time()[["elapsed"]]
  res <- shared_importance(d$x, d$y, learner = lrn, metric = cfg$data$metric, resamples = d$fold, seed = 1, on_error = "error")
  list(seconds = proc.time()[["elapsed"]] - t0, res = res)
}

runs <- list(); cells <- list(); imps <- list()
add_run <- function(row, kind, rep, seconds, load_before) {
  runs[[length(runs) + 1L]] <<- data.frame(language = "r", learner = learner, cell = row$cell, n = row$n, p = row$p, v = row$v,
                                           kind = kind, run = rep, seconds = seconds, loadavg_1min_before = load_before)
}
add_cell <- function(row, status, reason = "", sha = NA_character_, timed = 0L) {
  cells[[length(cells) + 1L]] <<- data.frame(language = "r", learner = learner, cell = row$cell, n = row$n, p = row$p, v = row$v,
                                             status = status, reason = reason, timed_runs = timed, predicted_seconds = row$predicted_seconds,
                                             data = row$data, fold_column = row$fold_column, data_sha256 = sha)
  cat(sprintf("[r/%s] %s: %s %s\n", learner, row$cell, status, reason))
}
keep_importance <- function(row, res) {
  imps[[length(imps) + 1L]] <<- cbind(language = "r", learner = learner, cell = row$cell, as.data.frame(res$importance))
}

n_warm <- cfg$protocol$warmup_runs; n_timed <- if (mode == "pilot") 1L else cfg$protocol$timed_runs
fit_count <- NULL
for (k in seq_len(nrow(plan))) {
  row <- plan[k, ]
  if (row$status != "run") { add_cell(row, row$status, "per-cell cap of the plan"); next }
  if (mode == "main" && proc.time()[["elapsed"]] - started > 1.25 * row$process_planned_seconds) {
    add_cell(row, "skipped (budget, process allowance)", sprintf("process had used more than 1.25 x %.0f s", row$process_planned_seconds)); next
  }
  result <- tryCatch({
    d <- load_cell(row)
    if (mode == "main" || k == 1L) {
      for (w in seq_len(n_warm)) { l <- loadavg(); r <- timed_call(d); add_run(row, "warmup", w, r$seconds, l) }
      if (mode == "main" && (n_warm + n_timed) * r$seconds > cfg$budget$abort_factor * row$cap_seconds) {
        add_cell(row, "skipped (budget, after warm-up)", sprintf("warm-up run took %.1f s", r$seconds), d$sha256)
        next
      }
    }
    for (i in seq_len(n_timed)) { l <- loadavg(); r <- timed_call(d); add_run(row, "timed", i, r$seconds, l) }
    keep_importance(row, r$res)
    add_cell(row, "measured", "", d$sha256, n_timed)
  }, error = function(e) add_cell(row, "failed", conditionMessage(e)))
}
if (mode == "pilot" && learner == "linear") {
  # how often is the learner fitted in one call? (counting OLS learner)
  fc <- cfg$pilot$fit_count_cell
  d <- load_cell(list(data = sprintf("rt_n%d_p%d", fc$n, fc$p), fold_column = sprintf("fold_v%d", fc$v)))
  count <- 0L
  counting <- sharedimp_learner(
    fit = function(x, y) { count <<- count + 1L; list(coef = stats::lm.fit(cbind(1, as.matrix(x)), y)$coefficients) },
    predict = function(model, x) drop(cbind(1, as.matrix(x)) %*% model$coef), label = "counting OLS"
  )
  invisible(timed_call(d, counting))
  fit_count <- list(n = fc$n, p = fc$p, v = fc$v, fits = count, expected = 2L * fc$p * fc$v)
}

prefix <- file.path(out, paste0("r_", learner))
write_csv_exact(do.call(rbind, runs), paste0(prefix, ".runs.csv"))
write_csv_exact(do.call(rbind, cells), paste0(prefix, ".cells.csv"))
write_csv_exact(if (length(imps)) do.call(rbind, imps) else data.frame(), paste0(prefix, ".importance.csv"))
ver <- function(p) if (requireNamespace(p, quietly = TRUE)) as.character(utils::packageVersion(p)) else NA_character_
cpu <- grep("^model name", readLines("/proc/cpuinfo"), value = TRUE)
envs <- c("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "R_RANGER_NUM_THREADS", "SHAREDIMP_EXP_THREADS")
write_json(c(list(
  language = "r", learner = learner, mode = mode, status = "ok", learner_description = cfg$learners[[learner]]$r,
  plan = args[2L], started_utc = started_utc, process_seconds = proc.time()[["elapsed"]] - started,
  timer = "proc.time() elapsed, resolution 1 ms",
  r_version = R.version.string,
  packages = list(sharedimp = ver("sharedimp"), parsnip = ver("parsnip"), ranger = ver("ranger"), rsample = ver("rsample"), yardstick = ver("yardstick")),
  blas = extSoftVersion()[["BLAS"]], la_library = La_library(), lapack_version = La_version(),
  cpu = sub("^model name\\s*:\\s*", "", cpu[1L]), logical_cpus = length(cpu),
  threads = as.integer(Sys.getenv("SHAREDIMP_EXP_THREADS", "1")), thread_env = as.list(Sys.getenv(envs, unset = NA)),
  loadavg_1min_end = loadavg(), fit_count = fit_count
), provenance()), paste0(prefix, ".meta.json"))
