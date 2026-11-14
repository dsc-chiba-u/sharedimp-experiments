# Checks of the built manuscript (workflow/07_manuscript.smk).
#
#   Rscript R/manuscript_checks.R paper results/summary/07_manuscript
#
# Reads paper/manuscript.tex and paper/manuscript.log (written by the render
# rule) and paper/references.bib; writes <summary>/checks.csv and
# results/tables/07_manuscript_checks.md. Limits are those of the SoftwareX
# template (docs/softwarex_requirements.md): 4000 words for the five main
# sections, at most six figures, abstract of about 100 words, at most six
# keywords. The word count is approximate (LaTeX commands, figures, tables,
# code listings and display mathematics are removed before counting).
args <- commandArgs(trailingOnly = TRUE)
paper <- args[1L]; out <- args[2L]
tex <- readLines(file.path(paper, "manuscript.tex"), warn = FALSE)
log <- readLines(file.path(paper, "manuscript.log"), warn = FALSE)
bib <- readLines(file.path(paper, "references.bib"), warn = FALSE)
rmd <- readLines(file.path(paper, "manuscript.Rmd"), warn = FALSE)
checks <- list()
add <- function(check, description, criterion, observed, pass) {
  checks[[length(checks) + 1L]] <<- data.frame(check = check, description = description, criterion = criterion, observed = as.character(observed),
                                               status = if (is.na(pass)) "reported" else if (pass) "pass" else "FAIL")
}
strip <- function(x) {
  x <- paste(x, collapse = "\n")
  for (env in c("figure", "table", "Shaded", "verbatim", "Highlighting", "equation", "tabular"))
    x <- gsub(sprintf("\\\\begin\\{%s\\*?\\}.*?\\\\end\\{%s\\*?\\}", env, env), " ", x, perl = TRUE)
  x <- gsub("\\$\\$.*?\\$\\$", " ", x, perl = TRUE)
  x <- gsub("\\\\\\[.*?\\\\\\]", " ", x, perl = TRUE)
  x <- gsub("(?m)^%.*$", " ", x, perl = TRUE)
  x <- gsub("\\\\(cite[a-z]*|ref|label|hypertarget|url)\\*?(\\[[^]]*\\])?\\{[^}]*\\}", " ", x, perl = TRUE)
  x <- gsub("\\\\[a-zA-Z]+\\*?(\\[[^]]*\\])?", " ", x, perl = TRUE)
  x <- gsub("[{}$\\\\~^_]", " ", x)
  x
}
words <- function(x) { w <- strsplit(strip(x), "[[:space:]]+")[[1L]]; sum(grepl("[[:alnum:]]", w)) }
a <- grep("MAIN-TEXT-START", tex); b <- grep("MAIN-TEXT-END", tex)
stopifnot(length(a) == 1L, length(b) == 1L, a < b)
main <- tex[(a + 1L):(b - 1L)]
n_main <- words(main)
add("main_text_words", "words in the five main sections (approximate; metadata, figures, tables, listings and references excluded)", "<= 4000", n_main, n_main <= 4000)
pdf_pages <- suppressWarnings(tryCatch(as.integer(sub("^.*Output written on .*\\(([0-9]+) pages.*$", "\\1", grep("Output written on", log, value = TRUE))), error = function(e) NA_integer_))
aux <- readLines(file.path(paper, "manuscript.aux"), warn = FALSE)
page_of <- function(label) { l <- grep(paste0("\\newlabel{", label, "}"), aux, value = TRUE, fixed = TRUE); if (!length(l)) return(NA_integer_); as.integer(strsplit(l[1L], "[{}]+")[[1L]][4L]) }
p1 <- page_of("motivation-and-significance"); p2 <- page_of("sec:repro")
add("body_pages", "pages from the start of section 1 to the end of section 5, figures and tables included (template: six pages excluding metadata, tables, figures and references, the word limit having priority)", "reported only", sprintf("pages %s to %s of %s", p1, p2, paste(pdf_pages, collapse = "")), NA)
stopifnot(!is.na(p1), !is.na(p2))
flat <- gsub("[[:space:]]+", " ", paste(main, collapse = " "))
sections <- sub("^\\\\section\\{([^}]*)\\}$", "\\1", unlist(regmatches(flat, gregexpr("\\\\section\\{[^}]*\\}", flat))))
required <- c("Motivation and significance", "Software description", "Illustrative examples", "Impact", "Conclusions")
add("main_sections", "the five main sections required by the template, in order", paste(required, collapse = "; "), paste(sections, collapse = "; "), identical(sections, required))
n_fig <- length(grep("\\\\begin\\{figure\\*?\\}", tex))
add("figures", "number of figures", "<= 6", n_fig, n_fig <= 6)
ab <- grep("\\\\begin\\{abstract\\}", tex); ae <- grep("\\\\end\\{abstract\\}", tex)
n_abs <- words(tex[(ab + 1L):(ae - 1L)])
add("abstract_words", "words in the abstract", "about 100 (template: 'ca. 100 words'); checked as <= 120", n_abs, n_abs <= 120)
kw <- grep("^keywords:", rmd); nxt <- grep("^[a-z-]+:", rmd); nxt <- min(nxt[nxt > kw])
n_kw <- length(grep("^  - ", rmd[(kw + 1L):(nxt - 1L)]))
add("keywords", "number of keywords", "<= 6", n_kw, n_kw <= 6)
undefined <- grep("Citation .* undefined|Reference .* undefined|There were undefined", log, value = TRUE)
add("references_resolved", "undefined citations or cross-references in the LaTeX log", "none", length(undefined), length(undefined) == 0L)
cited <- unique(unlist(strsplit(unlist(regmatches(tex, gregexpr("\\\\cite[a-z]*\\{[^}]*\\}", tex))), "[{},]")))
cited <- unique(trimws(cited[!grepl("^\\\\cite", cited) & nzchar(trimws(cited))]))
keys <- sub("^@[a-zA-Z]+\\{([^,]+),.*$", "\\1", grep("^@", bib, value = TRUE))
add("bibliography_keys", "every cited key is in references.bib and every entry is cited", "identical sets", sprintf("%d cited, %d entries", length(cited), length(keys)), setequal(cited, keys))
figs <- unlist(regmatches(tex, gregexpr("\\\\includegraphics(\\[[^]]*\\])?\\{[^}]*\\}", tex)))
paths <- sub("^.*\\{([^}]*)\\}$", "\\1", figs)
exists <- file.exists(ifelse(grepl("^/", paths), paths, file.path(paper, paths))) | file.exists(paste0(ifelse(grepl("^/", paths), paths, file.path(paper, paths)), ".pdf"))
add("figure_files", "every included figure file exists", "all", sprintf("%d of %d", sum(exists), length(exists)), all(exists))
todo <- length(grep("TO BE COMPLETED BY THE AUTHOR", tex))
add("author_items", "places marked 'TO BE COMPLETED BY THE AUTHOR'", "reported only", todo, NA)
overfull <- length(grep("^Overfull \\\\hbox", log))
add("overfull_boxes", "overfull horizontal boxes in the LaTeX log", "reported only", overfull, NA)
nums <- utils::read.csv(file.path(out, "numbers.csv"))
add("numbers", "values in the text read from results/ at build time (numbers.csv)", "reported only", nrow(nums), NA)
tab <- do.call(rbind, checks)
dir.create(out, recursive = TRUE, showWarnings = FALSE)
utils::write.csv(tab, file.path(out, "checks.csv"), row.names = FALSE, eol = "\n")
md <- c("<!-- generated by R/manuscript_checks.R; do not edit -->", "| check | description | criterion | observed | status |", "|---|---|---|---|---|",
        sprintf("| `%s` | %s | %s | %s | %s |", tab$check, tab$description, tab$criterion, tab$observed, tab$status))
writeLines(md, file.path(dirname(dirname(out)), "tables", "07_manuscript_checks.md"))
cat("[manuscript_checks]", paste(names(table(tab$status)), table(tab$status), collapse = ", "), "\n")
if (any(tab$status == "FAIL")) { print(tab[tab$status == "FAIL", c("check", "observed")]); quit(status = 1L) }
