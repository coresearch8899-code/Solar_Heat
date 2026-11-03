# Solar_Heat: annual energy offsets and peak-demand mitigation of hospital rooftop PV

Data and analysis code for the article

> T. Saengsuwan, *Divergence between annual energy offsets and peak-demand mitigation of rooftop PV: evidence from a
> monitored tropical hospital*, submitted to the Journal of Building Engineering.

The repository contains the CT-corrected 30-min data of a 2.51 MWp, three-zone rooftop PV system at a public hospital
in Chiang Rai, Thailand (3 March 2023 to 7 September 2026), the monthly utility invoices of the main account, and the
complete Python analysis, numbered in the order of the calculation. Running it reproduces every number, table and
figure of the article. The article has no Supplementary Material; the monthly results and the extended tables are
provided here.

## Quick start

```
python -m pip install -r requirements.txt
python run_all.py                 # Windows, macOS or Linux; about 30 min on a laptop
python check_reproduction.py reference_outputs . results.json results_rev.json results_val.json results_a7.json results_a8.json results_a10.json results_a12.json results_a13.json results_a13_raw.json results_a13_gamma.json results_a17.json results_a20.json results_a21.json results_extra.json
```

`bash run_all.sh` does the same on Linux or macOS. `python run_all.py RAW.csv` starts instead from the raw zone-level
portal export (Thai headers, cumulative counters), which is available from the author on reasonable request, subject
to the hospital's approval. `python run_all.py --from 11` resumes at a given step. All outputs are written to the
repository root (ignored by git); the article figures are collected in `figures_for_submission/`.

## Repository layout

| Path | Content |
|---|---|
| `data/` | Released input data (see `DATA_DICTIONARY.md`) |
| `01a_...py` to `20_...py` | Analysis scripts, numbered in the order of the calculation |
| `run_all.py`, `run_all.sh` | Run every step in order |
| `pea_invoices.py` | Monthly invoices of the main account (same data as `data/monthly_invoices_main_account.csv`) |
| `service.py` | Zone-level energy balance used whenever PV is scaled: each zone limits its own export, so the import is the sum over zones of max(0, L_z - k E_z) |
| `pdfwrap.py` | Runs a figure script and writes a vector PDF next to every PNG |
| `check_reproduction.py` | Compares a rerun with `reference_outputs/` |
| `reference_outputs/*.json` | Result files behind the article |
| `reference_outputs/tables/` | Monthly peaks and savings, monthly invoice check, seasonal and annual indicators, measured PV scaling, model sensitivity, fine-grid multipliers |
| `reference_outputs/former_supplementary/` | Extended tables (CSV) and figures (PNG) that accompanied an earlier version of the article: QC counts, model performance, seasonal indicators, heatwaves, monthly invoice check, IPCC increments, storage screening, monthly peaks and savings, data dictionary |

## Data (`data/`)

| File | Content |
|---|---|
| `zone_30min_series.csv` | CT-corrected 30-min series of the three PV zones; input of the analysis |
| `hospital_30min_series.csv` | Hospital totals of the zone series, with the uncorrected portal import |
| `monthly_invoices_main_account.csv` | Billing month, invoiced kWh, billed 15-min demand (kW) and invoice total (THB) of the main account |
| `tab_qc.csv` | QC summary of the raw export, copied by step 01b |

Zones are numbered as in the monitoring portal. In the as-built drawings, zone 1 (2,256.24 kWp) is labelled Zone 2 and
zone 2 (207.06 kWp) Zone 1; zone 3 (49.98 kWp) is Zone 3. The main account, billed from a single 22-33 kV revenue meter,
covers all three zones.

## Analysis steps

