# Figures of Phase 3 and of the Phase 2 follow-ups, drawn from summary files only.
#
#   Rscript R/figures_phase3.R results/summary results/figures
#
# Writes, each as .pdf and .png:
#   04b_maternal_duplicates  Maternal Health Risk: scores and importances with random folds, group-aware folds, identical records removed
#   04c_null_forest          null design: mean forest importance per setting (one factor changed at a time)
#   05_runtime_scaling       runtime against n, p and the number of folds, per comparison, R and Python
#   05_runtime_learners      runtime of every learner at the base cell, and Python / R along the sweeps
# No curve is fitted to the timings: the figures show what was measured.

suppressPackageStartupMessages({
  library(ggplot2)
  library(patchwork)
})
args <- commandArgs(trailingOnly = TRUE)
sum_dir <- args[1L]; fig_dir <- args[2L]
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)
read <- function(...) utils::read.csv(file.path(sum_dir, ...), stringsAsFactors = FALSE, na.strings = "NA")
save_fig <- function(name, plot, width, height) {
  ggsave(file.path(fig_dir, paste0(name, ".pdf")), plot, width = width, height = height, device = grDevices::pdf)
  ggsave(file.path(fig_dir, paste0(name, ".png")), plot, width = width, height = height, dpi = 200)
}
theme_set(theme_bw(base_size = 9) + theme(legend.position = "bottom", strip.background = element_rect(fill = "grey92")))
lang_cols <- c("R" = "#1b6ca8", "Python" = "#d1702e")
lang_label <- function(x) factor(ifelse(x == "r", "R", "Python"), levels = c("R", "Python"))

# ---- 04b_maternal_duplicates
variants <- c(maternal = "all rows,\nrandom folds", maternal_grouped = "all rows,\ngroup-aware folds", maternal_dedup = "identical records\nremoved,\ngroup-aware folds")
s <- read("04b_maternal", "scores.csv")
s <- s[s$metric == "log_loss", ]
s$variant <- factor(variants[s$variant], levels = variants)
s$language <- lang_label(s$language)
s$learner <- ifelse(s$learner == "linear", "multinomial logistic", "random forest (language-specific)")
m1 <- ggplot(s, aes(variant, -full_score, colour = language, shape = language, group = language)) +
  geom_line(linewidth = 0.3, position = position_dodge(width = 0.25)) + geom_point(size = 1.8, position = position_dodge(width = 0.25)) +
  facet_wrap(~learner) + scale_colour_manual(values = lang_cols, guide = "none") + scale_shape_manual(values = c(R = 16, Python = 17), guide = "none") +
  labs(x = NULL, y = "log-loss of the Full model (5 folds)", title = "Score of the Full model") +
  theme(plot.title = element_text(size = 9, face = "bold"))
w <- read("04b_maternal", "importance_by_variant.csv")
w <- w[w$metric == "log_loss", ]
long <- do.call(rbind, lapply(names(variants), function(v) data.frame(
  w[c("learner", "language", "feature")], variant = variants[[v]], importance = w[[v]], sd = w[[paste0("sd_", v)]])))
long$variant <- factor(long$variant, levels = variants)
long$language <- lang_label(long$language)
long$learner <- ifelse(long$learner == "linear", "multinomial logistic", "random forest (language-specific)")
m2 <- ggplot(long, aes(importance, feature, colour = language, shape = language)) +
  geom_vline(xintercept = 0, linewidth = 0.3) +
  geom_errorbar(aes(xmin = importance - sd, xmax = importance + sd), width = 0, linewidth = 0.35, position = position_dodge(width = 0.55), orientation = "y") +
  geom_point(size = 1.4, position = position_dodge(width = 0.55)) +
  facet_grid(learner ~ variant, scales = "free_x") +
  scale_colour_manual(values = lang_cols, name = NULL) + scale_shape_manual(values = c(R = 16, Python = 17), name = NULL) +
  labs(x = "importance (reduction in log-loss), mean ± SD over 5 splits", y = NULL, title = "Importance") +
  theme(plot.title = element_text(size = 9, face = "bold"))
save_fig("04b_maternal_duplicates", m1 / m2 + plot_layout(heights = c(1, 2), guides = "collect") & theme(legend.position = "bottom"), 7.5, 7.5)

# ---- 04c_null_forest
z <- read("04c_null_forest", "summary.csv")
z$language <- lang_label(z$language)
z$variant <- factor(z$variant, levels = rev(unique(z$variant)))
z$design <- factor(z$design, levels = unique(z$design))
p0 <- ggplot(z, aes(mean_importance, variant, colour = language, shape = language)) +
  geom_vline(xintercept = 0, linewidth = 0.3) +
  geom_errorbar(aes(xmin = mean_importance - 2 * mc_standard_error, xmax = mean_importance + 2 * mc_standard_error),
                width = 0, linewidth = 0.35, position = position_dodge(width = 0.6), orientation = "y") +
  geom_point(size = 1.4, position = position_dodge(width = 0.6)) +
  facet_wrap(~design, nrow = 1) +
  scale_colour_manual(values = lang_cols, name = NULL) + scale_shape_manual(values = c(R = 16, Python = 17), name = NULL) +
  labs(x = "mean importance, MSE(Reduced) - MSE(Full); bars: ± 2 Monte Carlo standard errors over the simulated data sets", y = NULL,
       caption = "response independent of the features; same data, folds and seeds in every row; one setting changed from the baseline per row")
