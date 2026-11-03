"""Zone-level (service-level) energy balance used whenever PV is scaled.

Each zone limits its own export through its portal meter (zero-export signal), so surplus PV in one zone cannot
offset the load of another zone. With PV scaled by k, the PV energy used on site is

    U_t = sum_z min(L_zt, k E_zt),   import B_t = L_t - U_t,   curtailment = k E_t - U_t.

Scaled or perturbed hospital totals are distributed over the zones with the observed zone shares of the interval
(load in proportion to the zone loads, PV in proportion to the zone PV outputs)."""
import numpy as np, pandas as pd


def zone_weights(index, c=1.0):
    """Zone shares of load and PV for the intervals in `index` (n x 3 arrays). `c` rescales import and export
    (c = 1.20 reproduces the uncorrected portal data)."""
    iv = pd.read_pickle('iv.pkl')
    wide = lambda col: iv.pivot_table(index=iv.index, columns='z', values=col).reindex(index).values
    Ez, Bz, Xz = wide('E'), wide('B'), wide('X')
    Lz = Ez + c*Bz - c*np.nan_to_num(Xz)
    L, E = Lz.sum(axis=1), Ez.sum(axis=1)
    wL = np.divide(Lz, L[:, None], out=np.zeros_like(Lz), where=L[:, None] > 0)
    wE = np.divide(Ez, E[:, None], out=np.zeros_like(Ez), where=E[:, None] > 0)
    bad = ~np.isfinite(wL).all(axis=1) | ~np.isfinite(wE).all(axis=1) | (L <= 0)
    wL[bad] = [1.0, 0.0, 0.0]; wE[bad] = [1.0, 0.0, 0.0]          # fall back to the hospital-level balance
    return wL, wE


def used(L, E, wL, wE):
    """PV energy used on site when every zone limits its own export: sum_z min(L w_Lz, E w_Ez)."""
    L = np.asarray(L, dtype=float); E = np.asarray(E, dtype=float)
    return np.minimum(L[:, None]*wL, E[:, None]*wE).sum(axis=1)
