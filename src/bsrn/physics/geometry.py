"""
solar geometry calculations.
Uses pvlib for high-precision solar position.
太阳几何计算。
使用 pvlib 进行高精度太阳位置计算。
"""

import pvlib
import pandas as pd

def get_solar_position(times, lat, lon, elev=0):
    """
    Calculates solar zenith angle ($Z$) and solar azimuth angle ($\phi$).
    计算太阳天顶角 ($Z$) 和太阳方位角 ($\phi$)。

    Parameters
    ----------
    times : pd.DatetimeIndex
        times for calculation.
        计算对应的时间。
    lat : float
        latitude.
        纬度。
    lon : float
        longitude.
        经度。
    elev : float, default 0
        elevation in meters.
        海拔（米）。

    Returns
    -------
    solpos : pd.DataFrame
        DataFrame with columns such as 'zenith', 'apparent_zenith', 'azimuth'.
        包含 'zenith'、'apparent_zenith'、'azimuth' 等列的 DataFrame。
    """
    solpos = pvlib.solarposition.get_solarposition(times, lat, lon, elev)
    return solpos


def get_bni_extra(times):
    """
    Calculates extraterrestrial beam normal irradiance (BNI_extra, $E_{0n}$).
    计算地外法向辐照度 (BNI_extra, $E_{0n}$)。

    Parameters
    ----------
    times : pd.DatetimeIndex
        times for calculation.
        计算对应的时间。

    Returns
    -------
    bni_extra : pd.Series
        extraterrestrial beam normal irradiance ($E_{0n}$) in W/m^2.
        地外法向辐照度 ($E_{0n}$)，单位 W/m^2。
    """
    return pvlib.irradiance.get_extra_radiation(times)
