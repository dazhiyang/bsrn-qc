"""
Clear-sky detection (CSD) utilities.

Implements selected CSD methods from the MATLAB csd-library with a common
Python output interface.

Original MATLAB implementations and methodology definitions are from
Jamie M. Bright's clear-sky detection library:
https://github.com/JamieMBright/csd-library
"""

import warnings
import numpy as np
import pandas as pd


def _as_1d_array(x, name, n=None):
    """
    Convert input to 1D float array and validate length.

    Parameters
    ----------
    x : array-like
        Input to convert.
    name : str
        Name for error messages.
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


def _resolve_index(times, n):
    """
    Resolve output index.

    Parameters
    ----------
    times : array-like, pd.DatetimeIndex, or None
        Time index; if None, return integer range.
    n : int
        Expected length.

    Returns
    -------
    pd.RangeIndex or pd.DatetimeIndex
        Index of length n.

    Raises
    ------
    ValueError
        When len(times) != n.
    """
    if times is None:
        return pd.RangeIndex(start=0, stop=n, step=1, name="time")
    if isinstance(times, pd.DatetimeIndex):
        if len(times) != n:
            raise ValueError("times length must match inputs.")
        return times
    idx = pd.DatetimeIndex(times)
    if len(idx) != n:
        raise ValueError("times length must match inputs.")
    return idx


def _hankel_window(values, window):
    """
    Build MATLAB-style Hankel windows with trailing NaN padding.

    Equivalent to MATLAB: to avoid a loop, the time series are concatenated
    with a tail so one matrix call builds all windows, e.g.
    ``ghi_window = hankel(ghi, [ghi(end), NaN(1, interval_size-1)])``.
    Each row i is the window [values[i], values[i+1], ..., values[i+window-1]],
    with NaN padding where the window extends past the end of the series.

    Parameters
    ----------
    values : array-like
        1D time series.
    window : int
        Window length (number of columns).

    Returns
    -------
    np.ndarray
        Shape (len(values), window); row i = window starting at index i.
    """
    n = len(values)
    mat = np.full((n, window), np.nan, dtype=float)
    for i in range(window):
        end = n - i
        if end > 0:
            mat[:end, i] = values[i:]
    return mat


def _window_sufficient_valid(window_mat):
    """
    True where each row has more than half non-NaN (e.g. window=10 -> at least 5).

    Parameters
    ----------
    window_mat : np.ndarray
        2D array, shape (n, window).

    Returns
    -------
    np.ndarray of bool
        True where row has >= (window+1)//2 finite values.
    """
    n_valid = np.sum(np.isfinite(window_mat), axis=1)
    min_required = (window_mat.shape[1] + 1) // 2
    return n_valid >= min_required



def _safe_divide(num, den):
    """
    Safe division with NaN on invalid entries.

    Parameters
    ----------
    num : array-like
        Numerator.
    den : array-like
        Denominator.

    Returns
    -------
    np.ndarray
        num/den with non-finite results set to NaN.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        out = num / den
    out[~np.isfinite(out)] = np.nan
    return out


def _nanmax_no_warn(arr, axis):
    """
    nanmax without emitting all-NaN runtime warnings.

    Parameters
    ----------
    arr : np.ndarray
        Input array.
    axis : int
        Axis over which to take maximum.

    Returns
    -------
    np.ndarray
        np.nanmax(arr, axis=axis).
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        out = np.nanmax(arr, axis=axis)
    return out


def _nanstd_no_warn(arr, axis, ddof=0):
    """
    nanstd without emitting empty-slice runtime warnings.

    Parameters
    ----------
    arr : np.ndarray
        Input array.
    axis : int
        Axis over which to take standard deviation.
    ddof : int, default 0
        Delta degrees of freedom for std.

    Returns
    -------
    np.ndarray
        np.nanstd(arr, axis=axis, ddof=ddof).
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        out = np.nanstd(arr, axis=axis, ddof=ddof)
    return out


def _csd_to_output(index, cloud_flag, method, diagnostics=None,
                   return_diagnostics=False):
    """
    Standardize CSD outputs.

    Parameters
    ----------
    index : pd.Index
        Output index.
    cloud_flag : array-like
        0=clear, 1=cloudy, NaN=invalid.
    method : str
        Method name for output column.
    diagnostics : dict, optional
        Extra arrays to add to output.
    return_diagnostics : bool, default False
        If True, include diagnostics in output.

    Returns
    -------
    pd.DataFrame
        Columns: is_clearsky, cloud_flag, method [, diagnostics].
    """
    cloud = np.asarray(cloud_flag, dtype=float)
    is_clearsky = pd.array(cloud == 0, dtype="boolean")
    is_clearsky[np.isnan(cloud)] = pd.NA

    out = pd.DataFrame(
        {
            "is_clearsky": is_clearsky,
            "cloud_flag": cloud,
            "method": method,
        },
        index=index,
    )
    if return_diagnostics and diagnostics is not None:
        for col, arr in diagnostics.items():
            out[col] = np.asarray(arr, dtype=float)
    return out


