"""Step 22: assemble Tables 2, 3, 6 and 7 of the article from the result files of steps 02-21.
Run from the repository root after run_all.py (or point DIR to reference_outputs/ and tables/).
Outputs: table2_measured_scaling.csv, table3_model_skill.csv, table6_multipliers.csv, table7_uncertainty.csv."""
import json, os, sys
import numpy as np, pandas as pd

DIR = sys.argv[1] if len(sys.argv) > 1 else '.'
TAB = sys.argv[2] if len(sys.argv) > 2 else DIR
J = lambda f: json.load(open(os.path.join(DIR, f)))
T = lambda f: pd.read_csv(os.path.join(TAB, f))
KWP = 2513.28
f1 = lambda x: f'{x:.1f}'; f2 = lambda x: f'{x:.2f}'; rng2 = lambda a, b: f'{min(a, b):.2f}–{max(a, b):.2f}'
rng1 = lambda a, b: f'{min(a, b):.1f}–{max(a, b):.1f}'

# ---- Table 2: measured response to PV scaling (zone-level balance) ----
s = T('tab_measured_scaling.csv'); fine = T('tab_measured_scaling_fine.csv'); fine.index = fine.k.round(2)
rows = []
for _, r in s.iterrows():
    k = round(r.k, 2); fr = fine.loc[k]
    rows.append({'k': k, 'PV capacity (MWp)': f2(k*KWP/1000), 'Annual grid import (GWh/yr)': f2(r.imp_GWh_yr),
                 'Import reduction vs no PV (%)': f1(100*(1 - r.imp/s.imp[0])), 'Mean monthly net peak (kW)': f'{r.peak:,.0f}',
                 'Peak reduction vs no PV (%)': f1(100*(1 - r.peak/s.peak[0])), 'PV curtailed (%)': '–' if k == 0 else f1(r.curt),
                 'Marginal import reduction (%)': '–' if k == 0 else f'{fr.m_imp_rel:.0f}', 'Marginal peak reduction (%)': '–' if k == 0 else f'{fr.m_peak_rel:.0f}'})
t2 = pd.DataFrame(rows); t2.to_csv('table2_measured_scaling.csv', index=False)

# ---- Table 3: skill of the reference gradient-boosting model ----
R = J('results.json'); V = J('results_val.json'); rev = J('results_rev.json')
rows = [{'Test set': f"Leave-one-year-out, {c['year']}", 'Intervals': f"{c['n']:,}", 'R2': f"{c['R2']:.3f}", 'CV(RMSE) (%)': f1(c['CVRMSE']), 'NMBE (%)': f1(c['NMBE'])} for c in R['ml_cv']]
cy = rev['cv_summary']['complete_years']
rows.append({'Test set': 'Mean of complete years (2024–2025)', 'Intervals': '–', 'R2': f"{cy['R2']:.3f}", 'CV(RMSE) (%)': f1(cy['CV']), 'NMBE (%)': f1(cy['NMBE'])})
fw = V['forward']
rows.append({'Test set': 'Forward holdout (train 2023–2024, test 2025–2026)', 'Intervals': f"{fw['n_test']:,}", 'R2': f"{fw['R2']:.3f}", 'CV(RMSE) (%)': f1(fw['CV']), 'NMBE (%)': f1(fw['NMBE'])})
t3 = pd.DataFrame(rows); t3.to_csv('table3_model_skill.csv', index=False)

# ---- Table 6: preservation multipliers under warming (reference model, zone-level balance) ----
K = T('tab_kstar_fine.csv'); a13 = J('results_a13.json'); ref = a13['GBM, monotone (reference)']; a8 = J('results_a8.json')
rows = []
for _, r in K.iterrows():
    d = f'{float(r.dT):.1f}'; x = ref.get(d)
    imp = ref['base']['imp']/a13['yrs']/1e6*(1 + (x['imp_k1_rel'] if x else 0)/100)
    kimp = 1.0 if d == '0.0' else x['k_imp']; kp = r.kP
    row = {'dT (degC)': d, 'L (GWh/yr)': f2(r.L_GWh), 'Grid import at k = 1 (GWh/yr)': f2(imp), 'Net peak at k = 1 (kW)': f'{r.peak:,.0f}',
           'k*_imp': f2(kimp), 'k*_peak': '> 6' if np.isnan(kp) else f2(kp), 'SHHR_hp at k = 1 (%)': f1(r.SHHR_hp), 'k*_SHHR': f2(r.kS_hp)}
    if d == '2.0':
        e13, e8 = a13['ensemble_2C']['k_imp'], a8['ensemble_2C']
        row['k*_imp'] += f" [{e13['lo']:.2f}, {e13['hi']:.2f}]"; row['k*_peak'] += f" [{e8['kP']['lo']:.2f}, {e8['kP']['hi']:.2f}]"
        row['k*_SHHR'] += f" [{e8['kS_hp']['lo']:.2f}, {e8['kS_hp']['hi']:.2f}]"
    rows.append(row)
t6 = pd.DataFrame(rows); t6.to_csv('table6_multipliers.csv', index=False)

