# Software overview diagram of the manuscript (no data).
#
#   Rscript R/figure_overview.R results/figures
#
# Writes 07_software_overview.{pdf,png}: the four inputs of
# shared_importance() with the objects that carry them in each package, the
# computation for one anchor feature and one split, and the result. Drawn at
# the width of the text block (6.5 in) so that the lettering is not scaled.
suppressPackageStartupMessages(library(ggplot2))
fig_dir <- commandArgs(trailingOnly = TRUE)[1L]
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)

box <- function(x0, x1, y0, y1, label, fill) data.frame(x0 = x0, x1 = x1, y0 = y0, y1 = y1, label = label, fill = fill)
b <- rbind(
  box(0.1, 3.1, 6.35, 7.7, "Data\nn rows, p numeric features;\nnumeric or class response", "io"),
  box(3.3, 6.3, 6.35, 7.7, "Splits\nR: rsample object or fold labels\nPython: splitter or index pairs", "io"),
  box(6.5, 9.5, 6.35, 7.7, "Learner\nR: parsnip model or built-in name\nPython: scikit-learn estimator", "io"),
  box(9.8, 12.8, 6.35, 7.7, "Metric\nR: yardstick metric or name\nPython: scorer or name", "io"),
  box(0.3, 3.2, 3.55, 5.25, "Residualize on the anchor\nregress each other feature on\nthe anchor, training rows only;\nsame coefficients for the\nassessment rows", "step"),
  box(3.8, 6.4, 4.6, 5.25, "Full: anchor and residuals", "rep"),
  box(3.8, 6.4, 3.55, 4.2, "Reduced: residuals only", "rep"),
  box(7.0, 9.5, 3.55, 5.25, "Fit the learner on the\ntraining rows, once per\nrepresentation", "step"),
  box(10.1, 12.6, 3.55, 5.25, "Score both models on\nthe same assessment\nrows (paired)", "step"),
  box(9.5, 12.8, 0.9, 2.1, "Importance in the split\nscore(Full) - score(Reduced)", "out"),
  box(5.0, 8.9, 0.9, 2.1, "Result\nmean and SD over splits; per-split table;\nthe same columns in R and Python", "out"),
  box(0.1, 4.4, 0.9, 2.1, "Common specification\nedge-case rules, metric definitions, result\nschema; implemented by both packages", "spec")
)
arrow_df <- function(x, y, xend, yend) data.frame(x = x, y = y, xend = xend, yend = yend)
a <- rbind(
  arrow_df(1.6, 6.35, 1.6, 5.25), arrow_df(4.8, 6.35, 4.8, 5.85), arrow_df(8.0, 6.35, 8.0, 5.25), arrow_df(11.3, 6.35, 11.3, 5.25),
  arrow_df(3.2, 4.7, 3.8, 4.925), arrow_df(3.2, 4.1, 3.8, 3.875),
  arrow_df(6.4, 4.925, 7.0, 4.7), arrow_df(6.4, 3.875, 7.0, 4.1), arrow_df(9.5, 4.4, 10.1, 4.4),
  arrow_df(11.3, 3.55, 11.3, 2.1), arrow_df(9.5, 1.5, 8.9, 1.5), arrow_df(2.25, 2.1, 2.25, 2.75)
)
fills <- c(io = "#f2f2f2", step = "#dbe9f6", rep = "#fbe5d6", out = "#e2efda", spec = "#fff2cc")
p <- ggplot() +
  annotate("rect", xmin = 0.1, xmax = 12.8, ymin = 2.75, ymax = 5.85, fill = NA, colour = "grey45", linetype = "dashed", linewidth = 0.3) +
  annotate("text", x = 0.3, y = 3.12, hjust = 0, size = 2.35, colour = "grey20", fontface = "italic",
           label = "repeated for every anchor feature and every split; 2 x p x (number of splits) model fits per call") +
  geom_rect(data = b, aes(xmin = x0, xmax = x1, ymin = y0, ymax = y1, fill = fill), colour = "grey25", linewidth = 0.3) +
  geom_text(data = b, aes((x0 + x1) / 2, (y0 + y1) / 2, label = label), size = 2.35, lineheight = 0.95) +
  geom_segment(data = a, aes(x = x, y = y, xend = xend, yend = yend), arrow = grid::arrow(length = grid::unit(0.06, "inches"), type = "closed"), linewidth = 0.3) +
  scale_fill_manual(values = fills, guide = "none") +
  coord_cartesian(xlim = c(0, 12.9), ylim = c(0.8, 7.8), expand = FALSE) + theme_void()
ggsave(file.path(fig_dir, "07_software_overview.pdf"), p, width = 6.5, height = 3.55, device = grDevices::pdf)
ggsave(file.path(fig_dir, "07_software_overview.png"), p, width = 6.5, height = 3.55, dpi = 300, bg = "white")
cat("[figure_overview] 07_software_overview ->", fig_dir, "\n")
