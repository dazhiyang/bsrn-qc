"""
Cloud enhancement event (CEE) detection utilities.
云增强事件 (CEE) 检测工具函数。

Implements algorithms for detecting periods when measured global
irradiance is significantly higher than a clear-sky reference
(cloud enhancement events).
实现若干检测实测总辐照度显著高于晴空参考（云增强事件）的算法。
"""

import numpy as np
import pandas as pd


def _as_1d_array(x, name, n=None):
    """
    Convert input to 1D float array and optionally validate length.
    将输入转换为一维浮点数组，并在需要时校验长度。

    Parameters
    ----------
    x : array-like
        Input to convert.
        待转换的输入。
    name : str
        Name used in error messages.
        错误信息中使用的名称。
    n : int, optional
        Required length; if set, raise when len(x) != n.
        要求长度；若设置则当 len(x) != n 时抛出异常。

    Returns
    -------
    np.ndarray
        1D float array.
        一维浮点数组。

    Raises
    ------
    ValueError
        When n is set and len(x) != n.
        当 n 已设置且 len(x) != n 时抛出异常。
    """
    arr = np.asarray(x, dtype=float).reshape(-1)
    if n is not None and len(arr) != n:
        raise ValueError(f"{name} must have length {n}. / {name} 长度必须为 {n}。")
    return arr


def _cee_to_output(index, cee_flag, method, diagnostics=None, return_diagnostics=False):
    """
    Standardize cloud enhancement detection outputs.
    标准化云增强事件检测输出。

    Parameters
    ----------
    index : pandas.Index
        Output index.
        输出索引。
    cee_flag : array-like
        1=enhancement, 0=non-enhancement, NaN=invalid.
        1 表示云增强，0 表示非增强，NaN 表示无效。
    method : str
        Method name for output column.
        方法名称（输出列）。
    diagnostics : dict, optional
        Extra arrays to add to output.
        需要附加到输出中的诊断数组。
    return_diagnostics : bool, default False
        If True, include diagnostics in output.
        若为 True，则在输出中包含诊断列。

    Returns
    -------
    pandas.DataFrame
        Columns: is_enhancement, cee_flag, method [, diagnostics].
        列：is_enhancement, cee_flag, method 以及可选诊断列。
    """
    cee = np.asarray(cee_flag, dtype=float)
    is_enhancement = pd.array(cee == 1.0, dtype="boolean")
    is_enhancement[np.isnan(cee)] = pd.NA

    out = pd.DataFrame(
        {
            "is_enhancement": is_enhancement,
            "cee_flag": cee,
            "method": method,
        },
        index=index,
    )
    if return_diagnostics and diagnostics is not None:
        for col, arr in diagnostics.items():
            out[col] = np.asarray(arr, dtype=float)
    return out


