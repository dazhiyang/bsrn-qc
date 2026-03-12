"""
Solar Geometry Calculations.
Uses pvlib for high-precision solar position.
太阳几何计算。
使用 pvlib 进行高精度太阳位置计算。
"""

import pvlib
import pandas as pd

def get_solar_position(times, lat, lon, elev=0):
    """
    Calculates solar zenith and azimuth.
    计算太阳天顶角和方位角。

    Parameters
    ----------
    times : pd.DatetimeIndex
        Times for calculation.
        计算对应的时间。
    lat : float
        Latitude.
        纬度。
    lon : float
        Longitude.
        经度。
    elev : float, default 0
        Elevation in meters.
        海拔（米）。

    Returns
    -------
    solpos : pd.DataFrame
        DataFrame with columns such as 'zenith', 'apparent_zenith', 'azimuth'.
        包含 'zenith'、'apparent_zenith'、'azimuth' 等列的 DataFrame。
    """
    solpos = pvlib.solarposition.get_solarposition(times, lat, lon, elev)
    return solpos
