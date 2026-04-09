"""
BSRN Level 1 (physically possible) quality tests.
"""

import numpy as np
import pandas as pd


def ghi_ppl_test(ghi, zenith, bni_extra):
    """
    Check global horizontal irradiance (GHI, $G_h$) against physically possible limits [1]_.

    Parameters
    ----------
    ghi : numeric or Series
        Global horizontal irradiance ($G_h$). [W/m^2]
    zenith : numeric or Series
        Solar zenith angle ($Z$). [degrees]
    bni_extra : numeric or Series
        Extraterrestrial beam normal irradiance ($E_{0n}$). [W/m^2]

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
    mu0 = np.maximum(mu0, 0)

    # Upper limit: 1.5 * E_0n * mu0^1.2 + 100
    upper_limit = 1.5 * bni_extra * (mu0 ** 1.2) + 100
    # Lower limit: -4 W/m^2
    lower_limit = -4

    return (ghi >= lower_limit) & (ghi <= upper_limit)


def bni_ppl_test(bni, bni_extra):
    """
    Check beam normal irradiance (BNI, $B_n$) against physically possible limits [1]_.

    Parameters
    ----------
    bni : numeric or Series
        Beam normal irradiance ($B_n$). [W/m^2]
    bni_extra : numeric or Series
        Extraterrestrial beam normal irradiance ($E_{0n}$). [W/m^2]

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
    # Upper limit: E_0n
    upper_limit = bni_extra
    # Lower limit: -4 W/m^2
    lower_limit = -4

    return (bni >= lower_limit) & (bni <= upper_limit)


def dhi_ppl_test(dhi, zenith, bni_extra):
    """
    Check diffuse horizontal irradiance (DHI, $D_h$) against physically possible limits [1]_.

    Parameters
    ----------
    dhi : numeric or Series
        Diffuse horizontal irradiance ($D_h$). [W/m^2]
    zenith : numeric or Series
        Solar zenith angle ($Z$). [degrees]
    bni_extra : numeric or Series
        Extraterrestrial beam normal irradiance ($E_{0n}$). [W/m^2]

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
    mu0 = np.maximum(mu0, 0)

    # Upper limit: 0.95 * E_0n * mu0^1.2 + 50
    upper_limit = 0.95 * bni_extra * (mu0 ** 1.2) + 50
    # Lower limit: -4 W/m^2
    lower_limit = -4

    return (dhi >= lower_limit) & (dhi <= upper_limit)


def lwd_ppl_test(lwd):
    """
    Check downward longwave radiation (LWD, $L_d$) against physically possible limits [1]_.

    Parameters
    ----------
    lwd : numeric or Series
        Downward longwave radiation ($L_d$). [W/m^2]

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
    # Lower limit: 40 W/m^2, upper limit: 700 W/m^2
    return (lwd >= 40) & (lwd <= 700)
