"""
clear-sky radiation models.
Provides theoretical reference for QC checks and separation modeling.
"""

import numpy as np
import pandas as pd
from bsrn.physics import geometry
from bsrn.constants import (
    BSRN_STATIONS,
    LINKE_TURBIDITY,
)
from bsrn.io.mcclear import fetch_mcclear
from bsrn.io.merra2 import fetch_rest2


def get_relative_airmass(zenith, model='kastenyoung1989'):
    """
    Calculate relative (not pressure-adjusted) airmass at sea level.

    Parameters
    ----------
    zenith : numeric
        Solar zenith angle ($Z$). [degrees]

    model : string, default 'kastenyoung1989'
        Available models include:
        * 'kasten1966' - See [1]_
        * 'kastenyoung1989' (default) - See [2]_

    Returns
    -------
    airmass_relative : numeric
        Relative airmass at sea level. Returns NaN values for any
        zenith angle greater than 90 degrees. [unitless]

    Raises
    ------
    ValueError
        If *model* is not ``'kastenyoung1989'`` or ``'kasten1966'``.

    References
    ----------
    .. [1] Kasten, F. (1965). A New Table and Approximation Formula for the
       Relative Optical Air Mass (Technical Report 136). Hanover, NH:
       CRREL (U.S. Army).
    .. [2] Kasten, F., & Young, A. T. (1989). Revised optical air mass
       tables and approximation formula. Applied Optics, 28(22), 4735-4738.
    """
    # Set zenith values greater than 90 to nans
    zenith = np.where(zenith > 90, np.nan, zenith)

    model = model.lower()

    if 'kastenyoung1989' == model:
        zenith_rad = np.radians(zenith)
        am = (1.0 / (np.cos(zenith_rad) +
              0.50572*((6.07995 + (90 - zenith)) ** - 1.6364)))
    elif 'kasten1966' == model:
        zenith_rad = np.radians(zenith)
        am = 1.0 / (np.cos(zenith_rad) + 0.15*((93.885 - zenith) ** - 1.253))
    else:
        raise ValueError(f'{model} is not a valid model for relative airmass.')

    if isinstance(zenith, pd.Series):
        am = pd.Series(am, index=zenith.index)

    return am

def get_absolute_airmass(airmass_relative, pressure=101325.0):
    """
    Calculates absolute (pressure-corrected) airmass.

    Parameters
    ----------
    airmass_relative : numeric
        Relative optical air mass. [unitless]
    pressure : numeric, default 101325.0
        Surface pressure. [Pa]

    Returns
    -------
    airmass_absolute : numeric
        Absolute optical air mass. [unitless]
    """
    return airmass_relative * pressure / 101325.

