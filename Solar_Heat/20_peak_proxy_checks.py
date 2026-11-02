"""Step 20 (released data only): checks of the monthly 30-min peak proxy reported in Sections 3.1 and S6.
(1) 41 complete months (April 2023 - August 2026, excluding the partial commissioning month March 2023);
(2) two-interval counter misallocations (energy of one interval logged in the next), which pass the QC rules:
    a high interval (> 1.2 x the outer neighbours) next to a low interval (< 0.8 x its other neighbour);
    the flagged pair is removed and the peak metrics and the comparison with billed 15-min demand recomputed.
Outputs: results_a20.json, peaks_monthly_checks.csv."""
import pandas as pd, numpy as np, json, sys
from scipy import stats
HF = sys.argv[1] if len(sys.argv) > 1 else 'data/hospital_30min_series.csv'
IF = sys.argv[2] if len(sys.argv) > 2 else 'data/monthly_invoices_main_account.csv'
TAR = dict(on=4.1839, off=2.6037, dem=132.93, ft=0.3972); KWP = 2513.28  # 4,224 x 595 Wp (as-built string layout)
H = pd.read_csv(HF, parse_dates=['interval_end_local_time']).set_index('interval_end_local_time')
H = H.rename(columns={'pv_kWh': 'E', 'gross_load_kWh': 'L', 'grid_import_kWh': 'B', 'non_working_day': 'hol'})
H['hol'] = H.hol.astype(bool)
h = H.index.hour + H.index.minute/60
H['on'] = (~H.hol) & (h > 9) & (h <= 22)                 # as in step 02
H['month'] = H.index.to_period('M')
V = H.dropna(subset=['E', 'L', 'B'])
cnt = V.groupby('month').size()

def flag(s):
    p1, n1, p2, n2 = s.shift(1), s.shift(-1), s.shift(2), s.shift(-2)
    hi_after_low = (s > 1.2*np.fmax(p2, n1)) & (p1 < 0.8*p2)      # low interval before the high one
    hi_before_low = (s > 1.2*np.fmax(p1, n2)) & (n1 < 0.8*n2)     # low interval after the high one
    bad = hi_after_low | hi_before_low
    return bad | hi_after_low.shift(-1, fill_value=False) | hi_before_low.shift(1, fill_value=False)

def peaks(V):
    on = V[V.on]; g = on.groupby('month')
    pk = pd.DataFrame({'Lpk': g.L.max()*2, 'Bpk': g.B.max()*2, 'tL': g.L.idxmax(), 'tB': g.B.idxmax()})
    pk = pk[cnt.reindex(pk.index) > 48*25]               # analysis months, as in step 02
    pk['dP'] = pk.Lpk - pk.Bpk
    return pk

def summary(V, pk, inv):
    f = V[V.month.isin(pk.index)]; n = len(pk)
    def bill(c):
        en = f[f.on][c].sum()*(TAR['on'] + TAR['ft']) + f[~f.on][c].sum()*(TAR['off'] + TAR['ft'])
        return en, (f[f.on].groupby('month')[c].max()*2).sum()*TAR['dem']
    (eL, dL), (eB, dB) = bill('L'), bill('B')
    dh = (pk.tB.dt.hour + pk.tB.dt.minute/60) - (pk.tL.dt.hour + pk.tL.dt.minute/60); nz = dh[dh != 0]
    bd = inv.reindex(pk.index); r = pk.Bpk/bd
    return dict(n_months=n, Lpk_mean=pk.Lpk.mean(), Bpk_mean=pk.Bpk.mean(), dP_mean=pk.dP.mean(), ECC=pk.dP.mean()/KWP*100,
                energy_saving_MTHB_yr=(eL - eB)/n*12/1e6, demand_saving_MTHB_yr=(dL - dB)/n*12/1e6,
                later=int((dh > 0).sum()), earlier=int((dh < 0).sum()), same_time_of_day=int((dh == 0).sum()),
                sign_p=float(stats.binomtest(int((nz > 0).sum()), len(nz), 0.5).pvalue),
                share_B_after15=float(((pk.tB.dt.hour + pk.tB.dt.minute/60) >= 15).mean()*100),
                r_billed=float(pk.Bpk.corr(bd)), ratio_median=float(r.median()), ratio_q25=float(r.quantile(.25)),
                ratio_q75=float(r.quantile(.75)), n_ratio_above_1=int((r > 1).sum()), ratio_max=float(r.max()),
                ratio_max_month=str(r.idxmax()))

inv = pd.read_csv(IF); inv.index = pd.PeriodIndex(inv.billing_month, freq='M'); inv = inv.billed_demand_kW
OUT = {}
pk = peaks(V); OUT['reference_42'] = summary(V, pk, inv)
p41 = pk[pk.index >= pd.Period('2023-04', 'M')]; OUT['complete_41'] = summary(V, p41, inv)
bad = (flag(H.B) | flag(H.L)).reindex(V.index).fillna(False)
OUT['n_flagged_intervals'] = int(bad.sum()); OUT['n_flagged_onpeak'] = int((bad & V.on).sum())
pkc = peaks(V[~bad]); OUT['artefacts_removed'] = summary(V[~bad], pkc, inv)
OUT['months_peak_set_by_artefact'] = sorted({str(m) for m in pk.index if bad.get(pk.loc[m, 'tB'], False) or bad.get(pk.loc[m, 'tL'], False)})
out = pk[['Lpk', 'Bpk', 'tL', 'tB']].join(pkc[['Lpk', 'Bpk', 'tL', 'tB']], rsuffix='_clean')
out['billed_kW'] = inv.reindex(out.index); out['ratio'] = out.Bpk/out.billed_kW; out['ratio_clean'] = out.Bpk_clean/out.billed_kW
out.to_csv('peaks_monthly_checks.csv')
json.dump(OUT, open('results_a20.json', 'w'), indent=1, default=float)
print(json.dumps(OUT, indent=1, default=float))
print(out[out.ratio > 1].round(3).to_string())