# ---- Table 7: separation of uncertainty sources ----
ip, ci = rev['ind_point'], rev['ind_CI']; fine2 = K[K.dT == 2.0].iloc[0]
fam = {n: v for n, v in a13.items() if isinstance(v, dict) and '2.0' in v}
a7 = J('results_a7.json'); cm = a7['cross_model_stress']; tn = a7['tn_sensitivity']; sc = a7['seasonal_control']['with_doy_harmonics']
a17 = J('results_a17.json'); mb = a17['month_bootstrap_2C']; alt = a17['alt_peak_2C']
raw = J('results_a13_raw.json')['raw']['2.0']; a12 = J('results_a12.json')['2.0']; g = J('results_a13_gamma.json')
a21 = J('results_a21.json'); a8f = [d for d in a8['fine'] if d['dT'] == 2.0][0]
vr = V['range_across_models']; unc = J('results_a10.json')['calibrated']['raw_portal']
dev = lambda x: '< 0.01' if round(x, 2) < 0.01 or x < 0.005 else f'±{x:.2f}'
rows = [
    ['Reference (GBM, Tn = 20.0 degC, corrected data)', f1(ip['heat_share']), f1(ip['SHHR_pr']), f1(ip['SHHR_hp']), f2(ref['2.0']['k_imp']), f2(fine2.kP), f2(fine2.kS_hp)],
    ['Sampling + model refits (95% CI, bootstrap ensemble)', rng1(*ci['heat_share']), rng1(*ci['SHHR_pr']), rng1(*ci['SHHR_hp']),
     rng2(a13['ensemble_2C']['k_imp']['lo'], a13['ensemble_2C']['k_imp']['hi']), rng2(a8['ensemble_2C']['kP']['lo'], a8['ensemble_2C']['kP']['hi']),
     rng2(a8['ensemble_2C']['kS_hp']['lo'], a8['ensemble_2C']['kS_hp']['hi'])],
    ['Model family (six families)', rng1(*vr['heat_share']), rng1(*vr['SHHR_pr']), rng1(*vr['SHHR_hp']),
     rng2(min(v['2.0']['k_imp'] for v in fam.values()), max(v['2.0']['k_imp'] for v in fam.values())),
     rng2(min(v['2.0']['k_peak'] for v in fam.values()), max(v['2.0']['k_peak'] for v in fam.values())),
     rng2(min(v['kS_hp_2.0'] for v in cm.values()), max(v['kS_hp_2.0'] for v in cm.values()))],
    ['Neutral temperature (Tn = 18.0–22.0 degC)', rng1(min(v['heat_share'] for v in tn.values()), max(v['heat_share'] for v in tn.values())),
     rng1(min(v['SHHR_pr'] for v in tn.values()), max(v['SHHR_pr'] for v in tn.values())), rng1(min(v['SHHR_hp'] for v in tn.values()), max(v['SHHR_hp'] for v in tn.values())),
     'indep.', 'indep.', rng2(min(v['kS_hp_2'] for v in tn.values()), max(v['kS_hp_2'] for v in tn.values()))],
    ['Seasonal control (day-of-year harmonics)', f1(sc['heat_share']), f1(sc['SHHR_pr']), f1(sc['SHHR_hp']), '–', '–', '–'],
    ['Sampling of months (95%, month bootstrap; k*_peak > 6 right-censored)', '–', '–', '–', rng2(mb['k_imp'][0], mb['k_imp'][2]), rng2(mb['k_peak'][0], mb['k_peak'][2]), '–'],
    ['Peak definition (top-3 mean; all-hours maximum)', '–', '–', '–', 'indep.', rng2(alt['top3_on']['k_star'], alt['all_hours']['k_star']), '–'],
    ['Allocation rule (bounds; order-averaged)', '–', f"{ip['SHHR_bl']:.1f}–{ip['SHHR_hp']:.1f}; {(ip['SHHR_bl'] + ip['SHHR_hp'])/2:.1f}", 'upper bound', 'indep.', 'indep.', f"{a8f['kS_pr']:.2f} (prop.)"],
    ['Scenario: PV temperature coefficient (gamma = -0.30 to -0.45 %/degC)', '–', '–', '–',
     dev(max(abs(g[x]['k_imp'] - g['-0.004']['k_imp']) for x in g)), dev(max(abs(g[x]['k_peak'] - g['-0.004']['k_peak']) for x in g)),
     # the reference value lies between the two scenario values (monotone in gamma), so half their spread bounds the change
     dev(abs(rev['gamma_sens']['-0.0045_scen']['kS'] - rev['gamma_sens']['-0.003_scen']['kS']))],
    ['Metering: uncorrected portal data (x1.20)', f1(unc['heat_share']), f1(unc['SHHR_pr']), f1(unc['SHHR_hp']), f2(raw['k_imp']), f2(raw['k_peak']), f2(a12['kS_hp'])],
    ['Import computed for the hospital as a whole (zones pooled)', '–', '–', '–', f2(a21['kstar_reference']['hospital']['2.0']['k_imp']), f2(a21['kstar_reference']['hospital']['2.0']['k_peak']), '–'],
    ['Suspected counter misallocations corrected (pair mean)', '–', '–', '–', f2(a21['cleaning']['kstar']['service']['2.0']['k_imp']), f2(a21['cleaning']['kstar']['service']['2.0']['k_peak']), '–'],
]
t7 = pd.DataFrame(rows, columns=['Source of uncertainty', 'Temp.-driven share (%)', 'SHHR_pr (%)', 'SHHR_hp (%)', 'k*_imp at +2 degC', 'k*_peak at +2 degC', 'k*_SHHR at +2 degC'])
t7.to_csv('table7_uncertainty.csv', index=False)
for name, t in [('Table 2', t2), ('Table 3', t3), ('Table 6', t6), ('Table 7', t7)]:
    print('\n' + name); print(t.to_string(index=False))
