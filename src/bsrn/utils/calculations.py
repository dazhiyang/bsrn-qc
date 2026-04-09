"""
Supporting mathematical and radiometric calculations.
"""

import numpy as np
import pandas as pd


def calc_kt(ghi, zenith, bni_extra, min_mu0=0.065,
            max_clearness_index=2.0):
    """
    Calculates clearness index ($k_t$) following pvlib conventions [1]_ [2]_ [3]_.

    $k_t = G_h / (E_{0n} \\cdot \\max(\\mu_0,\\; \\text{min\\_mu0}))$

    Parameters
    ----------
    ghi : numeric or Series
        Measured global horizontal irradiance ($G_h$). [W/m^2]
    zenith : numeric or Series
        True (not refraction-corrected) solar zenith angle ($Z$). [degrees]
    bni_extra : numeric or Series
        Extraterrestrial beam normal irradiance ($E_{0n}$). [W/m^2]
    min_mu0 : float, default 0.065
        Minimum $\\mu_0$ for the denominator (equiv. ~86.3 deg).
    max_clearness_index : float, default 2.0
        Upper clamp for $k_t$; 2.0 allows sub-hourly over-irradiance.

    Returns
    -------
    kt : numeric or Series
        Clearness index ($k_t$), clamped to [0, max_clearness_index]. [unitless]

    References
    ----------
    .. [1] Maxwell, E. L. (1987). A quasi-physical model for converting hourly
       global horizontal to direct normal insolation. Technical Report No.
       SERI/TR-215-3087, Golden, CO: Solar Energy Research Institute.
    .. [2] Holmgren, W. F., Hansen, C. W., & Mikofski, M. A. (2018). pvlib
       python: A python package for modeling solar energy systems. Journal of
       Open Source Software, 3(29), 884.
    .. [3] Anderson, K. S., Hansen, C. W., Holmgren, W. F., Jensen, A. R.,
       Mikofski, M. A., & Driesse, A. (2023). pvlib python: 2023 project
       update. Journal of Open Source Software, 8(92), 5994.
    """
    mu0 = np.cos(np.radians(zenith))
    ghi_extra = bni_extra * np.maximum(mu0, min_mu0)
    # ghi_extra can be 0 (e.g. bni_extra == 0); avoid RuntimeWarning on divide.
    with np.errstate(divide="ignore", invalid="ignore"):
        kt = ghi / ghi_extra
    kt = np.maximum(kt, 0)
    kt = np.minimum(kt, max_clearness_index)
    return kt


def calc_kb(bni, zenith, bni_extra, min_mu0=0.065,
            max_beam_transmittance=1.0):
    """
    Calculates beam transmittance ($k_b$) following pvlib conventions [1]_ [2]_.

    $k_b = B_n / E_{0n}$, floored at $\\mu_0 \\ge$ `min_mu0` for consistency,
    clamped to [0, max_beam_transmittance].

    Parameters
    ----------
    bni : numeric or Series
        Measured beam normal irradiance ($B_n$). [W/m^2]
    zenith : numeric or Series
        True (not refraction-corrected) solar zenith angle ($Z$). [degrees]
    bni_extra : numeric or Series
        Extraterrestrial beam normal irradiance ($E_{0n}$). [W/m^2]
    min_mu0 : float, default 0.065
        Minimum $\\mu_0$ to allow; timestamps where $\\mu_0 <$ `min_mu0`
        yield $k_b = 0$.
    max_beam_transmittance : float, default 1.0
        Upper clamp for $k_b$.

    Returns
    -------
    kb : numeric or Series
        Beam transmittance ($k_b$), clamped to [0, max_beam_transmittance]. [unitless]

    References
    ----------
    .. [1] Holmgren, W. F., Hansen, C. W., & Mikofski, M. A. (2018). pvlib
       python: A python package for modeling solar energy systems. Journal of
       Open Source Software, 3(29), 884.
    .. [2] Anderson, K. S., Hansen, C. W., Holmgren, W. F., Jensen, A. R.,
       Mikofski, M. A., & Driesse, A. (2023). pvlib python: 2023 project
       update. Journal of Open Source Software, 8(92), 5994.
    """
    mu0 = np.cos(np.radians(zenith))
    with np.errstate(divide="ignore", invalid="ignore"):
        kb = bni / bni_extra
    kb = np.where(mu0 < min_mu0, 0.0, kb)
    kb = np.maximum(kb, 0)
    kb = np.minimum(kb, max_beam_transmittance)
    return kb


