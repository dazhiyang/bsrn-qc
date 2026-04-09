"""
Irradiance separation models (Erbs, Engerer2, etc.).
Estimates diffuse fraction and DHI/BNI from GHI.
"""

import numpy as np
import pandas as pd
from bsrn.physics import geometry
from bsrn.constants import ENGERER2_PARAMS, YANG4_PARAMS
from bsrn.utils.calculations import calc_kt


def _get_solar_and_kt(times, ghi, lat, lon, elev=0, min_mu0=0.065,
                      max_clearness_index=1.0):
    """
    Get ghi_extra, zenith, mu0, kt, and night mask for separation.

    Uses pvlib-style clearness index: ghi_extra = bni_extra * max(mu0, min_mu0),
    kt from calc_kt, clamped and set to NaN at night.

    Parameters
    ----------
    times : pd.DatetimeIndex
        Timestamps (same length as ghi).
    ghi : array-like
        Global horizontal irradiance. [W/m^2]
    lat : float
        Latitude. [degrees]
    lon : float
        Longitude. [degrees]
    elev : float, default 0
        Site elevation. [m] Used for topocentric solar position (matches pvlib when same elev).
    min_mu0 : float, default 0.065
        Minimum cosine of solar zenith for ghi_extra and kt (equiv. ~86.3 deg).
    max_clearness_index : float, default 1.0
        Upper clamp for kt.

    Returns
    -------
    ghi, ghi_extra, zenith, mu0, kt, night : tuple
        Solar and clearness index components.

    Raises
    ------
    ValueError
        If ``times`` is not a :class:`~pandas.DatetimeIndex` or ``ghi`` length mismatches.
    """

    # Check if times is a pd.DatetimeIndex.
    if not isinstance(times, pd.DatetimeIndex):
        raise ValueError("times must be a pd.DatetimeIndex.")

    ghi = np.asarray(ghi, dtype=float)
    if len(ghi) != len(times):
        raise ValueError("ghi must have the same length as times.")

    # Get the solar position.
    solpos = geometry.get_solar_position(times, lat, lon, elev)
    zenith = solpos["zenith"].values
    mu0 = np.maximum(np.cos(np.radians(zenith)), 0.0)

    # Get the extraterrestrial BNI.
    bni_extra = np.asarray(geometry.get_bni_extra(times), dtype=float)
    ghi_extra = bni_extra * np.maximum(mu0, min_mu0)

    # Get the night mask.
    night = zenith >= 90

    # Get the clearness index.
    # Keep calc_kt output as-is; nighttime separation (k, dhi, bni) is set to 0 in each model.
    kt = calc_kt(ghi, zenith, bni_extra, min_mu0=min_mu0,
                  max_clearness_index=max_clearness_index)
    return ghi, ghi_extra, zenith, mu0, kt, night

def _k_to_dhi_bni(ghi, k, zenith, max_zenith=87.0, force_nan=None):
    """
    Convert diffuse fraction $k$ to DHI and BNI with pvlib-style edge handling.

    DHI = $k \\cdot G_h$, BNI = $(G_h - \\text{DHI}) / \\mu_0$. Where
    zenith > max_zenith, GHI < 0, BNI < 0, or $\\mu_0 \\le 0$, sets BNI = 0 and
    DHI = GHI to preserve closure. Optionally force DHI/BNI to NaN where
    force_nan is True (e.g. under-sampled days in BRL).

    Parameters
    ----------
    ghi : array-like
        Global horizontal irradiance ($G_h$). [W/m^2]
    k : array-like
        Diffuse fraction ($k$). [unitless]
    zenith : array-like
        Solar zenith angle ($Z$). [degrees]
    max_zenith : float, default 87.0
        Maximum zenith for valid BNI; beyond this BNI = 0, DHI = GHI. [degrees]
    force_nan : array-like or None, default None
        If provided, DHI and BNI are set to NaN where force_nan is True.

    Returns
    -------
    dhi, bni : tuple of np.ndarray
        Diffuse horizontal and beam normal irradiance. [W/m^2]
    """

    ghi = np.asarray(ghi, dtype=float)
    k = np.asarray(k, dtype=float)
    zenith = np.asarray(zenith, dtype=float)
    mu0 = np.maximum(np.cos(np.radians(zenith)), 0.0)
    dhi = ghi * k
    with np.errstate(divide="ignore", invalid="ignore"):
        bni = (ghi - dhi) / mu0
    bad_values = (zenith > max_zenith) | (ghi < 0) | (bni < 0) | (mu0 <= 0)
    bni = np.where(bad_values, 0.0, bni)
    dhi = np.where(bad_values, ghi, dhi)
    if force_nan is not None:
        force_nan = np.asarray(force_nan, dtype=bool)
        dhi = np.where(force_nan, np.nan, dhi)
        bni = np.where(force_nan, np.nan, bni)
    return dhi, bni
    
