"""
High-level QC runners and metadata helpers for BSRN DataFrames.
"""

import numpy as np
import pandas as pd
from bsrn.physics import geometry
from bsrn.constants import BSRN_STATIONS
from . import ppl, erl, closure, diff_ratio, k_index, tracker


def _get_metadata(station_code, lat, lon, elev):
    """
    Resolve lat/lon/elev from explicit values and/or BSRN station registry.

    Parameters
    ----------
    station_code : str or None
        BSRN station abbreviation, if used for lookup.
    lat, lon, elev : float or None
        Explicit coordinates; missing pieces may be filled from the registry.

    Returns
    -------
    tuple of float
        ``(lat, lon, elev)`` in degrees and meters.

    Raises
    ------
    ValueError
        If the station is unknown or coordinates are insufficient.
    """
    # Case 1: user provided explicit coordinates
    if lat is not None and lon is not None and elev is not None:
        return lat, lon, elev

    # Case 2: user provided a BSRN station code
    if station_code is not None:
        if station_code in BSRN_STATIONS:
            meta = BSRN_STATIONS[station_code]
            # Use provided values if available, otherwise fallback to registry
            lat = lat if lat is not None else meta['lat']
            lon = lon if lon is not None else meta['lon']
            elev = elev if elev is not None else meta['elev']
            return lat, lon, elev
        else:
            raise ValueError(
                f"Station '{station_code}' not found in BSRN registry. "
                "For non-BSRN stations, you must provide 'lat', 'lon', and 'elev' manually."
            )

    # Case 3: no station code and missing coordinates
    raise ValueError(
        "Insufficient metadata. Provide a valid BSRN 'station_code' or "
        "explicit 'lat', 'lon', and 'elev'."
    )


# Flag column → value columns to set NaN where flag == 1 (fail). Matches
# :mod:`bsrn.visualization.daily` QC marker grouping (not a blind row-sum).
_QC_SINGLE_FLAG_TARGETS = (
    ("flagPPLGHI", ("ghi",)),
    ("flagPPLBNI", ("bni",)),
    ("flagPPLDHI", ("dhi",)),
    ("flagPPLLWD", ("lwd",)),
    ("flagERLGHI", ("ghi",)),
    ("flagERLBNI", ("bni",)),
    ("flagERLDHI", ("dhi",)),
    ("flagERLLWD", ("lwd",)),
)
# If any listed flag is 1, NaN all listed value columns (OR over flags).
_QC_COMBINED_FLAG_TARGETS = (
    (("flag3lowSZA", "flag3highSZA"), ("ghi", "bni", "dhi")),
    (("flagKKt", "flagKlowSZA", "flagKhighSZA"), ("ghi", "dhi")),
    (("flagKbKt", "flagKb", "flagKt", "flagTracker"), ("ghi", "bni")),
)
_QC_FLAG_COLUMN_NAMES = frozenset(
    f for f, _ in _QC_SINGLE_FLAG_TARGETS
) | frozenset(
    f for grp, _ in _QC_COMBINED_FLAG_TARGETS for f in grp
)


