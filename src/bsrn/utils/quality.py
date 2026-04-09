"""
Quality control summary for BSRN data.
"""

import numpy as np
import pandas as pd
import bsrn.physics.geometry as geometry
import bsrn.qc.ppl as ppl
import bsrn.qc.erl as erl
import bsrn.qc.closure as closure
import bsrn.qc.k_index as k_index
import bsrn.qc.diff_ratio as diff_ratio
import bsrn.qc.tracker as tracker
from bsrn.modeling.clear_sky import add_clearsky_columns

_BSRN_MISSING_NUMERIC = (-999.0, -99.9, -99.99)
_BSRN_MISSING_ATOL = 5e-3


def _series_not_missing(s):
    """
    True where ``s`` is a measured value (not NaN / not BSRN missing codes).

    Parameters
    ----------
    s : pandas.Series
        Input column.

    Returns
    -------
    pandas.Series
        Boolean mask aligned to ``s.index``.
    """
    x = pd.to_numeric(s, errors="coerce")
    mask = x.notna().to_numpy(dtype=bool, copy=True)
    vals = x.to_numpy(dtype=np.float64, copy=True)
    for m in _BSRN_MISSING_NUMERIC:
        mask &= ~np.isclose(vals, m, rtol=0.0, atol=_BSRN_MISSING_ATOL, equal_nan=False)
    return pd.Series(mask, index=s.index)


def _series_finite_numeric(s):
    """
    True where ``s`` coerces to a finite float.

    Parameters
    ----------
    s : pandas.Series
        Input column.

    Returns
    -------
    pandas.Series
        Boolean mask aligned to ``s.index``.
    """
    x = pd.to_numeric(s, errors="coerce")
    v = x.to_numpy(dtype=np.float64, copy=False)
    ok = x.notna().to_numpy(dtype=bool, copy=True) & np.isfinite(v)
    return pd.Series(ok, index=s.index)


