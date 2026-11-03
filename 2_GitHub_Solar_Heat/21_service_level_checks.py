"""Step 21: checks requested in review (reference model; 42 analysis months).
(1) Zone-level import, B_t(k) = sum_z max(0, L_zt - k E_zt) (the main case in steps 02-17, see service.py), compared
    with the pooled hospital-level balance, max(0, L_t - k E_t) (sensitivity case),
    for the measured scaling (Table 2) and for k*_imp and k*_peak under warming (zone loads scaled in proportion
    to the modelled change of the hospital load).
(2) Billed demand: 30-min maximum of the summed import vs sum of the zone maxima, against the billed 15-min demand.
(3) Suspected two-interval counter misallocations: flagged pairs of the import counter are replaced by their pair mean
    (energy totals unchanged; PV is left as measured because it varies genuinely with clouds); measured scaling, peak metrics and k*_imp, k*_peak are recomputed.
(4) SHHR with the PV energy used on site, A_t = min(E_t, L_t), against SHHR with E_t.
(5) Reference gradient-boosting model with 400 instead of 600 iterations (setting of the bootstrap refits).
Outputs: results_a21.json."""
import json, numpy as np, pandas as pd
from scipy import stats
src = open('09_import_multiplier.py', encoding='utf-8').read().split('yrs = len(set(pk.month))/12')[0]
exec(src)                                   # S (42 analysis months), M, FAM, TN0, GAM, Tc0, KS, kstar, dLh_of, GBM
from sklearn.ensemble import HistGradientBoostingRegressor
OUT = {}
iv = pd.read_pickle('iv.pkl')
Lz = iv.pivot_table(index=iv.index, columns='z', values='L').reindex(S.index)
Ez = iv.pivot_table(index=iv.index, columns='z', values='E').reindex(S.index)
Bz = iv.pivot_table(index=iv.index, columns='z', values='B').reindex(S.index)
on = S.on.values.astype(bool); mon = S.month.astype(str).values; yrs = len(set(mon))/12
OUT['zone_sum_check'] = dict(max_abs_diff_L=float(np.nanmax(np.abs(Lz.sum(axis=1).values - S.L.values))))

def scaling(L, E, Lzv=None, Ezv=None, ks=(0, 1, 1.5, 2, 2.5, 3, 4)):
    r = []
    for k in ks:
        if Lzv is None:
            imp = np.clip(L - k*E, 0, None); curt = np.clip(k*E - L, 0, None).sum()
        else:
            imp = np.clip(Lzv - k*Ezv, 0, None).sum(axis=1); curt = np.clip(k*Ezv - Lzv, 0, None).sum()
        r.append(dict(k=k, imp_GWh_yr=imp.sum()/1e6/yrs, peak=pd.Series(imp[on]*2).groupby(mon[on]).max().mean(),
                      curt_pct=curt/max(k*E.sum(), 1e-9)*100))
    df = pd.DataFrame(r); df['imp_red_pct'] = 100*(1 - df.imp_GWh_yr/df.imp_GWh_yr.iloc[0]); df['peak_red_pct'] = 100*(1 - df.peak/df.peak.iloc[0])
    return df

L0, E0 = S.L.values, S.E.values
agg = scaling(L0, E0); zon = scaling(L0, E0, Lz.values, Ez.values)
OUT['scaling_hospital'] = agg.to_dict('records'); OUT['scaling_service'] = zon.to_dict('records')
print('measured scaling, hospital-level\n', agg.round(2).to_string(), '\nservice-level\n', zon.round(2).to_string())

ref = FAM['GBM, monotone (reference)'](TN0).fit(M)
def kstars(m, Lbase, Ebase, Lzb, Ezb, dTs=(1.0, 2.0, 3.0)):
    f0 = m.predict(S); out = {}
    def grid(dT, service):
        X = S.copy(); X[TFE] = X[TFE] + dT
        L = np.clip(Lbase + m.predict(X) - f0, 0, None); fac = (1 + GAM*(Tc0 + dT - 25))/(1 + GAM*(Tc0 - 25))
        r = []
        for k in KS:
            if service:
                Lzz = Lzb*(L/np.maximum(Lbase, 1e-9))[:, None]; imp = np.clip(Lzz - k*Ezb*fac[:, None], 0, None).sum(axis=1)
            else:
                imp = np.clip(L - k*Ebase*fac, 0, None)
            r.append((k, imp.sum(), pd.Series(imp[on]*2).groupby(mon[on]).max().mean()))
        return pd.DataFrame(r, columns=['k', 'imp', 'peak'])
    for service in (False, True):
        b = grid(0.0, service).iloc[0]; key = 'service' if service else 'hospital'; out[key] = {}
        for dT in dTs:
            df = grid(dT, service)
            out[key][dT] = dict(k_imp=kstar(b.imp, df, 'imp', decreasing=True), k_peak=kstar(b.peak, df, 'peak', decreasing=True))
    return out
OUT['kstar_reference'] = kstars(ref, L0, E0, Lz.values, Ez.values); print(OUT['kstar_reference'])