def mask_failed_irradiance(df, *, flag_remove=True):
    """
    Set shortwave / longwave irradiance columns to NaN where QC flags fail.

    Uses the same flag-to-column mapping as :func:`run_qc` outputs: each
    single-flag column (e.g. ``flagPPLGHI``) clears only its component; closure,
    diffuse-ratio, k-index, and tracker groups clear the components those tests share.
    Mutates ``df`` in place for irradiance values. When ``flag_remove`` is True
    (default), standard :func:`run_qc` flag columns are dropped afterward.

    Parameters
    ----------
    df : pandas.DataFrame
        Frame that already contains ``run_qc`` flag columns.
    flag_remove : bool, optional
        If True (default), drop QC flag columns after masking.

    Returns
    -------
    pandas.DataFrame
        ``df`` (same object), updated in place.

    Notes
    -----
    Call this **after** :func:`run_qc` when you want failed minutes cleared;
    :func:`run_qc` does not invoke it automatically.

    To keep an unmodified copy, run ``mask_failed_irradiance(df.copy(), ...)``.

    Does not clear auxiliary columns (e.g. ``ghi_clear``, ``zenith``).
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input 'df' must be a pandas DataFrame.")

    for fcol, vcols in _QC_SINGLE_FLAG_TARGETS:
        if fcol not in df.columns:
            continue
        bad = df[fcol].to_numpy() == 1
        if not bad.any():
            continue
        for vc in vcols:
            if vc in df.columns:
                df.loc[bad, vc] = np.nan

    for fcols, vcols in _QC_COMBINED_FLAG_TARGETS:
        present = [c for c in fcols if c in df.columns]
        if not present:
            continue
        bad = (df[present].to_numpy() == 1).any(axis=1)
        if not bad.any():
            continue
        for vc in vcols:
            if vc in df.columns:
                df.loc[bad, vc] = np.nan

    if flag_remove:
        drop_flags = [c for c in df.columns if c in _QC_FLAG_COLUMN_NAMES]
        if drop_flags:
            df.drop(columns=drop_flags, inplace=True)

    return df


def run_qc(df, station_code=None, lat=None, lon=None, elev=None,
           tests=('ppl', 'erl', 'closure', 'diff_ratio', 'k_index', 'tracker')):
    r"""
    Run a suite of QC tests on a BSRN DataFrame with optimized geometry calculations [1]_ [2]_.

    Parameters
    ----------
    df : pd.DataFrame
        Input BSRN data containing irradiance ($G_h, B_n, D_h, L_d$) and/or
        meteorological ($T, RH, P$) columns.
    station_code : str, optional
        BSRN station code to retrieve coordinates.
    lat : float, optional
        Latitude ($\phi$). [degrees]
    lon : float, optional
        Longitude ($\lambda$). [degrees]
    elev : float, optional
        Elevation ($H$). [m]
    tests : tuple of str, optional
        List of tests to run (e.g., 'ppl', 'erl', 'closure'). Default is all.

    Returns
    -------
    df : pd.DataFrame
        DataFrame with added QC flag columns (0 = Pass, 1 = Fail).

    Raises
    ------
    TypeError
        If ``df`` is not a :class:`~pandas.DataFrame`.
    ValueError
        If the index is not a :class:`~pandas.DatetimeIndex` or metadata resolution fails
        (see :func:`_get_metadata`).

    References
    ----------
    .. [1] Long, C. N., & Shi, Y. (2008). An automated quality assessment 
       and control algorithm for surface radiation measurements. The Open 
       Atmospheric Science Journal, 2(1), 23-37.
    .. [2] Forstinger, A., et al. (2021). Expert quality control of solar 
       radiation ground data sets. In SWC 2021: ISES Solar World Congress. 
       International Solar Energy Society.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input 'df' must be a pandas DataFrame.")

    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(
            "DataFrame index must be a DatetimeIndex to calculate solar position."
        )

    # 0. Validate metadata
    try:
        lat, lon, elev = _get_metadata(station_code, lat, lon, elev)
    except ValueError as e:
        raise ValueError(f"QC metadata error: {str(e)}") from e

    # 1. Pre-calculate solar geometry
    solpos = geometry.get_solar_position(df.index, lat, lon, elev)
    zenith = solpos["zenith"]
    bni_extra = geometry.get_bni_extra(df.index)

    # 2. Apply requested tests
    if 'ppl' in tests:
        if 'ghi' in df.columns:
            df['flagPPLGHI'] = (~ppl.ghi_ppl_test(df['ghi'], zenith, bni_extra)).astype(int)
        if 'bni' in df.columns:
            df['flagPPLBNI'] = (~ppl.bni_ppl_test(df['bni'], bni_extra)).astype(int)
        if 'dhi' in df.columns:
            df['flagPPLDHI'] = (~ppl.dhi_ppl_test(df['dhi'], zenith, bni_extra)).astype(int)
        if 'lwd' in df.columns:
            df['flagPPLLWD'] = (~ppl.lwd_ppl_test(df['lwd'])).astype(int)

    if 'erl' in tests:
        if 'ghi' in df.columns:
            df['flagERLGHI'] = (~erl.ghi_erl_test(df['ghi'], zenith, bni_extra)).astype(int)
        if 'bni' in df.columns:
            df['flagERLBNI'] = (~erl.bni_erl_test(df['bni'], zenith, bni_extra)).astype(int)
        if 'dhi' in df.columns:
            df['flagERLDHI'] = (~erl.dhi_erl_test(df['dhi'], zenith, bni_extra)).astype(int)
        if 'lwd' in df.columns:
            df['flagERLLWD'] = (~erl.lwd_erl_test(df['lwd'])).astype(int)

    if 'closure' in tests:
        if all(c in df.columns for c in ['ghi', 'bni', 'dhi']):
            df['flag3lowSZA'] = (~closure.closure_low_sza_test(df['ghi'], df['bni'], df['dhi'], zenith)).astype(int)
            df['flag3highSZA'] = (~closure.closure_high_sza_test(df['ghi'], df['bni'], df['dhi'], zenith)).astype(int)

    if 'diff_ratio' in tests:
        if all(c in df.columns for c in ['ghi', 'dhi']):
            df['flagKKt'] = (~diff_ratio.k_kt_combined_test(df['ghi'], df['dhi'], bni_extra, zenith)).astype(int)
            df['flagKlowSZA'] = (~diff_ratio.k_low_sza_test(df['ghi'], df['dhi'], zenith)).astype(int)
            df['flagKhighSZA'] = (~diff_ratio.k_high_sza_test(df['ghi'], df['dhi'], zenith)).astype(int)

    if 'k_index' in tests:
        if all(c in df.columns for c in ['ghi', 'bni']):
            df['flagKbKt'] = (~k_index.kb_kt_test(df['ghi'], df['bni'], bni_extra, zenith)).astype(int)
            df['flagKb'] = (~k_index.kb_limit_test(df['bni'], bni_extra, elev, df['ghi'])).astype(int)
            df['flagKt'] = (~k_index.kt_limit_test(df['ghi'], bni_extra, zenith)).astype(int)

    if 'tracker' in tests:
        if all(c in df.columns for c in ['ghi', 'bni']):
            ghi_extra = geometry.get_ghi_extra(df.index, zenith)
            ghi_c = df['ghi_clear'] if 'ghi_clear' in df.columns else None
            bni_c = df['bni_clear'] if 'bni_clear' in df.columns else None
            f_pass = tracker.tracker_off_test(df['ghi'], df['bni'], zenith, ghi_extra=ghi_extra, 
                                            ghi_clear=ghi_c, bni_clear=bni_c)
            df['flagTracker'] = (~f_pass).astype(int)

    return df