def _brightsun_component_flag(meas, clear, zenith, window=10, is_ghi=True,
                              return_diagnostics=False):
    """
    Bright-Sun component-level clear-sky test for one irradiance component.

    This helper implements the per-component criteria used inside the
    Bright-Sun tri-component method [1]_ (for either GHI or DHI):

    - Sliding-window statistics (length ``window`` minutes) on measured and
      clear-sky series.
    - Relative mean and max differences (|meas-clear|/clear) with
      zenith-dependent thresholds (:math:`c1`, :math:`c2`).
    - Normalized line-length difference of the time series (meas vs clear)
      with a zenith-dependent acceptance band (:math:`c3`).
    - Normalized slope variability (windowed std of first differences
      divided by mean) with threshold :math:`\\sigma_{\\mathrm{lim}}` (:math:`c4`).
    - Maximum absolute point-wise slope difference (X) with zenith-dependent
      limit (:math:`c5`).
    - Valid-clear check on clear-sky mean (:math:`c6`).

    For each time step, **1 = cloud, 0 = clear** at the component level.
    When all six criteria accept the point, it is considered clear for that
    component.

    Parameters
    ----------
    meas : array-like
        Measured component (GHI or DHI), 1D.
    clear : array-like
        Corresponding clear-sky estimate for the same component.
    zenith : array-like
        Solar zenith angle [degrees].
    window : int, default 10
        Sliding-window length (minutes) used to build Hankel matrices.
    is_ghi : bool, default True
        If True, apply Bright-Sun GHI parameterization; otherwise use the
        DHI parameterization.
    return_diagnostics : bool, default False
        If True, also return a diagnostics dict with individual criteria,
        thresholds, and intermediates.

    Returns
    -------
    cloud_flag : np.ndarray
        1 = cloudy, 0 = clear, NaN = invalid input.
    diagnostics : dict, optional
        Only when ``return_diagnostics=True``; contains arrays for c1–c6,
        intermediate statistics, and zenith-dependent thresholds.

    References
    ----------
    .. [1] Bright, J. M., Sun, X., Gueymard, C. A., Acord, B., Wang, P., &
       Engerer, N. A. (2020). Bright-Sun: A globally applicable 1-min
       irradiance clear-sky detection model. Renewable and Sustainable
       Energy Reviews, 121, 109706.
    """
    meas = _as_1d_array(meas, "meas")
    clear = _as_1d_array(clear, "clear", n=len(meas))
    zenith = _as_1d_array(zenith, "zenith", n=len(meas))
    n = len(meas)

    # Zenith grid 20–90°, 0.01 step; turnaround at 30° (MATLAB zenith_turn_around)
    z_ref = np.arange(20.0, 90.01, 0.01)
    n1 = int(round((30.0 - 20.0) / 0.01)) + 1
    if is_ghi:
        c1_lim_arr = np.flip(np.concatenate([
            np.linspace(0.5, 0.125, n1),
            np.linspace(0.125, 0.25, len(z_ref) - n1),
        ]))
        c2_lim_arr = np.flip(np.concatenate([
            np.linspace(0.5, 0.125, n1),
            np.linspace(0.125, 0.25, len(z_ref) - n1),
        ]))
        c3_lower_arr = np.flip(np.concatenate([
            np.linspace(-0.5, -0.5, n1),
            np.linspace(-0.5, -7.0, len(z_ref) - n1),
        ]))
        sigma_lim = 0.4
        c5_slope = 15.0
        c5_small = 45.0
    else:
        c1_lim_arr = np.flip(np.concatenate([
            np.linspace(0.5, 0.5, n1),
            np.linspace(0.5, 0.25, len(z_ref) - n1),
        ]))
        c2_lim_arr = np.flip(np.concatenate([
            np.linspace(0.5, 0.5, n1),
            np.linspace(0.5, 0.25, len(z_ref) - n1),
        ]))
        c3_lower_arr = np.flip(np.concatenate([
            np.linspace(-1.7, -1.7, n1),
            np.linspace(-1.7, -6.0, len(z_ref) - n1),
        ]))
        sigma_lim = 0.2
        c5_slope = 8.0
        c5_small = 24.0

    c3_upper_arr = np.abs(c3_lower_arr)
    c5_lim_arr = np.flip(np.concatenate([
        np.linspace(c5_slope, c5_slope, n1),
        np.linspace(c5_slope, c5_small, len(z_ref) - n1),
    ]))

    inds = np.searchsorted(z_ref, np.clip(zenith, z_ref[0], z_ref[-1]), side="left")
    inds = np.clip(inds, 0, len(z_ref) - 1)
    c1_lim = c1_lim_arr[inds]
    c2_lim = c2_lim_arr[inds]
    c3_lower = c3_lower_arr[inds]
    c3_upper = c3_upper_arr[inds]
    c5_lim = c5_lim_arr[inds]

    # Build Hankel matrices: each row = length-`window` time series segment,
    # used to compute local statistics over sliding windows.
    m_win = _hankel_window(meas, window)
    c_win = _hankel_window(clear, window)
    sufficient_m = _window_sufficient_valid(m_win)
    sufficient_c = _window_sufficient_valid(c_win)

    # Window-mean and window-max for measured / clear-sky component.
    meas_mean = np.nanmean(m_win, axis=1)
    clear_mean = np.nanmean(c_win, axis=1)
    meas_max = _nanmax_no_warn(m_win, axis=1)
    clear_max = _nanmax_no_warn(c_win, axis=1)
    meas_mean[~sufficient_m] = np.nan
    clear_mean[~sufficient_c] = np.nan
    meas_max[~sufficient_m] = np.nan
    clear_max[~sufficient_c] = np.nan

    # First differences for slope-based criteria and line-length.
    # MATLAB: diff along axis-0 (rows) + NaN-row pad → (n, window)
    _pad = lambda m: np.vstack([np.diff(m, axis=0),
                                np.full((1, m.shape[1]), np.nan)])
    meas_diff = _pad(m_win)
    clear_diff = _pad(c_win)
    meas_slope_nstd = _safe_divide(
        _nanstd_no_warn(meas_diff, axis=1, ddof=0), meas_mean)
    meas_line = np.nansum(
        np.sqrt(meas_diff * meas_diff + 1.0), axis=1)
    clear_line = np.nansum(
        np.sqrt(clear_diff * clear_diff + 1.0), axis=1)
    meas_slope_nstd[~sufficient_m] = np.nan
    meas_line[~sufficient_m] = np.nan
    clear_line[~sufficient_c] = np.nan

    line_diff_norm = _safe_divide(
        meas_line - clear_line, clear_line)
    X = _nanmax_no_warn(
        np.abs(meas_diff - clear_diff), axis=1)
    line_diff_norm[~sufficient_m | ~sufficient_c] = np.nan
    X[~sufficient_m | ~sufficient_c] = np.nan

    # 1=cloud by default; 0=clear when criterion passes (MATLAB: c1=0 when rel diff < lim)
    c1 = np.ones(n, dtype=float)
    c1[_safe_divide(np.abs(meas_mean - clear_mean), clear_mean) < c1_lim] = 0.0
    c2 = np.ones(n, dtype=float)
    c2[_safe_divide(np.abs(meas_max - clear_max), clear_max) < c2_lim] = 0.0
    c3 = np.ones(n, dtype=float)
    c3[(line_diff_norm > c3_lower) & (line_diff_norm < c3_upper)] = 0.0
    c4 = np.ones(n, dtype=float)
    c4[meas_slope_nstd < sigma_lim] = 0.0
    c5 = np.ones(n, dtype=float)
    c5[X < c5_lim] = 0.0
    c6 = np.ones(n, dtype=float)
    c6[(clear_mean != 0) & np.isfinite(clear_mean)] = 0.0

    cloud_flag = ((c1 + c2 + c3 + c4 + c5 + c6) > 0).astype(float)
    bad = np.isnan(meas) | np.isnan(clear)
    cloud_flag[bad] = np.nan
    if not return_diagnostics:
        return cloud_flag
    diagnostics = {
        "c1": c1,
        "c2": c2,
        "c3": c3,
        "c4": c4,
        "c5": c5,
        "c6": c6,
        "meas_mean": meas_mean,
        "clear_mean": clear_mean,
        "meas_max": meas_max,
        "clear_max": clear_max,
        "line_diff_norm": line_diff_norm,
        "meas_slope_nstd": meas_slope_nstd,
        "X": X,
        "c1_lim": c1_lim,
        "c2_lim": c2_lim,
        "c3_lower": c3_lower,
        "c3_upper": c3_upper,
        "c5_lim": c5_lim,
    }
    for key, arr in diagnostics.items():
        a = np.asarray(arr, dtype=float)
        a[bad] = np.nan
        diagnostics[key] = a
    return cloud_flag, diagnostics


