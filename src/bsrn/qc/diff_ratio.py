"""
BSRN Level 4 checks - diffuse ratio tests (k-tests).
"""

import numpy as np
import pandas as pd


def k_low_sza_test(ghi, dhi, zenith):
    r"""
    Check diffuse fraction ($k$) for low solar zenith angles ($Z < 75^\circ$) [1]_ [2]_.

    Parameters
    ----------
    ghi : numeric or Series
        Global horizontal irradiance ($G_h$). [W/m^2]
    dhi : numeric or Series
        Diffuse horizontal irradiance ($D_h$). [W/m^2]
    zenith : numeric or Series
        Solar zenith angle ($Z$). [degrees]

    Returns
    -------
    flags : Series or ndarray
        Boolean flags (True = Pass). [bool]

    References
    ----------
    .. [1] Forstinger, A., et al. (2021). Expert quality control of solar
       radiation ground data sets. In SWC 2021: ISES Solar World Congress.
       International Solar Energy Society.
    .. [2] Long, C. N., & Shi, Y. (2008). An automated quality assessment
       and control algorithm for surface radiation measurements. The Open
       Atmospheric Science Journal, 2(1), 23-37.
    """
    ghi_safe = np.where(ghi > 0, ghi, np.nan)
    k = dhi / ghi_safe

    # Domain: Z < 75 and GHI > 50 and k > 0
    in_domain = (zenith < 75) & (ghi > 50) & (k > 0)
    condition_met = k < 1.05

    if hasattr(in_domain, 'iloc'):
        return (~in_domain) | condition_met
    else:
        return (not in_domain) or condition_met


def k_high_sza_test(ghi, dhi, zenith):
    r"""
    Check diffuse fraction ($k$) for high solar zenith angles ($Z \ge 75^\circ$) [1]_ [2]_.

    Parameters
    ----------
    ghi : numeric or Series
        Global horizontal irradiance ($G_h$). [W/m^2]
    dhi : numeric or Series
        Diffuse horizontal irradiance ($D_h$). [W/m^2]
    zenith : numeric or Series
        Solar zenith angle ($Z$). [degrees]

    Returns
    -------
    flags : Series or ndarray
        Boolean flags (True = Pass). [bool]

    References
    ----------
    .. [1] Forstinger, A., et al. (2021). Expert quality control of solar
       radiation ground data sets. In SWC 2021: ISES Solar World Congress.
       International Solar Energy Society.
    .. [2] Long, C. N., & Shi, Y. (2008). An automated quality assessment
       and control algorithm for surface radiation measurements. The Open
       Atmospheric Science Journal, 2(1), 23-37.
    """
    ghi_safe = np.where(ghi > 0, ghi, np.nan)
    k = dhi / ghi_safe

    # Domain: Z >= 75 and GHI > 50 and k > 0
    in_domain = (zenith >= 75) & (ghi > 50) & (k > 0)
    condition_met = k < 1.1

    if hasattr(in_domain, 'iloc'):
        return (~in_domain) | condition_met
    else:
        return (not in_domain) or condition_met


def k_kt_combined_test(ghi, dhi, bni_extra, zenith):
    """
    Combined check of diffuse fraction ($k$) and clearness index ($k_t$) [1]_.

    Parameters
    ----------
    ghi : numeric or Series
        Global horizontal irradiance ($G_h$). [W/m^2]
    dhi : numeric or Series
        Diffuse horizontal irradiance ($D_h$). [W/m^2]
    bni_extra : numeric or Series
        Extraterrestrial beam normal irradiance ($E_{0n}$). [W/m^2]
    zenith : numeric or Series
        Solar zenith angle ($Z$). [degrees]

    Returns
    -------
    flags : Series or ndarray
        Boolean flags (True = Pass). [bool]

    References
    ----------
    .. [1] Forstinger, A., et al. (2021). Expert quality control of solar
       radiation ground data sets. In SWC 2021: ISES Solar World Congress.
       International Solar Energy Society.
    """
    mu0 = np.cos(np.radians(zenith))
    kt = ghi / (bni_extra * mu0)

    ghi_safe = np.where(ghi > 0, ghi, np.nan)
    k = dhi / ghi_safe

    # Domain: kt > 0.6 and GHI > 150 and Z < 85 and k > 0
    in_domain = (kt > 0.6) & (ghi > 150) & (zenith < 85) & (k > 0)
    condition_met = k < 0.96

    if hasattr(in_domain, 'iloc'):
        return (~in_domain) | condition_met
    else:
        return (not in_domain) or condition_met