def calc_kd(dhi, zenith, bni_extra, min_mu0=0.065,
            max_diffuse_transmittance=2.0):
    """
    Calculates diffuse transmittance ($k_d$) following pvlib conventions [1]_ [2]_.

    $k_d = D_h / (E_{0n} \\cdot \\max(\\mu_0,\\; \\text{min\\_mu0}))$

    Parameters
    ----------
    dhi : numeric or Series
        Measured diffuse horizontal irradiance ($D_h$). [W/m^2]
    zenith : numeric or Series
        True (not refraction-corrected) solar zenith angle ($Z$). [degrees]
    bni_extra : numeric or Series
        Extraterrestrial beam normal irradiance ($E_{0n}$). [W/m^2]
    min_mu0 : float, default 0.065
        Minimum $\\mu_0$ for the denominator (equiv. ~86.3 deg).
    max_diffuse_transmittance : float, default 2.0
        Upper clamp for $k_d$; 2.0 allows sub-hourly over-irradiance.

    Returns
    -------
    kd : numeric or Series
        Diffuse transmittance ($k_d$), clamped to
        [0, max_diffuse_transmittance]. [unitless]

    References
    ----------
    .. [1] Holmgren, W. F., Hansen, C. W., & Mikofski, M. A. (2018). pvlib
       python: A python package for modeling solar energy systems. Journal of
       Open Source Software, 3(29), 884.
    .. [2] Anderson, K. S., Hansen, C. W., Holmgren, W. F., Jensen, A. R.,
       Mikofski, M. A., & Driesse, A. (2023). pvlib python: 2023 project
       update. Journal of Open Source Software, 8(92), 5994.
    """
    mu0 = np.cos(np.radians(zenith))
    ghi_extra = bni_extra * np.maximum(mu0, min_mu0)
    kd = dhi / ghi_extra
    kd = np.maximum(kd, 0)
    kd = np.minimum(kd, max_diffuse_transmittance)
    return kd


def calc_k(dhi, ghi, zenith, min_mu0=0.065, max_diffuse_fraction=1.0):
    """
    Calculates diffuse fraction ($k$) following pvlib conventions [1]_ [2]_.

    $k = D_h / G_h$, with $\\mu_0$ guard and output clamping.

    Parameters
    ----------
    dhi : numeric or Series
        Measured diffuse horizontal irradiance ($D_h$). [W/m^2]
    ghi : numeric or Series
        Measured global horizontal irradiance ($G_h$). [W/m^2]
    zenith : numeric or Series
        True (not refraction-corrected) solar zenith angle ($Z$). [degrees]
    min_mu0 : float, default 0.065
        Minimum $\\mu_0$; timestamps where $\\mu_0 <$ `min_mu0`
        yield $k = $ NaN.
    max_diffuse_fraction : float, default 1.0
        Upper clamp for $k$.

    Returns
    -------
    k : numeric or Series
        Diffuse fraction ($k$), clamped to [0, max_diffuse_fraction]. [unitless]

    References
    ----------
    .. [1] Holmgren, W. F., Hansen, C. W., & Mikofski, M. A. (2018). pvlib
       python: A python package for modeling solar energy systems. Journal of
       Open Source Software, 3(29), 884.
    .. [2] Anderson, K. S., Hansen, C. W., Holmgren, W. F., Jensen, A. R.,
       Mikofski, M. A., & Driesse, A. (2023). pvlib python: 2023 project
       update. Journal of Open Source Software, 8(92), 5994.
    """
    mu0 = np.cos(np.radians(zenith))
    with np.errstate(divide="ignore", invalid="ignore"):
        k = dhi / ghi
    k = np.where(mu0 < min_mu0, np.nan, k)
    k = np.maximum(k, 0)
    k = np.minimum(k, max_diffuse_fraction)
    return k


def calc_kappa(ghi, ghi_clear, max_clearsky_index=2.0):
    """
    Calculates clear-sky index ($\\kappa$) following pvlib conventions [1]_ [2]_.

    $\\kappa = G_h / G_{hc}$

    Non-finite results are set to zero; NaN inputs are preserved.

    Parameters
    ----------
    ghi : numeric or Series
        Measured global horizontal irradiance ($G_h$). [W/m^2]
    ghi_clear : numeric or Series
        Modeled clear-sky global horizontal irradiance ($G_{hc}$). [W/m^2]
    max_clearsky_index : float, default 2.0
        Upper clamp for $\\kappa$; 2.0 allows sub-hourly over-irradiance.

    Returns
    -------
    kappa : numeric or Series
        Clear-sky index ($\\kappa$), clamped to [0, max_clearsky_index]. [unitless]

    References
    ----------
    .. [1] Holmgren, W. F., Hansen, C. W., & Mikofski, M. A. (2018). pvlib
       python: A python package for modeling solar energy systems. Journal of
       Open Source Software, 3(29), 884.
    .. [2] Anderson, K. S., Hansen, C. W., Holmgren, W. F., Jensen, A. R.,
       Mikofski, M. A., & Driesse, A. (2023). pvlib python: 2023 project
       update. Journal of Open Source Software, 8(92), 5994.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        kappa = ghi / ghi_clear
    kappa = np.where(~np.isfinite(kappa), 0.0, kappa)
    input_nan = ~np.isfinite(ghi) | ~np.isfinite(ghi_clear)
    kappa = np.where(input_nan, np.nan, kappa)
    kappa = np.maximum(kappa, 0)
    kappa = np.minimum(kappa, max_clearsky_index)

    if isinstance(ghi, pd.Series):
        kappa = pd.Series(kappa, index=ghi.index)

    return kappa