def ineichen_model(apparent_zenith, airmass_absolute, lt, elev, bni_extra):
    """
    Implementation of Ineichen clear-sky model [1]_ matching the formulation from pvlib.

    Parameters
    ----------
    apparent_zenith : numeric
        Apparent (refraction-corrected) solar zenith angle ($Z$). [degrees]
    airmass_absolute : numeric
        Absolute (pressure-corrected) air mass ($AM_a$). [unitless]
    lt : numeric
        Linke turbidity factor ($T_L$). [unitless]
    elev : float
        Elevation. [m]
    bni_extra : numeric
        Extraterrestrial beam normal irradiance ($E_{0n}$). [W/m^2]

    Returns
    -------
    ghi_clear : numeric
        Clear-sky global horizontal irradiance ($G_{hc}$). [W/m^2]
    bni_clear : numeric
        Clear-sky beam normal irradiance ($B_{nc}$). [W/m^2]
    dhi_clear : numeric
        Clear-sky diffuse horizontal irradiance ($D_{hc}$). [W/m^2]

    References
    ----------
    .. [1] Ineichen, P., & Perez, R. (2002). A new airmass independent 
       formulation for the Linke turbidity coefficient. Solar Energy, 73(3), 151-157.
    """
    mu0 = np.maximum(np.cos(np.radians(apparent_zenith)), 0)
    
    # Altitude-dependent coefficients
    fh1 = np.exp(-elev / 8000.0)
    fh2 = np.exp(-elev / 1250.0)
    cg1 = 5.09e-05 * elev + 0.868
    cg2 = 3.92e-05 * elev + 0.0387
    
    # GHI calculation
    # ghi_clear matches pvlib 'ghi' logic and NaN handling
    ghi_exp = np.exp(-cg2 * airmass_absolute * (fh1 + fh2 * (lt - 1)))
    ghi_clear = cg1 * bni_extra * mu0 * lt / lt * np.fmax(ghi_exp, 0)
    
    # BNI calculation
    # First component: direct beam attenuation
    b = 0.664 + 0.163 / fh1
    bni_clear_1 = b * np.exp(-0.09 * airmass_absolute * (lt - 1))
    bni_clear_1 = bni_extra * np.fmax(bni_clear_1, 0)
    
    # Second component: empirical correction
    with np.errstate(divide='ignore', invalid='ignore'):
        bni_multiplier = ((1.0 - (0.1 - 0.2 * np.exp(-lt)) / (0.1 + 0.882 / fh1)) /
                       mu0)
        bni_clear_2 = ghi_clear * np.fmin(np.fmax(bni_multiplier, 0), 1e20)
    
    bni_clear = np.minimum(bni_clear_1, bni_clear_2)
    
    # DHI by subtraction
    dhi_clear = ghi_clear - bni_clear * mu0
    
    return ghi_clear, bni_clear, dhi_clear


