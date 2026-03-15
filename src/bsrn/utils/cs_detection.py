"""
Clear-sky detection (CSD) utilities.
晴空检测（CSD）工具函数。

Implements selected CSD methods from the MATLAB csd-library with a common
Python output interface.
实现 MATLAB csd-library 中的部分 CSD 方法，并提供统一的 Python 输出接口。
"""

import warnings
import numpy as np
import pandas as pd


def _as_1d_array(x, name, n=None):
    """
    Convert input to 1D float array and validate length.
    将输入转为一维浮点数组并校验长度。

    Parameters
    ----------
    x : array-like
        Input to convert.
        待转换的输入。
    name : str
        Name for error messages.
        错误信息中的名称。
    n : int, optional
        Required length; if set, raise when len(x) != n.
        要求长度；若设置则校验。

    Returns
    -------
    np.ndarray
        1D float array.
        一维浮点数组。

    Raises
    ------
    ValueError
        When n is set and len(x) != n.
        当 n 已设置且 len(x) != n 时。
    """
    arr = np.asarray(x, dtype=float).reshape(-1)
    if n is not None and len(arr) != n:
        raise ValueError(f"{name} must have length {n}. / {name} 长度必须为 {n}。")
    return arr


def _resolve_index(times, n):
    """
    Resolve output index.
    解析输出索引。

    Parameters
    ----------
    times : array-like, pd.DatetimeIndex, or None
        Time index; if None, return integer range.
        时间索引；None 则返回整数范围。
    n : int
        Expected length.
        期望长度。

    Returns
    -------
    pd.RangeIndex or pd.DatetimeIndex
        Index of length n.
        长度为 n 的索引。

    Raises
    ------
    ValueError
        When len(times) != n.
        当 len(times) != n 时。
    """
    if times is None:
        return pd.RangeIndex(start=0, stop=n, step=1, name="time")
    if isinstance(times, pd.DatetimeIndex):
        if len(times) != n:
            raise ValueError("times length must match inputs. / times 长度必须与输入一致。")
        return times
    idx = pd.DatetimeIndex(times)
    if len(idx) != n:
        raise ValueError("times length must match inputs. / times 长度必须与输入一致。")
    return idx


def _hankel_window(values, window):
    """
    Build MATLAB-style Hankel windows with trailing NaN padding.
    构造 MATLAB 风格 Hankel 窗口并在尾部填充 NaN。

    Equivalent to MATLAB: to avoid a loop, the time series are concatenated
    with a tail so one matrix call builds all windows, e.g.
    ``ghi_window = hankel(ghi, [ghi(end), NaN(1, interval_size-1)])``.
    Each row i is the window [values[i], values[i+1], ..., values[i+window-1]],
    with NaN padding where the window extends past the end of the series.
    等价于 MATLAB：为避免循环，将时间序列与尾部拼接后一次构造所有窗口。

    Parameters
    ----------
    values : array-like
        1D time series.
        一维时间序列。
    window : int
        Window length (number of columns).
        窗口长度（列数）。

    Returns
    -------
    np.ndarray
        Shape (len(values), window); row i = window starting at index i.
        形状 (len(values), window)。
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
    每行非 NaN 超过半数时为 True（如 window=10 则至少 5 个）。

    Parameters
    ----------
    window_mat : np.ndarray
        2D array, shape (n, window).
        二维数组，形状 (n, window)。

    Returns
    -------
    np.ndarray of bool
        True where row has >= (window+1)//2 finite values.
        每行有限值数 >= (window+1)//2 为 True。
    """
    n_valid = np.sum(np.isfinite(window_mat), axis=1)
    min_required = (window_mat.shape[1] + 1) // 2
    return n_valid >= min_required


