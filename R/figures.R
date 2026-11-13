# Figures of Phase 2 (experiments B and C), drawn from the summary files only.
#
#   Rscript R/figures.R results/summary results/figures
#
# Writes, each as .pdf and .png:
#   03_official_designs        B4/B6: importance on the official synthetic designs, official code vs sharedimp
#   03_fold_internal_effect    B5b: all-rows vs fold-internal residualization as a function of n
#   04_real_data_importance    C: importance on the public data sets, R vs Python, linear and forest learners
#   04_r_python_agreement      R vs Python importance for every job of workflows 01, 02 and 04

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

# ---- 03_official_designs
d <- read("03_official_umfi", "importance_by_design.csv")
keep <- c(
  "official_r" = "official R (OOB, 100 trees)",
  "official_py/random_forest" = "official Python, RF (OOB, 100 trees)",
  "official_py/extra_trees" = "official Python, extra trees (OOB, 100 trees)",
  "sharedimp_r/rand_forest" = "sharedimp R (5-fold, forest)",
  "sharedimp_py/rand_forest" = "sharedimp Python (5-fold, forest)"
)
d <- d[d$variant %in% names(keep), ]
d$implementation <- factor(keep[d$variant], levels = keep)
d$design <- factor(d$design, levels = unique(d$design))
p1 <- ggplot(d, aes(feature, mean, fill = implementation)) +
  geom_hline(yintercept = 0, linewidth = 0.3) +
  geom_col(position = position_dodge(width = 0.85), width = 0.8) +
  geom_errorbar(aes(ymin = mean - sd_between_seeds, ymax = mean + sd_between_seeds),
                position = position_dodge(width = 0.85), width = 0.25, linewidth = 0.3) +
  facet_wrap(~design, nrow = 1, scales = "free_x") +
  scale_fill_manual(values = c("#08519c", "#a63603", "#fdae6b", "#6baed6", "#fd8d3c"), name = NULL) +
  guides(fill = guide_legend(nrow = 2)) +
  labs(x = NULL, y = expression("importance (gain in " * R^2 * ")"),
       caption = "bars: mean over 10 data sets per design; error bars: SD between data sets")
save_fig("03_official_designs", p1, 9, 4)

# ---- 03_fold_internal_effect
l <- read("03_official_umfi", "leak.csv")
ll <- rbind(
  data.frame(n = l$n, feature = l$feature, value = l$fold_internal, residualization = "training rows of each split (sharedimp)"),
  data.frame(n = l$n, feature = l$feature, value = l$all_rows, residualization = "all rows, then the same cross-validation"),
  data.frame(n = l$n, feature = l$feature, value = l$population, residualization = "population value")
)
ll$residualization <- factor(ll$residualization, levels = unique(ll$residualization))
p2 <- ggplot(ll, aes(n, value, colour = residualization, linetype = residualization)) +
  geom_line(linewidth = 0.5) + geom_point(data = ll[ll$residualization != "population value", ], size = 1) +
  facet_wrap(~feature, nrow = 1, scales = "free_y") + scale_x_log10(breaks = unique(l$n)) +
  scale_colour_manual(values = c("#1b6ca8", "#d1702e", "grey30"), name = NULL) +
  scale_linetype_manual(values = c("solid", "solid", "dashed"), name = NULL) +
  labs(x = "n (log scale)", y = "importance (reduction in MSE)",
       caption = "OLS learner, 5-fold cross-validation; mean over simulated data sets per n") +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))
save_fig("03_fold_internal_effect", p2, 9, 3.4)

# ---- 04_real_data_importance
w <- read("04_real_data", "importance_wide.csv")
primary <- c(concrete = "rmse", wdbc = "log_loss", maternal = "log_loss")
w <- w[w$metric == primary[w$dataset], ]
long <- rbind(
  data.frame(w[c("dataset", "learner", "metric", "feature")], language = "R", importance = w$importance_r, sd = w$sd_between_splits_r),
  data.frame(w[c("dataset", "learner", "metric", "feature")], language = "Python", importance = w$importance_python, sd = w$sd_between_splits_python)
)
long$language <- factor(long$language, levels = c("R", "Python"))
long$learner <- factor(ifelse(long$learner == "linear", "linear / logistic (same model in R and Python)", "random forest (language-specific)"),
                       levels = c("linear / logistic (same model in R and Python)", "random forest (language-specific)"))
