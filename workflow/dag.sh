#!/usr/bin/env bash
# Rule graphs of the implemented workflows (needs graphviz `dot`).
mkdir -p results/figures/dag
for s in 01_environment 02_validation; do
  snakemake -s workflow/$s.smk --rulegraph | dot -Tpng > results/figures/dag/$s.png
done