| Step | Script | Purpose | Article |
|---|---|---|---|
| 01a | `01a_prep_from_raw_export.py` | Raw counters to 30-min intervals, QC, closure check, invoice ratio, CT correction (/1.20) | Section 2.1 |
| 01b | `01b_load_released_data.py` | Same outputs rebuilt from the released zone series (default start) | Section 2.1 |
| 02 | `02_core_analysis.py` | Change-point and gradient-boosting models, attribution, indicators, monthly peaks, tariff-equivalent cost, stress grid | Sections 2.2-2.4, 3.1, 3.4, 3.5; Table 4 |
| 03 | `03_uncertainty_and_tests.py` | Allocation rules, model ensemble with block bootstrap, HAC elasticity, peak-timing tests, month bootstrap | Table 4 CIs; Section 3.1 |
| 04 | `04_model_families.py` | Six model families (LOYO-CV) and forward holdout | Tables 3, 5 |
| 05 | `05_robustness.py` | Seasonal control, day types, extrapolation, cross-model stress test, Tn sensitivity, monthly table | Sections 3.5, 3.7; Table 7 |
| 06 | `06_multipliers_finegrid.py` | Fine-grid k*_SHHR and k*_peak, ensemble at +2 degC | Table 6 |
| 07 | `07_invoices_seasons_surfaces.py` | Invoice check and Ft, uncorrected-data case, seasons and years, six-family surfaces | Section 3.3 |
| 08 | `08_multipliers_uncorrected.py` | Multipliers with the uncorrected import | Table 7 |
| 09 | `09_import_multiplier.py` (+ `raw`) | k*_imp and k*_peak for six families and the ensemble | Tables 6-8 |
| 10 | `10_gamma_sensitivity.py` | PV temperature-coefficient sensitivity | Table 7 |
| 16 | `16_additional_tests.py` | Measured PV scaling, persistence by year, month bootstrap of the multipliers, alternative peak definitions, proxy vs billed demand | Sections 3.1, 3.2, 3.7; Tables 2, 7, 8 |
| 20 | `20_peak_proxy_checks.py` | 41 complete months; two-interval counter misallocations; proxy vs billed 15-min demand | Sections 3.1, 3.3 |
| 21 | `21_service_level_checks.py` | Service-level import, coincident vs non-coincident billed demand, pair-mean correction of suspected counter misallocations, SHHR with on-site PV, 400 vs 600 boosting iterations | Sections 2.3, 2.4, 3.2, 3.3, 3.6; Table 7 |
| 11 | `11_figures_main.py` | Derived metrics; Figs. 1, 2, 4, 5, 6 and graphical abstract | Figs. 1, 2, 4-6 |
| 12 | `12_ipcc_and_synthesis.py` | IPCC increments and synthesis figure (extended material only) | - |
| 13 | `13_figure_robustness.py` | Robustness figure | Fig. 7 |
| 14 | `14_figure_surfaces.py` | Six-family surfaces (extended material only) | - |
| 17 | `17_figure_measured_scaling.py` | Measured PV-scaling figure and table | Fig. 3; Table 2 |
| 19 | `19_collect_figures.py` | Copies figures under the article names | all figures |
| 22 | `22_article_tables.py` | Assembles Tables 2, 3, 6 and 7 of the article as CSV from the result files | Tables 2, 3, 6, 7 |

Steps 15 and 18 were retired; the other steps keep their numbers so that the result files keep their names.

## Key assumptions

- PEA time-of-use tariff 4.2.2 (22-33 kV): on-peak 4.1839 and off-peak 2.6037 THB/kWh, demand 132.93 THB/kW/month,
  Ft 0.3972 THB/kWh (a monthly Ft inferred from the invoices is a sensitivity case); on-peak 09:00-22:00 on working days.
- CT-ratio correction of 1.20 for grid import and export in every zone (confirmed on site); PV measured by the inverters
  is not corrected.
- Neutral temperature Tn = Tb = 20.0 degC; PV temperature coefficient -0.40 %/degC (sensitivity -0.30 to -0.45);
  NOCT 45 degC; zero export in the stress test (k*_imp and k*_peak do not depend on it).
- PV scaling uses the zone-level balance (each zone curtails its own surplus); the pooled hospital-level balance is a
  sensitivity case (step 21).
- The main account is billed from a single 22-33 kV revenue meter, so the billed demand is the coincident 15-min
  maximum of the three zones.
- Installed capacity 2,513.28 kWp (4,224 modules x 595 Wp).

## Reproduction

Random seeds are fixed. The reference outputs were produced by a full run from the released data on 2 November 2026
(Windows 11, Python 3.13, pandas 2.3, NumPy 2.3, scikit-learn 1.7, statsmodels 0.14, SciPy 1.16, matplotlib 3.10).
Relative to the run behind the first manuscript version, zone 3 uses the as-built 49.98 kWp, the SHHR allocation uses
the PV energy consumed on site, min(E, L), and PV scaling uses the zone-level balance (`service.py`); the last change
raised k*_peak at +2 degC from 3.18 to 3.30 and k*_imp from 1.57 to 1.58.
