"""
Explicit time-window averages for :class:`~pandas.DatetimeIndex` frames (LR0100-style).

This is **not** :meth:`pandas.DataFrame.resample` semantics. For **floor / ceiling / center**
windows, monthly label trimming, coverage rules, and examples, see
``docs/tutorials/3.time_averaging.ipynb``.
"""

import numpy as np
import pandas as pd

_MIN_VALID_FRACTION = 0.5  # Strict majority (> half) for coverage checks.


def _period_delta(freq):
    """
    Map a fixed pandas frequency string to window length Δ.

    Parameters
    ----------
    freq : str
        Fixed offset alias (e.g. ``'30min'``, ``'1h'``). Must resolve to a fixed step.

    Returns
    -------
    pandas.Timedelta
        Window length Δ.

    Raises
    ------
    ValueError
        If ``freq`` is not a fixed frequency.
    """
    off = pd.tseries.frequencies.to_offset(freq)
    try:
        return pd.Timedelta(off)
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"freq {freq!r} must be a fixed frequency (e.g. '30min', '1h')."
        ) from e


def _archive_timestep_1_or_3(index):
    """
    Infer native timestep as 1 or 3 minutes from median index spacing (BSRN archives).

    Parameters
    ----------
    index : pandas.DatetimeIndex
        Input timestamps.

    Returns
    -------
    pandas.Timedelta
        ``Timedelta(minutes=1)`` or ``Timedelta(minutes=3)`` (fallback: 1 min).
    """
    if len(index) < 2:
        return pd.Timedelta(minutes=1)
    d = pd.Series(index).diff().median()
    if pd.isna(d) or d <= pd.Timedelta(0):
        return pd.Timedelta(minutes=1)
    sec = float(d.total_seconds())
    if 0.5 * 60 <= sec <= 1.5 * 60:
        return pd.Timedelta(minutes=1)
    if 2.5 * 60 <= sec <= 3.5 * 60:
        return pd.Timedelta(minutes=3)
    return pd.Timedelta(minutes=1)


def _label_grid(index, freq):
    """
    Build a regular label grid from ``floor(min)`` through ``ceil(max)`` at ``freq``.

    Parameters
    ----------
    index : pandas.DatetimeIndex
        Data extent.
    freq : str
        Bin frequency.

    Returns
    -------
    pandas.DatetimeIndex
        Labels inclusive of endpoints; empty if invalid range.
    """
    lo = index.min().floor(freq)
    hi = index.max().ceil(freq)
    if lo > hi:
        return pd.DatetimeIndex([], tz=index.tz)
    return pd.date_range(lo, hi, freq=freq, inclusive="both", tz=index.tz)


def _trim_labels_for_alignment(labels, index, freq, alignment,
                               match_ceiling_labels=True):
    """
    Drop edge labels that would mix months (align with floor / ceiling / center grids).

    Parameters
    ----------
    labels : pandas.DatetimeIndex
        Full grid from :func:`_label_grid`.
    index : pandas.DatetimeIndex
        Actual data index (defines month span ``lo``, ``hi``).
    freq : str
        Bin frequency.
    alignment : {'floor', 'ceiling', 'center'}
        Window alignment.
    match_ceiling_labels : bool, default True
        For ``center`` only: if True, apply ceiling-style trim (``labels > lo``); else floor-style
        (``labels < hi``).

    Returns
    -------
    pandas.DatetimeIndex
        Trimmed labels.

    Raises
    ------
    ValueError
        If ``alignment`` is not recognized.
    """
    if len(labels) == 0:
        return labels
    lo = index.min().floor(freq)
    hi = index.max().ceil(freq)
    if alignment == "floor":
        return labels[labels < hi]
    if alignment == "ceiling":
        return labels[labels > lo]
    if alignment == "center":
        if match_ceiling_labels:
            return labels[labels > lo]
        return labels[labels < hi]
    raise ValueError(f"Unknown alignment: {alignment!r}")


def _window_mask(index, L, delta, alignment, resolution):
    """
    Boolean mask: timestamps belonging to the averaging window for label ``L``.

    Parameters
    ----------
    index : pandas.DatetimeIndex
        Row timestamps.
    L : pandas.Timestamp
        Label (bin anchor).
    delta : pandas.Timedelta
        Bin length Δ.
    alignment : {'floor', 'ceiling', 'center'}
        Window alignment (see module docstring).
    resolution : pandas.Timedelta
        Native timestep; shifts the **center** window start by ``+resolution``.

    Returns
    -------
    numpy.ndarray
        Boolean array, same length as ``index``.

    Raises
    ------
    ValueError
        If ``alignment`` is not recognized.
    """
    half = delta / 2
    if alignment == "floor":
        return (index >= L) & (index < L + delta)
    if alignment == "ceiling":
        return (index > L - delta) & (index <= L)
    if alignment == "center":
        return (index >= L - half + resolution) & (index <= L + half)
    raise ValueError(f"Unknown alignment: {alignment!r}")


def _expected_timesteps(delta, resolution):
    """
    Nominal number of native steps in one bin (for coverage checks, floor/ceiling).

    Parameters
    ----------
    delta : pandas.Timedelta
        Bin length.
    resolution : pandas.Timedelta
        Native timestep.

    Returns
    -------
    int
        At least 1.
    """
    return max(1, int(round(float(delta / resolution))))


