"""
BSRN File Readers.
Handles .001, .002, ... and other archive formats.
"""

import pandas as pd
from pathlib import Path

def read_bsrn_station_to_archive(file_path: str):
    """
    Reader for station-to-archive format.
    These are usually space-separated or fixed-width text files.
    Each station file might have a header and multiple records.
    """
    # Sample logic for reading a BSRN text file
    # df = pd.read_csv(file_path, sep='\s+', header=None)
    pass

def read_bsrn_multiple_files(directory: str, extension: str = "*.001"):
    """
    Read multiple files in a directory and concatenate them.
    """
    path = Path(directory)
    files = list(path.glob(extension))
    # dataframes = [read_bsrn_station_to_archive(f) for f in files]
    # return pd.concat(dataframes)
    pass
