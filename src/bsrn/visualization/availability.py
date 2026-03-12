"""
visualization of bsrn file availability.
BSRN文件可用性的可视化。
"""

import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
from datetime import datetime
from bsrn.io.retrieval import get_bsrn_file_inventory


def plot_bsrn_availability(stations, username, password, start_year=1992, end_year=None):
    """
    Unified function to plot bsrn file availability from ftp.
    统一功能，用于绘制FTP中的BSRN文件可用性。

    Parameters
    ----------
    stations : str or list
        One or more station abbreviations (e.g., 'PAY' or ['PAY', 'NYA']).
        一个或多个站点缩写（例如 'PAY' 或 ['PAY', 'NYA']）。
    username : str
        BSRN FTP username.
        BSRN FTP 用户名。
    password : str
        BSRN FTP password.
        BSRN FTP 密码。
    start_year : int, default 1992
        year to start the visualization.
        可视化开始的年份。
    end_year : int, optional
        year to end the visualization. If not specified, the current year is used.
        可视化结束的年份。如果未指定，则使用当前年份。

    Returns
    -------
    fig : matplotlib.figure.Figure
        The generated availability heatmap figure.
        生成的可用性热图对象。
    """
    if isinstance(stations, str):
        stations = [stations]
    
    stations = [s.upper() for s in stations]
    stations.sort()  # Sort stations alphabetically / 按字母顺序对站点进行排序
    
    if end_year is None:
        end_year = datetime.now().year
        
    years = list(range(start_year, end_year + 1))
    
    # Fetch data from FTP / 从 FTP 获取数据
    print(f"Searching BSRN FTP for stations: {', '.join(stations)}...")
    inventory = get_bsrn_file_inventory(stations, username, password)
    
    # Pattern: STNMMYY.dat.gz or STNMMYY.001 / 匹配模式：STNMMYY.dat.gz 或 STNMMYY.001
    pattern = re.compile(r"([A-Z]{3})(\d{2})(\d{2})\.(?:dat\.gz|\d{3}).*", re.IGNORECASE)

    # Calculate dimensions to ensure square cells / 计算尺寸以确保方形单元格
    # Width = 160mm = 6.299 inches / 宽度 = 160mm = 6.299 英寸
    width_inch = 160 / 25.4
    num_cols = len(years)
    num_rows = 12 if len(stations) == 1 else len(stations)
    
    # Aspect ratio adjustment / 长宽比调整
    height_inch = width_inch * (num_rows / num_cols)
    total_height_inch = height_inch + 1.2  # Add extra height for labels and colorbar / 为标签和颜色条增加额外高度
    
    # Font settings / 字体设置
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
        
        # Plot single station / 绘制单个站点
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
        
        # Plot multiple stations / 绘制多个站点
        ax = sns.heatmap(df, cmap="viridis", cbar=True, linewidths=0.5, linecolor='white', square=True,
                         cbar_kws={"orientation": "horizontal", "pad": 0.35, "shrink": 0.5, "label": "Months Available"})
        plt.ylabel("Stations")

    plt.title(f"BSRN File Availability ({start_year}-{end_year})", pad=10)
    plt.xlabel("Year", labelpad=5)
    
    # Adjust X-ticks visibility / 调整 X 轴刻度可见性
    if len(years) > 20:
        for i, label in enumerate(ax.get_xticklabels()):
            if i % 2 != 0: label.set_visible(False)
    plt.xticks(rotation=45)

    plt.tight_layout()
    return fig