def rest2_model(index, zenith, rest2_inputs, no2=0.0002):
    """
    REST2 clear-sky model [1]_ translated from the provided R implementation.

    Parameters
    ----------
    index : pd.DatetimeIndex
        Time index for the calculation.
    zenith : array-like
        Solar zenith angle ($Z$). [degrees]
    rest2_inputs : pd.DataFrame
        Input dataframe from `fetch_rest2`, with columns:
        `PS`, `ALBEDO`, `ALPHA`, `BETA`, `TO3`, `TQV`.
    no2 : float, default 0.0002
        Total column nitrogen dioxide amount.

    Returns
    -------
    ghi_clear : np.ndarray
        Clear-sky global horizontal irradiance ($G_{hc}$). [W/m^2]
    bni_clear : np.ndarray
        Clear-sky beam normal irradiance ($B_{nc}$). [W/m^2]
    dhi_clear : np.ndarray
        Clear-sky diffuse horizontal irradiance ($D_{hc}$). [W/m^2]

    Raises
    ------
    ValueError
        If ``rest2_inputs`` is not a :class:`~pandas.DataFrame`, row counts differ,
        or required columns are missing.

    References
    ----------
    .. [1] Gueymard, C. A. (2008). REST2: High-performance solar radiation model
       for cloudless-sky irradiance, illuminance, and photosynthetically active
       radiation: Validation with a benchmark dataset. Solar Energy, 82(3), 272-285.
    """
    idx = pd.DatetimeIndex(index)
    if not isinstance(rest2_inputs, pd.DataFrame):
        raise ValueError("rest2_inputs must be a DataFrame.")
    if len(idx) != len(rest2_inputs):
        raise ValueError("index and rest2_inputs must have equal length.")

    required = {"PS", "ALBEDO", "ALPHA", "BETA", "TO3", "TQV"}
    missing = required - set(rest2_inputs.columns)
    if missing:
        raise ValueError(f"REST2 inputs missing required columns: {sorted(missing)}")

    # Read REST2 inputs directly from reanalysis preprocessing.
    ps = np.asarray(rest2_inputs["PS"], dtype=float)
    albedo_val = np.asarray(rest2_inputs["ALBEDO"], dtype=float)
    alpha = np.asarray(rest2_inputs["ALPHA"], dtype=float)
    beta = np.asarray(rest2_inputs["BETA"], dtype=float)
    ozone = np.asarray(rest2_inputs["TO3"], dtype=float)
    wv = np.asarray(rest2_inputs["TQV"], dtype=float)
    # 300 < p < 1100 hPa; 0 < uo < 0.6; 0 < un < 0.03; 0 < w < 10 cm; 0 < alpha < 2.5; 0 < beta < 1.1; 0 < albedo < 1
    ps = np.clip(ps, 300.0, 1100.0)
    ozone = np.clip(ozone, 0.0, 0.6)
    wv = np.clip(wv, 0.0, 10.0)
    alpha = np.clip(alpha, 0.0, 2.5)
    beta = np.clip(beta, 0.0, 1.1)
    albedo_val = np.clip(albedo_val, 0.0, 1.0)
    no2 = np.clip(no2, 0.0, 0.03)

    zenith = np.asarray(zenith, dtype=float)
    daytime = (zenith < 90.0) & np.isfinite(zenith)

    if not np.any(daytime):
        zeros = np.zeros(len(idx), dtype=float)
        return zeros, zeros, zeros

    # Clip and replace night/NaN to avoid domain errors (will be masked later)
    zenith = np.where(daytime, np.clip(zenith, 0.0, 89.999), 89.999)
    zenith_rad = np.radians(zenith)
    mu0 = np.cos(zenith_rad)

    # extraterrestrial BNI
    bni_extra = geometry.get_bni_extra(idx).to_numpy(dtype=float)

    # Air mass formulas per REST2 reference (complex dtype for edge cases).
    complex_temp = np.array(zenith, dtype=np.complex128)
    # air mass for aerosols extinction
    ama = np.abs(np.power(mu0 + 0.16851 * np.power(complex_temp, 0.18198) / np.power(95.318 - complex_temp, 1.9542), -1))
    # air mass for water vapor absorption
    amw = np.abs(np.power(mu0 + 0.10648 * np.power(complex_temp, 0.11423) / np.power(93.781 - complex_temp, 1.9203), -1))
    # air mass for ozone absorption
    amo = np.abs(np.power(mu0 + 1.0651 * np.power(complex_temp, 0.6379) / np.power(101.8 - complex_temp, 2.2694), -1))
    # air mass for Rayleigh scattering and uniformly mixed gases absorption
    amR = np.abs(np.power(mu0 + 0.48353 * np.power(complex_temp, 0.095846) / np.power(96.741 - complex_temp, 1.754), -1))
    amRe = np.abs((ps / 1013.25) * np.power(mu0 + 0.48353 * np.power(complex_temp, 0.095846) / np.power(96.741 - complex_temp, 1.754), -1))

    # Band 1
    # transmittance for Rayleigh scattering
    TR1 = (1 + 1.8169 * amRe - 0.033454 * amRe ** 2) / (1 + 2.063 * amRe + 0.31978 * amRe ** 2)
    # transmittance for uniformly mixed gases absorption
    Tg1 = (1 + 0.95885 * amRe + 0.012871 * amRe ** 2) / (1 + 0.96321 * amRe + 0.015455 * amRe ** 2)
    # transmittance for Ozone absorption
    uo = ozone
    f1 = uo * (10.979 - 8.5421 * uo) / (1 + 2.0115 * uo + 40.189 * uo ** 2)
    f2 = uo * (-0.027589 - 0.005138 * uo) / (1 - 2.4857 * uo + 13.942 * uo ** 2)
    f3 = uo * (10.995 - 5.5001 * uo) / (1 + 1.6784 * uo + 42.406 * uo ** 2)
    To1 = (1 + f1 * amo + f2 * amo ** 2) / (1 + f3 * amo)
    # transmittance for Nitrogen dioxide absorption
    un = np.full_like(zenith, float(no2))
    g1 = (0.17499 + 41.654 * un - 2146.4 * np.power(un, 2)) / (1 + 22295. * np.power(un, 2))
    g2 = un * (-1.2134 + 59.324 * un) / (1 + 8847.8 * np.power(un, 2))
    g3 = (0.17499 + 61.658 * un + 9196.4 * np.power(un, 2)) / (1 + 74109. * np.power(un, 2))
    Tn1_middle = (1 + g1 * amw + g2 * np.power(amw, 2)) / (1 + g3 * amw)
    Tn1_middle = np.minimum(Tn1_middle, 1.0)
    Tn1 = Tn1_middle
    Tn1166_middle = (1 + g1 * 1.66 + g2 * np.power(1.66, 2)) / (1 + g3 * 1.66)
    Tn1166_middle = np.minimum(Tn1166_middle, 1.0)
    Tn1166 = Tn1166_middle
    # transmittance for Water Vapor absorption
    h1 = wv * (0.065445 + 0.00029901 * wv) / (1 + 1.2728 * wv)
    h2 = wv * (0.065687 + 0.0013218 * wv) / (1 + 1.2008 * wv)
    Tw1 = (1 + h1 * amw) / (1 + h2 * amw)
    # at air mass=1.66
    Tw1166 = (1 + h1 * 1.66) / (1 + h2 * 1.66)

    # coefficients of angstrom_alpha
    AB1 = beta
    alph1 = alpha
    d0 = 0.57664 - 0.024743 * alph1
    d1 = (0.093942 - 0.2269 * alph1 + 0.12848 * alph1 ** 2) / (1 + 0.6418 * alph1)
    d2 = (-0.093819 + 0.36668 * alph1 - 0.12775 * alph1 ** 2) / (1 - 0.11651 * alph1)
    d3 = alph1 * (0.15232 - 0.087214 * alph1 + 0.012664 * alph1 ** 2) / (
        1 - 0.90454 * alph1 + 0.26167 * alph1 ** 2
    )
    # below Eq.7a
    ua1 = np.log(1 + ama * AB1)
    lam1 = (d0 + d1 * ua1 + d2 * ua1 ** 2) / (1 + d3 * ua1 ** 2)

    # Aerosol transmittance Eq.6,7
    ta1 = np.abs(AB1 * np.power(lam1, -1 * alph1))
    TA1 = np.exp(-ama * ta1)
    # Aerosol scattering transmittance
    # w1=0.92 recommended by author
    TAS1 = np.exp(-ama * 0.92 * ta1)

    # forward scattering fractions for Rayleigh extinction Eq.10,11
    BR1 = 0.5 * (0.89013 - 0.0049558 * amR + 0.000045721 * amR ** 2)
    # the aerosol forward scatterance factor
    Ba = 1 - np.exp(-0.6931 - 1.8326 * mu0)

    # Aerosol scattering correction factor Appendix
    g0 = (3.715 + 0.368 * ama + 0.036294 * np.power(ama, 2)) / (1 + 0.0009391 * np.power(ama, 2))
    g1 = (-0.164 - 0.72567 * ama + 0.20701 * np.power(ama, 2)) / (1 + 0.0019012 * np.power(ama, 2))
    g2 = (-0.052288 + 0.31902 * ama + 0.17871 * np.power(ama, 2)) / (1 + 0.0069592 * np.power(ama, 2))
    F1 = (g0 + g1 * ta1) / (1 + g2 * ta1)

    # sky albedo Appendix
    rs1 = (0.13363 + 0.00077358 * alph1 + AB1 * (0.37567 + 0.22946 * alph1) / (1 - 0.10832 * alph1)) / (
        1 + AB1 * (0.84057 + 0.68683 * alph1) / (1 - 0.08158 * alph1)
    )
    # ground albedo
    rg = albedo_val

    # Band 2
    # transmittance for Rayleigh scattering
    TR2 = (1 - 0.010394 * amRe) / (1 - 0.00011042 * amRe ** 2)
    # transmittance for uniformly mixed gases absorption
    Tg2 = (1 + 0.27284 * amRe - 0.00063699 * amRe ** 2) / (1 + 0.30306 * amRe)
    # transmittance for Ozone absorption
    # Ozone (none)
    To2 = 1.0
    # transmittance for Nitrogen dioxide absorption
    # Nitrogen (none)
    Tn2 = 1.0
    # at air mass=1.66
    Tn2166 = 1.0
    # transmittance for water vapor absorption
    c1 = wv * (19.566 - 1.6506 * wv + 1.0672 * wv ** 2) / (1 + 5.4248 * wv + 1.6005 * wv ** 2)
    c2 = wv * (0.50158 - 0.14732 * wv + 0.047584 * wv ** 2) / (1 + 1.1811 * wv + 1.0699 * wv ** 2)
    c3 = wv * (21.286 - 0.39232 * wv + 1.2692 * wv ** 2) / (1 + 4.8318 * wv + 1.412 * wv ** 2)
    c4 = wv * (0.70992 - 0.23155 * wv + 0.096514 * wv ** 2) / (1 + 0.44907 * wv + 0.75425 * wv ** 2)
    Tw2 = (1 + c1 * amw + c2 * amw ** 2) / (1 + c3 * amw + c4 * amw ** 2)
    # at air mass=1.66
    Tw2166 = (1 + c1 * 1.66 + c2 * 1.66 ** 2) / (1 + c3 * 1.66 + c4 * 1.66 ** 2)

    # coefficients of angstrom_alpha
    AB2 = beta
    alph2 = alpha
    e0 = (1.183 - 0.022989 * alph2 + 0.020829 * alph2 ** 2) / (1 + 0.11133 * alph2)
    e1 = (-0.50003 - 0.18329 * alph2 + 0.23835 * alph2 ** 2) / (1 + 1.6756 * alph2)
    e2 = (-0.50001 + 1.1414 * alph2 + 0.0083589 * alph2 ** 2) / (1 + 11.168 * alph2)
    e3 = (-0.70003 - 0.73587 * alph2 + 0.51509 * alph2 ** 2) / (1 + 4.7665 * alph2)
    # below Eq.7a
    ua2 = np.log(1 + ama * AB2)
    lam2 = (e0 + e1 * ua2 + e2 * ua2 ** 2) / (1 + e3 * ua2)

    # Aerosol transmittance below Eq.7a
    lam2_temp = np.array(lam2, dtype=np.complex128)
    ta2 = np.abs(AB2 * np.power(lam2_temp, -1 * alph2))
    TA2 = np.exp(-1 * ama * ta2)
    # Aerosol scattering transmittance
    # w2=0.84 recommended by author
    TAS2 = np.exp(-1 * ama * 0.84 * ta2)

    # forward scattering fractions for Rayleigh extinction
    # multi scatter negligible in Band 2
    BR2 = 0.5
    # the aerosol forward scatterance factor
    Ba = 1 - np.exp(-0.6931 - 1.8326 * mu0)

    # Aerosol scattering correction
    h0 = (3.4352 + 0.65267 * ama + 0.00034328 * np.power(ama, 2)) / (1 + 0.034388 * np.power(ama, 1.5))
    h1 = (1.231 - 1.63853 * ama + 0.20667 * np.power(ama, 2)) / (1 + 0.1451 * np.power(ama, 1.5))
    h2 = (0.8889 - 0.55063 * ama + 0.50152 * np.power(ama, 2)) / (1 + 0.14865 * np.power(ama, 1.5))
    F2 = (h0 + h1 * ta2) / (1 + h2 * ta2)

    # sky albedo Appendix
    rs2 = (0.010191 + 0.00085547 * alph2 + AB2 * (0.14618 + 0.062758 * alph2) / (1 - 0.19402 * alph2)) / (
        1 + AB2 * (0.58101 + 0.17426 * alph2) / (1 - 0.17586 * alph2)
    )
    # ground albedo
    rg = albedo_val

    # irradiance BAND1
    E0n1 = bni_extra * 0.46512
    # direct beam irradiance
    Ebn1 = E0n1 * TR1 * Tg1 * To1 * Tn1 * Tw1 * TA1
    # the incident diffuse irradiance on a perfectly absorbing ground
    Edp1 = E0n1 * mu0 * To1 * Tg1 * Tn1166 * Tw1166 * (
        BR1 * (1 - TR1) * np.power(TA1, 0.25) + Ba * F1 * TR1 * (1 - np.power(TAS1, 0.25)))
    # multiple reflections between the ground and the atmosphere
    Edd1 = rg * rs1 * (Ebn1 * mu0 + Edp1) / (1 - rg * rs1)

    # irradiance BAND2
    E0n2 = bni_extra * 0.51951
    # direct beam irradiance
    Ebn2 = E0n2 * TR2 * Tg2 * To2 * Tn2 * Tw2 * TA2
    # the incident diffuse irradiance on a perfectly absorbing ground
    Edp2 = E0n2 * mu0 * To2 * Tg2 * Tn2166 * Tw2166 * (
        BR2 * (1 - TR2) * np.power(TA2, 0.25) + Ba * F2 * TR2 * (1 - np.power(TAS2, 0.25)))
    # multiple reflections between the ground and the atmosphere
    Edd2 = rg * rs2 * (Ebn2 * mu0 + Edp2) / (1 - rg * rs2)

    # TOTALS BAND1+BAND2
    # direct normal irradiance
    Ebnrest2 = Ebn1 + Ebn2
    # diffuse horizontal irradiance
    Edhrest2 = Edp1 + Edd1 + Edp2 + Edd2
    # global horizontal irradiance
    Eghrest2 = Ebnrest2 * mu0 + Edhrest2

    # Convert to Python convention output names
    bni_clear = Ebnrest2
    dhi_clear = Edhrest2
    ghi_clear = Eghrest2

    # Nighttime filter and non-negative QC (matching provided Python 'lower=0' logic)
    bni_clear = np.where(daytime, np.where(bni_clear < 0.0, np.nan, bni_clear), 0.0)
    dhi_clear = np.where(daytime, np.where(dhi_clear < 0.0, np.nan, dhi_clear), 0.0)
    ghi_clear = np.where(daytime, np.where(ghi_clear < 0.0, np.nan, ghi_clear), 0.0)

    # Return in Python convention order: ghi, bni, dhi
    return ghi_clear, bni_clear, dhi_clear


