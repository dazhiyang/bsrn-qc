"""
Solar Geometry Calculations.
Uses pvlib for high-precision solar position.
"""

import pvlib
import pandas as pd

def get_solar_position(times, lat, lon, elev=0):
    """
    Calculates solar zenith and azimuth.
    
    Args:
        times (pd.DatetimeIndex): Times for calculation.
        lat (float): Latitude.
        lon (float): Longitude.
        elev (float): Elevation in meters.
        
    Returns:
        pd.DataFrame: Contains 'zenith', 'apparent_zenith', 'azimuth'.
    """
    solpos = pvlib.solarposition.get_solarposition(times, lat, lon, elev)
    return solpos
