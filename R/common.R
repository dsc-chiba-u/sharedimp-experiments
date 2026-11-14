# Paths, dataset loading and exact CSV/JSON output shared by the R scripts.
# Sourced, not a package. Mirrors python/sharedimp_exp/common.py.

exp_root <- function() {
  root <- Sys.getenv("SHAREDIMP_EXP_ROOT", "")
  if (!nzchar(root)) stop("SHAREDIMP_EXP_ROOT is not set; run through workflow/*.smk.")
  normalizePath(root, mustWork = TRUE)
}

sha256_file <- function(path) {
  out <- system2("sha256sum", shQuote(path), stdout = TRUE)
  sub(" .*$", "", out[1L])
}

read_json <- function(path) jsonlite::fromJSON(path, simplifyVector = FALSE)

write_json <- function(obj, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines(jsonlite::toJSON(obj, auto_unbox = TRUE, pretty = TRUE, digits = NA, null = "null", na = "null"), path)
}

# The Singularity image this process runs in (NULL outside a container); see
# container_record() in python/sharedimp_exp/common.py.
container_record <- function() {
  path <- "/.singularity.d/labels.json"
  if (!file.exists(path)) return(NULL)
  lab <- read_json(path)
  list(
    runtime = "singularity",
    runtime_version = lab[["org.label-schema.usage.singularity.version"]],
    image = lab[["org.label-schema.usage.singularity.deffile.from"]]
  )
}

pinned_image <- function() paste0(Sys.getenv("SHAREDIMP_R_IMAGE"), "@", Sys.getenv("SHAREDIMP_R_IMAGE_DIGEST"))
# The experiments image is built FROM the pinned sharedimp-r digest without
# reinstalling sharedimp (docker/experiments-r/Dockerfile), so it carries the
# same sharedimp commit.
derived_image <- function() paste0(Sys.getenv("SHAREDIMP_EXP_R_IMAGE"), "@", Sys.getenv("SHAREDIMP_EXP_R_IMAGE_DIGEST"))

# Container and commit fields written into every raw result. sharedimp_commit
# is the pinned commit only if the process runs inside the pinned image.
provenance <- function() {
  rec <- container_record()
  in_pinned <- !is.null(rec) && (identical(rec$image, pinned_image()) || identical(rec$image, derived_image()))
  exp_commit <- Sys.getenv("SHAREDIMP_EXP_COMMIT", "")
  list(
    container = rec,
    in_pinned_image = in_pinned,
    sharedimp_commit = if (in_pinned) Sys.getenv("SHAREDIMP_R_COMMIT") else NULL,
    experiments_commit = if (nzchar(exp_commit)) exp_commit else NULL,
    experiments_code_dirty = identical(Sys.getenv("SHAREDIMP_EXP_DIRTY"), "1")
  )
}

# Doubles are written with 17 significant digits (round-trip exact); integers,
# strings and logicals as they are; missing values as NA.
write_csv_exact <- function(df, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  df <- as.data.frame(df, stringsAsFactors = FALSE)
  for (nm in names(df)) {
    col <- df[[nm]]
    if (is.double(col)) {
      txt <- formatC(col, digits = 17, format = "g")
      txt[is.na(col)] <- "NA"
      df[[nm]] <- txt
    } else if (is.factor(col)) {
      df[[nm]] <- as.character(col)
    }
  }
  utils::write.csv(df, path, row.names = FALSE, quote = FALSE, na = "NA", eol = "\n")
}

# Looks a data set up in `manifest_dir` (if given), then in data/synthetic, data/real and data/derived.
find_dataset <- function(id, manifest_dir = NULL) {
  for (d in c(manifest_dir, file.path(exp_root(), "data", c("synthetic", "real", "derived")))) {
    mpath <- file.path(d, "manifest.json")
    if (!file.exists(mpath)) next
    entry <- read_json(mpath)$datasets[[id]]
    if (!is.null(entry)) {
      return(list(entry = entry, path = file.path(d, entry$file)))
    }
  }
  stop(sprintf("dataset '%s' is not in any manifest.json", id))
}

# Load a dataset and verify its checksum against the manifest.
load_dataset <- function(id, manifest_dir = NULL) {
  found <- find_dataset(id, manifest_dir)
  entry <- found$entry
  digest <- sha256_file(found$path)
  if (!identical(digest, entry$sha256)) {
    stop(sprintf("%s: sha256 %s != manifest %s", found$path, digest, entry$sha256))
  }
  df <- utils::read.csv(found$path, stringsAsFactors = FALSE, check.names = FALSE)
  features <- unlist(entry$features)
  x <- df[, features, drop = FALSE]
  x[] <- lapply(x, as.numeric)
  y <- df[[entry$target]]
  # Levels in sorted order (C locale), as scikit-learn orders classes.
  y <- if (entry$task == "regression") as.numeric(y) else factor(y, levels = sort(unique(as.character(y)), method = "radix"))
  list(id = id, entry = entry, x = x, y = y, fold = as.integer(df[[entry$fold]]), sha256 = digest)
}
