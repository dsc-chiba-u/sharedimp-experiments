# Paths, dataset loading and exact CSV/JSON output shared by the R scripts.
# Sourced, not a package. Mirrors python/sharedimp_exp/common.py.

exp_root <- function() {
  root <- Sys.getenv("SHAREDIMP_EXP_ROOT", "")
  if (!nzchar(root)) stop("SHAREDIMP_EXP_ROOT is not set; run through scripts/*.sh.")
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

find_dataset <- function(id) {
  for (group in c("synthetic", "real")) {
    mpath <- file.path(exp_root(), "data", group, "manifest.json")
    if (!file.exists(mpath)) next
    entry <- read_json(mpath)$datasets[[id]]
    if (!is.null(entry)) {
      return(list(entry = entry, path = file.path(exp_root(), "data", group, entry$file)))
    }
  }
  stop(sprintf("dataset '%s' is not in any data/*/manifest.json", id))
}

# Load a dataset and verify its checksum against the manifest.
load_dataset <- function(id) {
  found <- find_dataset(id)
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
