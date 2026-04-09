"""
Visualization of irradiance separation: k vs kt scatter (Erbs, BRL, etc.).
"""

import pandas as pd
import numpy as np
import matplotlib as mpl
from plotnine import (
    ggplot, aes, geom_tile,
    theme_minimal, theme,
    element_text, element_blank, labs,
    scale_x_continuous, scale_y_continuous,
    scale_fill_cmap, coord_fixed, facet_wrap
)

from bsrn.physics import geometry
from bsrn.utils.calculations import calc_kt
from bsrn.modeling import erbs_separation, brl_separation, engerer2_separation, yang4_separation

# Supported model names for k vs kt plot (Erbs, BRL, Engerer2, Yang4).
SUPPORTED_SEPARATION_MODELS = ("erbs", "brl", "engerer2", "yang4")

# Display names and facet order for k vs kt plot.
MODEL_DISPLAY_NAMES = {"erbs": "Erbs", "brl": "BRL", "engerer2": "Engerer2", "yang4": "Yang4"}
FACET_ORDER = ("Erbs", "BRL", "Engerer2", "Yang4")


def plot_k_vs_kt(df, models, lat, lon, ghi_col="ghi", dhi_col="dhi", k_mod_cols=None,
                 output_file=None, title=None):
    """
    Faceted scatter plot of k (diffuse fraction) vs kt (clearness index) from a DataFrame.

    One panel per model; measured (gray) and model (colored) in each panel.

    Parameters
    ----------
    df : pd.DataFrame
        Input data with DatetimeIndex and at least ``ghi_col`` and ``dhi_col``.
    models : sequence of str
        Model names to plot, e.g. ``('erbs', 'brl')``. Each in SUPPORTED_SEPARATION_MODELS.
    lat : float
        Latitude. [degrees]
    lon : float
        Longitude. [degrees]
    ghi_col : str, default "ghi"
        Column name for GHI.
    dhi_col : str, default "dhi"
        Column name for DHI.
    k_mod_cols : dict or None, optional
        Map model name to column name for model k. If None, runs each separation model.
        For ``engerer2`` and ``yang4``, k must be pre-computed and provided here (both need clear-sky GHI).
    output_file : str, optional
        Path to save the figure.
    title : str, optional
        Overall plot title.

    Notes
    -----
    To include Engerer2 or Yang4 (both require clear-sky GHI): add clear-sky GHI to ``df``
    (e.g. :func:`bsrn.physics.clearsky.add_clearsky_columns`), run the separation with
    ``ghi_clear=df["ghi_clear"].values``, assign the result's ``"k"`` to a column, then pass
    ``k_mod_cols={"engerer2": "k_engerer2", "yang4": "k_yang4"}``.

    Returns
    -------
    p : plotnine.ggplot
        The ggplot object. If ``output_file`` was set, this is a **new** instance
        (the one used for saving is not safe to draw again after ``plt.close``).
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("df must have a DatetimeIndex.")
    for col, name in [(ghi_col, "ghi"), (dhi_col, "dhi")]:
        if col not in df.columns:
            raise ValueError(f"DataFrame missing column '{col}' ({name}).")

    models = tuple(m.strip().lower() for m in models)
    if not models:
        raise ValueError("models must be a non-empty sequence.")
    for m in models:
        if m not in SUPPORTED_SEPARATION_MODELS:
            raise ValueError(
                f"model must be one of {SUPPORTED_SEPARATION_MODELS}, got {m!r}."
            )

    use = df[[ghi_col, dhi_col]].dropna()
    if len(use) == 0:
        raise ValueError("No valid ghi/dhi rows after dropna.")
    times = use.index
    ghi = np.asarray(use[ghi_col], dtype=float)
    dhi = np.asarray(use[dhi_col], dtype=float)
    k_meas = np.full_like(ghi, np.nan, dtype=float)
    pos = ghi > 0
    if np.any(pos):
        # Only index-wise divide (not np.where / ufunc where=), avoids divide-by-zero warnings.
        k_meas[pos] = dhi[pos] / ghi[pos]
    k_meas = np.clip(k_meas, 0.0, 1.0)

    zenith = np.asarray(
        geometry.get_solar_position(times, lat, lon)["zenith"], dtype=float
    )
    bni_extra = np.asarray(geometry.get_bni_extra(times), dtype=float)
    kt = calc_kt(ghi, zenith, bni_extra, min_mu0=0.065, max_clearness_index=1.0)

    day = zenith < 87
    kt = kt[day]
    k_meas = k_meas[day]
    times_day = times[day]
    ghi_day = ghi[day]

    n = len(kt)
    k_mod_cols = k_mod_cols or {}
    rows = []
    for model in models:
        if model in k_mod_cols and k_mod_cols[model] in df.columns:
            k_mod = np.asarray(df.loc[use.index, k_mod_cols[model]], dtype=float)[day]
        else:
            if model == "erbs":
                result = erbs_separation(times_day, ghi_day, lat, lon)
            elif model == "brl":
                result = brl_separation(times_day, ghi_day, lat, lon)
            elif model == "engerer2":
                raise ValueError(
                    "engerer2 requires pre-computed k. Run engerer2_separation and pass column in k_mod_cols."
                )
            elif model == "yang4":
                raise ValueError(
                    "yang4 requires pre-computed k. Run yang4_separation and pass column in k_mod_cols."
                )
            else:
                raise ValueError(f"Unknown model {model!r}.")
            k_mod = np.asarray(result["k"], dtype=float)
        label = MODEL_DISPLAY_NAMES[model]
        for i in range(n):
            rows.append({"kt": kt[i], "k": k_meas[i], "model": label, "source": "measured"})
            rows.append({"kt": kt[i], "k": k_mod[i], "model": label, "source": "model"})
    plot_df = pd.DataFrame(rows)
    # Fix facet order: Erbs, BRL, Engerer2, Yang4 (only include present models).
    order = [x for x in FACET_ORDER if x in plot_df["model"].values]
    plot_df["model"] = pd.Categorical(plot_df["model"], categories=order, ordered=True)

    # Scattermore-style: rasterize points to a fixed grid for clean, fast plots.
    df_meas = plot_df[plot_df["source"] == "measured"].dropna().copy()
    df_mod = plot_df[plot_df["source"] == "model"].dropna().copy()
    df_mod = df_mod[df_mod["k"] < 1].copy()

    # Density per model on grid for raster fill (like R MASS::kde2d).
    parts = []
    for _, grp in df_mod.groupby("model", observed=True):
        grp = grp.copy()
        grp["density"] = _get_density(grp["kt"].values, grp["k"].values, n=200)
        parts.append(grp)
    df_mod = pd.concat(parts)

    n_pixels = 512  # Scattermore-style resolution (like geom_scattermore pixels).
    facet_order = [x for x in FACET_ORDER if x in plot_df["model"].values]
    raster_meas = _points_to_raster(
        df_meas, "kt", "k", value=None, n=n_pixels,
        x_range=(0, 1), y_range=(0, 1), fill_style="gray", model_col="model",
        facet_models=facet_order
    )
    raster_mod = _points_to_raster(
        df_mod, "kt", "k", value="density", n=n_pixels,
        x_range=(0, 1), y_range=(0, 1), fill_style="viridis", model_col="model"
    )

    # Figure width 160 mm (standard journal column width)
    n_facets = plot_df["model"].nunique()
    width_mm = 160.0
    width_inch = width_mm / 25.4
    panel_width_inch = width_inch / n_facets
    fig_h = panel_width_inch * 0.9 + 0.35  # Extra height for legend bar below.

    # Use STIX math font so $k$ / $k_t$ match Times New Roman text (plotnine uses matplotlib).
    prev_fontset = mpl.rcParams.get("mathtext.fontset")
    try:
        mpl.rcParams["mathtext.fontset"] = "stix"
        cell_w = 1.0 / n_pixels
        cell_h = 1.0 / n_pixels

        def _ggplot():
            g = (
                ggplot()
                + geom_tile(
                    data=raster_meas,
                    mapping=aes(x="x", y="y"),
                    fill="#909090",
                    width=cell_w, height=cell_h
                )
                + geom_tile(
                    data=raster_mod,
                    mapping=aes(x="x", y="y", fill="value"),
                    width=cell_w, height=cell_h
                )
                + facet_wrap("model", ncol=n_facets, scales="free")
                + scale_fill_cmap(cmap_name="viridis", name="density")
                + labs(
                    x=r"$k_t$ (clearness index)",
                    y=r"$k$ (diffuse fraction)"
                )
                + scale_x_continuous(limits=(0, 1), breaks=np.arange(0, 1.1, 0.2))
                + scale_y_continuous(limits=(0, 1), breaks=np.arange(0, 1.1, 0.2))
                + coord_fixed(ratio=1)
                + theme_minimal()
                + theme(
                    text=element_text(family="Times New Roman", size=9),
                    plot_title=element_text(size=9),
                    axis_title=element_text(size=9),
                    axis_text=element_text(size=9),
                    legend_position="bottom",
                    legend_title=element_text(size=9),
                    legend_text=element_text(size=9),
                    legend_key_width=100,
                    legend_key_height=5,
                    legend_margin=-12,
                    legend_box_spacing=0,
                    axis_title_x=element_text(size=9, margin={"t": 1, "b": 2}),
                    plot_margin_top=0,
                    plot_margin_right=0,
                    plot_margin_bottom=0,
                    plot_margin_left=0,
                    panel_grid_minor=element_blank(),
                    figure_size=(width_inch, fig_h)
                )
            )
            if title is not None:
                g = g + labs(title=title)
            return g

        p = _ggplot()
        if output_file:
            # Rasterize tile layers so PDF stores them as bitmaps (KB not MB).
            fig = p.draw()
            for ax in fig.axes:
                for col in ax.collections:
                    col.set_rasterized(True)
            fig.savefig(output_file, dpi=300, bbox_inches="tight")
            mpl.pyplot.close(fig)
            # Fresh ggplot: draw()+close leaves plotnine layout state invalid for a second draw
            # (e.g. Jupyter _repr_mimebundle_ → save → IndexError in layout.get_scales).
            p = _ggplot()
        return p
    finally:
        if prev_fontset is not None:
            mpl.rcParams["mathtext.fontset"] = prev_fontset


def _points_to_raster(df, xcol, ycol, value=None, n=512, x_range=(0, 1), y_range=(0, 1),
                      fill_style="gray", model_col="model", facet_models=None):
    """
    Rasterize (x, y) points into a grid and assign fill colors (scattermore-style).

    Parameters
    ----------
    df : pd.DataFrame
        Data with xcol, ycol, and optionally value and model_col.
    xcol, ycol : str
        Column names for x and y.
    value : str or None
        If None, use count per cell; else aggregate this column (mean) per cell.
    n : int
        Grid resolution (n x n pixels).
    x_range, y_range : tuple
        (min, max) for x and y.
    fill_style : str
        'gray' (count → light gray to dark) or 'viridis' (value → viridis).
    model_col : str
        Column name for facet (model). Preserved in output.
    facet_models : sequence or None
        If provided and df has no model_col, replicate the raster for each value (e.g. for measured in all facets).

    Returns
    -------
    raster_df : pd.DataFrame
        Columns x, y, fill (hex), and model_col if present.
    """
    def _single_raster(_df, _xcol, _ycol, _value):
        x = np.asarray(_df[_xcol], dtype=float)
        y = np.asarray(_df[_ycol], dtype=float)
        valid = np.isfinite(x) & np.isfinite(y)
        valid &= (x >= x_range[0]) & (x <= x_range[1]) & (y >= y_range[0]) & (y <= y_range[1])
        if not np.any(valid):
            return None
        xf, yf = x[valid], y[valid]
        x_edges = np.linspace(x_range[0], x_range[1], n + 1)
        y_edges = np.linspace(y_range[0], y_range[1], n + 1)
        xi = np.clip(np.digitize(xf, x_edges) - 1, 0, n - 1)
        yi = np.clip(np.digitize(yf, y_edges) - 1, 0, n - 1)
        if _value is None:
            z = np.zeros((n, n))
            np.add.at(z, (yi, xi), 1.0)
        else:
            v = np.asarray(_df.loc[valid, _value], dtype=float)
            sums = np.zeros((n, n))
            cnt = np.zeros((n, n))
            np.add.at(sums, (yi, xi), v)
            np.add.at(cnt, (yi, xi), 1.0)
            with np.errstate(divide="ignore", invalid="ignore"):
                z = np.where(cnt > 0, sums / cnt, 0.0)
        x_center = (x_edges[:-1] + x_edges[1:]) / 2
        y_center = (y_edges[:-1] + y_edges[1:]) / 2
        rows = []
        for i in range(n):
            for j in range(n):
                if z[i, j] <= 0:
                    continue
                rows.append({"x": x_center[j], "y": y_center[i], "z": z[i, j]})
        return pd.DataFrame(rows) if rows else None

    out_list = []
    if model_col in df.columns and df[model_col].nunique() > 1:
        for _, grp in df.groupby(model_col, observed=True):
            single = _single_raster(grp, xcol, ycol, value)
            if single is not None:
                single[model_col] = grp[model_col].iloc[0]
                out_list.append(single)
    else:
        single = _single_raster(df, xcol, ycol, value)
        if single is not None:
            if facet_models is not None:
                for m in facet_models:
                    s = single.copy()
                    s[model_col] = m
                    out_list.append(s)
            elif model_col in df.columns:
                single[model_col] = df[model_col].iloc[0]
                out_list.append(single)
            else:
                out_list.append(single)

    if not out_list:
        cols = ["x", "y"] + (["value"] if fill_style == "viridis" else [])
        cols += [model_col] if (facet_models or (model_col in df.columns)) else []
        return pd.DataFrame(columns=cols)
    out = pd.concat(out_list, ignore_index=True)

    zvals = out["z"].values
    out = out.drop(columns=["z"])
    if fill_style == "gray":
        # Single gray for measured layer (no density scale)
        pass
    else:
        # Viridis: keep numeric value for legend bar
        zmin, zmax = np.nanmin(zvals), np.nanmax(zvals)
        out["value"] = (
            np.ones_like(zvals)
            if zmax <= zmin
            else np.clip((zvals - zmin) / (zmax - zmin), 0, 1)
        )

    if model_col in out.columns:
        order = [x for x in FACET_ORDER if x in out[model_col].values]
        if order:
            out[model_col] = pd.Categorical(out[model_col], categories=order, ordered=True)
    return out


def _get_density(x, y, n=200):
    """
    Grid-based 2-D density estimate, equivalent to R's MASS::kde2d + findInterval lookup.
    """
    from scipy.ndimage import gaussian_filter

    finite = np.isfinite(x) & np.isfinite(y)
    density = np.full(len(x), np.nan)
    if finite.sum() < 2:
        return density
    xf, yf = x[finite], y[finite]
    counts, xedges, yedges = np.histogram2d(xf, yf, bins=n)
    z = gaussian_filter(counts.T, sigma=n / 25.0)
    ix = np.clip(np.digitize(xf, xedges) - 1, 0, n - 1)
    iy = np.clip(np.digitize(yf, yedges) - 1, 0, n - 1)
    density[finite] = z[iy, ix]
    return density