def killinger_ced(ghi, ghi_clear, zenith, times, return_diagnostics=False):
    """
    Detect cloud enhancement events using Killinger et al. (2017).
    使用 Killinger 等 (2017) 方法检测云增强事件。

    Parameters
    ----------
    ghi : array-like
        1‑minute global horizontal irradiance. [W/m^2]
        1 分钟水平总辐照度。[瓦/平方米]
    ghi_clear : array-like
        1‑minute clear-sky global horizontal irradiance. [W/m^2]
        1 分钟晴空水平总辐照度。[瓦/平方米]
    zenith : array-like
        1‑minute solar zenith angle. [degrees]
        1 分钟太阳天顶角。[度]
    times : pandas.DatetimeIndex or array-like
        1‑minute timestamps convertible to ``DatetimeIndex``.
        可转换为 ``DatetimeIndex`` 的 1 分钟时间戳。
    return_diagnostics : bool, default False
        If True, include diagnostic columns (ratio, sdev_rel, n_valid, zenith).
        若为 True，同时返回诊断列（ratio, sdev_rel, n_valid, zenith）。

    Returns
    -------
    out : pandas.DataFrame
        DataFrame indexed by aggregated timestamps (e.g. 6‑minute) with:

        * ``is_enhancement`` – True where a cloud enhancement is detected.
        * ``ced_flag`` – 1 for enhancement, 0 otherwise, NaN when invalid.

        以聚合时间戳（如 6 分钟）为索引的 DataFrame，包含：

        * ``is_enhancement`` – 检测到云增强时为 True。
        * ``ced_flag`` – 1 表示云增强，0 表示非增强，无效为 NaN。

    References
    ----------
    .. [1] Killinger, S., Engerer, N., & Müller, B. (2017). QCPV: A quality
       control algorithm for distributed photovoltaic array power output.
       Solar Energy, 143, 120–131.
    """
    # Fixed Killinger parameters (see method description above).
    # 固定 Killinger 判据参数（详见方法描述）。
    window_minutes = 6
    sdev_threshold = 0.05
    kappa_threshold = 1.10
    zenith_max = 75.0

    ghi = _as_1d_array(ghi, "ghi")
    ghi_clear = _as_1d_array(ghi_clear, "ghi_clear", n=len(ghi))
    zenith = _as_1d_array(zenith, "zenith", n=len(ghi))

    idx = pd.DatetimeIndex(times)
    if len(idx) != len(ghi):
        raise ValueError("times length must match inputs. / times 长度必须与输入一致。")

    # Use ±6‑minute neighbours around each 1‑minute sample: GHI_{t-6min}, GHI_t, GHI_{t+6min}.
    # 在每个 1 分钟样本周围使用 ±6 分钟邻点：GHI_{t-6min}, GHI_t, GHI_{t+6min}。
    s = pd.Series(ghi, index=idx)
    s_m6 = s.shift(window_minutes)
    s_p6 = s.shift(-window_minutes)
    window_df = pd.DataFrame({"m6": s_m6, "t": s, "p6": s_p6})

    # Number of finite points in the three-sample window and relative standard deviation.
    # 三点窗口中的有效样本数以及相对标准差。
    n_valid = np.sum(np.isfinite(window_df.to_numpy(dtype=float)), axis=1)
    mean_val = window_df.mean(axis=1, skipna=False)
    sdev = window_df.std(axis=1, ddof=1, skipna=False)
    with np.errstate(divide="ignore", invalid="ignore"):
        sdev_rel = (sdev / mean_val).to_numpy(dtype=float)

    # Clear-sky index (kappa = ghi / ghi_clear) and zenith condition
    # at the central 1‑minute point.
    # 在中心 1 分钟点上计算晴空指数 (kappa = ghi / ghi_clear) 与天顶角条件。
    with np.errstate(divide="ignore", invalid="ignore"):
        kappa = ghi / ghi_clear
    cond_kappa = kappa > kappa_threshold
    cond_zen = zenith < zenith_max
    cond_sdev = sdev_rel > sdev_threshold

    # Final enhancement condition on each 1‑minute sample.
    # 在每个 1 分钟样本上应用最终云增强条件。
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

    diagnostics = None
    if return_diagnostics:
        diagnostics = {
            "kappa": kappa,
            "sdev_rel": sdev_rel,
            "n_valid": n_valid.astype(float),
            "zenith": zenith,
        }

    return _cee_to_output(idx, cee_flag, "killinger", diagnostics, return_diagnostics)