def threlkeld_jordan_model(zenith, day_of_year):
    """
    Threlkeld-Jordan clear-sky GHI model [1]_.
    The published Engerer2 reference uses this for the ktc predictor.

    Parameters
    ----------
    zenith : array-like
        Solar zenith angle. [degrees]
    day_of_year : array-like
        Day of year. [1–366]

    Returns
    -------
    ghi_clear : np.ndarray
        Clear-sky GHI ($G_{hc}$). [W/m^2]

    References
    ----------
    .. [1] Threlkeld, J. L., & Jordan, R. C. (1958). Direct solar radiation 
       availability on clear days. ASHRAE Trans, 64(1), 45-105.
    """
    mu0 = np.maximum(np.cos(np.radians(zenith)), 0)
    doy = np.asarray(day_of_year, dtype=float)
    
    # Avoid division by zero when sun is below horizon
    # Use small floor for stability
    mu0_safe = np.fmax(mu0, 1e-10)

    a_tj = 1160 + 75 * np.sin(np.radians(360 * (doy - 275) / 365))
    k_tj = 0.174 + 0.035 * np.sin(np.radians(360 * (doy - 100) / 365))
    c_tj = 0.095 + 0.04 * np.sin(np.radians(360 * (doy - 100) / 365))

    dni_clear = a_tj * np.exp(-k_tj / mu0_safe)
    ghi_clear = dni_clear * mu0 + c_tj * dni_clear
    
    # Mask night
    ghi_clear = np.where(mu0 > 0, ghi_clear, 0.0)
    return ghi_clear