def _reno_cloud_flag(ghi, ghi_clear, window=10, mean_lim=75.0, max_lim=75.0,
                     lower_L_lim=-5.0, upper_L_lim=10.0, sigma_lim=0.005,
                     X_lim=8.0):
    """
    Core Reno-style five-criteria cloud flag with an additional valid-clear
    criterion, following csd-library Reno2016CSD logic.

    Parameters
    ----------
    ghi : array-like
        Global horizontal irradiance. [W/m^2]
    ghi_clear : array-like
        Clear-sky GHI. [W/m^2]
    window : int, default 10
        Window size for criteria.
    mean_lim, max_lim, lower_L_lim, upper_L_lim, sigma_lim, X_lim : float
        Thresholds for the five criteria and line-diff bounds.

    Returns
    -------
    cloud_flag : np.ndarray
        0=clear, 1=cloudy, NaN=invalid.
    diagnostics : dict
        Arrays for each criterion and intermediates.
    """
    ghi = _as_1d_array(ghi, "ghi")
    ghi_clear = _as_1d_array(ghi_clear, "ghi_clear", n=len(ghi))
    n = len(ghi)

    # Build sliding-window matrices (each row = one window of length `window`).
    ghi_window = _hankel_window(ghi, window)
    clear_window = _hankel_window(ghi_clear, window)

    # Require more than half of window points to be valid; else treat stats as invalid.
    sufficient_ghi = _window_sufficient_valid(ghi_window)
    sufficient_clear = _window_sufficient_valid(clear_window)

    # Window mean and max: used in criteria c1 (mean difference) and c2 (max difference).
    meas_mean = np.nanmean(ghi_window, axis=1)
    clear_mean = np.nanmean(clear_window, axis=1)
    meas_max = _nanmax_no_warn(ghi_window, axis=1)
    clear_max = _nanmax_no_warn(clear_window, axis=1)
    meas_mean[~sufficient_ghi] = np.nan
    clear_mean[~sufficient_clear] = np.nan
    meas_max[~sufficient_ghi] = np.nan
    clear_max[~sufficient_clear] = np.nan

    # Along-window differences and derived stats: slope variability (c4) and line length (c3).
    # MATLAB: diff along axis-0 (rows) + NaN-row pad → (n, window)
    _pad = lambda m: np.vstack([np.diff(m, axis=0),
                                np.full((1, m.shape[1]), np.nan)])
    meas_diff = _pad(ghi_window)
    clear_diff = _pad(clear_window)

    meas_slope_nstd = _safe_divide(
        _nanstd_no_warn(meas_diff, axis=1, ddof=0), meas_mean)
    meas_line = np.nansum(
        np.sqrt(meas_diff * meas_diff + 1.0), axis=1)
    clear_line = np.nansum(
        np.sqrt(clear_diff * clear_diff + 1.0), axis=1)
    meas_slope_nstd[~sufficient_ghi] = np.nan
    meas_line[~sufficient_ghi] = np.nan
    clear_line[~sufficient_clear] = np.nan

    line_diff = meas_line - clear_line
    X = _nanmax_no_warn(
        np.abs(meas_diff - clear_diff), axis=1)
    line_diff[~sufficient_ghi | ~sufficient_clear] = np.nan
    X[~sufficient_ghi | ~sufficient_clear] = np.nan

    # Five Reno criteria plus valid-clear check: any True -> cloudy (1).
    c1 = np.abs(meas_mean - clear_mean) > mean_lim      # mean GHI vs clear-sky
    c2 = np.abs(meas_max - clear_max) > max_lim          # max GHI vs clear-sky
    c3 = (line_diff < lower_L_lim) | (line_diff > upper_L_lim)  # line-length difference
    c4 = meas_slope_nstd > sigma_lim                    # normalized slope std
    c5 = X > X_lim                                      # max absolute diff
    c6 = (clear_mean == 0) | (~np.isfinite(clear_mean))  # invalid or zero clear-sky

    cloud_flag = (c1 | c2 | c3 | c4 | c5 | c6).astype(float)
    bad = np.isnan(ghi) | np.isnan(ghi_clear)
    cloud_flag[bad] = np.nan

    # Package diagnostics and mask invalid input rows.
    diagnostics = {
        "c1": c1.astype(float),
        "c2": c2.astype(float),
        "c3": c3.astype(float),
        "c4": c4.astype(float),
        "c5": c5.astype(float),
        "c6": c6.astype(float),
        "meas_mean": meas_mean,
        "clear_mean": clear_mean,
        "meas_max": meas_max,
        "clear_max": clear_max,
        "line_diff": line_diff,
        "meas_slope_nstd": meas_slope_nstd,
        "X": X,
    }
    for key in diagnostics:
        arr = np.asarray(diagnostics[key], dtype=float)
        arr[bad] = np.nan
        diagnostics[key] = arr
    return cloud_flag, diagnostics


