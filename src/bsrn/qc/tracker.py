"""
BSRN Level 6 checks - tracker-off detection.
"""

import numpy as np
import pandas as pd


def tracker_off_test(ghi, bni, zenith, ghi_extra=None, ghi_clear=None,
                     dhi_clear=None, bni_clear=None):
    """
    Check if the solar tracker is off by comparing measured and clear-sky irradiances [1]_.

    Parameters
    ----------
    ghi : numeric or Series
        Measured global horizontal irradiance ($G_h$). [W/m^2]
    bni : numeric or Series
        Measured beam normal irradiance ($B_n$). [W/m^2]
    zenith : numeric or Series
        Solar zenith angle ($Z$). [degrees]
    ghi_extra : numeric or Series, optional
        Extraterrestrial horizontal irradiance ($E_0$). [W/m^2]
    ghi_clear : numeric or Series, optional
        Reference clear-sky global horizontal irradiance ($G_{hc}$). [W/m^2]
    dhi_clear : numeric or Series, optional
        Reference clear-sky diffuse horizontal irradiance ($D_{hc}$). [W/m^2]
    bni_clear : numeric or Series, optional
        Reference clear-sky beam normal irradiance ($B_{nc}$). [W/m^2]

    Returns
    -------
    flags : Series or ndarray
        Boolean flags (True = Pass). [bool]

    Raises
    ------
    ValueError
        If ``ghi_clear`` is not provided and ``ghi_extra`` is also missing.

    References
    ----------
    .. [1] Forstinger, A., et al. (2021). Expert quality control of solar
       radiation ground data sets. In SWC 2021: ISES Solar World Congress.
       International Solar Energy Society.
    """
    mu0 = np.cos(np.radians(zenith))

    # Fallback definitions per Forstinger et al. (2021)
    if ghi_clear is None:
        if ghi_extra is None:
            raise ValueError(
                "ghi_extra must be provided if ghi_clear is not supplied."
            )
        # GHIC ($G_{hc}$) = 0.8 * GHIE ($E_{0}$)
        ghi_clear = 0.8 * ghi_extra

    if dhi_clear is None:
        # DHIC ($D_{hc}$) = 0.165 * GHIC ($G_{hc}$)
        dhi_clear = 0.165 * ghi_clear

    if bni_clear is None:
        # BNIC ($B_{nc}$) = (GHIC - DHIC) / mu0
        bni_clear = (ghi_clear - dhi_clear) / np.maximum(mu0, 0.01)

    # Tracker-off: GHI near clear-sky but BNI far below reference
    # Term 1: (GHIC - GHI) / (GHIC + GHI) < 0.2
    term1 = (ghi_clear - ghi) / (ghi_clear + ghi)

    # Term 2: (BNIC - BNI) / (BNIC + BNI) > 0.95
    term2 = (bni_clear - bni) / (bni_clear + bni)

    # Apply when zenith < 85°
    tracker_is_off = (term1 < 0.2) & (term2 > 0.95) & (zenith < 85)

    if hasattr(tracker_is_off, 'iloc'):
        return ~tracker_is_off
    else:
        return not tracker_is_off