def _count_valid_timesteps(part, df_columns_numeric):
    """
    Count rows with at least one finite numeric value in selected columns.

    Parameters
    ----------
    part : pandas.DataFrame
        Window subset.
    df_columns_numeric : list of str
        Column names to test (numeric dtypes).

    Returns
    -------
    int
        Row count.
    """
    if part.empty:
        return 0
    if len(df_columns_numeric) == 0:
        return len(part)
    return int(part[df_columns_numeric].notna().any(axis=1).sum())


def _nan_row_like(df):
    """
    One row of NaNs with the same columns as ``df`` (placeholder for insufficient coverage).

    Parameters
    ----------
    df : pandas.DataFrame
        Template frame.

    Returns
    -------
    pandas.Series
        All-NaN row.
    """
    return pd.Series(np.nan, index=df.columns)


def _finalize_row(agg, df):
    """
    Normalize aggregation output to a ``Series`` aligned to ``df.columns``.

    Parameters
    ----------
    agg : pandas.Series or scalar or mapping
        Result of ``aggfunc``.
    df : pandas.DataFrame
        Column order reference.

    Returns
    -------
    pandas.Series
        Reindexed series.
    """
    if isinstance(agg, pd.Series):
        s = agg
    else:
        s = pd.Series(agg)
    return s.reindex(df.columns)


def _aggregate(part, aggfunc):
    """
    Apply ``aggfunc`` to ``part`` (string name or callable).

    Parameters
    ----------
    part : pandas.DataFrame
        Window subset.
    aggfunc : str or callable
        ``'mean'``, ``'sum'``, ``'median'``, any name accepted by ``DataFrame.agg``, or
        ``callable(DataFrame) -> Series|scalar``.

    Returns
    -------
    scalar or pandas.Series
        Aggregation result.
    """
    if isinstance(aggfunc, str):
        if aggfunc == "mean":
            return part.mean(numeric_only=True)
        if aggfunc == "sum":
            return part.sum(numeric_only=True)
        if aggfunc == "median":
            return part.median(numeric_only=True)
        return part.agg(aggfunc)
    return aggfunc(part)


def pretty_average(df, freq, alignment="ceiling",
                   aggfunc="mean", resolution=None, match_ceiling_labels=True):
    """
    Average ``df`` over explicit labeled windows (not pandas ``resample`` semantics).
    Semantics and examples: ``docs/tutorials/3.time_averaging.ipynb``.

    Parameters
    ----------
    df : pandas.DataFrame
        Must use a :class:`~pandas.DatetimeIndex`.
    freq : str
        Fixed bin frequency (e.g. ``'1h'``, ``'30min'``).
    alignment : {'floor', 'ceiling', 'center'}, default ``'ceiling'``
        **floor** ``[L, L+Δ)`` · **ceiling** ``(L-Δ, L]`` · **center** ``[L-Δ/2+res, L+Δ/2]``.
        Definitions: tutorial ``docs/tutorials/3.time_averaging.ipynb``.
    aggfunc : str or callable, default ``'mean'``
        Passed to :func:`_aggregate`.
    resolution : pandas.Timedelta or None, default None
        Native timestep for **center** windows; if None, inferred as 1 or 3 min via
        :func:`_archive_timestep_1_or_3`.
    match_ceiling_labels : bool, default True
        When ``alignment='center'``, trim monthly edge labels like **ceiling** (default) or **floor**.

    Returns
    -------
    pandas.DataFrame
        One row per output label; insufficient coverage yields NaN rows (labels retained).

    Raises
    ------
    TypeError
        If ``df.index`` is not a :class:`~pandas.DatetimeIndex`.
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError(
            "pretty_average requires a DatetimeIndex; set df.index or use set_index."
        )

    if df.empty:
        return df.copy()

    delta = _period_delta(freq)
    res = resolution if resolution is not None else _archive_timestep_1_or_3(df.index)
    labels = _label_grid(df.index, freq)
    labels = _trim_labels_for_alignment(
        labels, df.index, freq, alignment, match_ceiling_labels=match_ceiling_labels
    )
    if len(labels) == 0:
        return df.iloc[0:0].copy()

    rows = []
    out_labels = []
    num_cols = list(df.select_dtypes(include=["number"]).columns)
    n_exp = _expected_timesteps(delta, res)

    for L in labels:
        mask = _window_mask(df.index, L, delta, alignment, res)
        part = df.loc[mask]
        n_valid = _count_valid_timesteps(part, num_cols)
        if alignment == "center":
            n_den = len(part)
            insufficient = n_den == 0 or n_valid <= n_den * _MIN_VALID_FRACTION
        else:
            insufficient = n_valid <= n_exp * _MIN_VALID_FRACTION

        if insufficient:
            rows.append(_nan_row_like(df))
            out_labels.append(L)
            continue

        rows.append(_finalize_row(_aggregate(part, aggfunc), df))
        out_labels.append(L)

    if not rows:
        return df.iloc[0:0].copy()

    out = pd.DataFrame(rows, index=pd.DatetimeIndex(out_labels, tz=df.index.tz))
    return out
