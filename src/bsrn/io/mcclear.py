"""
CAMS McClear HTTP retrieval helpers.
"""

import io
import pandas as pd
import requests
from bsrn.constants import MCCLEAR_INTEGRATED_COLUMNS, MCCLEAR_VARIABLE_MAP, MCCLEAR_API_HOST


def _parse_mcclear(raw_or_buffer):
    """
    Parse SoDa McClear CSV into the project DataFrame (used by ``_download_mcclear`` only).

    Parameters
    ----------
    raw_or_buffer : str or file-like
        Raw CAMS text or readable text buffer.

    Returns
    -------
    data : pd.DataFrame
        Parsed time-series data with UTC index for sub-daily resolutions.

    Raises
    ------
    ValueError
        If the McClear header line is missing or the payload is invalid.

    References
    ----------
    .. [1] CAMS McClear service info. (n.d.). SoDa.
       http://www.soda-pro.com/web-services/radiation/cams-mcclear/info
    """
    if isinstance(raw_or_buffer, str):
        fbuf = io.StringIO(raw_or_buffer)
    else:
        fbuf = raw_or_buffer

    # Read metadata header lines until column names line
    while True:
        line = fbuf.readline()
        if not line:
            raise ValueError("Invalid McClear payload: header not found.")
        line = line.rstrip("\n")
        if line.startswith("# Observation period"):
            names = line.lstrip("# ").split(";")
            break

    data = pd.read_csv(fbuf, sep=";", comment="#", header=None, names=names)
    
    # Interval bounds from first column
    obs_period = data["Observation period"].str.split("/")
    # Using the first part of the period (start-time) for floor-style labeling.
    data.index = pd.to_datetime(obs_period.str[0], utc=True)

    # Convert Wh/m^2 to W/m^2 using interval duration
    integrated_cols = [c for c in MCCLEAR_INTEGRATED_COLUMNS if c in data.columns]
    time_delta = pd.to_datetime(obs_period.str[1]) - pd.to_datetime(obs_period.str[0])
    hours = time_delta.dt.total_seconds() / 3600.0
    data[integrated_cols] = data[integrated_cols].divide(hours.tolist(), axis="rows")

    data.index.name = None
    data = data.rename(columns=MCCLEAR_VARIABLE_MAP)
    return data