save_fig("04c_null_forest", p0, 8.5, 4.2)

# ---- 05_runtime_scaling
cmp <- read("05_runtime", "comparisons.csv")
titles <- c(A_linear = "A. linear regression", B_forest_aligned = "B. random forest, aligned settings", C_forest_customary = "C. random forest, customary settings")
sweep_lab <- c(n = "rows n (p = 10, 5 folds)", p = "features p (n = 1000, 5 folds)", v = "folds v (n = 1000, p = 10)")
rt <- do.call(rbind, lapply(c("n", "p", "v"), function(f) {
  d <- cmp[vapply(strsplit(cmp$sweeps, "+", fixed = TRUE), function(x) f %in% x, logical(1)), ]
  rbind(
    data.frame(comparison = d$comparison, sweep = f, x = d[[f]], language = "R", median = d$r_median, q1 = d$r_q1, q3 = d$r_q3),
    data.frame(comparison = d$comparison, sweep = f, x = d[[f]], language = "Python", median = d$python_median, q1 = d$python_q1, q3 = d$python_q3)
  )
}))
rt <- rt[!is.na(rt$median), ]
rt$comparison <- factor(titles[rt$comparison], levels = titles)
rt$sweep <- factor(sweep_lab[rt$sweep], levels = sweep_lab)
rt$language <- factor(rt$language, levels = c("R", "Python"))
n_skipped <- sum(cmp$r_status != "measured") + sum(cmp$python_status != "measured")
p5 <- ggplot(rt, aes(x, median, colour = language, shape = language)) +
  geom_line(linewidth = 0.35) + geom_errorbar(aes(ymin = q1, ymax = q3), width = 0, linewidth = 0.4) + geom_point(size = 1.5) +
  facet_grid(comparison ~ sweep, scales = "free") + scale_x_log10() + scale_y_log10() +
  scale_colour_manual(values = lang_cols, name = NULL) + scale_shape_manual(values = c(R = 16, Python = 17), name = NULL) +
  labs(x = "value of the factor (log scale)", y = "seconds per call of shared_importance() (log scale)",
       caption = sprintf("median of 5 timed runs, bars: quartiles; 1 thread; cells over the time budget are not measured (%d of %d cell-language pairs, listed in results/tables/05_runtime.md)",
                         n_skipped, 2L * nrow(cmp)))
save_fig("05_runtime_scaling", p5, 8, 6.5)

# ---- 05_runtime_learners
cells <- read("05_runtime", "cells.csv")
base <- cells[cells$sweeps == "n+p+v" & cells$status == "measured", ]
base$what <- sprintf("%s: %s", ifelse(base$language == "r", "R", "Python"), base$learner)
base$language <- lang_label(base$language)
l1 <- ggplot(base, aes(median, stats::reorder(what, median), colour = language)) +
  geom_errorbar(aes(xmin = q1, xmax = q3), width = 0.25, linewidth = 0.4, orientation = "y") + geom_point(size = 1.8) +
  scale_x_log10() + scale_colour_manual(values = lang_cols, guide = "none") +
  labs(x = "seconds per call at the base cell (log scale)", y = NULL, title = sprintf("Base cell: n = %d, p = %d, %d folds", base$n[1L], base$p[1L], base$v[1L])) +
  theme(plot.title = element_text(size = 9, face = "bold"))
ratio <- do.call(rbind, lapply(c("n", "p", "v"), function(f) {
  d <- cmp[vapply(strsplit(cmp$sweeps, "+", fixed = TRUE), function(x) f %in% x, logical(1)) & !is.na(cmp$python_over_r_median), ]
  data.frame(comparison = d$comparison, sweep = f, x = d[[f]], ratio = d$python_over_r_median)
}))
ratio$comparison <- factor(titles[ratio$comparison], levels = titles)
ratio$sweep <- factor(sweep_lab[ratio$sweep], levels = sweep_lab)
l2 <- ggplot(ratio, aes(x, ratio, colour = comparison, shape = comparison)) +
  geom_hline(yintercept = 1, linewidth = 0.3) + geom_line(linewidth = 0.35) + geom_point(size = 1.5) +
  facet_wrap(~sweep, nrow = 1, scales = "free_x") + scale_x_log10() + scale_y_log10() +
  scale_colour_manual(values = c("#444444", "#1b9e77", "#7570b3"), name = NULL) + scale_shape_manual(values = c(16, 17, 15), name = NULL) +
  guides(colour = guide_legend(nrow = 3)) +
  labs(x = "value of the factor (log scale)", y = "median seconds, Python / R (log scale)", title = "Python relative to R",
       caption = "includes the differences between the learners (lm.fit vs LinearRegression, ranger vs scikit-learn) and between the frameworks") +
  theme(plot.title = element_text(size = 9, face = "bold"))
save_fig("05_runtime_learners", l1 / l2 + plot_layout(heights = c(1, 1.6)), 7.5, 7)
cat("[figures_phase3] 4 figures ->", fig_dir, "\n")