def reno_csd(ghi, ghi_clear, times=None, return_diagnostics=False):
    """
    Reno2016 clear-sky detection [1]_.

    MATLAB mapping: `Reno2016CSD(ghi, ghics, plot_figure)` with `ghics -> ghi_clear`.

    Parameters
    ----------
    ghi : array-like
        Global horizontal irradiance (`ghi`). [W/m^2]
    ghi_clear : array-like
        Clear-sky global horizontal irradiance (`ghics -> ghi_clear`). [W/m^2]
    times : array-like or pd.DatetimeIndex, optional
        Time index for outputs.
    return_diagnostics : bool, default False
        If True, include method diagnostics.

    Returns
    -------
    out : pd.DataFrame
        Standardized output with `is_clearsky`, `cloud_flag`, and optional diagnostics.

    Raises
    ------
    ValueError
        When input lengths do not match.

    References
    ----------
    .. [1] Reno, M. J., & Hansen, C. W. (2016). Identification of periods of clear sky
       irradiance in time series of GHI measurements. Renewable Energy, 90, 520-531.
    """
    ghi = _as_1d_array(ghi, "ghi")
    idx = _resolve_index(times, len(ghi))
    cloud_flag, diagnostics = _reno_cloud_flag(ghi, ghi_clear)
    return _csd_to_output(idx, cloud_flag, "reno", diagnostics, return_diagnostics)


