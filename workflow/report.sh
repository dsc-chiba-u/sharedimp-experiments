#!/usr/bin/env bash
# Snakemake HTML reports (run statistics, rule graph, software) of finished runs.
mkdir -p report
for s in 01_environment 02_validation; do
  snakemake -s workflow/$s.smk --report report/$s.html
done