def calculate_vapor_pressure(temp, rh):
    """
    Calculates actual vapor pressure ($e_a$) in hPa using the Magnus-Tetens formula.

    Parameters
    ----------
    temp : numeric
        Air temperature ($T$). [°C]
    rh : numeric
        Relative humidity ($RH$). [%]

    Returns
    -------
    ea : numeric
        Actual vapor pressure ($e_a$). [hPa]

    References
    ----------
    .. [1] Murray, F. W. (1966). On the computation of saturation vapor 
       pressure (Technical Report P3423). Santa Monica, CA: RAND Corp.
    """
    # 1. Calculate saturation vapor pressure (es)
    # 6.112 is the saturation pressure at 0°C in hPa
    es = 6.112 * np.exp((17.67 * temp) / (temp + 243.5))
    
    # 2. Calculate actual vapor pressure (ea)
    ea = es * (rh / 100.0)
    return ea

def brutsaert_model(temp_c, rh):
    """
    Calculates clear-sky downward longwave radiation ($L_{dc}$) using Brutsaert (1975) [1]_.

    Parameters
    ----------
    temp_c : numeric
        Air temperature. [°C]
    rh : numeric
        Relative humidity. [%]

    Returns
    -------
    lwd_clear : numeric
        Clear-sky downward longwave radiation ($L_{dc}$). [W/m^2]

    References
    ----------
    .. [1] Brutsaert, W. (1975). On a derivable formula for long-wave 
       radiation from clear skies. Water Resources Research, 11(5), 742-744.
    """
    # Constants
    sigma = 5.670373e-8  # Stefan-Boltzmann constant (W/m^2/K^4)
    temp_k = temp_c + 273.15  # Convert to Kelvin

    # Get vapor pressure (ea) in hPa
    ea = calculate_vapor_pressure(temp_c, rh)
    
    # Brutsaert (2005) updated emissivity formula
    # epsilon = 1.323 * (ea / Ta)^(1/7) for ea in hPa (millibars)
    emissivity = 1.323 * (ea / temp_k)**(1/7)
    
    # Calculate final downward radiation (L_down)
    lwd_clear = emissivity * sigma * (temp_k**4)
    
    return lwd_clear


