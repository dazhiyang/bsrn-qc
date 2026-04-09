"""
BSRN Level 5 checks - radiometric index tests (k-tests).
"""

import numpy as np
import pandas as pd


def kb_kt_test(ghi, bni, bni_extra, zenith):
    """
    Check if beam transmittance ($k_b$) is less than clearness index ($k_t$) [1]_.

    Parameters
    ----------
    ghi : numeric or Series
        Global horizontal irradiance ($G_h$). [W/m^2]
    bni : numeric or Series
        Beam normal irradiance ($B_n$). [W/m^2]
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

    kb = bni / bni_extra
    kt = ghi / (bni_extra * mu0)

    # Domain: GHI > 50 and kb > 0 and kt > 0
    in_domain = (ghi > 50) & (kb > 0) & (kt > 0)
    condition_met = kb < kt

    if hasattr(in_domain, 'iloc'):
        return (~in_domain) | condition_met
    else:
        return (not in_domain) or condition_met


def kb_limit_test(bni, bni_extra, elevation, ghi):
    """
    Check if beam transmittance ($k_b$) stays within absolute physical limits based on elevation [1]_.

    Parameters
    ----------
    bni : numeric or Series
        Beam normal irradiance ($B_n$). [W/m^2]
    bni_extra : numeric or Series
        Extraterrestrial beam normal irradiance ($E_{0n}$). [W/m^2]
    elevation : numeric
        Site elevation. [m]
    ghi : numeric or Series
        Global horizontal irradiance ($G_h$). [W/m^2]

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
    kb = bni / bni_extra

    # Domain: GHI > 50 and kb > 0
    in_domain = (ghi > 50) & (kb > 0)
    condition_met = kb < (1100 + 0.03 * elevation) / bni_extra

    if hasattr(in_domain, 'iloc'):
        return (~in_domain) | condition_met
    else:
        return (not in_domain) or condition_met


def kt_limit_test(ghi, bni_extra, zenith):
    """
    Check if clearness index ($k_t$) is within physically possible limits [1]_.

    Parameters
    ----------
    ghi : numeric or Series
        Global horizontal irradiance ($G_h$). [W/m^2]
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

    # Domain: GHI > 50 and kt > 0
    in_domain = (ghi > 50) & (kt > 0)
    condition_met = kt < 1.35

    if hasattr(in_domain, 'iloc'):
        return (~in_domain) | condition_met
    else:
        return (not in_domain) or condition_met
