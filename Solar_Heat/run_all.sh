#!/usr/bin/env bash
# Reproduces every table and figure, in the order of the calculation.
#   bash run_all.sh            start from the released CT-corrected zone series (data/zone_30min_series.csv)
#   bash run_all.sh RAW.csv    start from the raw zone-level portal export (available from the author on request)
# Each figure script is run through pdfwrap.py so that a vector PDF is written next to every PNG.
set -e
if [ -n "$1" ]; then python 01a_prep_from_raw_export.py "$1"; else python 01b_load_released_data.py; fi
# ---- calculation ----
python 02_core_analysis.py                 # attribution, indicators, peaks, cost, stress grid, battery (~5 min)
python 03_uncertainty_and_tests.py         # ensemble + bootstrap CIs, peak tests, heatwaves (~15 min)
python 04_model_families.py                # six model families, forward holdout (~5 min)
python 05_robustness.py                    # seasonal control, day types, extrapolation, cross-model stress test
python 06_multipliers_finegrid.py          # fine-grid k*_SHHR, k*_peak and ensemble at +2 degC
python 07_invoices_seasons_surfaces.py     # invoices, Ft, uncorrected data, seasons/years, six-family surfaces (~10 min)
python 08_multipliers_uncorrected.py       # k*_SHHR, k*_peak with uncorrected import
python 09_import_multiplier.py             # k*_imp, k*_peak: six families + ensemble (~5 min)
python 09_import_multiplier.py raw         # k*_imp with uncorrected import
python 10_gamma_sensitivity.py             # PV temperature-coefficient sensitivity
python 16_additional_tests.py              # marginal capacity credit, measured PV scaling, month bootstrap, peak definitions, billed demand
python 20_peak_proxy_checks.py             # 41 complete months; counter-misallocation check of the peak proxy vs billed demand (Sections 3.1, 3.3)
# ---- figures and scenario tables ----
python pdfwrap.py 11_figures_main.py       # Figs. 1, 2, 4, 5, 6, graphical abstract; extended figures
python pdfwrap.py 12_ipcc_and_synthesis.py # extended material: IPCC increments, synthesis figure
python pdfwrap.py 13_figure_robustness.py  # Fig. 7
python pdfwrap.py 14_figure_surfaces.py    # extended material: six-family surfaces
python pdfwrap.py 17_figure_measured_scaling.py  # Fig. 3, Table 3
python pdfwrap.py 18_data_article_figures.py     # Data in Brief Figs. 1-4
python 19_collect_figures.py               # figures_for_submission/
