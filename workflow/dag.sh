#!/usr/bin/env bash
# Rule graphs of the implemented workflows (needs graphviz `dot`).
mkdir -p results/figures/dag
for s in 01_environment 02_validation 02b_rf_settings 03_official_umfi 04_real_data 06_figures; do
  snakemake -s workflow/$s.smk --rulegraph | dot -Tpng > results/figures/dag/$s.png
done
