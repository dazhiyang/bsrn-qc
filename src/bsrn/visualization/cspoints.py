"""
Clear-sky detection (CSD) results: one page per day, four rows per page (one CSD model per row).
"""

import numpy as np
import pandas as pd
from plotnine import (
    ggplot,
    aes,
    geom_line,
    geom_point,
    geom_ribbon,
    facet_grid,
    theme_minimal,
    theme,
    element_text,
    labs,
    scale_x_datetime,
)
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

from bsrn.constants import BSRN_STATIONS, WONG_PALETTE
from bsrn.dataset import BSRNDataset
from bsrn.modeling.clear_sky import add_clearsky_columns
from bsrn.physics.geometry import get_solar_position, get_ghi_extra
from bsrn.utils import reno_csd, ineichen_csd, lefevre_csd, brightsun_csd

# Display order for the four CSD methods (rows top to bottom).
CSD_METHOD_ORDER = ("Reno", "Ineichen", "Lefevre", "BrightSun")


def plot_csd_booklet(file_path, output_file, station_code, df=None, title=None):
    """
    Generate a PDF: one page per day, four rows (CSD methods) × three columns (GHI, BNI, DHI).

    Clear-sky detection is driven by GHI (and each method's required inputs). The same
    ``is_clearsky`` flag is overlaid on the GHI, BNI, and DHI time series in each row.

    Parameters
    ----------
    file_path : str
        Path to the BSRN station-to-archive file (one month, e.g. .dat.gz).
        Ignored if ``df`` is provided.
    output_file : str
        Path to the output PDF file.
    station_code : str
        Station abbreviation (e.g. "QIQ") for clear-sky and site location.
    df : pd.DataFrame, optional
        If provided, use this DataFrame instead of reading from ``file_path``.
        Must have one-month DatetimeIndex and columns ghi, bni, dhi.
    title : str, optional
        Same title on every PDF page. If None (default), no plot title.

    Returns
    -------
    None
        Saves the booklet to the given PDF path.
    """

    # Load data and ensure December only.
    if df is None:
        df = BSRNDataset.from_file(file_path).data()

    df = df.sort_index()
    unique_months = df.index.to_period("M").unique()
    if len(unique_months) != 1:
        raise ValueError(f"File must contain exactly one month. Found: {unique_months}")

    stn = BSRN_STATIONS.get(station_code, {"lat": 0, "lon": 0, "elev": 0})
    lat, lon, elev = stn["lat"], stn["lon"], stn["elev"]

    # Solar position and extraterrestrial GHI
    solpos = get_solar_position(df.index, lat, lon, elev)
    zenith = solpos["zenith"].values
    ghi_extra = np.asarray(get_ghi_extra(df.index, zenith), dtype=float)

    # Clear-sky columns (required for Reno, BrightSun, and reference curves)
    df = add_clearsky_columns(df, station_code)

    ghi = df["ghi"].values
    bni = df["bni"].values
    dhi = df["dhi"].values
    ghi_clear = df["ghi_clear"].values
    bni_clear = df["bni_clear"].values
    dhi_clear = df["dhi_clear"].values
    times = df.index

    # Run all four CSD methods (inputs are GHI and method-specific: ghi_clear, ghi_extra, zenith, dhi, etc.).
    out_reno = reno_csd(ghi, ghi_clear, times=times)
    out_ineichen = ineichen_csd(ghi, ghi_extra, zenith, times=times)
    out_lefevre = lefevre_csd(ghi, dhi, ghi_extra, zenith, times=times)
    out_brightsun = brightsun_csd(zenith, ghi, ghi_clear, dhi, dhi_clear, times)

    # Build merged frame: time, ghi/bni/dhi, clear-sky cols, and one column per method.
    merged = pd.DataFrame(
        index=times,
        data={
            "ghi": ghi,
            "bni": bni,
            "dhi": dhi,
            "ghi_clear": ghi_clear,
            "bni_clear": bni_clear,
            "dhi_clear": dhi_clear,
            "is_reno": out_reno["is_clearsky"],
            "is_ineichen": out_ineichen["is_clearsky"],
            "is_lefevre": out_lefevre["is_clearsky"],
            "is_brightsun": out_brightsun["is_clearsky"],
        },
    )
    merged.index.name = "time"
    merged = merged.reset_index()

    # Long format: one row per (time, method), with ghi, bni, dhi and clear-sky, is_clearsky.
    long_list = []
    for method in CSD_METHOD_ORDER:
        col = f"is_{method.lower()}"
        sub = merged[
            ["time", "ghi", "bni", "dhi", "ghi_clear", "bni_clear", "dhi_clear", col]
        ].copy()
        sub = sub.rename(columns={col: "is_clearsky"})
        sub["method"] = method
        long_list.append(sub)
    long_df = pd.concat(long_list, ignore_index=True)
    long_df["method"] = pd.Categorical(
        long_df["method"], categories=list(CSD_METHOD_ORDER), ordered=True
    )

    # Long format for plotting: GHI / BNI / DHI time series; overlay is_clearsky points on all three.
    m1 = long_df.melt(
        id_vars=["time", "method", "is_clearsky"],
        value_vars=["ghi", "bni", "dhi"],
        var_name="param",
        value_name="measured",
    )
    m2 = long_df.melt(
        id_vars=["time", "method"],
        value_vars=["ghi_clear", "bni_clear", "dhi_clear"],
        var_name="param_clear",
        value_name="clearsky",
    )
    param_map = {"ghi": "GHI", "bni": "BNI", "dhi": "DHI"}
    m1["parameter"] = m1["param"].map(param_map)
    m2["parameter"] = m2["param_clear"].str.replace("_clear", "").map(param_map)
    plot_df = m1[["time", "method", "parameter", "measured", "is_clearsky"]].merge(
        m2[["time", "method", "parameter", "clearsky"]],
        on=["time", "method", "parameter"],
    )
    plot_df["parameter"] = pd.Categorical(
        plot_df["parameter"], categories=["GHI", "BNI", "DHI"], ordered=True
    )
    clear_only = plot_df.loc[plot_df["is_clearsky"] == True].copy()

    # Figure size: 160 mm wide, height for 4 facet rows × 3 columns
    width_inch = 160 / 25.4
    height_inch = width_inch / 3 * 4 / 1.4

    print(f"Generating CSD booklet: {output_file} ...")
    with PdfPages(output_file) as pdf:
        for date, day_df in plot_df.groupby(pd.to_datetime(plot_df["time"]).dt.date):
            day_clear = clear_only.loc[
                pd.to_datetime(clear_only["time"]).dt.date == date
            ]
            # Wong: [1] sky blue (ribbon/clear curve), [0] orange (measured), [2] bluish green (CSD points)
            ribbon_color = WONG_PALETTE[1]
            _lab = {"x": "Time (UTC)", "y": "[W/m²]"}
            if title is not None:
                _lab["title"] = title
            p = (
                ggplot(day_df, aes(x="time"))
                + geom_ribbon(
                    mapping=aes(ymin=0, ymax="clearsky"),
                    fill=ribbon_color,
                    alpha=0.25,
                )
                + geom_line(
                    aes(y="clearsky"), color=ribbon_color, size=0.2, alpha=0.7, linetype="dashed"
                )
                + geom_line(aes(y="measured"), color=WONG_PALETTE[0], size=0.5)
                + geom_point(
                    data=day_clear,
                    mapping=aes(y="measured"),
                    color=WONG_PALETTE[2],
                    size=0.3,
                    alpha=0.7,
                )
                + facet_grid("method ~ parameter", scales="free_y")
                + labs(**_lab)
                + theme_minimal()
                + theme(
                    text=element_text(family="Times New Roman", size=9),
                    axis_title=element_text(size=9),
                    axis_text=element_text(size=9),
                    plot_title=element_text(size=9, margin={"b": 10}),
                    figure_size=(width_inch, height_inch),
                    strip_text=element_text(size=9),
                )
                + scale_x_datetime(date_labels="%H:%M")
            )
            fig = p.draw()
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    print("Done.")
