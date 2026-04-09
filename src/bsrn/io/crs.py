"""
CAMS solar radiation service (CRS) HTTP retrieval helpers.

CRS and McClear are both exposed on SoDa (same ``api.soda-solardata.com`` WPS endpoint);
this module mirrors :mod:`bsrn.io.mcclear` but uses WPS ``Identifier=get_cams_radiation``.
"""

import io
import pandas as pd
import requests
from huggingface_hub import hf_hub_url
from bsrn.constants import (
    BSRN_STATIONS,
    CRS_API_HOST,
    CRS_HF_REPO_ID,
    CRS_INTEGRATED_COLUMNS,
    HF_MAINTAINER_EMAIL,
    CRS_OUTPUT_COLUMNS,
    CRS_VARIABLE_MAP,
    CRS_HIMAWARI_MIN_START_UTC,
    CRS_MSG_MIN_START_UTC,
)
from bsrn.physics.geometry import in_satellite_disk
from bsrn.io.retrieval import get_bsrn_file_inventory, months_from_ftp_filenames

# ---------------------------------------------------------------------------
#  Private helpers
# ---------------------------------------------------------------------------

def _crs_min_start_utc(latitude, longitude):
    """
    Get the earliest allowed CRS start date [UTC] for a given site.

    Parameters
    ----------
    latitude : float
        Site latitude [degrees].
    longitude : float
        Site longitude [degrees].

    Returns
    -------
    min_start : pd.Timestamp or None
        The earliest start date, or None if the site is outside all disks.
    """
    in_himawari = in_satellite_disk(latitude, longitude, "Himawari")
    in_msg = in_satellite_disk(latitude, longitude, "MSG")

    if not in_himawari and not in_msg:
        return None

    # Earliest allowed start: union of applicable satellite minima (favor earliest)
    candidates = []
    if in_himawari:
        candidates.append(pd.Timestamp(CRS_HIMAWARI_MIN_START_UTC))
    if in_msg:
        candidates.append(pd.Timestamp(CRS_MSG_MIN_START_UTC))

    return min(candidates)


def _check_crs_coverage(latitude, longitude, start):
    """
    Require the site inside the Himawari or MSG **60° reliability disk** and *start* not
    before the applicable minimum.

    Parameters
    ----------
    latitude : float
        Site latitude [degrees].
    longitude : float
        Site longitude [degrees].
    start : datetime-like
        Request period start.

    Raises
    ------
    ValueError
        If the site is outside both satellite disks or *start* is before the required minimum.
    """
    min_start = _crs_min_start_utc(latitude, longitude)
    if min_start is None:
        raise ValueError(
            "Site is outside the Himawari (140.7°E) and MSG (0°E) 60° reliability disks."
        )

    # Compare *start* as UTC-naive timestamp
    start_ts = pd.Timestamp(start)
    if start_ts.tzinfo is not None:
        start_cmp = start_ts.tz_convert("UTC").tz_localize(None)
    else:
        start_cmp = start_ts

    if start_cmp < min_start:
        raise ValueError(
            f"CRS request start must be on or after {min_start.date()} for this location."
        )


def _parse_crs(raw_or_buffer):
    """
    Parse SoDa CAMS CRS CSV into the project irradiance frame (used by ``download_crs`` only).

    Parameters
    ----------
    raw_or_buffer : str or file-like
        Raw SoDa CAMS text or readable text buffer.

    Returns
    -------
    data : pd.DataFrame
        UTC index and columns ``ghi_crs``, ``bni_crs``, ``dhi_crs`` [W/m²] only.

    Raises
    ------
    ValueError
        Missing header line, missing columns after rename, or unreadable CSV.

    References
    ----------
    .. [1] CAMS radiation service — SoDa.
       https://www.soda-pro.com/web-services/radiation/cams-radiation-service
    """
    if isinstance(raw_or_buffer, str):
        fbuf = io.StringIO(raw_or_buffer)
    else:
        fbuf = raw_or_buffer

    # Skip preamble until column-name row
    while True:
        line = fbuf.readline()
        if not line:
            raise ValueError("Invalid CRS payload: header not found.")
        line = line.rstrip("\n")
        if line.startswith("# Observation period"):
            names = line.lstrip("# ").split(";")
            break

    data = pd.read_csv(fbuf, sep=";", comment="#", header=None, names=names)
    # Interval bounds from first column
    obs_period = data["Observation period"].str.split("/")
    # Using the first part of the period (start-time) for floor-style labeling.
    data.index = pd.to_datetime(obs_period.str[0], utc=True)

    # SoDa integrated irradiance → mean irradiance over the step [W/m²]
    integrated_cols = [c for c in CRS_INTEGRATED_COLUMNS if c in data.columns]
    time_delta = pd.to_datetime(obs_period.str[1]) - pd.to_datetime(obs_period.str[0])
    hours = time_delta.dt.total_seconds() / 3600.0
    data[integrated_cols] = data[integrated_cols].divide(hours.tolist(), axis="rows")

    data.index.name = None  # Remove index name
    data = data.rename(columns=CRS_VARIABLE_MAP)
    missing = [c for c in CRS_OUTPUT_COLUMNS if c not in data.columns]
    if missing:
        raise ValueError(
            "CRS payload missing required columns after rename: "
            f"{missing}."
        )
    return data[CRS_OUTPUT_COLUMNS].copy()


