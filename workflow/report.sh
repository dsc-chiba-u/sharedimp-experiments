#!/usr/bin/env bash
# Snakemake HTML reports (run statistics, rule graph, software) of finished runs.
mkdir -p report
for s in 01_environment 02_validation 02b_rf_settings 03_official_umfi 04_real_data 04b_maternal 04c_null_forest 05_runtime 06_figures; do
  snakemake -s workflow/$s.smk -c1 --report report/$s.html
done
