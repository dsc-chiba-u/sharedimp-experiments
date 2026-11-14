# Figure of the illustrative examples of the manuscript, from summary files only.
#
#   Rscript R/figure_examples.R results/summary results/figures
#
# Writes 07_examples_importance.{pdf,png}: importances in R and Python on the
# three example data sets. Concrete and Breast Cancer come from experiment C
# (results/summary/04_real_data/importance_wide.csv); for Maternal Health Risk
# the analysis with group-aware folds is shown
# (results/summary/04b_maternal/importance_by_variant.csv, column
# maternal_grouped), which is the multiclass example of the paper
# (docs/maternal_duplicates.md, docs/multiclass_dataset_selection.md).
suppressPackageStartupMessages({
  library(ggplot2)
  library(patchwork)
})
args <- commandArgs(trailingOnly = TRUE)
sum_dir <- args[1L]; fig_dir <- args[2L]
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)
read <- function(...) utils::read.csv(file.path(sum_dir, ...), stringsAsFactors = FALSE)
theme_set(theme_bw(base_size = 9) + theme(legend.position = "bottom", strip.background = element_rect(fill = "grey92")))
lang_cols <- c("R" = "#1b6ca8", "Python" = "#d1702e")

w <- read("04_real_data", "importance_wide.csv")
primary <- c(concrete = "rmse", wdbc = "log_loss")
w <- w[w$dataset %in% names(primary), ]
w <- w[w$metric == primary[w$dataset], ]
long <- rbind(
  data.frame(w[c("dataset", "learner", "feature")], language = "R", importance = w$importance_r, sd = w$sd_between_splits_r),
  data.frame(w[c("dataset", "learner", "feature")], language = "Python", importance = w$importance_python, sd = w$sd_between_splits_python)
)
m <- read("04b_maternal", "importance_by_variant.csv")
m <- m[m$metric == "log_loss", ]
long <- rbind(long, data.frame(dataset = "maternal_grouped", learner = m$learner, feature = m$feature,
                               language = ifelse(m$language == "r", "R", "Python"), importance = m$maternal_grouped, sd = m$sd_maternal_grouped))
long$language <- factor(long$language, levels = c("R", "Python"))
lev <- c("linear / logistic (same model in R and Python)", "random forest (language-specific settings)")
long$learner <- factor(ifelse(long$learner == "linear", lev[1L], lev[2L]), levels = lev)
panel <- function(ds, title, metric) {
  x <- long[long$dataset == ds, ]
  ord <- x[x$language == "R" & x$learner == lev[1L], ]
  x$feature <- factor(x$feature, levels = ord$feature[order(ord$importance)])
  ggplot(x, aes(importance, feature, colour = language, shape = language)) +
    geom_vline(xintercept = 0, linewidth = 0.3) +
    geom_errorbar(aes(xmin = importance - sd, xmax = importance + sd), width = 0, linewidth = 0.35, position = position_dodge(width = 0.55), orientation = "y") +
    geom_point(size = 1.4, position = position_dodge(width = 0.55)) +
    facet_wrap(~learner, nrow = 1, scales = "free_x") +
    scale_colour_manual(values = lang_cols, name = NULL) + scale_shape_manual(values = c(R = 16, Python = 17), name = NULL) +
    labs(x = sprintf("importance (reduction in %s), mean ± SD over 5 splits", metric), y = NULL, title = title) +
    theme(plot.title = element_text(size = 9, face = "bold"))
}
n_of <- function(ds) read("04_real_data", "datasets.csv")
d <- n_of()
n <- stats::setNames(d$n, d$dataset)
p <- panel("concrete", sprintf("Concrete compressive strength (regression, n = %d)", n[["concrete"]]), "RMSE") /
  panel("wdbc", sprintf("Breast cancer Wisconsin, mean features (binary, n = %d)", n[["wdbc"]]), "log-loss") /
  panel("maternal_grouped", sprintf("Maternal health risk (three classes, n = %d), group-aware folds", n[["maternal"]]), "log-loss") +
  plot_layout(guides = "collect", heights = c(8, 10, 6)) & theme(legend.position = "bottom")
ggsave(file.path(fig_dir, "07_examples_importance.pdf"), p, width = 7.5, height = 8.5, device = grDevices::pdf)
ggsave(file.path(fig_dir, "07_examples_importance.png"), p, width = 7.5, height = 8.5, dpi = 200)
cat("[figure_examples] 07_examples_importance ->", fig_dir, "\n")
