"""
Calendar-style clear-sky vs measured irradiance plots.
日历样式的晴空与实测辐照度对比图。
"""

import numpy as np
import pandas as pd
from plotnine import (
    aes,
    element_blank,
    element_line,
    element_text,
    facet_grid,
    geom_line,
    geom_ribbon,
    geom_vline,
    ggplot,
    labs,
    scale_x_continuous,
    scale_y_continuous,
    theme,
    theme_minimal,
)

from bsrn.constants import WONG_PALETTE
from bsrn.io.readers import read_station_to_archive
from bsrn.modeling.clear_sky import add_clearsky_columns
from bsrn.physics.geometry import get_solar_position


def plot_clearsky_calendar(
    file_path,
    output_file,
    station_code,
    component="ghi",
    clearsky_model="ineichen",
):
    """
    Plot a one-page calendar-style view of measured vs clear-sky irradiance.
    生成单页日历样式图，展示实测与晴空辐照度。

    Each facet is a calendar cell (rows = weeks, columns = Mon–Sun). Within
    each cell, the x-axis is a simple sample index (0, 1, 2, …) so that the
    daytime transients are continuous and night-time tails are removed.

    每个子图对应一个日历单元（行=周，列=周一至周日）。子图内 x 轴为简单采样索引
    （0, 1, 2, …），保证日间过程连续，同时去除夜间的时间序列尾巴。
    """
    component = component.lower()
    if component not in {"ghi", "bni", "dhi"}:
        raise ValueError("component must be one of {'ghi', 'bni', 'dhi'}.")

    df = read_station_to_archive(file_path)
    if df is None:
        raise ValueError(f"Failed to read BSRN file: {file_path}")

    df = df.sort_index()
    unique_months = df.index.to_period("M").unique()
    if len(unique_months) != 1:
        raise ValueError(
            f"Input must contain exactly one month. Found: {list(unique_months)}"
        )

    # Add clear-sky columns for the chosen model.
    df_cs = add_clearsky_columns(df.copy(), station_code=station_code, model=clearsky_model)

    # Solar geometry for day/night mask.
    from bsrn.constants import BSRN_STATIONS

    meta = BSRN_STATIONS.get(station_code, {})
    lat = meta.get("lat", 0.0)
    lon = meta.get("lon", 0.0)
    elev = meta.get("elev", 0.0)

    solpos = get_solar_position(df_cs.index, lat, lon, elev)
    zenith = solpos["zenith"].to_numpy(dtype=float)

    # Keep only daytime samples (sun above horizon).
    # 仅保留日间样本（太阳在地平线上方）。
    daytime_mask = zenith < 90.0
    df_cs = df_cs.loc[daytime_mask]
    if df_cs.empty:
        raise ValueError("No daytime data found for this file.")

    # Extract measured and clear-sky components.
    meas_col = component
    cs_col = f"{component}_clear"
    if meas_col not in df_cs.columns or cs_col not in df_cs.columns:
        raise ValueError(f"Required columns '{meas_col}' and '{cs_col}' not found.")

    times = df_cs.index
    vals_meas = df_cs[meas_col].to_numpy(dtype=float)
    vals_cs = df_cs[cs_col].to_numpy(dtype=float)

    # Optionally remove very low clear-sky values to trim twilight tails.
    # 可选：去掉极低的晴空值以裁剪“黄昏尾巴”。
    cs_min = 5.0  # W/m^2
    keep = vals_cs > cs_min
    times = times[keep]
    vals_meas = vals_meas[keep]
    vals_cs = vals_cs[keep]
    if len(times) == 0:
        raise ValueError("No usable daytime samples after clear-sky filtering.")

    # Calendar coordinates.
    # 日历坐标。
    dates = times.normalize()
    day = dates.day
    weekday = dates.weekday  # 0=Mon, ..., 6=Sun

    first_date = dates.min()
    first_monday = first_date - pd.Timedelta(days=int(first_date.weekday()))
    week = ((dates - first_monday).days // 7).astype(int)

    # Sample index within each day (0, 1, 2, …).
    # 每日内部的采样索引（0, 1, 2, …）。
    day_series = pd.Series(dates, index=times)
    t_index = day_series.groupby(day_series).cumcount().to_numpy()

    base = pd.DataFrame(
        {
            "t_index": t_index,
            "date": dates,
            "day": day,
            "weekday": weekday,
            "week": week,
            "measured": vals_meas,
            "clearsky": vals_cs,
        },
        index=times,
    )

    # Long format: two kinds (measured, clearsky).
    # 长格式：两条曲线（实测、晴空）。
    long_df = base.melt(
        id_vars=["t_index", "date", "day", "weekday", "week"],
        value_vars=["measured", "clearsky"],
        var_name="kind",
        value_name="value",
    )

    # Limit to 5 weeks (rows) for visual compactness.
    long_df["week"] = long_df["week"].clip(upper=4)

    # First/last sample index per day for visual day bounds.
    # 每日首末采样索引用于绘制“日界线”。
    bounds = (
        base.reset_index()
        .groupby("date", as_index=False)
        .agg(
            t_start=("t_index", "min"),
            t_end=("t_index", "max"),
            week=("week", "first"),
            weekday=("weekday", "first"),
        )
    )

    # Weekday labels and ordering (Mon–Sun).
    weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    long_df["weekday"] = pd.Categorical(
        [weekday_labels[i] for i in long_df["weekday"].to_numpy()],
        categories=weekday_labels,
        ordered=True,
    )
    bounds["weekday"] = pd.Categorical(
        [weekday_labels[i] for i in bounds["weekday"].to_numpy()],
        categories=weekday_labels,
        ordered=True,
    )

    # Separate measured and clear-sky series.
    meas_long = long_df[long_df["kind"] == "measured"].copy()
    cs_long = long_df[long_df["kind"] == "clearsky"].copy()

    # Colors follow timeseries convention.
    measured_color = WONG_PALETTE[0]
    clearsky_color = WONG_PALETTE[1]

    comp_label = component.upper()
    month_str = unique_months[0].strftime("%Y %b")
    title = f"{station_code} – {month_str} – {comp_label} (measured vs clear-sky)"

    width_inch = 160 / 25.4
    height_inch = width_inch * (5 / 7)

    # X-axis tick at 0 and half of daily sample length (rounded).
    # x 轴在 0 与日内样本长度一半处打刻度（取整）。
    max_t = int(base["t_index"].max())
    half_t = int(round(max_t / 2)) if max_t > 0 else 0

    p = (
        ggplot()
        + geom_ribbon(
            data=cs_long,
            mapping=aes(x="t_index", ymin=0, ymax="value", group="date"),
            fill=clearsky_color,
            alpha=0.25,
        )
        + geom_line(
            data=cs_long,
            mapping=aes(x="t_index", y="value", group="date"),
            color=clearsky_color,
            size=0.25,
        )
        + geom_line(
            data=meas_long,
            mapping=aes(x="t_index", y="value", group="date"),
            color=measured_color,
            size=0.25,
        )
        # Vertical lines at first/last sample of each day.
        # 每日首末采样位置的垂直参考线。
        + geom_vline(
            data=bounds,
            mapping=aes(xintercept="t_start"),
            color="#999999",
            size=0.2,
            alpha=0.7,
            linetype="dashed",
        )
        + geom_vline(
            data=bounds,
            mapping=aes(xintercept="t_end"),
            color="#999999",
            size=0.2,
            alpha=0.7,
            linetype="dashed",
        )
        + facet_grid("week ~ weekday", scales="fixed")
        + scale_x_continuous(
            breaks=[0, half_t] if half_t > 0 else [0],
            limits=(0, max_t),
            expand=(0, 0),
        )
        + scale_y_continuous(breaks=[0, 500], expand=(0.05, 0.1))
        + labs(
            title=title,
            x="",
            y="Irradiance [W/m²]",
        )
        + theme_minimal()
        + theme(
            text=element_text(family="Times New Roman", size=7),
            axis_title=element_text(size=7),
            axis_text=element_text(size=7),
            axis_text_x=element_blank(),
            plot_title=element_text(size=8, face="bold"),
            # Keep weekday labels (top strips), hide week indices (row strips).
            # 顶部保留星期标签，行方向周索引隐藏。
            strip_text_x=element_text(size=7, face="bold"),
            strip_text_y=element_blank(),
            figure_size=(width_inch, height_inch),
            panel_grid_major=element_line(size=0.15, alpha=0.7),
            panel_spacing=0,
            panel_border=element_blank(),
        )
    )

    if output_file:
        p.save(output_file, dpi=300)

    return p