def ineichen_csd(ghi, ghi_extra, zenith, times=None, return_diagnostics=False):
    """
    Ineichen2009 clear-sky detection [1]_.

    MATLAB mapping: `Ineichen2009CSD(ghi, exth, zen, plot_figure)` with
    `exth -> ghi_extra`, `zen -> zenith`.
    Convention: MATLAB csd(kt_prime<0.65)=1 marks low clearness (cloudy); here cloud_flag 0=clear,
    1=cloudy, so cloud_flag=1 where kt_prime<0.65.

    Parameters
    ----------
    ghi : array-like
        Global horizontal irradiance (`ghi`). [W/m^2]
    ghi_extra : array-like
        Horizontal extraterrestrial irradiance (`exth -> ghi_extra`). [W/m^2]
    zenith : array-like
        Solar zenith angle (`zen -> zenith`). [degrees]
    times : array-like or pd.DatetimeIndex, optional
        Time index for outputs.
    return_diagnostics : bool, default False
        If True, include method diagnostics.

    Returns
    -------
    out : pd.DataFrame
        Standardized output with `is_clearsky`, `cloud_flag`, and optional diagnostics.

    Raises
    ------
    ValueError
        When input lengths do not match.

    References
    ----------
    .. [1] Ineichen, P., Barroso, C. S., Geiger, B., Hollmann, R., Marsouin, A., &
       Mueller, R. (2009). Satellite Application Facilities irradiance products:
       hourly time step comparison and validation over Europe. International
       Journal of Remote Sensing, 30(21), 5549-5571.
    """
    ghi = _as_1d_array(ghi, "ghi")
    ghi_extra = _as_1d_array(ghi_extra, "ghi_extra", n=len(ghi))
    zenith = _as_1d_array(zenith, "zenith", n=len(ghi))
    idx = _resolve_index(times, len(ghi))

    kt = _safe_divide(ghi, ghi_extra)
    h = 90.0 - zenith
    with np.errstate(divide="ignore", invalid="ignore"):
        M = 1.0 / (np.sin(np.radians(h)) + 0.15 * np.power(h + 3.885, -1.253))
        kt_prime = kt / (1.031 * np.exp(-1.4 / (0.9 + 9.4 / M)) + 0.1)

    # Convention: Python cloud_flag 0=clear, 1=cloudy. In the reference MATLAB, csd(kt_prime<0.65)=1
    # assigns 1 where modified clearness is low (cloudy). So: kt_prime < 0.65 -> cloudy (cloud_flag=1).
    cloud_flag = np.zeros(len(ghi), dtype=float)
    cloud_flag[kt_prime < 0.65] = 1.0
    bad = (np.isnan(ghi) | np.isnan(ghi_extra)
           | np.isnan(zenith) | (zenith >= 90.0)
           | (ghi_extra <= 0.0))
    cloud_flag[bad] = np.nan

    diagnostics = {"kt": kt, "M": M, "kt_prime": kt_prime}
    for key in diagnostics:
        arr = np.asarray(diagnostics[key], dtype=float)
        arr[bad] = np.nan
        diagnostics[key] = arr
    return _csd_to_output(idx, cloud_flag, "ineichen", diagnostics, return_diagnostics)


