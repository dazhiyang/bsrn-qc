"""
Cloud enhancement event (CEE) detection utilities.

Implements algorithms for detecting periods when measured global
irradiance is significantly higher than a clear-sky reference
(cloud enhancement events).
"""

import numpy as np
import pandas as pd


def _as_1d_array(x, name, n=None):
    """
    Convert input to 1D float array and optionally validate length.

    Parameters
    ----------
    x : array-like
        Input to convert.
    name : str
        Name used in error messages.
    n : int, optional
        Required length; if set, raise when len(x) != n.

    Returns
    -------
    np.ndarray
        1D float array.

    Raises
    ------
    ValueError
        When n is set and len(x) != n.
    """
    arr = np.asarray(x, dtype=float).reshape(-1)
    if n is not None and len(arr) != n:
        raise ValueError(f"{name} must have length {n}.")
    return arr


def _cee_to_output(index, cee_flag, method):
    """
    Standardize cloud enhancement detection outputs.

    Parameters
    ----------
    index : pandas.Index
        Output index.
    cee_flag : array-like
        1=enhancement, 0=non-enhancement, NaN=invalid.
    method : str
        Method name for output column.

    Returns
    -------
    pandas.DataFrame
        Columns: is_enhancement, cee_flag, method.
    """
    cee = np.asarray(cee_flag, dtype=float)
    is_enhancement = pd.array(cee == 1.0, dtype="boolean")
    is_enhancement[np.isnan(cee)] = pd.NA

    return pd.DataFrame(
        {
            "is_enhancement": is_enhancement,
            "cee_flag": cee,
            "method": method,
        },
        index=index,
    )


def _cee_sliding_triplet(ghi, ghi_clear, zenith, times, *,
                         window_minutes, sdev_threshold, kappa_threshold,
                         zenith_max, method):
    """
    Three-sample rolling window with clear-sky index, relative SD, and zenith gate.

    Parameters
    ----------
    ghi : array-like
        Global horizontal irradiance $G_h$. [W/m^2]
    ghi_clear : array-like
        Clear-sky global horizontal irradiance $G_{hc}$. [W/m^2]
    zenith : array-like
        Solar zenith angle $Z$. [degrees]
    times : pandas.DatetimeIndex or array-like
        Timestamps aligned to ``ghi`` (1-minute cadence expected).
    window_minutes : int
        Lag in minutes for the ``lo`` and ``hi`` samples around the centre minute.
    sdev_threshold : float
        Minimum relative standard deviation of the three-point window.
    kappa_threshold : float
        Minimum clear-sky index $\\kappa = G_h / G_{hc}$.
    zenith_max : float
        Maximum solar zenith angle for valid detection. [degrees]
    method : str
        Value for the ``method`` column in the output DataFrame.

    Returns
    -------
    pandas.DataFrame
        Standardized CEE output (``is_enhancement``, ``cee_flag``, ``method``).
    """
    # Coerce inputs to aligned 1D float arrays
    ghi = _as_1d_array(ghi, "ghi")
    ghi_clear = _as_1d_array(ghi_clear, "ghi_clear", n=len(ghi))
    zenith = _as_1d_array(zenith, "zenith", n=len(ghi))

    idx = pd.DatetimeIndex(times)
    if len(idx) != len(ghi):
        raise ValueError("times length must match inputs.")

    # Rolling triplet: t-lag, t, t+lag (minutes)
    s = pd.Series(ghi, index=idx)
    s_lo = s.shift(window_minutes)
    s_hi = s.shift(-window_minutes)
    window_df = pd.DataFrame({"lo": s_lo, "t": s, "hi": s_hi})

    # Per-row finite count, mean, sample std (ddof=1)
    n_valid = np.sum(np.isfinite(window_df.to_numpy(dtype=float)), axis=1)
    mean_val = window_df.mean(axis=1, skipna=False)
    sdev = window_df.std(axis=1, ddof=1, skipna=False)
    with np.errstate(divide="ignore", invalid="ignore"):
        sdev_rel = (sdev / mean_val).to_numpy(dtype=float)

    # Clear-sky index κ = G_h / G_{hc}
    with np.errstate(divide="ignore", invalid="ignore"):
        kappa = ghi / ghi_clear
    cond_kappa = kappa > kappa_threshold
    cond_zen = zenith < zenith_max
    cond_sdev = sdev_rel > sdev_threshold

    n = len(ghi)
    cee_flag = np.zeros(n, dtype=float)
    valid_core = (
        (n_valid == 3)
        & np.isfinite(ghi)
        & np.isfinite(ghi_clear)
        & np.isfinite(zenith)
        & (mean_val.to_numpy(dtype=float) > 0.0)
    )
    cond_all = cond_sdev & cond_kappa & cond_zen & valid_core
    cee_flag[cond_all] = 1.0
    cee_flag[~valid_core] = np.nan

    return _cee_to_output(idx, cee_flag, method)


