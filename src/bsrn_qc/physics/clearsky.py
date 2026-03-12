"""
Clear-Sky Radiation Models.
Provides theoretical reference for QC checks.
晴空辐射模型。
为 QC 检查提供理论参考。
"""

import pvlib

def get_clearsky_ineichen(times, lat, lon, elev=0, linke_turbidity=3):
    """
    Calculates clear-sky irradiance using the Ineichen-Perez model.
    使用 Ineichen-Perez 模型计算晴空辐照度。

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
    linke_turbidity : float, default 3
        Linke turbidity factor.
        Linke 浑浊因子。

    Returns
    -------
    clearsky : pd.DataFrame
        DataFrame with columns 'ghi', 'dni', 'dhi'.
        包含 'ghi'、'dni'、'dhi' 的 DataFrame。
    """
    location = pvlib.location.Location(lat, lon, altitude=elev)
    clearsky = location.get_clearsky(times, model='ineichen', linke_turbidity=linke_turbidity)
    return clearsky
