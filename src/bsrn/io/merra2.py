"""
MERRA-2 parquet loader for REST2 clear-sky inputs.

Fetches MERRA-2 parquet from Hugging Face (dazhiyang/bsrn-merra2) into RAM (no disk cache).
"""

import io
import pandas as pd
import requests

from bsrn.constants import MERRA2_HF_REPO_ID, HF_MAINTAINER_EMAIL


def _hf_fetch_to_memory(repo_id, filename):
    """
    Fetch one dataset file from Hugging Face into RAM (no disk cache; used by ``_fetch_merra2_from_hf``).

    Parameters
    ----------
    repo_id : str
        Hugging Face dataset repo id.
    filename : str
        Path within the repo (e.g. ``stn/stnMMYY_merra2.parquet``).

    Returns
    -------
    content : bytes
        Raw file bytes.

    Raises
    ------
    ImportError
        If ``huggingface_hub`` is not installed.
    FileNotFoundError
        On 404 or other fetch failure; message includes maintainer contact.
    """
    try:
        from huggingface_hub import hf_hub_url
    except ImportError:
        raise ImportError(
            "huggingface_hub is required for MERRA-2. Install with: pip install huggingface_hub"
        )
    print(f"Fetching MERRA-2 from Hugging Face: {filename}")
    try:
        url = hf_hub_url(
            repo_id=repo_id, filename=filename, repo_type="dataset"
        )
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return resp.content
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise FileNotFoundError(
                f"{filename} is not yet on huggingface, please contact the maintainer "
                f"Dazhi Yang at {HF_MAINTAINER_EMAIL} for update."
            ) from e
        raise FileNotFoundError(
            f"{filename} is not yet on huggingface, please contact the maintainer "
            f"Dazhi Yang at {HF_MAINTAINER_EMAIL} for update."
        ) from e
    except Exception as e:
        raise FileNotFoundError(
            f"{filename} is not yet on huggingface, please contact the maintainer "
            f"Dazhi Yang at {HF_MAINTAINER_EMAIL} for update."
        ) from e


def _fetch_merra2_from_hf(station_code, index):
    """
    Fetch one parquet per unique (year, month) in *index* from Hugging Face (used by ``fetch_rest2``).

    Parameters
    ----------
    station_code : str
        BSRN station code (case-insensitive).
    index : pd.DatetimeIndex
        Non-empty target index; months present determine which files are fetched.

    Returns
    -------
    contents : list of bytes
        One element per month, in sorted (year, month) order.

    Raises
    ------
    ValueError
        If *index* is empty.
    """
    if index.empty:
        raise ValueError("index must not be empty.")
    stn = station_code.lower()
    # Use (year, month) pairs to avoid PeriodIndex (which drops tz and triggers a warning)
    unique_pairs = set(zip(index.year, index.month))
    contents = []
    for year, month in sorted(unique_pairs):
        filename = f"{stn}{month:02d}{year % 100:02d}_merra2.parquet"
        hf_filename = f"{stn}/{filename}"
        content = _hf_fetch_to_memory(MERRA2_HF_REPO_ID, hf_filename)
        contents.append(content)
    return contents


def _load_merra2_parquet(path_or_bytes):
    """
    Load one MERRA-2 parquet into a UTC-indexed DataFrame (used by ``fetch_rest2`` only).

    Parameters
    ----------
    path_or_bytes : str, path-like, bytes, or file-like
        Path to the parquet file, or bytes content, or file-like object.

    Returns
    -------
    data : pd.DataFrame
        MERRA-2 data with columns AOD55, ALPHA, ALBEDO, TQV, TO3, PS
        and UTC DatetimeIndex.
    """
    if isinstance(path_or_bytes, bytes):
        path_or_bytes = io.BytesIO(path_or_bytes)
    data = pd.read_parquet(path_or_bytes)
    if not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError(
            "MERRA-2 parquet must have DatetimeIndex."
        )
    if data.index.tz is None:
        data.index = data.index.tz_localize("UTC")
    else:
        data.index = data.index.tz_convert("UTC")
    return data


def _parse_merra2_for_rest2(raw, target_index):
    """
    Reindex, interpolate, derive BETA, convert units for REST2 (used by ``fetch_rest2`` only).

    Parameters
    ----------
    raw : pd.DataFrame
        MERRA-2 data with columns AOD55, ALPHA, ALBEDO, TQV, TO3, PS.
    target_index : pd.DatetimeIndex
        Target 1-min index, typically the BSRN time index.

    Returns
    -------
    rest2 : pd.DataFrame
        REST2-ready DataFrame with columns PS, ALBEDO, ALPHA, BETA, TO3, TQV.
    """
    if not isinstance(target_index, pd.DatetimeIndex):
        raise ValueError(
            "target_index must be a DatetimeIndex."
        )

    df = raw.copy()

    # Reindex to 1-min target index and interpolate
    df = df.reindex(target_index)
    num_cols = df.select_dtypes(include="number").columns
    if len(num_cols) > 0:
        df[num_cols] = df[num_cols].interpolate(method="time", limit_direction="both")

    # Unit conversions
    # PS: Pa → hPa (÷ 100)
    if "PS" in df.columns:
        df["PS"] = df["PS"] / 100.0
    # TQV: kg/m² → atm.cm (÷ 10)
    if "TQV" in df.columns:
        df["TQV"] = df["TQV"] / 10.0
    # TO3: Dobson → atm.cm (÷ 1000)
    if "TO3" in df.columns:
        df["TO3"] = df["TO3"] / 1000.0

    # Derive BETA = AOD55 * 0.55^ALPHA; replace AOD55=0 with 0.001 before
    if {"AOD55", "ALPHA"}.issubset(df.columns):
        aod55 = df["AOD55"].replace(0.0, 0.001)
        df["BETA"] = aod55 * (0.55 ** df["ALPHA"])
        df = df.drop(columns=["AOD55"])

    return df


def fetch_rest2(index, station_code):
    """
    Fetch MERRA-2 from Hugging Face and return REST2-ready inputs aligned to target index.
    Parallel to fetch_mcclear; both return aligned clear-sky inputs.

    Parameters
    ----------
    index : pd.DatetimeIndex
        Target time index to align REST2 outputs to.
    station_code : str
        BSRN station code (e.g. "QIQ").

    Returns
    -------
    aligned : pd.DataFrame
        REST2 inputs reindexed to `index` with columns PS, ALBEDO, ALPHA, BETA, TO3, TQV.

    Raises
    ------
    ValueError
        If ``index`` is not a :class:`~pandas.DatetimeIndex` or is empty.
    FileNotFoundError
        If a required monthly parquet is missing on Hugging Face.
    """
    if not isinstance(index, pd.DatetimeIndex):
        raise ValueError(
            "index must be a pandas DatetimeIndex."
        )
    if index.empty:
        raise ValueError("index must not be empty.")

    contents = _fetch_merra2_from_hf(station_code, index)
    dfs = [_load_merra2_parquet(c) for c in contents]
    raw = pd.concat(dfs).sort_index()
    raw = raw[~raw.index.duplicated(keep="first")]
    rest2 = _parse_merra2_for_rest2(raw, index)
    return rest2