def _safe_divide(num, den):
    """
    Safe division with NaN on invalid entries.
    安全除法，对无效位置返回 NaN。

    Parameters
    ----------
    num : array-like
        Numerator.
        分子。
    den : array-like
        Denominator.
        分母。

    Returns
    -------
    np.ndarray
        num/den with non-finite results set to NaN.
        商，非有限处为 NaN。
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        out = num / den
    out[~np.isfinite(out)] = np.nan
    return out


def _nanmax_no_warn(arr, axis):
    """
    nanmax without emitting all-NaN runtime warnings.
    计算 nanmax 且不发出全 NaN 运行时警告。

    Parameters
    ----------
    arr : np.ndarray
        Input array.
        输入数组。
    axis : int
        Axis over which to take maximum.
        沿该轴取最大值。

    Returns
    -------
    np.ndarray
        np.nanmax(arr, axis=axis).
        沿轴 nanmax 结果。
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        out = np.nanmax(arr, axis=axis)
    return out


def _nanstd_no_warn(arr, axis, ddof=0):
    """
    nanstd without emitting empty-slice runtime warnings.
    计算 nanstd 且不发出空切片运行时警告。

    Parameters
    ----------
    arr : np.ndarray
        Input array.
        输入数组。
    axis : int
        Axis over which to take standard deviation.
        沿该轴计算标准差。
    ddof : int, default 0
        Delta degrees of freedom for std.
        标准差自由度。

    Returns
    -------
    np.ndarray
        np.nanstd(arr, axis=axis, ddof=ddof).
        沿轴 nanstd 结果。
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        out = np.nanstd(arr, axis=axis, ddof=ddof)
    return out


def _to_output(index, cloud_flag, method, diagnostics=None, return_diagnostics=False):
    """
    Standardize CSD outputs.
    标准化 CSD 输出。

    Parameters
    ----------
    index : pd.Index
        Output index.
        输出索引。
    cloud_flag : array-like
        0=clear, 1=cloudy, NaN=invalid.
        0 晴空，1 有云，NaN 无效。
    method : str
        Method name for output column.
        方法名（输出列）。
    diagnostics : dict, optional
        Extra arrays to add to output.
        附加诊断数组。
    return_diagnostics : bool, default False
        If True, include diagnostics in output.
        为 True 时输出含诊断列。

    Returns
    -------
    pd.DataFrame
        Columns: is_clearsky, cloud_flag, method [, diagnostics].
        列：is_clearsky, cloud_flag, method 等。
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


