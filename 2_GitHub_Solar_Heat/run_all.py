"""Run the complete analysis in the order of the calculation (Windows, macOS, Linux).

    python run_all.py              start from the released CT-corrected zone series (data/zone_30min_series.csv)
    python run_all.py RAW.csv      start from the raw zone-level portal export (available from the author on request)
    python run_all.py --from 11    resume at a given step (earlier outputs must exist)

Outputs are written to the repository root; run check_reproduction.py afterwards (see README.md).
"""
import subprocess, sys, time

FIG = 'fig'   # figure scripts are run through pdfwrap.py, which writes a vector PDF next to every PNG
STEPS = [
    ('02', '02_core_analysis.py', None, 'Models, attribution, indicators, peaks, cost, stress grid'),
    ('03', '03_uncertainty_and_tests.py', None, 'Ensemble and bootstrap CIs, peak-timing tests'),
    ('04', '04_model_families.py', None, 'Six model families, forward holdout'),
    ('05', '05_robustness.py', None, 'Seasonal control, day types, extrapolation, monthly table'),
    ('06', '06_multipliers_finegrid.py', None, 'Fine-grid k*_SHHR, k*_peak, ensemble at +2 degC'),
    ('07', '07_invoices_seasons_surfaces.py', None, 'Invoice check, Ft, uncorrected case, seasons, surfaces'),
    ('08', '08_multipliers_uncorrected.py', None, 'Multipliers with the uncorrected import'),
    ('09', '09_import_multiplier.py', None, 'k*_imp and k*_peak, six families and ensemble'),
    ('09raw', '09_import_multiplier.py', ['raw'], 'k*_imp with the uncorrected import'),
    ('10', '10_gamma_sensitivity.py', None, 'PV temperature-coefficient sensitivity'),
    ('16', '16_additional_tests.py', None, 'Measured PV scaling, month bootstrap, peak definitions'),
    ('20', '20_peak_proxy_checks.py', None, '41 complete months, counter-misallocation check'),
    ('21', '21_service_level_checks.py', None, 'Service-level import, billed-demand aggregation, pair-mean correction, iterations'),
    ('11', '11_figures_main.py', FIG, 'Figs. 1, 2, 4, 5 and derived metrics'),
    ('12', '12_ipcc_and_synthesis.py', FIG, 'Former supplementary: IPCC increments, synthesis figure'),
    ('13', '13_figure_robustness.py', FIG, 'Fig. 7'),
    ('14', '14_figure_surfaces.py', FIG, 'Former supplementary: six-family surfaces'),
    ('17', '17_figure_measured_scaling.py', FIG, 'Fig. 3, Table 3'),
    ('19', '19_collect_figures.py', None, 'Copy figures under the article names'),
    ('22', '22_article_tables.py', None, 'Tables 2, 3, 6 and 7 as CSV'),
]


def run(cmd, label, note):
    t0 = time.time()
    print(f'[{label}] {note}: {" ".join(cmd)}', flush=True)
    subprocess.run([sys.executable] + cmd, check=True)
    print(f'[{label}] done in {time.time() - t0:.0f} s', flush=True)


def main():
    args = sys.argv[1:]
    start = None
    if '--from' in args:
        i = args.index('--from'); start = args[i + 1]; del args[i:i + 2]
    if start is None:
        if args:
            run(['01a_prep_from_raw_export.py', args[0]], '01a', 'Raw export to 30-min intervals, QC, CT correction')
        else:
            run(['01b_load_released_data.py'], '01b', 'Load the released zone series')
    active = start is None
    for label, script, extra, note in STEPS:
        active = active or label == start
        if not active:
            continue
        if extra == FIG:
            run(['pdfwrap.py', script], label, note)
        else:
            run([script] + (extra or []), label, note)


if __name__ == '__main__':
    main()