def _apparent_solar_time(times, lon):
    """
    Calculate apparent solar time (AST, hours) from timestamps and longitude.

    Uses the equation of time formulation from Ridley et al. (2010), consistent
    with the BRL, Engerer2 and Yang4 models.

    Parameters
    ----------
    times : pd.DatetimeIndex
        Timestamps for calculation.
    lon : float
        Longitude. [degrees]

    Returns
    -------
    ast : np.ndarray
        Apparent solar time in hours. [h]
    """

    doy = times.dayofyear.values
    decimal_hour = (
        times.hour.values
        + times.minute.values / 60.0
        + times.second.values / 3600.0
    )
    beta_eot = (360.0 / 365.242) * (doy - 1)
    eot = (
        0.258 * np.cos(np.radians(beta_eot))
        - 7.416 * np.sin(np.radians(beta_eot))
        - 3.648 * np.cos(np.radians(2 * beta_eot))
        - 9.228 * np.sin(np.radians(2 * beta_eot))
    )
    lsn = 12 - lon / 15.0 - eot / 60.0
    hour_angle = (decimal_hour - lsn) * 15.0
    hour_angle = np.where(hour_angle >= 180, hour_angle - 360, hour_angle)
    hour_angle = np.where(hour_angle <= -180, hour_angle + 360, hour_angle)
    ast = hour_angle / 15.0 + 12.0
    ast = np.where(ast < 0, np.abs(ast), ast)
    return ast

