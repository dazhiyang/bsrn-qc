"""
BSRN Level 1 (Physically Possible) checks.
Reference: BSRN Operations Manual (2018).
"""

import pandas as pd
import numpy as np

def check_ghi_physical(ghi: pd.Series, sza: pd.Series) -> pd.Series:
    """
    Check if GHI values are within physically possible limits.
    Upper bound: 1.5 * I0 * cos(Z)^1.2 + 100
    Lower bound: -4
    """
    # Assuming GHI and SZA (Solar Zenith Angle) are provided
    # Standard I0 ~ 1361 W/m2
    # This is a placeholder for the actual formula
    pass

def check_dhi_physical(dhi: pd.Series) -> pd.Series:
    """Check DHI: [-4, 1100] W/m2."""
    pass

def check_dni_physical(dni: pd.Series) -> pd.Series:
    """Check DNI: [-4, 1100] W/m2."""
    pass