def gueymard_ced(ghi, ghi_extra, times=None, return_diagnostics=False):
    """
    Detect cloud enhancement events when GHI exceeds extraterrestrial GHI.
    当 GHI 大于地外水平辐照度时检测云增强事件。

    Parameters
    ----------
    ghi : array-like
        Global horizontal irradiance. [W/m^2]
        水平总辐照度。[瓦/平方米]
    ghi_extra : array-like
        Horizontal extraterrestrial irradiance. [W/m^2]
        地外水平辐照度。[瓦/平方米]
    times : array-like or pandas.DatetimeIndex, optional
        Time index for outputs. If None, a simple RangeIndex is used.
        输出时间索引；若为 None，则使用 RangeIndex。
    return_diagnostics : bool, default False
        If True, include the clearness index ``kt`` as diagnostics.
        若为 True，则在诊断信息中包含晴朗指数 ``kt``。

    Returns
    -------
    pandas.DataFrame
        Standardized CEE output with columns `is_enhancement`, `cee_flag`,
        `method`, and optionally `ratio`.
        标准化 CEE 输出，包含 `is_enhancement`、`cee_flag`、`method` 以及可选的 `ratio` 列。

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
            raise ValueError("times length must match inputs. / times 长度必须与输入一致。")
        idx = times
    else:
        idx = pd.DatetimeIndex(times)
        if len(idx) != len(ghi):
            raise ValueError("times length must match inputs. / times 长度必须与输入一致。")

    with np.errstate(divide="ignore", invalid="ignore"):
        kt = ghi / ghi_extra
    cee_flag = np.zeros(len(ghi), dtype=float)
    cee_flag[kt > 1.0] = 1.0
    bad = ~np.isfinite(ghi) | ~np.isfinite(ghi_extra)
    cee_flag[bad] = np.nan

    diagnostics = None
    if return_diagnostics:
        kt_array = np.asarray(kt, dtype=float)
        kt_array[bad] = np.nan
        diagnostics = {"kt": kt_array}

    return _cee_to_output(idx, cee_flag, "gueymard", diagnostics, return_diagnostics)


def wang_ced(ghi, ghi_clear, bni, bni_clear, dhi, dhi_clear, times,
             mag_threshold=1.10, bni_fraction=0.8, dhi_multiplier=1.5,
             max_duration_minutes=15.0, return_diagnostics=False):
    """
    Cloud enhancement detection with additional beam and diffuse checks.
    带有束和散射分量附加判据的云增强事件检测。

    This method follows a four-step logic:
    本方法遵循四步逻辑：

    1. Index alignment – all inputs share a common time index.
       索引对齐——所有输入共享同一时间索引。
    2. Instantaneous masks – three vectorized conditions:
       瞬时掩码——三个向量化条件：

       * Magnitude: :math:`G_h / G_{hc} >` ``mag_threshold``.
         幅值：:math:`G_h / G_{hc} >` ``mag_threshold``。
       * Beam: :math:`B_n / B_{nc} >` ``bni_fraction``.
         束：:math:`B_n / B_{nc} >` ``bni_fraction``。
       * Diffuse: :math:`D_h / D_{hc} >` ``dhi_multiplier``.
         散射：:math:`D_h / D_{hc} >` ``dhi_multiplier``。

    3. Instantaneous intersection – logical AND of the three masks gives a
       preliminary enhancement mask.
       瞬时交集——三者按位与得到初始云增强掩码。

    4. 15‑minute volatility filter – consecutive True runs longer than
       ``max_duration_minutes`` are rejected.
       15 分钟波动过滤——连续 True 片段若时间长度超过 ``max_duration_minutes`` 则被剔除。

    Parameters
    ----------
    ghi : array-like
        Global horizontal irradiance (`ghi`). [W/m^2]
        水平总辐照度 (`ghi`)。[瓦/平方米]
    ghi_clear : array-like
        Clear-sky global horizontal irradiance (`ghi_clear`). [W/m^2]
        晴空水平总辐照度 (`ghi_clear`)。[瓦/平方米]
    bni : array-like
        Beam normal irradiance (`bni`). [W/m^2]
        法向直接辐照度 (`bni`)。[瓦/平方米]
    bni_clear : array-like
        Clear-sky beam normal irradiance (`bni_clear`). [W/m^2]
        晴空法向直接辐照度 (`bni_clear`)。[瓦/平方米]
    dhi : array-like
        Diffuse horizontal irradiance (`dhi`). [W/m^2]
        水平散射辐照度 (`dhi`)。[瓦/平方米]
    dhi_clear : array-like
        Clear-sky diffuse horizontal irradiance (`dhi_clear`). [W/m^2]
        晴空水平散射辐照度 (`dhi_clear`)。[瓦/平方米]
    times : array-like or pandas.DatetimeIndex
        Time index, ideally at 1‑minute cadence.
        时间索引，建议为 1 分钟分辨率。
    mag_threshold : float, default 1.10
        Threshold for :math:`G_h / G_{hc}`.
        :math:`G_h / G_{hc}` 的阈值。
    bni_fraction : float, default 0.8
        Fraction applied to :math:`B_{nc}` in the beam mask.
        束判据中乘于 :math:`B_{nc}` 的系数。
    dhi_multiplier : float, default 1.5
        Multiplier applied to :math:`D_{hc}` in the diffuse mask.
        散射判据中乘于 :math:`D_{hc}` 的系数。
    max_duration_minutes : float, default 15.0
        Maximum allowed duration (in minutes) of a consecutive enhancement block.
        允许的连续云增强片段的最长持续时间（分钟）。
    return_diagnostics : bool, default False
        If True, include intermediate masks and kappa in diagnostics.
        若为 True，则在诊断信息中返回中间掩码与晴空指数。

    Returns
    -------
    pandas.DataFrame
        Standardized CEE output with columns `is_enhancement`, `cee_flag`,
        `method`, and optional diagnostics.
        标准化 CEE 输出，包含 `is_enhancement`、`cee_flag`、`method` 以及可选诊断列。
    """
    ghi = _as_1d_array(ghi, "ghi")
    ghi_clear = _as_1d_array(ghi_clear, "ghi_clear", n=len(ghi))
    bni = _as_1d_array(bni, "bni", n=len(ghi))
    bni_clear = _as_1d_array(bni_clear, "bni_clear", n=len(ghi))
    dhi = _as_1d_array(dhi, "dhi", n=len(ghi))
    dhi_clear = _as_1d_array(dhi_clear, "dhi_clear", n=len(ghi))

    idx = pd.DatetimeIndex(times)
    if len(idx) != len(ghi):
        raise ValueError("times length must match inputs. / times 长度必须与输入一致。")

    with np.errstate(divide="ignore", invalid="ignore"):
        kappa = ghi / ghi_clear
        mask_mag = kappa > float(mag_threshold)
        mask_bni = bni > (float(bni_fraction) * bni_clear)
        mask_dhi = dhi > (float(dhi_multiplier) * dhi_clear)

    finite_all = (
        np.isfinite(ghi)
        & np.isfinite(ghi_clear)
        & np.isfinite(bni)
        & np.isfinite(bni_clear)
        & np.isfinite(dhi)
        & np.isfinite(dhi_clear)
    )
    prelim_mask = mask_mag & mask_bni & mask_dhi & finite_all

    # Derive sample interval in minutes to generalize beyond exact 1‑min cadence.
    # 推断采样间隔（分钟），以兼容非严格 1 分钟分辨率。
    if len(idx) > 1:
        dt_minutes = (idx[1] - idx[0]).total_seconds() / 60.0
        if dt_minutes <= 0:
            dt_minutes = 1.0
    else:
        dt_minutes = 1.0
    max_len = int(np.floor(max_duration_minutes / dt_minutes + 1e-9))
    if max_len < 1:
        max_len = 1

    prelim = np.asarray(prelim_mask, dtype=bool)
    allowed = np.zeros(len(prelim), dtype=bool)
    n = len(prelim)
    i = 0
    while i < n:
        if not prelim[i]:
            i += 1
            continue
        j = i + 1
        while j < n and prelim[j]:
            j += 1
        block_len = j - i
        if block_len <= max_len:
            allowed[i:j] = True
        i = j

    cee_flag = np.zeros(n, dtype=float)
    cee_flag[allowed] = 1.0
    cee_flag[~finite_all] = np.nan

    diagnostics = None
    if return_diagnostics:
        kappa_arr = np.asarray(kappa, dtype=float)
        kappa_arr[~finite_all] = np.nan
        diagnostics = {
            "kappa": kappa_arr,
            "mask_mag": mask_mag.astype(float),
            "mask_bni": mask_bni.astype(float),
            "mask_dhi": mask_dhi.astype(float),
            "prelim_mask": prelim.astype(float),
            "allowed_mask": allowed.astype(float),
        }

    return _cee_to_output(idx, cee_flag, "wang", diagnostics, return_diagnostics)


def detect_cee(method, **kwargs):
    """
    Wrapper for cloud enhancement event (CEE) detection methods.
    云增强事件检测方法封装函数。

    Parameters
    ----------
    method : {"killinger", "gueymard", "wang"}
        Method name.
        方法名称。
    **kwargs : dict
        Arguments forwarded to method function.
        传递给具体方法函数的参数。

    Returns
    -------
    pandas.DataFrame
        Standardized CEE output with is_enhancement, cee_flag, method, etc.
        标准化 CEE 输出，包含 is_enhancement、cee_flag、method 等列。

    Raises
    ------
    ValueError
        When method is not one of the supported CEE methods.
        当方法名不在支持列表中时抛出异常。
    """
    method_key = str(method).strip().lower()
    if method_key == "killinger":
        return killinger_ced(**kwargs)
    if method_key == "gueymard":
        return gueymard_ced(**kwargs)
    if method_key == "wang":
        return wang_ced(**kwargs)
    raise ValueError(
        "Unsupported method. Choose one of gueymard, killinger, wang. / "
        "不支持的方法，请选择 gueymard、killinger、wang。"
    )