def _hf_fetch_to_memory(repo_id, filename):
    """
    Fetch a file from Hugging Face Hub directly to memory (bytes).

    Parameters
    ----------
    repo_id : str
        Hugging Face repository ID (e.g., "dazhiyang/bsrn-v1").
    filename : str
        Path within the repository (e.g., "qiq/qiq0624_crs.parquet").

    Returns
    -------
    content : bytes
        Raw file bytes.

    Raises
    ------
    FileNotFoundError
        If the file is missing on the Hub or the HTTP request fails.
    """
    print(f"Fetching CRS from Hugging Face: {filename}")
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


def _fetch_crs_from_hf(station_code, index):
    """
    Fetch raw bytes from Hugging Face for the months required by the index.

    Parameters
    ----------
    station_code : str
        BSRN station code (case-insensitive).
    index : pd.DatetimeIndex
        Non-empty target index; months present determine which files are fetched.

    Returns
    -------
    contents : list of bytes
        One element per month, in sorted order.

    Raises
    ------
    ValueError
        If index is empty.
    """
    if index.empty:
        raise ValueError("index must not be empty.")
    stn = station_code.lower()

    # With floor-labeling (start-of-interval), the month in the index directly
    # determines which monthly file we need to fetch.
    unique_months = sorted(set(zip(index.year, index.month)))

    contents = []  # Accumulate raw bytes
    for year, month in unique_months:
        yy = str(year)[2:]
        mm = f"{month:02d}"
        # Monthly filename format: qiq0124_crs.parquet
        filename = f"{stn}{mm}{yy}_crs.parquet"
        hf_filename = f"{stn}/{filename}"
        content = _hf_fetch_to_memory(CRS_HF_REPO_ID, hf_filename)
        contents.append(content)
    return contents


def _load_crs_parquet(path_or_bytes):
    """
    Load one CRS parquet into a UTC-indexed DataFrame.

    Parameters
    ----------
    path_or_bytes : str, path-like, bytes, or file-like
        Path to the parquet file, or bytes content, or file-like object.

    Returns
    -------
    data : pd.DataFrame
        CRS data with columns ghi_crs, bni_crs, dhi_crs and UTC DatetimeIndex.
    """
    if isinstance(path_or_bytes, bytes):
        path_or_bytes = io.BytesIO(path_or_bytes)
    data = pd.read_parquet(path_or_bytes)
    if not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError("CRS parquet must have DatetimeIndex.")
    if data.index.tz is None:
        data.index = data.index.tz_localize("UTC")  # Localize to UTC
    else:
        data.index = data.index.tz_convert("UTC")  # Convert to UTC
    return data


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def check_crs_availability(stations, username, password):
    """
    Check which BSRN stations are geographically covered by CAMS Radiation Service (CRS)
    **and** have BSRN archive files overlapping the CRS temporal range.

    Workflow:
    1. Filter *stations* by spatial coverage (MSG and Himawari disks).
    2. Query BSRN FTP for the covered subset to obtain file inventories.
    3. Extract years from filenames and intersect with the CRS year range.

    Parameters
    ----------
    stations : list of str
        BSRN station codes to check (e.g. ``['BIL', 'BON', 'DRA']``).
    username : str
        BSRN FTP username.
    password : str
        BSRN FTP password.

    Returns
    -------
    availability : dict
        A dictionary mapping station codes to availability metadata:
        ``{station_code: {'years': [list of years], 'months': [list of (y,m) tuples]}}``.
        ``years`` is used for bulk API downloads, and ``months`` for monthly
        parquet writing. Stations with no overlap are omitted.
    """
    # Mission start years for MSG and Himawari
    y_min_msg = 2004
    y_min_hima = 2016
    y_max = pd.Timestamp.now(tz="UTC").year

    # Step 1: geographic filter
    covered = {}  # maps station to its min_year
    for code in stations:
        code_upper = code.upper()
        if code_upper not in BSRN_STATIONS:
            continue
        meta = BSRN_STATIONS[code_upper]
        lat, lon = meta["lat"], meta["lon"]

        # Use library logic to determine coverage and minimum start date
        in_msg = in_satellite_disk(lat, lon, "MSG")
        in_hima = in_satellite_disk(lat, lon, "Himawari")

        if in_msg or in_hima:
            # Union of applicable satellite minima
            min_y = y_min_msg
            if in_hima and not in_msg:
                min_y = y_min_hima
            elif in_hima and in_msg:
                min_y = min(y_min_msg, y_min_hima)
            covered[code_upper] = min_y

    if not covered:
        return {}

    # Step 2: FTP inventory for covered stations
    inventory = get_bsrn_file_inventory(list(covered.keys()), username, password)

    # Step 3: extract years and intersect with CRS range
    availability = {}
    for stn, files in inventory.items():
        stn_upper = stn.upper()
        min_y = covered[stn_upper]
        
        # Standardize month extraction
        all_months = months_from_ftp_filenames(files)
        ym_filtered = [(y, m) for y, m in all_months if min_y <= y <= y_max]

        if ym_filtered:
            unique_years = sorted(list(set(y for y, m in ym_filtered)))
            # Store metadata for station
            availability[stn_upper] = {
                "years": unique_years,
                "months": sorted(list(set(ym_filtered)))
            }

    return availability