def _download_mcclear(latitude, longitude, start, end, email, elev=None,
                      timeout=30):
    """
    Download and parse CAMS McClear from SoDa (used by ``fetch_mcclear`` only).

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
        Station elevation. [m] If None, use SoDa default terrain lookup.
    timeout : int, default 30
        HTTP request timeout in seconds.

    Returns
    -------
    data : pd.DataFrame
        Parsed McClear data.

    Raises
    ------
    ValueError
        If the request starts before 2004-01-01 or the response is not valid CSV.
    requests.Timeout
        If the HTTP request exceeds *timeout*.
    requests.HTTPError
        If SoDa returns a non-success status after ``raise_for_status``.

    References
    ----------
    .. [1] Lefèvre, M., Oumbe, A., Blanc, P., Espinar, B., Gschwind, B., Qu, Z.,
       et al. (2013). McClear: A new model estimating downwelling solar
       radiation at ground level in clear-sky conditions. Atmospheric
       Measurement Techniques, 6(9), 2403–2418.
    .. [2] Gschwind, B., Wald, L., Blanc, P., Lefèvre, M., Schroedter-Homscheidt, M.,
       & Arola, A. (2019). Improving the McClear model estimating the downwelling
       solar radiation at ground level in cloud-free conditions – McClear-v3.
       Meteorologische Zeitschrift, 28(2).
    """
    if elev is None:
        elev = -999

    # McClear availability: service is defined from 2004-01-01 onward.
    start_ts = pd.Timestamp(start)
    if start_ts.tzinfo is not None:
        start_cmp = start_ts.tz_convert("UTC").tz_localize(None)
    else:
        start_cmp = start_ts
    if start_cmp < pd.Timestamp("2004-01-01"):
        raise ValueError(
            "McClear data are only available from 2004-01-01 onward."
        )

    # Format dates and username for SoDa request
    end_ts = pd.Timestamp(end)
    if start_ts.tzinfo is not None:
        start_str = start_ts.tz_convert("UTC").strftime("%Y-%m-%d")
    else:
        start_str = start_ts.strftime("%Y-%m-%d")
    if end_ts.tzinfo is not None:
        end_str = end_ts.tz_convert("UTC").strftime("%Y-%m-%d")
    else:
        end_str = end_ts.strftime("%Y-%m-%d")
    email_encoded = email.replace("@", "%2540")

    # Build WPS DataInputs payload for McClear (1‑min, UT)
    data_inputs_dict = {
        "latitude": latitude,
        "longitude": longitude,
        "altitude": elev,
        "date_begin": start_str,
        "date_end": end_str,
        "time_ref": "UT",
        "summarization": "PT01M",
        "username": email_encoded,
        "verbose": "false",
    }
    data_inputs = ";".join([f"{key}={value}" for key, value in data_inputs_dict.items()])
    params = {
        "Service": "WPS",
        "Request": "Execute",
        "Identifier": "get_mcclear",
        "version": "1.0.0",
        "RawDataOutput": "irradiation",
    }

    # Use the same HTTPS endpoint and request pattern as pvlib.iotools.get_cams,
    # with the host defined in project constants.
    base_url = f"https://{MCCLEAR_API_HOST}/service/wps"

    try:
        res = requests.get(
            base_url + "?DataInputs=" + data_inputs,
            params=params,
            timeout=timeout,
        )
    except requests.Timeout as exc:
        raise requests.Timeout(
            f"McClear request timed out for {base_url}: {exc}"
        ) from exc

    # If an error occurs on the server side, CAMS returns a PyWPS-style XML/HTML
    # with ows:ExceptionText; bubble that up for easier debugging.
    if not res.ok:
        text = res.text or ""
        if "ows:ExceptionText" in text:
            try:
                errors = text.split("ows:ExceptionText")[1][1:-2]
            except Exception:
                errors = text
            res.reason = f"{res.reason}: <{errors}>"
        res.raise_for_status()

    # Successful responses are CSV; parse directly from memory.
    fbuf = io.StringIO(res.content.decode("utf-8"))
    data = _parse_mcclear(fbuf)
    return data


def fetch_mcclear(index, latitude, longitude, elev, email, timeout=30):
    """
    Retrieve and align McClear data to a target DatetimeIndex.

    Parameters
    ----------
    index : pd.DatetimeIndex
        Target time index to align McClear outputs to.
    latitude : float
        Latitude in decimal degrees. [degrees]
    longitude : float
        Longitude in decimal degrees. [degrees]
    elev : float
        Site elevation. [m]
    email : str
        SoDa account email.
    timeout : int, default 30
        HTTP request timeout in seconds.

    Returns
    -------
    aligned : pd.DataFrame
        McClear data reindexed to `index`. Must contain
        `ghi_clear`, `bni_clear`, and `dhi_clear`.

    Raises
    ------
    ValueError
        If ``index`` is not a DatetimeIndex, McClear columns are missing, or the
        downloaded frame has an invalid index.
    requests.Timeout
        Propagated from :func:`_download_mcclear` when the HTTP call times out.
    requests.HTTPError
        Propagated from SoDa on HTTP failure.
    """
    if not isinstance(index, pd.DatetimeIndex):
        raise ValueError(
            "index must be a pandas DatetimeIndex."
        )

    # Determine inclusive date range from index
    start = pd.Timestamp(index.min()).to_pydatetime()
    end = pd.Timestamp(index.max()).to_pydatetime()

    data = _download_mcclear(
        latitude=latitude,
        longitude=longitude,
        start=start,
        end=end,
        email=email,
        elev=elev,
        timeout=timeout,
    )

    if not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError(
            "McClear data index must be DatetimeIndex."
        )

    data = data.copy()
    if data.index.tz is None:
        data.index = data.index.tz_localize("UTC")
    else:
        data.index = data.index.tz_convert("UTC")

    required_cols = {"ghi_clear", "bni_clear", "dhi_clear"}
    missing = required_cols - set(data.columns)
    if missing:
        raise ValueError(
            f"McClear data missing required columns: {sorted(missing)}"
        )

    aligned = data.reindex(index)
    return aligned
