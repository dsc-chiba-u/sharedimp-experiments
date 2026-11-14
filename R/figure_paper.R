# Paper versions of two figures, from summary files only.
#
#   Rscript R/figure_paper.R results/summary results/figures
#
# Writes, each as .pdf and .png, at the width of the text block (6.5 in) so
# that the lettering is not scaled down in the manuscript:
#   07_fold_internal_effect  experiment B5b (results/summary/03_official_umfi/leak.csv):
#                            fold-internal against all-rows residualization
#   07_runtime               experiment D (results/summary/05_runtime/comparisons.csv):
#                            comparisons A (least squares) and B (forests, aligned settings)
# The figures of workflow 06 (03_fold_internal_effect, 05_runtime_scaling)
# show the same data and are left as they are. No curve is fitted.
suppressPackageStartupMessages(library(ggplot2))
args <- commandArgs(trailingOnly = TRUE)
sum_dir <- args[1L]; fig_dir <- args[2L]
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)
read <- function(...) utils::read.csv(file.path(sum_dir, ...), stringsAsFactors = FALSE, na.strings = "NA")
save_fig <- function(name, plot, width, height) {
  ggsave(file.path(fig_dir, paste0(name, ".pdf")), plot, width = width, height = height, device = grDevices::pdf)
  ggsave(file.path(fig_dir, paste0(name, ".png")), plot, width = width, height = height, dpi = 300)
}
theme_set(theme_bw(base_size = 8) + theme(legend.position = "bottom", strip.background = element_rect(fill = "grey92"),
                                          legend.margin = margin(0, 0, 0, 0), legend.box.spacing = grid::unit(2, "pt"), panel.grid.minor = element_blank()))

# ---- 07_fold_internal_effect
l <- read("03_official_umfi", "leak.csv")
stopifnot(length(unique(l$n_seeds)) == 1L)
lev <- c("training rows of each split (sharedimp)", "all rows, then the same cross-validation", "all rows, preprocessing of the reference R package (with its dependence test), then the same cross-validation")
ll <- rbind(
  data.frame(n = l$n, feature = l$feature, value = l$fold_internal, se = l$sd_fold_internal / sqrt(l$n_seeds), residualization = lev[1L]),
  data.frame(n = l$n, feature = l$feature, value = l$all_rows, se = NA, residualization = lev[2L]),
  data.frame(n = l$n, feature = l$feature, value = l$all_rows_official_gate, se = NA, residualization = lev[3L])
)
ll$residualization <- factor(ll$residualization, levels = lev)
pop <- unique(l[c("feature", "population")])
lab <- stats::setNames(sprintf("%s (large-sample value %s)", pop$feature, sprintf("%.3g", pop$population)), pop$feature)
p1 <- ggplot(ll, aes(n, value, colour = residualization, shape = residualization)) +
  geom_hline(data = pop, aes(yintercept = population), linetype = "dashed", linewidth = 0.3, colour = "grey30") +
  geom_errorbar(aes(ymin = value - 2 * se, ymax = value + 2 * se), width = 0, linewidth = 0.35, na.rm = TRUE) +
  geom_line(linewidth = 0.4) + geom_point(size = 1.1) +
  facet_wrap(~feature, nrow = 1, scales = "free_y", labeller = as_labeller(lab)) + scale_x_log10(breaks = unique(l$n)) +
  scale_colour_manual(values = c("#1b6ca8", "#d1702e", "grey45"), name = "residualization fitted on") +
  scale_shape_manual(values = c(16, 17, 4), name = "residualization fitted on") +
  guides(colour = guide_legend(ncol = 1, title.position = "top"), shape = guide_legend(ncol = 1, title.position = "top")) +
  labs(x = "number of rows n (log scale)", y = "importance (reduction in MSE)") +
  theme(axis.text.x = element_text(angle = 45, hjust = 1), strip.text = element_text(size = 6.2), legend.key.height = grid::unit(9, "pt"))
save_fig("07_fold_internal_effect", p1, 6.5, 3.0)

# ---- 07_runtime
cmp <- read("05_runtime", "comparisons.csv")
titles <- c(A_linear = "least squares", B_forest_aligned = "random forest, 500 trees")
sweep_lab <- c(n = "rows n (p = 10, v = 5)", p = "features p (n = 1000, v = 5)", v = "folds v (n = 1000, p = 10)")
cmp <- cmp[cmp$comparison %in% names(titles), ]
rt <- do.call(rbind, lapply(names(sweep_lab), function(f) {
  d <- cmp[vapply(strsplit(cmp$sweeps, "+", fixed = TRUE), function(x) f %in% x, logical(1)), ]
  rbind(data.frame(comparison = d$comparison, sweep = f, x = d[[f]], language = "R", median = d$r_median),
        data.frame(comparison = d$comparison, sweep = f, x = d[[f]], language = "Python", median = d$python_median))
}))
rt <- rt[!is.na(rt$median), ]
rt$comparison <- factor(titles[rt$comparison], levels = titles)
rt$sweep <- factor(sweep_lab[rt$sweep], levels = sweep_lab)
rt$language <- factor(rt$language, levels = c("R", "Python"))
x_breaks <- function(lim) if (lim[2L] > 1000) c(125, 500, 2000, 8000, 32000) else if (lim[2L] > 25) c(5, 10, 20, 40, 80, 160) else c(2, 3, 5, 10, 20)
p2 <- ggplot(rt, aes(x, median, colour = language, shape = language)) +
  geom_line(linewidth = 0.35) + geom_point(size = 1.3) +
  facet_grid(comparison ~ sweep, scales = "free") + scale_x_log10(breaks = x_breaks) + scale_y_log10() +
  scale_colour_manual(values = c("R" = "#1b6ca8", "Python" = "#d1702e"), name = NULL) + scale_shape_manual(values = c(R = 16, Python = 17), name = NULL) +
  labs(x = "value of the factor varied (log scale)", y = "seconds per call, median of 5 (log scale)") +
  theme(panel.spacing.x = grid::unit(12, "pt"))
save_fig("07_runtime", p2, 6.5, 3.7)
cat("[figure_paper] 07_fold_internal_effect, 07_runtime ->", fig_dir, "\n")