def download_crs(latitude, longitude, start, end, email, elev=None,
                 summarization="PT01H", timeout=30):
    """
    Download and parse CAMS Radiation Service (CRS) time series from SoDa.

    CRS provides **all-sky** satellite-derived irradiances (not a clear-sky model like McClear).
    Requests use ``time_ref=UT`` and ``verbose=false`` (fixed; not configurable).
    Parsed frame contains only UTC index and all-sky ``ghi_crs``, ``bni_crs``, ``dhi_crs`` [W/m²]
    (other SoDa fields are dropped). Location and *start* are validated by ``_check_crs_coverage``.

    Parameters
    ----------
    latitude : float
        Latitude in decimal degrees. [degrees]
    longitude : float
        Longitude in decimal degrees. [degrees]
    start : datetime.datetime or pandas.Timestamp
        Start date (inclusive) of requested period.
    end : datetime.datetime or pandas.Timestamp
        End date (inclusive) of requested period.
    email : str
        SoDa account email.
    elev : float, optional
        Station elevation [m]. If None, use SoDa default terrain lookup (-999).
    summarization : str, default "PT01H"
        ISO-8601 duration for temporal aggregation (e.g., "PT01M", "PT15M", "PT01H").
    timeout : int, default 30
        HTTP request timeout in seconds.

    Returns
    -------
    data : pd.DataFrame
        Columns ghi_crs, bni_crs, dhi_crs only; UTC DatetimeIndex.

    Raises
    ------
    requests.HTTPError
        SoDa returned a non-success HTTP status (often with ows:ExceptionText in the body).
    ValueError
        Coverage or start failed _check_crs_coverage, XML instead of CSV, parse error, or empty data.

    References
    ----------
    .. [1] Schroedter-Homscheidt, M., et al. (2016). User's Guide to the CAMS Radiation Service.
       European Commission.
    """
    if elev is None:
        elev = -999  # Default to terrain lookup

    _check_crs_coverage(latitude, longitude, start)

    # WPS date strings in UTC
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if start_ts.tzinfo is not None:
        start_str = start_ts.tz_convert("UTC").strftime("%Y-%m-%d")
    else:
        start_str = start_ts.strftime("%Y-%m-%d")
    if end_ts.tzinfo is not None:
        end_str = end_ts.tz_convert("UTC").strftime("%Y-%m-%d")
    else:
        end_str = end_ts.strftime("%Y-%m-%d")
    # Double-encode @ for query string
    email_encoded = email.replace("@", "%2540")

    # SoDa Execute payload (DataInputs)
    data_inputs_dict = {
        "latitude": latitude,
        "longitude": longitude,
        "altitude": elev,
        "date_begin": start_str,
        "date_end": end_str,
        "time_ref": "UT",
        "summarization": summarization,
        "username": email_encoded,
        "verbose": "false",
    }
    data_inputs = ";".join([f"{key}={value}" for key, value in data_inputs_dict.items()])
    params = {
        "Service": "WPS",
        "Request": "Execute",
        "Identifier": "get_cams_radiation",
        "version": "1.0.0",
        "RawDataOutput": "irradiation",
    }

    base_url = f"https://{CRS_API_HOST}/service/wps"

    try:
        res = requests.get(
            base_url + "?DataInputs=" + data_inputs,
            params=params,
            timeout=timeout,
        )
    except requests.Timeout as exc:
        raise requests.Timeout(
            f"CRS request timed out for {base_url}: {exc}"
        ) from exc

    # Enrich HTTPError with OWS exception text when present
    if not res.ok:
        text = res.text or ""
        if "ows:ExceptionText" in text:
            try:
                errors = text.split("ows:ExceptionText")[1][1:-2]
            except Exception:
                errors = text
            res.reason = f"{res.reason}: <{errors}>"
        res.raise_for_status()

    body_text = res.content.decode("utf-8")
    stripped = body_text.lstrip()
    # 200 OK can still be XML on some errors
    if stripped.startswith("<?xml") or stripped.startswith("<ows:ExceptionReport"):
        raise ValueError(
            "SoDa CRS returned XML instead of CSV."
        )

    data = _parse_crs(body_text)

    if len(data.index) == 0:
        raise ValueError(
            "SoDa CRS returned no data rows."
        )
    return data