# (2) billed demand: coincident vs non-coincident aggregation
inv = pd.read_csv('data/monthly_invoices_main_account.csv'); inv.index = inv.billing_month.astype(str)
Bon = Bz[on]; mon_on = mon[on]
coinc = pd.Series(Bon.sum(axis=1).values*2).groupby(mon_on).max()
noncoinc = (Bon*2).groupby(mon_on).max().sum(axis=1)
bd = inv.billed_demand_kW.reindex(coinc.index)
OUT['billed_demand'] = dict(
    coincident=dict(median_ratio=float((coinc/bd).median()), r=float(coinc.corr(bd)), n_above_1=int((coinc/bd > 1).sum())),
    sum_of_zone_maxima=dict(median_ratio=float((noncoinc/bd).median()), r=float(noncoinc.corr(bd)), n_above_1=int((noncoinc/bd > 1).sum())),
    mean_difference_kW=float((noncoinc - coinc).mean()), n=int(bd.notna().sum()))
print(OUT['billed_demand'])

# (3) suspected counter misallocations: pair-mean replacement on the hospital import and PV series
def pair_mean(s):
    s = s.copy(); p1, n1, p2, n2 = s.shift(1), s.shift(-1), s.shift(2), s.shift(-2)
    a = (s > 1.2*np.fmax(p2, n1)) & (p1 < 0.8*p2)           # low interval before the high one
    b = (s > 1.2*np.fmax(p1, n2)) & (n1 < 0.8*n2)           # low interval after the high one
    v = s.values.copy(); idx = np.arange(len(s)); n = 0
    for i in idx[a.values]:
        m_ = (v[i - 1] + v[i])/2; v[i - 1] = v[i] = m_; n += 1
    for i in idx[b.values & ~a.values]:
        if i + 1 < len(v):
            m_ = (v[i] + v[i + 1])/2; v[i] = v[i + 1] = m_; n += 1
    return pd.Series(v, index=s.index), n
H = pd.read_pickle('hosp.pkl'); Hc = H.copy()
Hc['B'], nB = pair_mean(H.B); Hc['L'] = H.E + Hc.B - H.X       # import counter only; PV varies genuinely with clouds
_, nE = pair_mean(H.E)                                               # PV pairs flagged by the same rule (not corrected)
Lc, Ec = Hc.L.reindex(S.index).values, Hc.E.reindex(S.index).values
OUT['cleaning'] = dict(pairs_B=int(nB), pairs_E=int(nE), energy_change_L_pct=float((np.nansum(Lc) - L0.sum())/L0.sum()*100))
def peakstats(L, E):
    B = np.clip(L - E, 0, None)  # = measured import within 0.1 % (export neglected at k = 1)
    g = pd.DataFrame({'L': L[on]*2, 'B': B[on]*2, 'm': mon[on], 't': S.index[on]})
    pkL = g.loc[g.groupby('m').L.idxmax()].set_index('m'); pkB = g.loc[g.groupby('m').B.idxmax()].set_index('m')
    hL = pkL.t.dt.hour + pkL.t.dt.minute/60; hB = pkB.t.dt.hour + pkB.t.dt.minute/60; dh = (hB - hL)
    return dict(Lpk=float(pkL.L.mean()), Bpk=float(pkB.B.mean()), dP=float((pkL.L - pkB.B).mean()), later=int((dh > 0).sum()), earlier=int((dh < 0).sum()))
OUT['cleaning']['peaks_reference'] = peakstats(L0, E0); OUT['cleaning']['peaks_clean'] = peakstats(Lc, Ec)
OUT['cleaning']['scaling_hospital'] = scaling(Lc, Ec).to_dict('records')
OUT['cleaning']['kstar'] = kstars(ref, Lc, Ec, Lz.values*(Lc/np.maximum(L0, 1e-9))[:, None], Ez.values*(Ec/np.maximum(E0, 1e-9))[:, None])
print(OUT['cleaning'])

# (4) SHHR with A_t = min(E_t, L_t)
V = M.dropna(subset=['E']).copy(); d = np.minimum(dLh_of(ref, V, TN0), V.L.values); E = V.E.values; L = V.L.values; A = np.minimum(E, L)
def shhr(P):
    return dict(hp=np.minimum(P, d).sum()/d.sum()*100, pr=(P*d/L).sum()/d.sum()*100, bl=np.minimum(np.clip(P - (L - d), 0, None), d).sum()/d.sum()*100)
OUT['shhr_E'] = shhr(E); OUT['shhr_A'] = shhr(A); OUT['share_intervals_E_gt_L'] = float((E > L).mean()*100)
print('SHHR with E', OUT['shhr_E'], 'with A', OUT['shhr_A'])

# (5) 400 vs 600 boosting iterations (full data, same seed)
m4 = GBM(FEAT, [0,0,0,1,1,1,1,1,0]); m4.mod = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, max_leaf_nodes=48,
    min_samples_leaf=40, l2_regularization=1.0, monotonic_cst=[0,0,0,1,1,1,1,1,0], categorical_features=[0,1,2], random_state=0).fit(M[FEAT], M.L)
def point(m):
    dd = np.minimum(dLh_of(m, V, TN0), L)
    ks_ = kstars(m, L0, E0, Lz.values, Ez.values, dTs=(2.0,))['hospital'][2.0]
    return dict(heat_share=dd.sum()/L.sum()*100, SHHR_pr=(A*dd/L).sum()/dd.sum()*100, SHHR_hp=np.minimum(A, dd).sum()/dd.sum()*100, **ks_)
OUT['iter600'] = point(ref); OUT['iter400'] = point(m4); print('600', OUT['iter600'], '\n400', OUT['iter400'])
json.dump(OUT, open('results_a21.json', 'w'), indent=1, default=float); print('done')