def _reno_cloud_flag(ghi, ghi_clear, window=10, mean_lim=75.0, max_lim=75.0,
                    lower_L_lim=-5.0, upper_L_lim=10.0, sigma_lim=0.005, X_lim=8.0):
    """
    Core Reno-style five-criteria cloud flag with an additional valid-clear
    criterion, following csd-library Reno2016CSD logic.
    Reno 风格五准则云标记（含有效晴空附加准则），遵循 csd-library Reno2016CSD 逻辑。

    Parameters
    ----------
    ghi : array-like
        Global horizontal irradiance. [W/m^2]
        水平总辐照度。[瓦/平方米]
    ghi_clear : array-like
        Clear-sky GHI. [W/m^2]
        晴空水平总辐照度。[瓦/平方米]
    window : int, default 10
        Window size for criteria.
        判据窗口长度。
    mean_lim, max_lim, lower_L_lim, upper_L_lim, sigma_lim, X_lim : float
        Thresholds for the five criteria and line-diff bounds.
        五准则及线差阈值。

    Returns
    -------
    cloud_flag : np.ndarray
        0=clear, 1=cloudy, NaN=invalid.
        0 晴空，1 有云，NaN 无效。
    diagnostics : dict
        Arrays for each criterion and intermediates.
        各判据及中间量。
    """
    ghi = _as_1d_array(ghi, "ghi")
    ghi_clear = _as_1d_array(ghi_clear, "ghi_clear", n=len(ghi))
    n = len(ghi)

    # Build sliding-window matrices (each row = one window of length `window`).
    # 构造滑动窗口矩阵（每行为一个长度为 window 的窗口）。
    ghi_window = _hankel_window(ghi, window)
    clear_window = _hankel_window(ghi_clear, window)

    # Require more than half of window points to be valid; else treat stats as invalid.
    # 要求窗口内超过半数点为有效，否则该窗口的统计量视为无效。
    sufficient_ghi = _window_sufficient_valid(ghi_window)
    sufficient_clear = _window_sufficient_valid(clear_window)

    # Window mean and max: used in criteria c1 (mean difference) and c2 (max difference).
    # 窗口均值与最大值：用于判据 c1（均值差）与 c2（最大值差）。
    meas_mean = np.nanmean(ghi_window, axis=1)
    clear_mean = np.nanmean(clear_window, axis=1)
    meas_max = _nanmax_no_warn(ghi_window, axis=1)
    clear_max = _nanmax_no_warn(clear_window, axis=1)
    meas_mean[~sufficient_ghi] = np.nan
    clear_mean[~sufficient_clear] = np.nan
    meas_max[~sufficient_ghi] = np.nan
    clear_max[~sufficient_clear] = np.nan

    # Along-window differences and derived stats: slope variability (c4) and line length (c3).
    # 沿窗口的差分及派生量：斜率变异性（c4）与折线长度差（c3）。
    meas_diff = np.diff(ghi_window, axis=1)
    clear_diff = np.diff(clear_window, axis=1)

    meas_slope_nstd = _safe_divide(_nanstd_no_warn(meas_diff, axis=1, ddof=0), meas_mean)
    meas_line = np.nansum(np.sqrt(meas_diff * meas_diff + 1.0), axis=1)
    clear_line = np.nansum(np.sqrt(clear_diff * clear_diff + 1.0), axis=1)
    meas_slope_nstd[~sufficient_ghi] = np.nan
    meas_line[~sufficient_ghi] = np.nan
    clear_line[~sufficient_clear] = np.nan

    line_diff = meas_line - clear_line
    X = _nanmax_no_warn(np.abs(meas_diff - clear_diff), axis=1)
    line_diff[~sufficient_ghi | ~sufficient_clear] = np.nan
    X[~sufficient_ghi | ~sufficient_clear] = np.nan

    # Five Reno criteria plus valid-clear check: any True -> cloudy (1).
    # 五个 Reno 判据加有效晴空检查：任一为 True 则判为有云 (1)。
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
    # 打包诊断量并屏蔽无效输入行。
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
    Reno2016 clear-sky detection.
    Reno2016 晴空检测。

    MATLAB mapping: `Reno2016CSD(ghi, ghics, plot_figure)`.
    MATLAB 变量映射：`ghics -> ghi_clear`。

    Parameters
    ----------
    ghi : array-like
        Global horizontal irradiance (`ghi`). [W/m^2]
        水平总辐照度 (`ghi`)。[瓦/平方米]
    ghi_clear : array-like
        Clear-sky global horizontal irradiance (`ghics -> ghi_clear`). [W/m^2]
        晴空水平总辐照度 (`ghics -> ghi_clear`)。[瓦/平方米]
    times : array-like or pd.DatetimeIndex, optional
        Time index for outputs.
        输出时间索引。
    return_diagnostics : bool, default False
        If True, include method diagnostics.
        若为 True，返回方法诊断量。

    Returns
    -------
    out : pd.DataFrame
        Standardized output with `is_clearsky`, `cloud_flag`, and optional diagnostics.
        标准化输出，含 `is_clearsky`、`cloud_flag` 及可选诊断量。

    Raises
    ------
    ValueError
        When input lengths do not match.
        输入长度不一致时。

    References
    ----------
    .. [1] Reno, M. J., & Hansen, C. W. (2016). Identification of periods of clear sky
       irradiance in time series of GHI measurements. Renewable Energy, 90, 520-531.
    """
    ghi = _as_1d_array(ghi, "ghi")
    idx = _resolve_index(times, len(ghi))
    cloud_flag, diagnostics = _reno_cloud_flag(ghi, ghi_clear)
    return _to_output(idx, cloud_flag, "reno", diagnostics, return_diagnostics)


def ineichen_csd(ghi, ghi_extra, zenith, times=None, return_diagnostics=False):
    """
    Ineichen2009 clear-sky detection.
    Ineichen2009 晴空检测。

    MATLAB mapping: `Ineichen2009CSD(ghi, exth, zen, plot_figure)`.
    MATLAB 变量映射：`exth -> ghi_extra`, `zen -> zenith`。

    Parameters
    ----------
    ghi : array-like
        Global horizontal irradiance (`ghi`). [W/m^2]
        水平总辐照度 (`ghi`)。[瓦/平方米]
    ghi_extra : array-like
        Horizontal extraterrestrial irradiance (`exth -> ghi_extra`). [W/m^2]
        地外水平辐照度 (`exth -> ghi_extra`)。[瓦/平方米]
    zenith : array-like
        Solar zenith angle (`zen -> zenith`). [degrees]
        太阳天顶角 (`zen -> zenith`)。[度]
    times : array-like or pd.DatetimeIndex, optional
        Time index for outputs.
        输出时间索引。
    return_diagnostics : bool, default False
        If True, include method diagnostics.
        若为 True，返回方法诊断量。

    Returns
    -------
    out : pd.DataFrame
        Standardized output with `is_clearsky`, `cloud_flag`, and optional diagnostics.
        标准化输出，含 `is_clearsky`、`cloud_flag` 及可选诊断量。

    Raises
    ------
    ValueError
        When input lengths do not match.
        输入长度不一致时。

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

    cloud_flag = np.zeros(len(ghi), dtype=float)
    cloud_flag[kt_prime < 0.65] = 1.0
    bad = np.isnan(ghi) | np.isnan(ghi_extra) | np.isnan(zenith)
    cloud_flag[bad] = np.nan

    diagnostics = {"kt": kt, "M": M, "kt_prime": kt_prime}
    for key in diagnostics:
        arr = np.asarray(diagnostics[key], dtype=float)
        arr[bad] = np.nan
        diagnostics[key] = arr
    return _to_output(idx, cloud_flag, "ineichen", diagnostics, return_diagnostics)