def add_clearsky_columns(df, station_code=None, lat=None, lon=None, elev=None,
                        model="ineichen", mcclear_email=None):
    """
    Adds clear-sky radiation columns to a DataFrame based on its DatetimeIndex.

    Location can be given by BSRN station code or by explicit lat/lon/elev
    (e.g. for non-BSRN stations), consistent with the QC wrapper metadata pattern.

    Parameters
    ----------
    df : pd.DataFrame
        Input data with pd.DatetimeIndex.
    station_code : str, optional
        BSRN station abbreviation. [e.g. 'QIQ'] Used if lat/lon/elev not provided.
    lat : float, optional
        Latitude. [degrees] Required for non-BSRN stations if station_code omitted.
    lon : float, optional
        Longitude. [degrees] Required for non-BSRN stations if station_code omitted.
    elev : float, optional
        Elevation. [m] Required for non-BSRN stations if station_code omitted.
    model : str, default 'ineichen'
        Clear-sky model to use. ['ineichen', 'mcclear', 'rest2', or 'tj']
    mcclear_email : str, optional
        SoDa account email used when downloading McClear automatically
        for the 'mcclear' model.

    Returns
    -------
    df : pd.DataFrame
        DataFrame with added _clear columns.

    Raises
    ------
    ValueError
        If ``df.index`` is not a :class:`~pandas.DatetimeIndex`.
    ValueError
        If solar geometry columns are missing and the DataFrame frequency is >5 min,
        causing the automatic `add_solpos_columns` fallback to fail.
    ValueError
        If neither a valid station_code nor complete (lat, lon, elev) is provided.
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame index must be a pandas DatetimeIndex.")

    # Resolve metadata: explicit lat/lon/elev or BSRN lookup (same pattern as QC wrapper)
    if lat is not None and lon is not None and elev is not None:
        pass  # use provided coordinates
    elif station_code is not None and station_code in BSRN_STATIONS:
        meta = BSRN_STATIONS[station_code]
        lat, lon, elev = meta["lat"], meta["lon"], meta["elev"]
    elif station_code is not None:
        raise ValueError(
            f"Station '{station_code}' not found in BSRN registry. "
            "For non-BSRN stations, provide 'lat', 'lon', and 'elev' explicitly."
        )
    else:
        raise ValueError(
            "Insufficient metadata. Provide a valid BSRN 'station_code' or "
            "explicit 'lat', 'lon', and 'elev'."
        )
    
    # Ensure solar geometry columns exist
    required_cols = {"zenith", "apparent_zenith", "bni_extra"}
    if not required_cols.issubset(df.columns):
        if len(df.index) > 1:
            median_dt = pd.Series(df.index).diff().median()
            if pd.notna(median_dt) and median_dt > pd.Timedelta(minutes=5):
                raise ValueError(
                    f"Geometrical error: Generating clear-sky models on low-frequency data (timestep ≈ {median_dt}) "
                    "introduces severe inaccuracies. Always calculate clear-sky at high resolution (e.g., 1-minute)."
                )
        solpos = geometry.get_solar_position(df.index, lat=lat, lon=lon, elev=elev)
        zenith = solpos["zenith"].round(3)
        apparent_zenith = solpos["apparent_zenith"].round(3)
        bni_extra = geometry.get_bni_extra(df.index).round(3)
    else:
        zenith = df["zenith"]
        apparent_zenith = df["apparent_zenith"]
        bni_extra = df["bni_extra"]
    
    if model.lower() == "ineichen":
        # Handle monthly Linke turbidity values
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        default_lt = {m: 3.0 for m in month_names}
        lt_mapping = LINKE_TURBIDITY.get(station_code, default_lt)
        
        # Map months to lt
        months = df.index.month - 1
        lt_series = np.array([lt_mapping[month_names[m]] for m in months])
        
        # Airmass calculations
        am_rel = get_relative_airmass(zenith)
        # Use pvlib-equivalent elevation-to-pressure conversion in Pa
        pressure = geometry.get_pressure_from_elevation(elev)
        am_abs = get_absolute_airmass(am_rel, pressure)
        
        # Calculate clear-sky components
        ghi_clear, bni_clear, dhi_clear = ineichen_model(apparent_zenith, am_abs, lt_series, elev, bni_extra)
    
    elif model.lower() == "mcclear":
        if mcclear_email is None:
            raise ValueError(
                "mcclear_email is required when using model='mcclear'."
            )

        mcclear_data = fetch_mcclear(
            df.index,
            latitude=lat,
            longitude=lon,
            elev=elev,
            email=mcclear_email,
        )

        aligned = mcclear_data
        ghi_clear = aligned["ghi_clear"].to_numpy(dtype=float)
        bni_clear = aligned["bni_clear"].to_numpy(dtype=float)
        dhi_clear = aligned["dhi_clear"].to_numpy(dtype=float)

    elif model.lower() == "rest2":
        if station_code is None:
            raise ValueError(
                "station_code is required when model='rest2'."
            )
        rest2_data = fetch_rest2(df.index, station_code)
        ghi_clear, bni_clear, dhi_clear = rest2_model(df.index, zenith, rest2_data)
    
    elif model.lower() in ("threlkeld_jordan", "tj"):
        # Threlkeld-Jordan (GHI only; for engerer2)
        ghi_clear = threlkeld_jordan_model(zenith, df.index.dayofyear.values)
        bni_clear = np.full_like(ghi_clear, np.nan)
        dhi_clear = np.full_like(ghi_clear, np.nan)
    else:
        raise ValueError(f"Unknown model: {model}")

    df["ghi_clear"] = ghi_clear
    df["bni_clear"] = bni_clear
    df["dhi_clear"] = dhi_clear
    
    # Calculate clear-sky LWD if temp and rh are available
    if "temp" in df.columns and "rh" in df.columns:
        df["lwd_clear"] = brutsaert_model(df["temp"], df["rh"])
    
    return df