panel <- function(ds, title) {
  x <- long[long$dataset == ds, ]
  ord <- x[x$language == "R" & grepl("^linear", x$learner), ]
  x$feature <- factor(x$feature, levels = ord$feature[order(ord$importance)])
  ggplot(x, aes(importance, feature, colour = language, shape = language)) +
    geom_vline(xintercept = 0, linewidth = 0.3) +
    geom_errorbar(aes(xmin = importance - sd, xmax = importance + sd), width = 0, linewidth = 0.35, position = position_dodge(width = 0.55), orientation = "y") +
    geom_point(size = 1.4, position = position_dodge(width = 0.55)) +
    facet_wrap(~learner, nrow = 1, scales = "free_x") +
    scale_colour_manual(values = lang_cols, name = NULL) + scale_shape_manual(values = c(R = 16, Python = 17), name = NULL) +
    labs(x = sprintf("importance (reduction in %s), mean ± SD over 5 splits", primary[[ds]]), y = NULL, title = title) +
    theme(plot.title = element_text(size = 9, face = "bold"))
}
p3 <- panel("concrete", "Concrete compressive strength (regression, n = 1030)") /
  panel("wdbc", "Breast cancer Wisconsin, mean features (binary, n = 569)") /
  panel("maternal", "Maternal health risk (three classes, n = 1014)") +
  plot_layout(guides = "collect", heights = c(8, 10, 6)) & theme(legend.position = "bottom")
save_fig("04_real_data_importance", p3, 7.5, 8.5)

# ---- 04_r_python_agreement
a <- do.call(rbind, lapply(c("01_environment", "02_validation", "04_real_data"), function(s) {
  x <- read(s, "importance_long.csv")
  r <- x[x$language == "r", ]; p <- x[x$language == "python", ]
  stopifnot(identical(r$job, p$job), identical(r$feature, p$feature))
  data.frame(workflow = s, job = r$job, learner = r$learner, r = r$importance, python = p$importance)
}))
a$learner <- ifelse(a$learner == "linear", "linear / logistic", "random forest")
scale_job <- ave(pmax(abs(a$r), abs(a$python)), a$job, FUN = max)   # one scale per job so that all jobs fit one panel
a$r_scaled <- a$r / scale_job; a$python_scaled <- a$python / scale_job
p4a <- ggplot(a, aes(r_scaled, python_scaled)) +
  geom_abline(slope = 1, intercept = 0, linewidth = 0.3, colour = "grey40") +
  geom_point(size = 1, alpha = 0.7, colour = "#1b6ca8") + facet_wrap(~learner) + coord_equal() +
  labs(x = "importance in R (divided by the largest |importance| of the job)", y = "importance in Python (same scaling)")
par <- do.call(rbind, lapply(c("01_environment", "02_validation", "04_real_data"), function(s) {
  x <- read(s, "parity.csv"); x <- x[x$parity_class != "none", ]
  stats::aggregate(max_abs_diff ~ job + parity_class + tolerance, data = x, FUN = max)
}))
par$parity_class <- factor(par$parity_class, levels = c("exact", "logistic", "multinomial"), labels = c("OLS", "binary logistic", "multinomial logistic"))
floor_val <- 1e-17
p4b <- ggplot(par, aes(pmax(max_abs_diff, floor_val), stats::reorder(job, max_abs_diff))) +
  geom_segment(aes(x = tolerance, xend = tolerance, y = -Inf, yend = Inf), colour = "#d1702e", linetype = "dashed", linewidth = 0.4) +
  geom_point(size = 1.4, colour = "#1b6ca8") + facet_grid(parity_class ~ ., scales = "free_y", space = "free_y") +
  scale_x_log10() +
  labs(x = "largest |R - Python| over all numeric result columns (dashed: tolerance fixed in advance)", y = NULL) +
  theme(strip.text.y = element_text(angle = 0))
save_fig("04_r_python_agreement", p4a / p4b + plot_layout(heights = c(1, 1.6)), 7.5, 8)
cat("[figures] 4 figures ->", fig_dir, "\n")