def lefevre_csd(ghi, dhi, ghi_extra, zenith, times=None,
                return_diagnostics=False):
    """
    Lefevre2013 clear-sky detection [1]_.

    MATLAB mapping: `Lefevre2013CSD(ghi, dif, exth, zen, plot_figure)` with
    `dif -> dhi`, `exth -> ghi_extra`, `zen -> zenith`.

    Parameters
    ----------
    ghi : array-like
        Global horizontal irradiance (`ghi`). [W/m^2]
    dhi : array-like
        Diffuse horizontal irradiance (`dif -> dhi`). [W/m^2]
    ghi_extra : array-like
        Horizontal extraterrestrial irradiance (`exth -> ghi_extra`). [W/m^2]
    zenith : array-like
        Solar zenith angle (`zen -> zenith`). [degrees]
    times : array-like or pd.DatetimeIndex, optional
        Time index for outputs.
    return_diagnostics : bool, default False
        If True, include method diagnostics.

    Returns
    -------
    out : pd.DataFrame
        Standardized output with `is_clearsky`, `cloud_flag`, and optional diagnostics.

    Raises
    ------
    ValueError
        When input lengths do not match.

    References
    ----------
    .. [1] Lefèvre, M., Oumbe, A., Blanc, P., Espinar, B., Gschwind, B., Qu, Z., ...
       & Morcrette, J. J. (2013). McClear: a new model estimating downwelling
       solar radiation at ground level in clear-sky conditions. Atmospheric
       Measurement Techniques, 6(9), 2403-2418.
    """
    ghi = _as_1d_array(ghi, "ghi")
    dhi = _as_1d_array(dhi, "dhi", n=len(ghi))
    ghi_extra = _as_1d_array(ghi_extra, "ghi_extra", n=len(ghi))
    zenith = _as_1d_array(zenith, "zenith", n=len(ghi))
    idx = _resolve_index(times, len(ghi))

    cloud_flag = np.ones(len(ghi), dtype=float)
    k = _safe_divide(dhi, ghi)
    # Invalidate k where GHI or DHI are non-physical (negative or zero GHI).
    non_physical = (ghi <= 0) | (dhi < 0)
    k[non_physical] = np.nan
    first_filter_clear = k < 0.3
    cloud_flag[first_filter_clear] = 0.0

    kt = _safe_divide(ghi, ghi_extra)
    h = 90.0 - zenith
    with np.errstate(divide="ignore", invalid="ignore"):
        M = 1.0 / (np.sin(np.radians(h)) + 0.15 * np.power(h + 3.885, -1.253))
        kt_prime = kt / (1.031 * np.exp(-1.4 / (0.9 + 9.4 / M)) + 0.1)

    # Lefevre second filter: require enough first-filter-retained points
    # in both [t-90, t] and [t, t+90], then evaluate std of kt' over [t-90, t+90].
    retained = first_filter_clear & np.isfinite(kt_prime)
    retained_f = pd.Series(retained.astype(float))
    min_retained = int(np.ceil(0.3 * 91))
    prev_count = retained_f.rolling(91, min_periods=91).sum().to_numpy()
    next_count = retained_f.iloc[::-1].rolling(91, min_periods=91).sum().iloc[::-1].to_numpy()
    enough_30pct = (prev_count >= min_retained) & (next_count >= min_retained)

    kt_prime_masked = np.where(retained, kt_prime, np.nan)
    KTp = pd.Series(kt_prime_masked).rolling(181, center=True, min_periods=1).std(ddof=0).to_numpy()
    # Keep second filter on the subset retained by first filter (k<0.3),
    # consistent with the textual method description ("remaining data").
    second_filter_clear = first_filter_clear & enough_30pct & np.isfinite(KTp) & (KTp < 0.02)
    cloud_flag[second_filter_clear] = 0.0

    bad = (
        np.isnan(ghi)
        | np.isnan(dhi)
        | np.isnan(ghi_extra)
        | np.isnan(zenith)
        | (ghi <= 0)
        | (dhi < 0)
    )
    cloud_flag[bad] = np.nan

    diagnostics = {"k": k, "kt": kt, "M": M, "kt_prime": kt_prime, "KTp": KTp}
    for key in diagnostics:
        # Writable copy: ``np.asarray`` can alias read-only buffers (e.g. pandas ``rolling`` output).
        arr = np.array(diagnostics[key], dtype=float, copy=True)
        arr[bad] = np.nan
        diagnostics[key] = arr
    return _csd_to_output(idx, cloud_flag, "lefevre", diagnostics, return_diagnostics)


def _optimise_alpha(meas, clear):
    """
    Closed-form RMSE-optimal scalar alpha: min_a sqrt(mean((y-a*x)^2)).

    Mathematically equivalent to MATLAB ``fminsearch`` on the same
    scalar-alpha RMSE objective.

    Parameters
    ----------
    meas : np.ndarray
        Measured irradiance (clear-period subset).
    clear : np.ndarray
        Clear-sky irradiance (clear-period subset).

    Returns
    -------
    float or None
        Optimal alpha, or None if denominator is non-positive.
    """
    denom = np.nansum(clear * clear)
    if not np.isfinite(denom) or denom <= 0:
        return None
    alpha = np.nansum(meas * clear) / denom
    if not np.isfinite(alpha):
        return None
    return float(alpha)



