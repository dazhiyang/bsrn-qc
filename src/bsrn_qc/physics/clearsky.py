"""
Clear-Sky Radiation Models.
Provides theoretical reference for QC checks.
"""

import pvlib

def get_clearsky_ineichen(times, lat, lon, elev=0, linke_turbidity=3):
    """
    Calculates clear-sky irradiance using the Ineichen-Perez model.
    """
    # Simple wrapper for pvlib
    location = pvlib.location.Location(lat, lon, altitude=elev)
    clearsky = location.get_clearsky(times, model='ineichen', linke_turbidity=linke_turbidity)
    return clearsky
