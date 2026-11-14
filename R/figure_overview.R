# Software overview diagram of the manuscript (no data).
#
#   Rscript R/figure_overview.R results/figures
#
# Writes 07_software_overview.{pdf,png}: the computation of shared_importance()
# for one anchor feature and one split, and the two implementations of the
# common specification.
suppressPackageStartupMessages(library(ggplot2))
fig_dir <- commandArgs(trailingOnly = TRUE)[1L]
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)

box <- function(id, x, y, w, h, label, fill) data.frame(id = id, x = x, y = y, w = w, h = h, label = label, fill = fill)
b <- rbind(
  box("in", 1.2, 4.6, 2.0, 1.5, "Input\nfeatures X (n x p), response y\nlearner, metric, splits", "io"),
  box("res", 4.0, 4.6, 2.3, 1.5, "Residualize on the anchor x[i]\nOLS of every x[j] on x[i]\nfitted on training rows only", "step"),
  box("full", 7.0, 5.45, 2.4, 0.8, "Full: x[i] + residuals (p columns)", "rep"),
  box("red", 7.0, 3.75, 2.4, 0.8, "Reduced: residuals (p - 1 columns)", "rep"),
  box("fit", 10.0, 4.6, 2.2, 1.5, "Fit the same learner\non each representation\n(training rows)", "step"),
  box("score", 12.8, 4.6, 2.2, 1.5, "Score both models on the\nsame assessment rows\n(paired)", "step"),
  box("imp", 12.8, 2.2, 2.2, 1.0, "importance =\nscore(Full) - score(Reduced)", "out"),
  box("agg", 9.3, 2.2, 3.4, 1.0, "Over splits: mean, between-split SD,\nper-split table (common schema)", "out"),
  box("spec", 2.9, 2.2, 3.2, 1.0, "One specification\n(definitions, edge cases, output schema)", "spec"),
  box("r", 1.9, 0.7, 2.6, 0.8, "R: parsnip, rsample, yardstick", "impl"),
  box("py", 5.0, 0.7, 2.6, 0.8, "Python: scikit-learn", "impl")
)
arrow_df <- function(x, y, xend, yend) data.frame(x = x, y = y, xend = xend, yend = yend)
a <- rbind(
  arrow_df(2.2, 4.6, 2.85, 4.6), arrow_df(5.15, 4.9, 5.8, 5.45), arrow_df(5.15, 4.3, 5.8, 3.75),
  arrow_df(8.2, 5.45, 8.9, 4.9), arrow_df(8.2, 3.75, 8.9, 4.3), arrow_df(11.1, 4.6, 11.7, 4.6),
  arrow_df(12.8, 3.85, 12.8, 2.7), arrow_df(11.7, 2.2, 11.0, 2.2),
  arrow_df(2.4, 1.7, 1.9, 1.1), arrow_df(3.4, 1.7, 5.0, 1.1)
)
fills <- c(io = "#f2f2f2", step = "#dbe9f6", rep = "#fbe5d6", out = "#e2efda", spec = "#fff2cc", impl = "#f2f2f2")
p <- ggplot() +
  annotate("rect", xmin = 2.7, xmax = 14.05, ymin = 3.15, ymax = 6.35, fill = NA, colour = "grey45", linetype = "dashed", linewidth = 0.3) +
  annotate("text", x = 2.8, y = 6.15, hjust = 0, size = 2.6, colour = "grey25",
           label = "for every anchor feature i and every split (training rows / assessment rows); coefficients are applied unchanged to the assessment rows") +
  geom_rect(data = b, aes(xmin = x - w / 2, xmax = x + w / 2, ymin = y - h / 2, ymax = y + h / 2, fill = fill), colour = "grey25", linewidth = 0.3) +
  geom_text(data = b, aes(x, y, label = label), size = 2.5, lineheight = 0.95) +
  geom_segment(data = a, aes(x = x, y = y, xend = xend, yend = yend), arrow = grid::arrow(length = grid::unit(0.07, "inches"), type = "closed"), linewidth = 0.3) +
  scale_fill_manual(values = fills, guide = "none") +
  coord_cartesian(xlim = c(0.1, 14.2), ylim = c(0.2, 6.45), expand = FALSE) + theme_void()
ggsave(file.path(fig_dir, "07_software_overview.pdf"), p, width = 9.4, height = 4.2, device = grDevices::pdf)
ggsave(file.path(fig_dir, "07_software_overview.png"), p, width = 9.4, height = 4.2, dpi = 200, bg = "white")
cat("[figure_overview] 07_software_overview ->", fig_dir, "\n")