def lefevre_csd(ghi, dhi, ghi_extra, zenith, times=None, return_diagnostics=False):
    """
    Lefevre2013 clear-sky detection.
    Lefevre2013 晴空检测。

    MATLAB mapping: `Lefevre2013CSD(ghi, dif, exth, zen, plot_figure)`.
    MATLAB 变量映射：`dif -> dhi`, `exth -> ghi_extra`, `zen -> zenith`。

    Parameters
    ----------
    ghi : array-like
        Global horizontal irradiance (`ghi`). [W/m^2]
        水平总辐照度 (`ghi`)。[瓦/平方米]
    dhi : array-like
        Diffuse horizontal irradiance (`dif -> dhi`). [W/m^2]
        水平散射辐照度 (`dif -> dhi`)。[瓦/平方米]
    ghi_extra : array-like
        Horizontal extraterrestrial irradiance (`exth -> ghi_extra`). [W/m^2]
        地外水平辐照度 (`exth -> ghi_extra`)。[瓦/平方米]
    zenith : array-like
        Solar zenith angle (`zen -> zenith`). [degrees]
        太阳天顶角 (`zen -> zenith`)。[度]
    times : array-like or pd.DatetimeIndex, optional
        Time index for outputs.
        输出时间索引。
    return_diagnostics : bool, default False
        If True, include method diagnostics.
        若为 True，返回方法诊断量。

    Returns
    -------
    out : pd.DataFrame
        Standardized output with `is_clearsky`, `cloud_flag`, and optional diagnostics.
        标准化输出，含 `is_clearsky`、`cloud_flag` 及可选诊断量。

    Raises
    ------
    ValueError
        When input lengths do not match.
        输入长度不一致时。

    References
    ----------
    .. [1] Lefevre, M., et al. (2013). Using reduced data sets ISCCP-B2 from the Meteosat satellites
       to assess surface solar irradiance. Solar Energy, 86(11), 3351-3364.
    """
    ghi = _as_1d_array(ghi, "ghi")
    dhi = _as_1d_array(dhi, "dhi", n=len(ghi))
    ghi_extra = _as_1d_array(ghi_extra, "ghi_extra", n=len(ghi))
    zenith = _as_1d_array(zenith, "zenith", n=len(ghi))
    idx = _resolve_index(times, len(ghi))

    cloud_flag = np.ones(len(ghi), dtype=float)
    k = _safe_divide(dhi, ghi)
    # Invalidate k where GHI or DHI are non-physical (negative or zero GHI).
    # 当 GHI 或 DHI 非物理（负值或 GHI 为零）时，将 k 视为无效。
    non_physical = (ghi <= 0) | (dhi < 0)
    k[non_physical] = np.nan
    cloud_flag[k < 0.3] = 0.0

    kt = _safe_divide(ghi, ghi_extra)
    h = 90.0 - zenith
    with np.errstate(divide="ignore", invalid="ignore"):
        M = 1.0 / (np.sin(np.radians(h)) + 0.15 * np.power(h + 3.885, -1.253))
        kt_prime = kt / (1.031 * np.exp(-1.4 / (0.9 + 9.4 / M)) + 0.1)

    ktp_window = _hankel_window(kt_prime, 90)
    sufficient_ktp = _window_sufficient_valid(ktp_window)
    KTp = _nanstd_no_warn(ktp_window, axis=1, ddof=0)
    KTp[~sufficient_ktp] = np.nan
    cloud_flag[KTp < 0.02] = 0.0

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
        arr = np.asarray(diagnostics[key], dtype=float)
        arr[bad] = np.nan
        diagnostics[key] = arr
    return _to_output(idx, cloud_flag, "lefevre", diagnostics, return_diagnostics)