def killinger_ced(ghi, ghi_clear, zenith, times):
    """
    Detect cloud enhancement events using Killinger et al. (2017) [1]_.

    Parameters
    ----------
    ghi : array-like
        1‑minute global horizontal irradiance. [W/m^2]
    ghi_clear : array-like
        1‑minute clear-sky global horizontal irradiance. [W/m^2]
    zenith : array-like
        1‑minute solar zenith angle. [degrees]
    times : pandas.DatetimeIndex or array-like
        1‑minute timestamps convertible to ``DatetimeIndex``.

    Returns
    -------
    pandas.DataFrame
        Standardized CEE output (``method`` column ``\"killinger\"``).

    References
    ----------
    .. [1] Killinger, S., Engerer, N., & Müller, B. (2017). QCPV: A quality
       control algorithm for distributed photovoltaic array power output.
       Solar Energy, 143, 120–131.
    """
    # Killinger-style defaults: shorter lag, looser zenith cap, lower kappa gate vs. Yang.
    return _cee_sliding_triplet(
        ghi,
        ghi_clear,
        zenith,
        times,
        window_minutes=5,
        sdev_threshold=0.05,
        kappa_threshold=1.05,
        zenith_max=85.0,
        method="killinger",
    )


def yang_ced(ghi, ghi_clear, zenith, times):
    """
    Detect cloud enhancement events using Yang et al. (2018) [1]_.

    Parameters
    ----------
    ghi : array-like
        1‑minute global horizontal irradiance. [W/m^2]
    ghi_clear : array-like
        1‑minute clear-sky global horizontal irradiance. [W/m^2]
    zenith : array-like
        1‑minute solar zenith angle. [degrees]
    times : pandas.DatetimeIndex or array-like
        1‑minute timestamps convertible to ``DatetimeIndex``.

    Returns
    -------
    out : pandas.DataFrame
        DataFrame indexed by aggregated timestamps (e.g. 6‑minute) with:

        * ``is_enhancement`` – True where a cloud enhancement is detected.
        * ``ced_flag`` – 1 for enhancement, 0 otherwise, NaN when invalid.

    References
    ----------
    .. [1] Yang, D., Yagli, G. M., & Quan, H. (2018, May). Quality control for solar
       irradiance data. In *2018 IEEE Innovative Smart Grid Technologies-Asia (ISGT Asia)*
       (pp. 208–213). IEEE.
    """
    return _cee_sliding_triplet(
        ghi,
        ghi_clear,
        zenith,
        times,
        window_minutes=6,
        sdev_threshold=0.05,
        kappa_threshold=1.10,
        zenith_max=75.0,
        method="yang",
    )


def gueymard_ced(ghi, ghi_extra, times=None):
    """
    Detect cloud enhancement events when GHI exceeds extraterrestrial GHI [1]_.

    Parameters
    ----------
    ghi : array-like
        Global horizontal irradiance. [W/m^2]
    ghi_extra : array-like
        Horizontal extraterrestrial irradiance. [W/m^2]
    times : array-like or pandas.DatetimeIndex, optional
        Time index for outputs. If None, a simple RangeIndex is used.

    Returns
    -------
    pandas.DataFrame
        Standardized CEE output with columns `is_enhancement`, `cee_flag`, `method`.

    References
    ----------
    .. [1] Gueymard, C. A. (2017). Cloud and albedo enhancement impacts on
       solar irradiance using high-frequency measurements from thermopile and
       photodiode radiometers. Part 1: Impacts on global horizontal irradiance.
       Solar Energy, 153, 755–765.
    """
    ghi = _as_1d_array(ghi, "ghi")
    ghi_extra = _as_1d_array(ghi_extra, "ghi_extra", n=len(ghi))

    if times is None:
        idx = pd.RangeIndex(start=0, stop=len(ghi), step=1, name="time")
    elif isinstance(times, pd.DatetimeIndex):
        if len(times) != len(ghi):
            raise ValueError("times length must match inputs.")
        idx = times
    else:
        idx = pd.DatetimeIndex(times)
        if len(idx) != len(ghi):
            raise ValueError("times length must match inputs.")

    with np.errstate(divide="ignore", invalid="ignore"):
        kt = ghi / ghi_extra
    cee_flag = np.zeros(len(ghi), dtype=float)
    cee_flag[kt > 1.0] = 1.0
    bad = ~np.isfinite(ghi) | ~np.isfinite(ghi_extra)
    cee_flag[bad] = np.nan

    return _cee_to_output(idx, cee_flag, "gueymard")


def detect_cee(method, **kwargs):
    """
    Wrapper for cloud enhancement event (CEE) detection methods.

    Parameters
    ----------
    method : {"killinger", "yang", "gueymard"}
        Method name.
    **kwargs : dict
        Arguments forwarded to method function.

    Returns
    -------
    pandas.DataFrame
        Standardized CEE output with is_enhancement, cee_flag, method, etc.

    Raises
    ------
    ValueError
        When method is not one of the supported CEE methods.
    """
    method_key = str(method).strip().lower()
    if method_key == "killinger":
        return killinger_ced(**kwargs)
    if method_key == "yang":
        return yang_ced(**kwargs)
    if method_key == "gueymard":
        return gueymard_ced(**kwargs)
    raise ValueError(
        "Unsupported method. Choose one of killinger, yang, gueymard."
    )