def test_physically_possible(df, station_code=None, lat=None,
                             lon=None, elev=None):
    """
    Run all Phase 1 (Physically Possible) checks on a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input BSRN data.
    station_code : str, optional
        BSRN station code.
    lat, lon, elev : float, optional
        Station coordinates and elevation.

    Returns
    -------
    df : pd.DataFrame
        DataFrame with added 'flagPPL*' flag columns.

    Raises
    ------
    TypeError, ValueError
        Same as :func:`run_qc` for the ``ppl`` test subset.
    """
    return run_qc(df, station_code, lat, lon, elev, tests=('ppl',))


def test_extremely_rare(df, station_code=None, lat=None,
                        lon=None, elev=None):
    """
    Run all Phase 2 (Extremely Rare) checks on a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input BSRN data.
    station_code : str, optional
        BSRN station code.
    lat, lon, elev : float, optional
        Station coordinates and elevation.

    Returns
    -------
    df : pd.DataFrame
        DataFrame with added 'flagERL*' flag columns.

    Raises
    ------
    TypeError, ValueError
        Same as :func:`run_qc` for the ``erl`` test subset.
    """
    return run_qc(df, station_code, lat, lon, elev, tests=('erl',))


def test_closure(df, station_code=None, lat=None,
                 lon=None, elev=None):
    """
    Run all Phase 3 (Closure) consistency checks on a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input BSRN data.
    station_code : str, optional
        BSRN station code.
    lat, lon, elev : float, optional
        Station coordinates and elevation.

    Returns
    -------
    df : pd.DataFrame
        DataFrame with added 'flag3lowSZA' and 'flag3highSZA' flag columns.

    Raises
    ------
    TypeError, ValueError
        Same as :func:`run_qc` for the ``closure`` test subset.
    """
    return run_qc(df, station_code, lat, lon, elev, tests=('closure',))


def test_diff_ratio(df, station_code=None, lat=None,
                    lon=None, elev=None):
    """
    Run all Phase 3 Diffuse Ratio (k) consistency checks on a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input BSRN data.
    station_code : str, optional
        BSRN station code.
    lat, lon, elev : float, optional
        Station coordinates and elevation.

    Returns
    -------
    df : pd.DataFrame
        DataFrame with added 'flagKKt', 'flagKlowSZA', 'flagKhighSZA' flag columns.

    Raises
    ------
    TypeError, ValueError
        Same as :func:`run_qc` for the ``diff_ratio`` test subset.
    """
    return run_qc(df, station_code, lat, lon, elev, tests=('diff_ratio',))


def test_k_index(df, station_code=None, lat=None,
                 lon=None, elev=None):
    """
    Run all Phase 3 Radiometric Index (k-index) checks on a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input BSRN data.
    station_code : str, optional
        BSRN station code.
    lat, lon, elev : float, optional
        Station coordinates and elevation.

    Returns
    -------
    df : pd.DataFrame
        DataFrame with added 'flagKbKt', 'flagKb', 'flagKt' flag columns.

    Raises
    ------
    TypeError, ValueError
        Same as :func:`run_qc` for the ``k_index`` test subset.
    """
    return run_qc(df, station_code, lat, lon, elev, tests=('k_index',))


def test_tracker_off(df, station_code=None, lat=None,
                     lon=None, elev=None):
    """
    Run Tracker-off detection on a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input BSRN data.
    station_code : str, optional
        BSRN station code.
    lat, lon, elev : float, optional
        Station coordinates and elevation.

    Returns
    -------
    df : pd.DataFrame
        DataFrame with added 'flagTracker' flag column.

    Raises
    ------
    TypeError, ValueError
        Same as :func:`run_qc` for the ``tracker`` test subset.
    """
    return run_qc(df, station_code, lat, lon, elev, tests=('tracker',))