def _brl_daily_clearness_index(times, ghi, ghi_extra, night):
    """
    Daily clearness index K_t = sum(ghi over day) / sum(ghi_extra over day).

    A daily K_t is only computed when more than half of the daytime hourly
    values (ghi_extra > 0) have non-NaN GHI; otherwise K_t for that day is NaN.

    Parameters
    ----------
    times : DatetimeIndex
        Timestamps for calculation.
    ghi : numeric or Series
        Global horizontal irradiance. [W/m^2]
    ghi_extra : numeric or Series
        Extraterrestrial horizontal irradiance. [W/m^2]
    night : array-like
        Night mask at the native resolution (True for night).

    Returns
    -------
    Kt : np.ndarray
        Daily clearness index ($K_t$). [unitless]
    """

    idx = pd.DatetimeIndex(times)
    ghi_ser = pd.Series(ghi, index=idx)
    ghi_extra_ser = pd.Series(ghi_extra, index=idx)
    night_ser = pd.Series(night, index=idx)

    # Resample to hourly means (GHI, GHI_extra) and any-night mask
    hourly_ghi = ghi_ser.resample("1h").mean()
    hourly_ghi_extra = ghi_extra_ser.resample("1h").mean()
    hourly_night = night_ser.resample("1h").max().astype(bool)

    # Define daytime as hours with at least one non-night sample
    is_daytime = ~hourly_night
    has_data = is_daytime & hourly_ghi.notna()

    # Per-day sums and counts restricted to daytime
    dates = hourly_ghi.index.date
    daily_ghi = hourly_ghi.where(is_daytime).groupby(dates).sum()
    daily_ghi_extra = hourly_ghi_extra.where(is_daytime).groupby(dates).sum()
    daily_count_daytime = is_daytime.groupby(dates).sum()
    daily_count_valid = has_data.groupby(dates).sum()

    # Only compute K_t when > half of daytime hours have valid data
    enough_data = daily_count_valid > (daily_count_daytime / 2.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        Kt_day = daily_ghi / daily_ghi_extra
    Kt_day = Kt_day.where(enough_data, np.nan)

    date_to_Kt = dict(zip(Kt_day.index, Kt_day.values))
    dates = np.array([t.date() for t in times])
    Kt = np.array([date_to_Kt.get(d, np.nan) for d in dates])
    return Kt

def _brl_psi(kt, night, dates):
    """
    Piecewise linear interpolation for BRL ψ parameter.

    ψ = (k_{t-1}+k_{t+1})/2 for sunrise < t < sunset; at sunrise ψ=k_{t+1}, at sunset ψ=k_{t-1}.

    Parameters
    ----------
    kt : array-like
        Clearness index. [unitless]
    night : array-like
        Night mask (True for night).
    dates : array-like
        Dates corresponding to timestamps.

    Returns
    -------
    psi : np.ndarray
        BRL ψ parameter. [unitless]
    """

    n = len(kt)
    psi = np.full(n, np.nan, dtype=float)
    kt_arr = np.asarray(kt, dtype=float)
    kt_pad = np.concatenate([[np.nan], kt_arr, [np.nan]])
    daytime = ~night
    # Per-day first and last daytime indices (sunrise / sunset)
    sunrise_idx = {}
    sunset_idx = {}
    for i in range(n):
        if not daytime[i]:
            continue
        d = dates[i]
        if d not in sunrise_idx:
            sunrise_idx[d] = i
        sunset_idx[d] = i
    for i in range(n):
        if not daytime[i]:
            continue
        d = dates[i]
        k_prev = kt_pad[i]
        k_next = kt_pad[i + 2]
        if i == sunrise_idx.get(d, -1):
            psi[i] = k_next if np.isfinite(k_next) else np.nan
        elif i == sunset_idx.get(d, -2):
            psi[i] = k_prev if np.isfinite(k_prev) else np.nan
        else:
            both = np.array([k_prev, k_next])
            psi[i] = np.nanmean(both) if np.any(np.isfinite(both)) else np.nan
    return psi


def _engerer2_k_at_resolution(df, lat, lon, period_minutes, ghi_col="ghi",
                              ghi_clear_col="ghi_clear"):
    """
    Compute Engerer2 diffuse fraction at a given temporal resolution by resampling.

    Requires a clear-sky GHI column in df (caller must provide it).

    Resamples the input to `period_minutes` using right-closed bins (e.g. (10:00, 11:00]
    for the hour labeled 11:00), runs Engerer2 with the corresponding coefficient set,
    and maps the resulting k back to the original index using first-future (backward fill):
    each 1-min time t in (10:00, 11:00] gets the hourly k at 11:00. Use this when you
    need true period-averaged Engerer2 k (e.g. k_60min for Yang4).

    Parameters
    ----------
    df : pd.DataFrame
        Input data with DatetimeIndex and a clear-sky GHI column.
    lat : float
        Latitude. [degrees]
    lon : float
        Longitude. [degrees]
    period_minutes : int
        Resampling resolution. [minutes]
    ghi_col : str, default "ghi"
        Column name for GHI. [W/m^2]
    ghi_clear_col : str, default "ghi_clear"
        Column name for clear-sky GHI. [W/m^2] Must be present in df.

    Returns
    -------
    k : np.ndarray
        Diffuse fraction k aligned to `df.index`. [unitless]

    Raises
    ------
    ValueError
        If ``ghi_clear_col`` is missing, ``period_minutes`` is unsupported, or
        ``df.index`` is not a :class:`~pandas.DatetimeIndex`.
    """
    if ghi_clear_col not in df.columns:
        raise ValueError(
            f"DataFrame must contain clear-sky column '{ghi_clear_col}'. "
            "Provide ghi_clear (e.g. :func:`bsrn.modeling.clear_sky.add_clearsky_columns`) before calling."
        )

    resample_rule = {
        1: "1min",
        5: "5min",
        10: "10min",
        15: "15min",
        30: "30min",
        60: "1h",
        1440: "1D",
    }
    if period_minutes not in resample_rule:
        raise ValueError(
            "period_minutes must be one of 1, 5, 10, 15, 30, 60, 1440."
        )
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must have a DatetimeIndex.")

    rule = resample_rule[period_minutes]
    cols = [ghi_col, ghi_clear_col]
    # Right-closed bins: (t-1h, t] so the value at 11:00 is the mean over (10:00, 11:00]
    resample_kw = {"rule": rule, "closed": "right", "label": "right"}
    counts = df[cols].resample(**resample_kw).count()
    bin_size = df.resample(**resample_kw).size()
    # Keep only those periods where more than half the data points are present for ghi_col
    enough_data = counts[ghi_col] > (bin_size / 2)
    # Compute mean over each right-closed period, set to NaN where not enough data
    df_rs = df[cols].resample(**resample_kw).mean()
    df_rs.loc[~enough_data] = np.nan
    df_rs = df_rs.dropna(subset=[ghi_col])

    # Use mid-interval timestamps for solar position so zenith/AST are representative of the hour,
    # avoiding systematic bias (e.g. end-of-hour sun making k trend monotonically through the day).
    period_td = pd.Timedelta(minutes=period_minutes)
    times_mid = df_rs.index - period_td / 2

    result = engerer2_separation(
        times_mid, df_rs[ghi_col].values, lat, lon,
        ghi_clear=df_rs[ghi_clear_col].values,
        averaging_period=period_minutes
    )
    # Align result back to hour-end index for assignment (result index is mid-interval).
    result = result.set_index(df_rs.index)

    # First-future assignment: for each 1-min t, use the hourly k at the end of the hour containing t
    # e.g. 1-min in (10:00, 11:00] get the k at 11:00 (mean over (10:00, 11:00])
    k_series = result["k"].reindex(df.index, method="bfill")
    return np.asarray(k_series, dtype=float)

def erbs_separation(times, ghi, lat, lon, elev=0, min_mu0=0.065,
                    max_zenith=87.0):
    """
    Erbs irradiance separation [1]_: diffuse fraction $k$ from clearness index $k_t$, then DHI and BNI.

    Inputs are time, ghi, and location (lat, lon, elev); zenith and clearness index are computed inside.

    Piecewise formula (Erbs et al.):
    - $k_t \\leq 0.22$: $k = 1.0 - 0.09 k_t$
    - $0.22 < k_t \\leq 0.80$: $k = 0.9511 - 0.1604 k_t + 4.388 k_t^2 - 16.638 k_t^3 + 12.336 k_t^4$
    - $k_t > 0.80$: $k = 0.165$

    Parameters
    ----------
    times : pd.DatetimeIndex
        Timestamps.
    ghi : array-like
        Global horizontal irradiance. [W/m^2]
    lat : float
        Latitude. [degrees]
    lon : float
        Longitude. [degrees]
    elev : float, default 0
        Site elevation. [m] Use same value as for zenith when comparing to pvlib.
    min_mu0 : float, default 0.065
        Minimum $\\mu_0$ when computing $k_t$.
    max_zenith : float, default 87.0
        Maximum zenith for valid BNI; beyond this BNI is set to 0. [degrees]

    Returns
    -------
    out : pd.DataFrame
        DataFrame with index=times and columns ``k``, ``dhi``, ``bni`` (modeled).

    Raises
    ------
    ValueError
        Propagated from :func:`_get_solar_and_kt` if ``times`` or ``ghi`` are invalid.

    References
    ----------
    .. [1] Erbs, D. G., Klein, S. A., & Duffie, J. A. (1982). Estimation of
       the diffuse radiation fraction for hourly, daily and monthly-average
       global radiation. Solar Energy, 28(4), 293-302.
    """
    ghi, ghi_extra, zenith, mu0, kt, night = _get_solar_and_kt(
        times, ghi, lat, lon, elev=elev, min_mu0=min_mu0, max_clearness_index=1.0
    )

    # Calculate diffuse fraction
    # For Kt <= 0.22, set the diffuse fraction
    k = 1.0 - 0.09 * kt

    # For Kt > 0.22 and Kt <= 0.8, set the diffuse fraction
    k = np.where(
        (kt > 0.22) & (kt <= 0.8),
        0.9511 - 0.1604 * kt + 4.388 * kt ** 2
        - 16.638 * kt ** 3 + 12.336 * kt ** 4,
        k
    )

    # For Kt > 0.8, set the diffuse fraction
    k = np.where(kt > 0.8, 0.165, k)

    # This ensures the diffuse fraction is physically valid; values <0 or >1 are not physical.
    k = np.clip(k, 0.0, 1.0)

    # Calculate DHI and BNI
    dhi, bni = _k_to_dhi_bni(ghi, k, zenith, max_zenith=max_zenith)

    # Nighttime separation handled by _k_to_dhi_bni and zenith limits.
    return pd.DataFrame({"k": k, "dhi": dhi, "bni": bni}, index=times)

def brl_separation(times, ghi, lat, lon, min_mu0=0.065, max_zenith=87.0):
    """
    BRL irradiance separation [1]_: diffuse fraction $k$ from logistic function of
    $k_t$, AST, $\\alpha$, $K_t$, $\\psi$.

    $k = 1 / (1 + \\exp(-5.38 + 6.63 k_t + 0.006\\,\\text{AST} - 0.007\\,\\alpha
    + 1.75 K_t + 1.31 \\psi))$. $\\psi$ at sunrise = $k_{t+1}$, at sunset =
    $k_{t-1}$, else $(k_{t-1}+k_{t+1})/2$. $K_t$ = daily clearness index.

    Parameters
    ----------
    times : pd.DatetimeIndex
        Timestamps.
    ghi : array-like
        Global horizontal irradiance. [W/m^2]
    lat : float
        Latitude. [degrees]
    lon : float
        Longitude. [degrees]
    min_mu0 : float, default 0.065
        Minimum $\\mu_0$ when computing $k_t$.
    max_zenith : float, default 87.0
        Maximum zenith for valid BNI; beyond this BNI is set to 0. [degrees]

    Returns
    -------
    out : pd.DataFrame
        DataFrame with index=times and columns ``k``, ``dhi``, ``bni`` (modeled).

    Raises
    ------
    ValueError
        Propagated from :func:`_get_solar_and_kt` if ``times`` or ``ghi`` are invalid.

    References
    ----------
    .. [1] Ridley, B., Boland, J., & Lauret, P. (2010). Modelling of
       diffuse solar fraction with multiple predictors. Renewable
       Energy, 35(2), 478-483.
    """
    ghi, ghi_extra, zenith, mu0, kt, night = _get_solar_and_kt(
        times, ghi, lat, lon, min_mu0=min_mu0, max_clearness_index=1.0
    )

    # Daily clearness index Kt (Eq. 7), only when enough daytime data
    Kt = _brl_daily_clearness_index(times, ghi, ghi_extra, night)
    good_day = np.isfinite(Kt)

    # Apparent solar time AST (hours)
    ast = _apparent_solar_time(times, lon)

    # Solar altitude alpha (degrees) = 90 - zenith
    alpha = 90.0 - zenith

    # psi: piecewise from kt at adjacent timesteps
    dates = np.array([t.date() for t in times])
    psi = _brl_psi(kt, night, dates)
    # For days without a valid Kt, psi is not defined
    psi = np.where(good_day, psi, np.nan)

    # k = 1 / (1 + exp(...)); hourly kt and daily Kt
    exponent = (
        -5.38 + 6.63 * kt + 0.006 * ast - 0.007 * alpha
        + 1.75 * Kt + 1.31 * psi
    )
    with np.errstate(invalid="ignore", over="ignore"):
        k = 1.0 / (1.0 + np.exp(exponent))

    # This ensures the diffuse fraction is physically valid; values <0 or >1 are not physical.
    k = np.clip(k, 0.0, 1.0)

    # Nighttime or days without valid Kt: k is NaN
    k = np.where(night | ~good_day, np.nan, k)

    # Calculate DHI and BNI
    dhi, bni = _k_to_dhi_bni(ghi, k, zenith, max_zenith=max_zenith, force_nan=~good_day)

    # Nighttime separation handled by _k_to_dhi_bni and zenith limits.
    return pd.DataFrame({"k": k, "dhi": dhi, "bni": bni}, index=times)

def engerer2_separation(times, ghi, lat, lon, ghi_clear, averaging_period=1):
    """
    Engerer2 irradiance separation: estimate diffuse fraction ($k$), DHI and BNI from GHI.

    Caller must provide clear-sky GHI (e.g. from a clear-sky model or add_clearsky_columns).

    Parameters
    ----------
    times : pd.DatetimeIndex
        Timestamps.
    ghi : array-like
        Global horizontal irradiance. [W/m^2]
    lat : float
        Latitude. [degrees]
    lon : float
        Longitude. [degrees]
    ghi_clear : array-like
        Clear-sky GHI. [W/m^2] Same length as times. Required.
    averaging_period : int, default 1
        Coefficient set for resolution. [minutes] 1, 5, 10, 15, 30, 60, or 1440.

    Returns
    -------
    out : pd.DataFrame
        DataFrame with index=times and columns ``k``, ``dhi``, ``bni`` (modeled).

    Raises
    ------
    ValueError
        If ``averaging_period`` is not in the supported set, ``times`` is not a
        :class:`~pandas.DatetimeIndex`, or ``ghi`` / ``ghi_clear`` lengths mismatch.

    References
    ----------
    .. [1] Bright, J. M., & Engerer, N. A. (2019). Engerer2: Global
       re-parameterisation, update, and validation of an irradiance
       separation model at different temporal resolutions. Journal of
       Renewable and Sustainable Energy, 11(3), 033701.
    .. [2] Engerer, N. A. (2015). Minute resolution estimates of the
       diffuse fraction of global irradiance for southeastern Australia.
       Solar Energy, 116, 215-237.
    """
    if averaging_period not in ENGERER2_PARAMS:
        raise ValueError(
            "averaging_period must be one of 1, 5, 10, 15, 30, 60, 1440 (minutes)."
        )
    if not isinstance(times, pd.DatetimeIndex):
        raise ValueError("times must be a pd.DatetimeIndex.")
    ghi = np.asarray(ghi, dtype=float)
    if len(ghi) != len(times):
        raise ValueError("ghi must have the same length as times.")
    ghi_clear = np.asarray(ghi_clear, dtype=float)
    if len(ghi_clear) != len(times):
        raise ValueError("ghi_clear must have the same length as times.")

    ghi, ghi_extra, zenith, mu0, kt, night = _get_solar_and_kt(
        times, ghi, lat, lon, min_mu0=0.065, max_clearness_index=1.0
    )
    ast = _apparent_solar_time(times, lon)

    ghi_extra_safe = np.where(ghi_extra > 0, ghi_extra, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        ktc = ghi_clear / ghi_extra_safe
    dktc = ktc - kt
    cloud_enh = np.where(ghi - ghi_clear > 0.015, ghi - ghi_clear, 0.0)
    # np.where evaluates both branches; divide(..., where=) skips ghi<=0 (no divide warning).
    k_de = np.zeros_like(ghi, dtype=float)
    np.divide(cloud_enh, ghi, out=k_de, where=ghi > 0)

    ktc = np.where(night, np.nan, ktc)
    dktc = np.where(night, np.nan, dktc)
    ast = np.where(night, np.nan, ast)
    k_de = np.where(night, np.nan, k_de)

    # Engerer2 logistic formula
    c, b0, b1, b2, b3, b4, b5 = ENGERER2_PARAMS[averaging_period]
    with np.errstate(invalid="ignore"):
        k = c + (1 - c) / (1 + np.exp(
            b0 + b1 * kt + b2 * ast + b3 * zenith + b4 * dktc
        )) + b5 * k_de
    k = np.clip(k, 0.0, 1.0)

    dhi, bni = _k_to_dhi_bni(ghi, k, zenith, max_zenith=87.0)

    # Nighttime separation handled by _k_to_dhi_bni and zenith limits.
    return pd.DataFrame({"k": k, "dhi": dhi, "bni": bni}, index=times)

def yang4_separation(times, ghi, lat, lon, ghi_clear):
    """
    Yang4 irradiance separation: diffuse fraction k_d from k_t, AST, Z, Δk_tc, k_de, and Engerer2 60-min k.
    k_d^YANG4 = C + (1-C)/(1 + exp(β0 + β1*k_t + β2*AST + β3*Z + β4*Δk_tc + β6*k_d,60min^ENGERER2)) + β5*k_de.
    Uses YANG2 coefficient set (TABLE III) from 1-min SURFRAD data.

    Caller must provide clear-sky GHI (e.g. from a clear-sky model or add_clearsky_columns).

    Parameters
    ----------
    times : pd.DatetimeIndex
        Timestamps.
    ghi : array-like
        Global horizontal irradiance. [W/m^2]
    lat : float
        Latitude. [degrees]
    lon : float
        Longitude. [degrees]
    ghi_clear : array-like
        Clear-sky GHI. [W/m^2] Same length as times. Required.

    Returns
    -------
    out : pd.DataFrame
        DataFrame with index=times and columns ``k``, ``dhi``, ``bni`` (modeled).

    Raises
    ------
    ValueError
        If ``times`` is not a :class:`~pandas.DatetimeIndex`, lengths mismatch, or
        :func:`_engerer2_k_at_resolution` rejects inputs (e.g. missing ``ghi_clear``).

    References
    ----------
    .. [1] Yang, D. (2021). Temporal-resolution cascade model for
       separation of 1-min beam and diffuse irradiance. Journal of
       Renewable and Sustainable Energy, 13(5), 053703.
    .. [2] Yang, D., & Boland, J. (2019). Satellite-augmented diffuse
       solar radiation separation models. Journal of Renewable and
       Sustainable Energy, 11(2), 023704.
    """
    if not isinstance(times, pd.DatetimeIndex):
        raise ValueError("times must be a pd.DatetimeIndex.")
    ghi = np.asarray(ghi, dtype=float)
    if len(ghi) != len(times):
        raise ValueError("ghi must have the same length as times.")
    ghi_clear = np.asarray(ghi_clear, dtype=float)
    if len(ghi_clear) != len(times):
        raise ValueError("ghi_clear must have the same length as times.")

    # Build minimal df for _engerer2_k_at_resolution (resampling)
    df_min = pd.DataFrame({"ghi": ghi, "ghi_clear": ghi_clear}, index=times)
    k_engerer2_60 = _engerer2_k_at_resolution(
        df_min, lat, lon, 60, ghi_col="ghi", ghi_clear_col="ghi_clear"
    )

    ghi, ghi_extra, zenith, mu0, kt, night = _get_solar_and_kt(
        times, ghi, lat, lon, min_mu0=0.065, max_clearness_index=1.0
    )
    ast = _apparent_solar_time(times, lon)

    ghi_extra_safe = np.where(ghi_extra > 0, ghi_extra, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        kt = ghi / ghi_extra_safe
        ktc = ghi_clear / ghi_extra_safe
    dktc = ktc - kt
    cloud_enh = np.where(ghi - ghi_clear > 0.015, ghi - ghi_clear, 0.0)
    k_de = np.zeros_like(ghi, dtype=float)
    np.divide(cloud_enh, ghi, out=k_de, where=ghi > 0)

    dktc = np.where(night, np.nan, dktc)
    ast = np.where(night, np.nan, ast)
    k_de = np.where(night, np.nan, k_de)
    k_engerer2_60 = np.where(night, np.nan, k_engerer2_60)

    # Yang4 logistic formula
    C, b0, b1, b2, b3, b4, b5, b6 = YANG4_PARAMS
    exponent = b0 + b1 * kt + b2 * ast + b3 * zenith + b4 * dktc + b6 * k_engerer2_60
    with np.errstate(invalid="ignore", over="ignore"):
        k = C + (1 - C) / (1 + np.exp(exponent)) + b5 * k_de
    k = np.clip(k, 0.0, 1.0)

    dhi, bni = _k_to_dhi_bni(ghi, k, zenith, max_zenith=87.0)

    # Nighttime separation handled by _k_to_dhi_bni and zenith limits.
    return pd.DataFrame({"k": k, "dhi": dhi, "bni": bni}, index=times)