def get_daily_stats(df, lat, lon, elev, station_code=None):
    """
    Calculate daily QC statistics and sunshine duration.

    Parameters
    ----------
    df : pd.DataFrame
        BSRN data archive.
    lat : float
        Latitude. [degrees]
    lon : float
        Longitude. [degrees]
    elev : float
        Elevation. [m]
    station_code : str, optional
        BSRN station abbreviation. If ``ghi_clear`` / ``bni_clear`` are not on ``df``,
        used with :func:`~bsrn.modeling.clear_sky.add_clearsky_columns` so the
        **tracker** row matches :func:`~bsrn.qc.wrapper.run_qc` (Ineichen references).

    Returns
    -------
    daily_df : pd.DataFrame
        Daily counts of flags and sunshine duration metrics.

    Notes
    -----
    Minutes with BSRN missing codes (``-999``, ``-99.9``, ``-99.99``) or NaN in the
    relevant input column do not add to per-test failure sums. ``is_sunshine`` only
    counts minutes with a valid (non-missing) BNI value above the threshold.

    **TRACKER** uses Ineichen ``ghi_clear`` / ``bni_clear`` like ``run_qc`` (not the
    GHIE-only fallback). Pass ``station_code`` so Linke turbidity matches the registry;
    if only ``lat`` / ``lon`` / ``elev`` are available, clear-sky is still computed but
    turbidity defaults may differ from ``run_qc`` with a named station.
    """
    # Calculate solar geometry
    solpos = geometry.get_solar_position(df.index, lat, lon, elev)
    zenith = solpos["zenith"]
    bni_extra = geometry.get_bni_extra(df.index)
    ghi_extra = geometry.get_ghi_extra(df.index, zenith)

    nm = _series_not_missing
    g, b, d, lwd = df["ghi"], df["bni"], df["dhi"], df["lwd"]
    nm_g, nm_b, nm_d, nm_l = nm(g), nm(b), nm(d), nm(lwd)
    bni_x = pd.Series(bni_extra, index=df.index)
    geo_ok = _series_finite_numeric(zenith) & _series_finite_numeric(bni_x)

    # Sunshine duration (h): ACT = BNI > 120 W/m^2; MAX = zenith < 90°
    df["is_sunshine"] = ((df["bni"] > 120) & nm_b).astype(int)
    df["is_daylight"] = (zenith < 90).astype(int)

    # QC tests (True = pass, False = fail); failure sums exclude missing inputs per test.
    df["GHI_PPL"] = (
        (~ppl.ghi_ppl_test(g, zenith, bni_extra)) & nm_g & geo_ok
    ).astype(int)
    df["GHI_ERL"] = (
        (~erl.ghi_erl_test(g, zenith, bni_extra)) & nm_g & geo_ok
    ).astype(int)
    df["DHI_PPL"] = (
        (~ppl.dhi_ppl_test(d, zenith, bni_extra)) & nm_d & geo_ok
    ).astype(int)
    df["DHI_ERL"] = (
        (~erl.dhi_erl_test(d, zenith, bni_extra)) & nm_d & geo_ok
    ).astype(int)
    df["BNI_PPL"] = ((~ppl.bni_ppl_test(b, bni_extra)) & nm_b & geo_ok).astype(int)
    df["BNI_ERL"] = (
        (~erl.bni_erl_test(b, zenith, bni_extra)) & nm_b & geo_ok
    ).astype(int)
    df["LWD_PPL"] = (~ppl.lwd_ppl_test(lwd) & nm_l).astype(int)
    df["LWD_ERL"] = (~erl.lwd_erl_test(lwd) & nm_l).astype(int)

    v3 = nm_g & nm_b & nm_d
    low = closure.closure_low_sza_test(g, b, d, zenith)
    high = closure.closure_high_sza_test(g, b, d, zenith)
    df["CMP_CLO"] = (((~low) | (~high)) & v3).astype(int)

    v2 = nm_g & nm_d
    df["CMP_DIF"] = (
        ((~diff_ratio.k_low_sza_test(g, d, zenith))
         | (~diff_ratio.k_high_sza_test(g, d, zenith)))
        & v2
    ).astype(int)

    fail_kbkt = ~k_index.kb_kt_test(g, b, bni_extra, zenith) & nm_g & nm_b & geo_ok
    fail_kkt = (
        ~diff_ratio.k_kt_combined_test(g, d, bni_extra, zenith) & nm_g & nm_d & geo_ok
    )
    fail_kbl = ~k_index.kb_limit_test(b, bni_extra, elev, g) & nm_b & nm_g & geo_ok
    fail_ktl = ~k_index.kt_limit_test(g, bni_extra, zenith) & nm_g & geo_ok
    df["CMP_K"] = (fail_kbkt | fail_kkt | fail_kbl | fail_ktl).astype(int)

    # Tracker: match run_qc using Ineichen ghi_clear/bni_clear when not on df
    ghi_clear = df["ghi_clear"] if "ghi_clear" in df.columns else None
    bni_clear = df["bni_clear"] if "bni_clear" in df.columns else None
    if ghi_clear is None or bni_clear is None:
        if station_code is not None:
            _sky = add_clearsky_columns(df.copy(), station_code=station_code)
        else:
            _sky = add_clearsky_columns(df.copy(), lat=lat, lon=lon, elev=elev)
        ghi_clear = _sky["ghi_clear"]
        bni_clear = _sky["bni_clear"]

    vt = nm_g & nm_b & geo_ok
    pass_trk = tracker.tracker_off_test(
        g, b, zenith, ghi_extra=ghi_extra, ghi_clear=ghi_clear, bni_clear=bni_clear
    )
    df["TRACKER"] = ((~pass_trk) & vt).astype(int)

    # Aggregate by day
    daily = df.groupby(df.index.date).agg({
        'is_sunshine': 'sum',
        'is_daylight': 'sum',
        'GHI_PPL': 'sum', 'GHI_ERL': 'sum',
        'DHI_PPL': 'sum', 'DHI_ERL': 'sum',
        'BNI_PPL': 'sum', 'BNI_ERL': 'sum',
        'LWD_PPL': 'sum', 'LWD_ERL': 'sum',
        'CMP_CLO': 'sum', 'CMP_DIF': 'sum', 'CMP_K': 'sum',
        'TRACKER': 'sum'
    })

    daily['SD_ACT'] = daily['is_sunshine'] / 60.0
    daily['SD_MAX'] = daily['is_daylight'] / 60.0
    daily['SD_REL'] = (daily['SD_ACT'] / daily['SD_MAX'] * 100.0).fillna(0)

    return daily
