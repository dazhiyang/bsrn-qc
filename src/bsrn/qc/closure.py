"""
BSRN Level 3 inter-comparison checks: GHI–BNI–DHI closure.
"""

import numpy as np
import pandas as pd


def closure_low_sza_test(ghi, bni, dhi, zenith):
    r"""
    Check consistency between GHI, BNI, and DHI for low solar zenith angles ($Z \le 75^\circ$) [1]_.

    Parameters
    ----------
    ghi : numeric or Series
        Global horizontal irradiance ($G_h$). [W/m^2]
    bni : numeric or Series
        Beam normal irradiance ($B_n$). [W/m^2]
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
    .. [1] Long, C. N., & Shi, Y. (2008). An automated quality assessment
       and control algorithm for surface radiation measurements. The Open
       Atmospheric Science Journal, 2(1), 23-37.
    """
    mu0 = np.cos(np.radians(zenith))

    # GHI reconstructed from BNI and DHI
    ghi_calc = bni * mu0 + dhi
    ghi_calc_safe = np.where(ghi_calc > 0, ghi_calc, np.nan)

    # Condition: |GHI / (DNI * cos(SZA) + DIF) - 1| <= 0.08
    diff_ratio = np.abs(ghi / ghi_calc_safe - 1)

    # Domain: Z <= 75 and GHI > 50
    in_domain = (zenith <= 75) & (ghi > 50)
    condition_met = diff_ratio <= 0.08

    if hasattr(in_domain, 'iloc'):
        return (~in_domain) | condition_met
    else:
        return (not in_domain) or condition_met


def closure_high_sza_test(ghi, bni, dhi, zenith):
    r"""
    Check consistency between GHI, BNI, and DHI for high solar zenith angles ($Z > 75^\circ$) [1]_.

    Parameters
    ----------
    ghi : numeric or Series
        Global horizontal irradiance ($G_h$). [W/m^2]
    bni : numeric or Series
        Beam normal irradiance ($B_n$). [W/m^2]
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
    .. [1] Long, C. N., & Shi, Y. (2008). An automated quality assessment
       and control algorithm for surface radiation measurements. The Open
       Atmospheric Science Journal, 2(1), 23-37.
    """
    mu0 = np.cos(np.radians(zenith))

    # GHI reconstructed from BNI and DHI
    ghi_calc = bni * mu0 + dhi
    ghi_calc_safe = np.where(ghi_calc > 0, ghi_calc, np.nan)

    # Condition: |GHI / (DNI * cos(SZA) + DIF) - 1| <= 0.15
    diff_ratio = np.abs(ghi / ghi_calc_safe - 1)

    # Domain: Z > 75 and GHI > 50
    in_domain = (zenith > 75) & (ghi > 50)
    condition_met = diff_ratio <= 0.15

    if hasattr(in_domain, 'iloc'):
        return (~in_domain) | condition_met
    else:
        return (not in_domain) or condition_met