def brightsun_csd(zenith, ghi, ghi_clear, dhi, dhi_clear,
                  times, return_diagnostics=False):
    """
    BrightSun2020CSDc clear-sky detection (tri-component) [1]_.

    MATLAB mapping:
    ``BrightSun2020CSDc(zen, ghi, ghics, dif, difcs, LST)`` with
    ``zen -> zenith``, ``ghics -> ghi_clear``, ``dif -> dhi``, ``difcs -> dhi_clear``.

    The method proceeds in four stages matching the MATLAB routine:

    1. Initial Reno-style CSD guess for candidate clear periods.
    2. Daily clear-sky optimisation scales GHI, DHI, BNI
       clear-sky curves independently (alpha bounds
       ``[0.7, 1.5]`` for GHI/BNI, ``[0.3, 1.5]`` for DHI).
    3. Tri-component analysis on optimised curves.
    4. Cascaded duration filters (90/30/10-min).

    Parameters
    ----------
    zenith : array-like
        Solar zenith angle. [degrees]
    ghi : array-like
        Global horizontal irradiance. [W/m^2]
    ghi_clear : array-like
        Clear-sky GHI. [W/m^2]
    dhi : array-like
        Diffuse horizontal irradiance. [W/m^2]
    dhi_clear : array-like
        Clear-sky DHI. [W/m^2]
    times : array-like or pd.DatetimeIndex
        Time index (MATLAB ``LST`` equivalent).
    return_diagnostics : bool, default False
        If True, include method diagnostics.

    Returns
    -------
    out : pd.DataFrame
        Columns: ``is_clearsky``, ``cloud_flag`` (duration-filtered),
        ``method``; diagnostics when requested.

    Raises
    ------
    ValueError
        When input lengths do not match.

    References
    ----------
    .. [1] Bright, J. M., Sun, X., Gueymard, C. A., Acord, B.,
       Wang, P., & Engerer, N. A. (2020). Bright-Sun: A globally
       applicable 1-min irradiance clear-sky detection model.
       Renewable and Sustainable Energy Reviews, 121, 109706.
    """
    zenith = _as_1d_array(zenith, "zenith")
    ghi = _as_1d_array(ghi, "ghi", n=len(zenith))
    ghi_clear = _as_1d_array(
        ghi_clear, "ghi_clear", n=len(zenith))
    dhi = _as_1d_array(dhi, "dhi", n=len(zenith))
    dhi_clear = _as_1d_array(
        dhi_clear, "dhi_clear", n=len(zenith))
    idx = _resolve_index(times, len(zenith))
    n_output = len(zenith)

    # Cap DHI at GHI
    dhi = np.minimum(dhi, ghi)
    dhi_clear = np.minimum(dhi_clear, ghi_clear)

    # BNI from closure
    mu0 = np.cos(np.radians(zenith))
    bni = _safe_divide(ghi - dhi, mu0)
    bni_clear = _safe_divide(ghi_clear - dhi_clear, mu0)

    # NaN removal (MATLAB pattern)
    idxs_nan = (np.isnan(ghi) | np.isnan(bni)
                | np.isnan(dhi))
    not_nan = ~idxs_nan

    ghi_c = ghi[not_nan].copy()
    bni_c = bni[not_nan].copy()
    dhi_c = dhi[not_nan].copy()
    ghics_c = ghi_clear[not_nan].copy()
    bnics_c = bni_clear[not_nan].copy()
    dhics_c = dhi_clear[not_nan].copy()
    zen_c = zenith[not_nan].copy()
    n_clean = len(ghi_c)

    times_c = None
    if isinstance(idx, pd.DatetimeIndex):
        times_c = idx[not_nan]

    # ---- Stage 1: initial Reno guess (sigma_lim=0.1) ----
    csd_initial, _ = _reno_cloud_flag(
        ghi_c, ghics_c,
        mean_lim=75.0, max_lim=75.0,
        lower_L_lim=-5.0, upper_L_lim=10.0,
        sigma_lim=0.1, X_lim=8.0,
    )
    csd_initial = np.where(
        np.isfinite(csd_initial), csd_initial, 1.0)

    # ---- Stage 2: daily optimisation (GHI, DHI, BNI) ----
    opt_thres = 30.0
    upper_a = 1.5
    lower_a = 0.7
    lower_a_dhi = 0.3

    if times_c is not None and len(times_c) > 0:
        day_key = times_c.floor("D")
        for d in np.unique(day_key):
            ix = np.where(day_key == d)[0]
            csdd = csd_initial[ix].copy()
            csdd[(dhi_c[ix] < opt_thres)
                 | (ghi_c[ix] < opt_thres)] = 1.0
            cm = csdd == 0.0
            if np.sum(cm) <= 60:
                continue
            # GHI optimisation
            a = _optimise_alpha(ghi_c[ix][cm],
                                ghics_c[ix][cm])
            if a is not None:
                ghics_c[ix] *= np.clip(a, lower_a, upper_a)
            # DHI optimisation
            a = _optimise_alpha(dhi_c[ix][cm],
                                dhics_c[ix][cm])
            if a is not None:
                dhics_c[ix] *= np.clip(a, lower_a_dhi,
                                       upper_a)
            # BNI optimisation
            a = _optimise_alpha(bni_c[ix][cm],
                                bnics_c[ix][cm])
            if a is not None:
                bnics_c[ix] *= np.clip(a, lower_a, upper_a)

    # ---- Stage 3: tri-component analysis ----
    cloud_ghi = _brightsun_component_flag(
        ghi_c, ghics_c, zen_c, window=10, is_ghi=True)
    cloud_dhi = _brightsun_component_flag(
        dhi_c, dhics_c, zen_c, window=10, is_ghi=False)

    # BNI: zenith-dependent kcb threshold
    z_ref = np.arange(30.0, 90.01, 0.01)
    kc_lims = np.flip(np.linspace(0.5, 0.9, len(z_ref)))
    inds = np.searchsorted(
        z_ref, np.clip(zen_c, z_ref[0], z_ref[-1]),
        side="left")
    inds = np.clip(inds, 0, len(z_ref) - 1)
    kc_lim_c = kc_lims[inds]
    kcb_c = _safe_divide(bni_c, bnics_c)
    cloud_bni = np.ones(n_clean, dtype=float)
    cloud_bni[kcb_c > kc_lim_c] = 0.0

    csd_overall = np.ones(n_clean, dtype=float)
    csd_overall[(cloud_ghi + cloud_dhi + cloud_bni) == 0] = 0.0

    # ---- Stage 4: duration filters ----
    # Inline centred Hankel filter: sum forward window, shift to centre
    def _dur(flags, w, tol):
        h = np.nansum(_hankel_window(flags, w), axis=1)
        h = np.concatenate([np.full(w // 2, np.nan),
                            h[:n_clean - w // 2]])
        out = np.zeros(n_clean, dtype=float)
        out[h > tol] = 1.0
        return out

    # 1st: 90 min, tolerance 10
    csd_1st = _dur(csd_overall, 90, 10)

    # Sunrise/sunset proximity (zen ≈ 85°)
    ss_idx = np.where(np.round(zen_c) == 85)[0]
    if len(ss_idx) > 0:
        all_i = np.arange(n_clean)
        ss_s = np.sort(ss_idx)
        pos = np.searchsorted(ss_s, all_i)
        pos = np.clip(pos, 0, len(ss_s) - 1)
        pl = np.clip(pos - 1, 0, len(ss_s) - 1)
        dist_ss = np.minimum(
            np.abs(all_i - ss_s[pos]),
            np.abs(all_i - ss_s[pl]))
    else:
        dist_ss = np.full(n_clean, n_clean)
    csd_1st[dist_ss < 90] = 0.0

    # 2nd: 30 min, tolerance 0
    csd_2nd = _dur(csd_overall, 30, 0)

    # 3rd: 10 min, tolerance 2 (sunrise/sunset override)
    csd_3rd = _dur(csd_overall, 10, 2)
    csd_2nd[(csd_3rd == 0) & (dist_ss < 90)] = 0.0

    # Final: all must agree clear
    csd_filtered = np.ones(n_clean, dtype=float)
    csd_filtered[
        (csd_overall + csd_1st + csd_2nd) == 0] = 0.0

    # ---- Map back to full length ----
    cloud_flag = np.ones(n_output, dtype=float)
    cloud_flag[not_nan] = csd_filtered
    cloud_flag[idxs_nan] = np.nan

    def _expand(arr):
        full = np.full(n_output, np.nan)
        full[not_nan] = arr
        return full

    diagnostics = {
        "cloud_ghi": _expand(cloud_ghi),
        "cloud_dhi": _expand(cloud_dhi),
        "cloud_bni": _expand(cloud_bni),
        "kcb": _expand(kcb_c),
        "kc_lim": _expand(kc_lim_c),
        "mu0": mu0,
        "bni": bni,
        "bni_clear": bni_clear,
    }
    return _csd_to_output(
        idx, cloud_flag, "brightsun",
        diagnostics, return_diagnostics)


def detect_clearsky(method, **kwargs):
    """
    Wrapper for clear-sky detection methods.

    Parameters
    ----------
    method : {"reno", "ineichen", "lefevre", "brightsun"}
        Method name.
    **kwargs : dict
        Arguments forwarded to method function.

    Returns
    -------
    out : pd.DataFrame
        Standardized CSD output.

    Raises
    ------
    ValueError
        When method is not one of reno, ineichen, lefevre, brightsun.
    """
    method_key = str(method).strip().lower()
    if method_key == "reno":
        return reno_csd(**kwargs)
    if method_key == "ineichen":
        return ineichen_csd(**kwargs)
    if method_key == "lefevre":
        return lefevre_csd(**kwargs)
    if method_key == "brightsun":
        return brightsun_csd(**kwargs)
    raise ValueError(
        "Unsupported method. Choose one of brightsun, ineichen, lefevre, reno."
    )
