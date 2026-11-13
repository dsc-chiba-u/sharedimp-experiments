# Record the R side of the environment as JSON.
#   Rscript R/env_info.R results/raw/01_environment/r.json
# Exit status 1 if the process does not run inside the image pinned in
# config/pins.env.
source(file.path(Sys.getenv("SHAREDIMP_EXP_ROOT"), "R", "common.R"))
`%||%` <- function(a, b) if (is.null(a)) b else a
out <- commandArgs(trailingOnly = TRUE)[1L]
pkgs <- c("sharedimp", "parsnip", "rsample", "yardstick", "ranger", "rlang", "tibble", "nnet", "jsonlite", "ggplot2")
ver <- function(p) if (requireNamespace(p, quietly = TRUE)) as.character(utils::packageVersion(p)) else NA_character_
prov <- provenance()
os_release <- if (file.exists("/etc/os-release")) readLines("/etc/os-release") else character()
os_name <- gsub('^PRETTY_NAME=|"', "", grep("^PRETTY_NAME=", os_release, value = TRUE))
si <- utils::sessionInfo()
envs <- c("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "R_RANGER_NUM_THREADS", "SHAREDIMP_EXP_THREADS")
info <- list(
  language = "r",
  r_version = R.version.string,
  platform = R.version$platform,
  running = si$running,
  executable = file.path(R.home("bin"), "R"),
  sharedimp = list(version = ver("sharedimp"), commit = prov$sharedimp_commit),
  container = prov$container,
  pinned_image = pinned_image(),
  in_pinned_image = prov$in_pinned_image,
  os = if (length(os_name)) os_name[1L] else NULL,
  packages = as.list(stats::setNames(vapply(pkgs, ver, character(1)), pkgs)),
  blas = si$BLAS, lapack = si$LAPACK, la_library = La_library(), lapack_version = La_version(), matprod = si$matprod,
  ext_soft = as.list(extSoftVersion()[c("BLAS")]),
  logical_cpus = parallel::detectCores(logical = TRUE),
  physical_cpus = parallel::detectCores(logical = FALSE),
  thread_env = as.list(Sys.getenv(envs, unset = NA)),
  locale = Sys.getlocale("LC_COLLATE"),
  rng_kind = as.list(RNGkind())
)
write_json(info, out)
cat(sprintf("[r] %s | sharedimp %s (%s)\n", R.version.string, info$sharedimp$version, substr(info$sharedimp$commit %||% "unknown", 1, 7)))
if (!prov$in_pinned_image) {
  message("[r] ERROR not running inside the pinned image ", pinned_image())
  quit(status = 1L)
}