def brightsun_csd(zenith, ghi, ghi_clear, dhi, dhi_clear, times, return_diagnostics=False):
    """
    BrightSun2020CSDc clear-sky detection (tri-component style).
    BrightSun2020CSDc 晴空检测（三分量风格）。

    MATLAB mapping:
    `BrightSun2020CSDc(zen, ghi, ghics, dif, difcs, LST, plot_figure)`.
    MATLAB 变量映射：`zen -> zenith`, `ghics -> ghi_clear`, `dif -> dhi`, `difcs -> dhi_clear`。

    Notes
    -----
    This implementation preserves the tri-component spirit used in the MATLAB
    routine: GHI and DHI via Reno-style criteria + DNI via clear-sky beam index
    threshold varying with zenith, then combines the three flags.
    此实现保留 MATLAB 三分量思路：GHI、DHI 采用 Reno 风格判据，DNI 采用随天顶角变化的
    晴空束辐照指数阈值，最终合并三者判据。

    Parameters
    ----------
    zenith : array-like
        Solar zenith angle (`zen -> zenith`). [degrees]
        太阳天顶角 (`zen -> zenith`)。[度]
    ghi : array-like
        Global horizontal irradiance (`ghi`). [W/m^2]
        水平总辐照度 (`ghi`)。[瓦/平方米]
    ghi_clear : array-like
        Clear-sky global horizontal irradiance (`ghics -> ghi_clear`). [W/m^2]
        晴空水平总辐照度 (`ghics -> ghi_clear`)。[瓦/平方米]
    dhi : array-like
        Diffuse horizontal irradiance (`dif -> dhi`). [W/m^2]
        水平散射辐照度 (`dif -> dhi`)。[瓦/平方米]
    dhi_clear : array-like
        Clear-sky diffuse horizontal irradiance (`difcs -> dhi_clear`). [W/m^2]
        晴空水平散射辐照度 (`difcs -> dhi_clear`)。[瓦/平方米]
    times : array-like or pd.DatetimeIndex
        Time index (MATLAB `LST` equivalent input sequence).
        时间索引（对应 MATLAB `LST` 输入序列）。
    return_diagnostics : bool, default False
        If True, include method diagnostics.
        若为 True，返回方法诊断量。

    Returns
    -------
    out : pd.DataFrame
        Standardized output with `is_clearsky`, `cloud_flag`, and optional diagnostics.
        标准化输出，含 `is_clearsky`、`cloud_flag` 及可选诊断量。

    Raises
    ------
    ValueError
        When input lengths do not match.
        输入长度不一致时。

    References
    ----------
    .. [1] Bright, J. M., et al. (2020). Bright-Sun clear-sky detection methodology.
       (Implemented following the MATLAB csd-library BrightSun2020CSDc routine).
    """
    zenith = _as_1d_array(zenith, "zenith")
    ghi = _as_1d_array(ghi, "ghi", n=len(zenith))
    ghi_clear = _as_1d_array(ghi_clear, "ghi_clear", n=len(zenith))
    dhi = _as_1d_array(dhi, "dhi", n=len(zenith))
    dhi_clear = _as_1d_array(dhi_clear, "dhi_clear", n=len(zenith))
    idx = _resolve_index(times, len(zenith))

    dhi = np.minimum(dhi, ghi)
    dhi_clear = np.minimum(dhi_clear, ghi_clear)

    mu0 = np.cos(np.radians(zenith))
    bni = _safe_divide(ghi - dhi, mu0)
    bni_clear = _safe_divide(ghi_clear - dhi_clear, mu0)

    cloud_ghi, diag_ghi = _reno_cloud_flag(
        ghi,
        ghi_clear,
        mean_lim=75.0,
        max_lim=75.0,
        lower_L_lim=-5.0,
        upper_L_lim=10.0,
        sigma_lim=0.1,
        X_lim=8.0,
    )
    cloud_dhi, diag_dhi = _reno_cloud_flag(
        dhi,
        dhi_clear,
        mean_lim=0.5,
        max_lim=0.5,
        lower_L_lim=-1.7,
        upper_L_lim=10.0,
        sigma_lim=0.2,
        X_lim=8.0,
    )

    z_ref = np.arange(30.0, 90.01, 0.01)
    kc_lims = np.flip(np.linspace(0.5, 0.9, len(z_ref)))
    inds = np.searchsorted(z_ref, np.clip(zenith, z_ref[0], z_ref[-1]), side="left")
    inds = np.clip(inds, 0, len(z_ref) - 1)
    kc_lim = kc_lims[inds]
    kcb = _safe_divide(bni, bni_clear)
    cloud_bni = np.ones(len(zenith), dtype=float)
    cloud_bni[kcb > kc_lim] = 0.0

    cloud_flag = np.ones(len(zenith), dtype=float)
    cloud_flag[(cloud_ghi + cloud_dhi + cloud_bni) == 0] = 0.0

    bad = (
        np.isnan(zenith)
        | np.isnan(ghi)
        | np.isnan(ghi_clear)
        | np.isnan(dhi)
        | np.isnan(dhi_clear)
    )
    cloud_flag[bad] = np.nan
    cloud_bni[bad] = np.nan

    diagnostics = {
        "cloud_ghi": cloud_ghi,
        "cloud_dhi": cloud_dhi,
        "cloud_bni": cloud_bni,
        "kcb": kcb,
        "kc_lim": kc_lim,
        "mu0": mu0,
        "bni": bni,
        "bni_clear": bni_clear,
        "ghi_line_diff": diag_ghi["line_diff"],
        "dhi_line_diff": diag_dhi["line_diff"],
    }
    for key in diagnostics:
        arr = np.asarray(diagnostics[key], dtype=float)
        arr[bad] = np.nan
        diagnostics[key] = arr
    return _to_output(idx, cloud_flag, "brightsun", diagnostics, return_diagnostics)


def detect_clearsky(method, **kwargs):
    """
    Wrapper for clear-sky detection methods.
    晴空检测方法封装函数。

    Parameters
    ----------
    method : {"reno", "ineichen", "lefevre", "brightsun"}
        Method name.
        方法名称。
    **kwargs : dict
        Arguments forwarded to method function.
        传递给具体方法函数的参数。

    Returns
    -------
    out : pd.DataFrame
        Standardized CSD output.
        标准化 CSD 输出。

    Raises
    ------
    ValueError
        When method is not one of reno, ineichen, lefevre, brightsun.
        方法名不在支持列表中时。
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
        "Unsupported method. Choose one of brightsun, ineichen, lefevre, reno. / "
        "不支持的方法，请选择 brightsun、ineichen、lefevre、reno。"
    )
