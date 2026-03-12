"""
Visualization of BSRN file availability.
"""

import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
from datetime import datetime
from ftplib import FTP
from bsrn_qc.io.retrieval import get_bsrn_file_inventory


def plot_bsrn_availability(stations, username: str, password: str,
                           start_year: int = 1992, end_year: int = None):
    """
    Unified function to plot BSRN file availability from FTP.
    
    Args:
        stations (str or list): One or more station abbreviations ('PAY' or ['PAY', 'NYA']).
        username (str): BSRN FTP username.
        password (str): BSRN FTP password.
        start_year (int): Year to start (default 1992).
        end_year (int): Year to end (default current).
    """
    if isinstance(stations, str):
        stations = [stations]
    
    stations = [s.upper() for s in stations]
    stations.sort() # Sort stations alphabetically
    if end_year is None:
        end_year = datetime.now().year
        
    years = list(range(start_year, end_year + 1))
    
    # Fetch data from FTP
    print(f"Searching BSRN FTP for stations: {', '.join(stations)}...")
    inventory = get_bsrn_file_inventory(stations, username, password)
    
    # Updated pattern: STNMMYY.dat.gz or STNMMYY.001
    pattern = re.compile(r"([A-Z]{3})(\d{2})(\d{2})\.(?:dat\.gz|\d{3}).*", re.IGNORECASE)

    # Calculate dimensions to ensure square cells
    # Width = 160mm = 6.299 inches
    width_inch = 160 / 25.4
    num_cols = len(years)
    num_rows = 12 if len(stations) == 1 else len(stations)
    
    # Aspect ratio adjustment: height = width * (rows/cols)
    height_inch = width_inch * (num_rows / num_cols)
    # Add extra height for labels, title, and colorbar at bottom
    total_height_inch = height_inch + 1.2
    
    # Font settings
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman'],
        'font.size': 7,
        'axes.titlesize': 7,
        'axes.labelsize': 7,
        'xtick.labelsize': 7,
        'ytick.labelsize': 7,
        'legend.fontsize': 7
    })
    
    fig = plt.figure(figsize=(width_inch, total_height_inch))
    
    if len(stations) == 1:
        stn = stations[0]
        months = list(range(1, 13))
        df = pd.DataFrame(0, index=months, columns=years)
        for filename in inventory.get(stn, []):
            basename = os.path.basename(filename)
            match = pattern.match(basename)
            if match:
                stn_match, mm_str, yy_str = match.groups()
                month, yy = int(mm_str), int(yy_str)
                year = (1900 + yy) if yy >= 92 else (2000 + yy)
                if year in df.columns and month in df.index:
                    df.at[month, year] = 1
        
        # Use viridis for single station (0 or 1)
        ax = sns.heatmap(df, cmap="viridis", cbar=True, linewidths=0.5, linecolor='white', 
                         square=True, yticklabels=['J', 'F', 'M', 'A', 'M', 'J', 
                                                  'J', 'A', 'S', 'O', 'N', 'D'],
                         cbar_kws={"orientation": "horizontal", "pad": 0.35, "shrink": 0.5, "label": "Availability"})
        plt.ylabel(f"Station: {stn}")
    else:
        df = pd.DataFrame(0, index=stations, columns=years)
        for stn in stations:
            for filename in inventory.get(stn, []):
                basename = os.path.basename(filename)
                match = pattern.match(basename)
                if match:
                    stn_match, mm_str, yy_str = match.groups()
                    yy = int(yy_str)
                    year = (1900 + yy) if yy >= 92 else (2000 + yy)
                    if year in df.columns:
                        df.at[stn, year] += 1
        
        # Use viridis for multiple stations (0-12 months)
        ax = sns.heatmap(df, cmap="viridis", cbar=True, linewidths=0.5, linecolor='white', square=True,
                         cbar_kws={"orientation": "horizontal", "pad": 0.35, "shrink": 0.5, "label": "Months Available"})
        plt.ylabel("Stations")

    plt.title(f"BSRN File Availability ({start_year}-{end_year})", pad=10)
    plt.xlabel("Year", labelpad=5)
    
    # Adjust X-ticks to be less crowded if range is large
    if len(years) > 20:
        for i, label in enumerate(ax.get_xticklabels()):
            if i % 2 != 0: label.set_visible(False)
    plt.xticks(rotation=45)

    plt.tight_layout()
    return fig