def fetch_crs_hf(index, station_code):
    """
    Fetch CRS from Hugging Face and return inputs aligned to target index.

    Parameters
    ----------
    index : pd.DatetimeIndex
        Target time index to align CRS outputs to.
    station_code : str
        BSRN station code (e.g., "QIQ").

    Returns
    -------
    aligned : pd.DataFrame
        CRS inputs reindexed to `index` with columns ghi_crs, bni_crs, dhi_crs.

    Raises
    ------
    ValueError
        If ``index`` is not a :class:`~pandas.DatetimeIndex` or is empty.
    FileNotFoundError
        From Hugging Face fetch helpers when a monthly parquet is unavailable.
    """
    if not isinstance(index, pd.DatetimeIndex):
        raise ValueError(
            "index must be a pandas DatetimeIndex."
        )
    if index.empty:
        raise ValueError("index must not be empty.")

    contents = _fetch_crs_from_hf(station_code, index)
    dfs = [_load_crs_parquet(c) for c in contents]
    raw = pd.concat(dfs).sort_index()
    raw = raw[~raw.index.duplicated(keep="first")]

    # By default, use direct reindexing.
    # To align with ceiling average, we often need +1 hour shift here
    # but I'm leaving it as-is for now based on user's 'revert'.
    aligned = raw.reindex(index)
    return aligned


def add_crs_columns(df, station_code=None, lat=None, lon=None, elev=None):
    """
    Adds CRS (CAMS Radiation Service) all-sky columns to a DataFrame.
    Fetches data from Hugging Face automatically.

    Location can be given by BSRN station code or by explicit lat/lon/elev.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to which columns will be added. Index must be DatetimeIndex.
    station_code : str, optional
        BSRN station abbreviation. [e.g. 'QIQ'] Used if lat/lon/elev not provided.
    lat : float, optional
        Latitude. [degrees] Required for non-BSRN stations if station_code omitted.
    lon : float, optional
        Longitude. [degrees] Required for non-BSRN stations if station_code omitted.
    elev : float, optional
        Elevation. [m] Required for non-BSRN stations if station_code omitted.

    Returns
    -------
    df : pd.DataFrame
        The input DataFrame with added crs columns.

    Raises
    ------
    ValueError
        If ``df.index`` is not a :class:`~pandas.DatetimeIndex`.
    ValueError
        If neither a valid station_code nor complete (lat, lon, elev) is provided.
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame index must be a pandas DatetimeIndex.")

    # Resolve metadata: explicit lat/lon/elev or BSRN lookup
    if lat is not None and lon is not None and elev is not None:
        pass  # use provided coordinates
    elif station_code is not None and station_code in BSRN_STATIONS:
        meta = BSRN_STATIONS[station_code]
        lat, lon, elev = meta["lat"], meta["lon"], meta["elev"]
    elif station_code is not None:
        raise ValueError(
            f"Station '{station_code}' not found in BSRN registry. "
            "For non-BSRN stations, provide 'lat', 'lon', and 'elev' explicitly."
        )
    else:
        raise ValueError(
            "Insufficient metadata. Provide a valid BSRN 'station_code' or "
            "explicit 'lat', 'lon', and 'elev'."
        )

    if station_code is None:
        raise ValueError("fetch_crs_hf currently requires 'station_code' to fetch parquets from Hugging Face.")

    crs_data = fetch_crs_hf(df.index, station_code)
    for col in crs_data.columns:
        df[col] = crs_data[col]
    return df
