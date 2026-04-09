"""
BSRN station-to-archive field validators.

Each ``*_validateFunction`` name matches ``LR_SPECS`` ``validate_func``. The ``LR*`` models
in :mod:`bsrn.archive.records_models` call them through Pydantic
:class:`pydantic.functional_validators.AfterValidator` (scalar fields) and
:func:`pydantic.field_validator` (LR0100 / LR4000 minute vectors with ``yearMonth``).
Lookup tables live in :mod:`bsrn.archive.specs` (``QUANTITIES``, …).
"""

import calendar
import re
from datetime import datetime

from .specs import QUANTITIES, SURFACES, TOPOGRAPHIES, PYRGEOMETER_BODY, PYRGEOMETER_DOME

# =============================================================================
# Header / metadata logical records (LR0001–LR0008)
# =============================================================================

# --- Core Fortran-style checks (I / A / F widths, C numeric, L logical) ---


def I_validateFunction(value, digits, v_min=0, v_max=None):
    """
    Validate integer ``value`` for Fortran ``I`` width and optional bounds.

    BSRN Fortran ``I`` width and optional numeric bounds.

    Parameters
    ----------
    value : int or float
        Candidate integer.
    digits : int
        Number of decimal digits allowed (``10**digits - 1`` upper bound if ``v_max`` is None).
    v_min : int, optional
        Minimum inclusive value; default ``0``.
    v_max : int or None, optional
        Maximum inclusive value; if ``None``, set from ``digits``.

    Returns
    -------
    int
        Validated integer.

    Raises
    ------
    ValueError
        If ``value`` is not integral or outside ``[v_min, v_max]``.
    """
    if v_max is None:
        v_max = (10**digits) - 1
    if not isinstance(value, (int, float)):
        raise ValueError("must be a numerical value")
    if value % 1 != 0:
        raise ValueError("must be an integer")
    if value < v_min or value > v_max:
        raise ValueError(f"must be between {v_min} and {v_max}")
    return int(value)


def C_validateFunction(value):
    """
    Accept any non-empty numeric-like token (archive ``C`` / free numeric).

    Coefficient / free-numeric token rules for archive constants.

    Parameters
    ----------
    value : object
        Candidate value.

    Returns
    -------
    object
        ``value`` unchanged when valid.

    Raises
    ------
    ValueError
        If ``value`` is ``None`` or empty string.
    """
    if value is None or value == "":
        raise ValueError("Value cannot be NULL or empty")
    return value


def A_validateFunction(value, maxLenght=float("inf")):
    """
    Validate non-empty string length for Fortran ``A`` fields.

    Fortran ``A`` (alphanumeric) width checks for archive strings.

    Parameters
    ----------
    value : str
        Candidate string.
    maxLenght : float, optional
        Maximum length (default: no upper bound beyond positivity).

    Returns
    -------
    str
        Validated string.

    Raises
    ------
    ValueError
        If not a ``str`` or length outside ``[1, maxLenght]``.
    """
    if not isinstance(value, str):
        raise ValueError("must be a character")
    n = len(value)
    if n < 1 or n > maxLenght:
        raise ValueError(f"number of character must be between 1 and {maxLenght}")
    return value


def F_validateFunction(value, w, d):
    """
    Validate float width for Fortran ``F{w}.{d}`` (integer and fractional parts).

    Fortran ``F`` width and decimal rules for archive floats.

    Parameters
    ----------
    value : int or float
        Candidate numeric.
    w : int
        Total field width.
    d : int
        Digits after the decimal point.

    Returns
    -------
    float
        Validated float.

    Raises
    ------
    ValueError
        If not numeric or if string representation violates ``F{w}.{d}``.
    """
    if not isinstance(value, (int, float)):
        raise ValueError("must be a numerical value")
    s = str(value).split(".")
    if len(s) >= 1:
        # Integer width excludes the minus sign when checking against (w - d).
        int_part = s[0].replace("-", "")
        if len(int_part) >= (w - d):
            raise ValueError(f"must be at format F{w}.{d}")
    if len(s) > 1:
        if len(s[1]) > d:
            raise ValueError(f"must be at format F{w}.{d}")
    return float(value)


def L_validateFunction(value):
    """
    Validate Python ``bool`` for Fortran logical ``L`` fields.

    Logical / boolean archive fields (``L`` format).

    Parameters
    ----------
    value : bool
        Candidate flag.

    Returns
    -------
    bool
        Validated boolean.

    Raises
    ------
    ValueError
        If ``value`` is not a ``bool``.
    """
    if not isinstance(value, bool):
        raise ValueError("must be a logical value (TRUE or FALSE)")
    return value


# --- Fixed-width integer tokens (I2 … I8) ---


def I2_validateFunction(value):
    """
    Validate Fortran ``I2`` integer field.

    Two-digit Fortran ``I2`` archive integer token.

    Parameters
    ----------
    value : int or float
        Candidate value.

    Returns
    -------
    int
        Validated integer.

    Raises
    ------
    ValueError
        From :func:`I_validateFunction`.
    """
    return I_validateFunction(value, 2)


def I3_validateFunction(value):
    """
    Validate Fortran ``I3`` integer field.

    Three-digit Fortran ``I3`` archive integer token.

    Parameters
    ----------
    value : int or float
        Candidate value.

    Returns
    -------
    int
        Validated integer.

    Raises
    ------
    ValueError
        From :func:`I_validateFunction`.
    """
    return I_validateFunction(value, 3)


def I4_validateFunction(value):
    """
    Validate Fortran ``I4`` integer field.

    Four-digit Fortran ``I4`` archive integer token.

    Parameters
    ----------
    value : int or float
        Candidate value.

    Returns
    -------
    int
        Validated integer.

    Raises
    ------
    ValueError
        From :func:`I_validateFunction`.
    """
    return I_validateFunction(value, 4)


def I5_validateFunction(value):
    """
    Validate Fortran ``I5`` integer field.

    Five-digit Fortran ``I5`` archive integer token.

    Parameters
    ----------
    value : int or float
        Candidate value.

    Returns
    -------
    int
        Validated integer.

    Raises
    ------
    ValueError
        From :func:`I_validateFunction`.
    """
    return I_validateFunction(value, 5)


def I8_validateFunction(value):
    """
    Validate Fortran ``I8`` integer field.

    Eight-digit Fortran ``I8`` archive integer token (e.g. ``yyyymmdd``).

    Parameters
    ----------
    value : int or float
        Candidate value.

    Returns
    -------
    int
        Validated integer.

    Raises
    ------
    ValueError
        From :func:`I_validateFunction`.
    """
    return I_validateFunction(value, 8)


# --- Calendar parts (month, year, day, hour, minute) ---


def month_validateFunction(value):
    """
    Validate calendar month in ``1``–``12`` (``I2``).

    Parameters
    ----------
    value : int or float
        Candidate month.

    Returns
    -------
    int
        Validated month.

    Raises
    ------
    ValueError
        From :func:`I_validateFunction`.
    """
    return I_validateFunction(value, 2, 1, 12)


def year_validateFunction(value):
    """
    Validate four-digit year (``I4``, minimum ``1992`` per BSRN spec).

    Parameters
    ----------
    value : int or float
        Candidate year.

    Returns
    -------
    int
        Validated year.

    Raises
    ------
    ValueError
        From :func:`I_validateFunction`.
    """
    return I_validateFunction(value, 4, 1992)


def day_validateFunction(value):
    """
    Validate day-of-month in ``1``–``31`` (``I2``).

    Parameters
    ----------
    value : int or float
        Candidate day.

    Returns
    -------
    int
        Validated day.

    Raises
    ------
    ValueError
        From :func:`I_validateFunction`.
    """
    return I_validateFunction(value, 2, 1, 31)


def hour_validateFunction(value):
    """
    Validate hour of day ``0``–``23`` (``I2``).

    Parameters
    ----------
    value : int or float
        Candidate hour.

    Returns
    -------
    int
        Validated hour.

    Raises
    ------
    ValueError
        From :func:`I_validateFunction`.
    """
    return I_validateFunction(value, 2, 0, 23)


def minute_validateFunction(value):
    """
    Validate minute ``0``–``59`` (``I2``).

    Parameters
    ----------
    value : int or float
        Candidate minute.

    Returns
    -------
    int
        Validated minute.

    Raises
    ------
    ValueError
        From :func:`I_validateFunction`.
    """
    return I_validateFunction(value, 2, 0, 59)


# --- Fixed-width strings (A5 … A80) ---


def A5_validateFunction(value):
    """
    Validate Fortran ``A5`` string field.

    Parameters
    ----------
    value : str
        Candidate string.

    Returns
    -------
    str
        Validated string.

    Raises
    ------
    ValueError
        From :func:`A_validateFunction`.
    """
    return A_validateFunction(value, 5)


def A15_validateFunction(value):
    """
    Validate Fortran ``A15`` string field.

    Parameters
    ----------
    value : str
        Candidate string.

    Returns
    -------
    str
        Validated string.

    Raises
    ------
    ValueError
        From :func:`A_validateFunction`.
    """
    return A_validateFunction(value, 15)


def A18_validateFunction(value):
    """
    Validate Fortran ``A18`` string field.

    Parameters
    ----------
    value : str
        Candidate string.

    Returns
    -------
    str
        Validated string.

    Raises
    ------
    ValueError
        From :func:`A_validateFunction`.
    """
    return A_validateFunction(value, 18)


def A25_validateFunction(value):
    """
    Validate Fortran ``A25`` string field.

    Parameters
    ----------
    value : str
        Candidate string.

    Returns
    -------
    str
        Validated string.

    Raises
    ------
    ValueError
        From :func:`A_validateFunction`.
    """
    return A_validateFunction(value, 25)


def A30_validateFunction(value):
    """
    Validate Fortran ``A30`` string field.

    Parameters
    ----------
    value : str
        Candidate string.

    Returns
    -------
    str
        Validated string.

    Raises
    ------
    ValueError
        From :func:`A_validateFunction`.
    """
    return A_validateFunction(value, 30)


def A38_validateFunction(value):
    """
    Validate Fortran ``A38`` string field.

    Parameters
    ----------
    value : str
        Candidate string.

    Returns
    -------
    str
        Validated string.

    Raises
    ------
    ValueError
        From :func:`A_validateFunction`.
    """
    return A_validateFunction(value, 38)


def A40_validateFunction(value):
    """
    Validate Fortran ``A40`` string field.

    Parameters
    ----------
    value : str
        Candidate string.

    Returns
    -------
    str
        Validated string.

    Raises
    ------
    ValueError
        From :func:`A_validateFunction`.
    """
    return A_validateFunction(value, 40)


def A80_validateFunction(value):
    """
    Validate Fortran ``A80`` string field.

    Parameters
    ----------
    value : str
        Candidate string.

    Returns
    -------
    str
        Validated string.

    Raises
    ------
    ValueError
        From :func:`A_validateFunction`.
    """
    return A_validateFunction(value, 80)


# --- Contact / network string patterns (telephone, TCP/IP, e-mail) ---


def telephone_validateFunction(value):
    """
    Validate telephone string (length + simple digit pattern).

    Parameters
    ----------
    value : str
        Candidate telephone text.

    Returns
    -------
    str
        Validated string.

    Raises
    ------
    ValueError
        From :func:`A_validateFunction` or if pattern does not match.
    """
    A_validateFunction(value, 20)
    telephoneRegex = r"^[+]?[\d\s]{8,20}$"
    if not re.search(telephoneRegex, value):
        raise ValueError("must have a telephone format")
    return value


def tcpip_validateFunction(value):
    """
    Validate IPv4-style TCP/IP string (``A15``).

    Parameters
    ----------
    value : str
        Candidate address.

    Returns
    -------
    str
        Validated string.

    Raises
    ------
    ValueError
        From :func:`A_validateFunction` or if pattern does not match.
    """
    A_validateFunction(value, 15)
    tcpipRegex = (
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    )
    if not re.search(tcpipRegex, value):
        raise ValueError("must have a TCP/IP format")
    return value


def email_validateFunction(value):
    """
    Validate e-mail string (``A50``).

    Parameters
    ----------
    value : str
        Candidate e-mail.

    Returns
    -------
    str
        Validated string.

    Raises
    ------
    ValueError
        From :func:`A_validateFunction` or if pattern does not match.
    """
    A_validateFunction(value, 50)
    emailRegex = r"^[\w\.-]+@[\w-]+\.[\w]{2,4}$"
    if not re.search(emailRegex, value):
        raise ValueError("must have a e-mail format")
    return value


# --- Encoded fields vs ``specs`` tables (A3–A7) ---


def quantities_validateFunction(value):
    """
    Validate radiation quantity code against ``specs.QUANTITIES``.

    Parameters
    ----------
    value : object
        Candidate code (must match a value in ``QUANTITIES``).

    Returns
    -------
    object
        ``value`` when valid.

    Raises
    ------
    ValueError
        If ``value`` is not in ``QUANTITIES.values()``.
    """
    if value not in QUANTITIES.values():
        raise ValueError("must be in A5 quantities (specs.QUANTITIES)")
    return value


def surface_validateFunction(value):
    """
    Validate surface type code against ``specs.SURFACES``.

    Parameters
    ----------
    value : object
        Candidate code.

    Returns
    -------
    object
        ``value`` when valid.

    Raises
    ------
    ValueError
        If ``value`` is not in ``SURFACES.values()``.
    """
    if value not in SURFACES.values():
        raise ValueError("must be in A4 surfaces (specs.SURFACES)")
    return value


def topography_validateFunction(value):
    """
    Validate topography code against ``specs.TOPOGRAPHIES``.

    Parameters
    ----------
    value : object
        Candidate code.

    Returns
    -------
    object
        ``value`` when valid.

    Raises
    ------
    ValueError
        If ``value`` is not in ``TOPOGRAPHIES.values()``.
    """
    if value not in TOPOGRAPHIES.values():
        raise ValueError("must be in A3 topographies (specs.TOPOGRAPHIES)")
    return value


def body_validateFunction(value):
    """
    Validate pyrgeometer body compensation code against ``specs.PYRGEOMETER_BODY``.

    Parameters
    ----------
    value : object
        Candidate code.

    Returns
    -------
    object
        ``value`` when valid.

    Raises
    ------
    ValueError
        If ``value`` is not in ``PYRGEOMETER_BODY.values()``.
    """
    if value not in PYRGEOMETER_BODY.values():
        raise ValueError("must be in A6 pyrgeometer body (specs.PYRGEOMETER_BODY)")
    return value


def dome_validateFunction(value):
    """
    Validate pyrgeometer dome compensation code against ``specs.PYRGEOMETER_DOME``.

    Parameters
    ----------
    value : object
        Candidate code.

    Returns
    -------
    object
        ``value`` when valid.

    Raises
    ------
    ValueError
        If ``value`` is not in ``PYRGEOMETER_DOME.values()``.
    """
    if value not in PYRGEOMETER_DOME.values():
        raise ValueError("must be in A7 pyrgeometer dome (specs.PYRGEOMETER_DOME)")
    return value


# --- Float formats F7.3 and F12.4 (underscores replace dots in Python names) ---


def F7_3_validateFunction(value):
    """
    Validate ``F7.3`` float field (underscore name avoids a dot in Python).

    Parameters
    ----------
    value : int or float
        Candidate value.

    Returns
    -------
    float
        Validated float.

    Raises
    ------
    ValueError
        From :func:`F_validateFunction`.
    """
    return F_validateFunction(value, 7, 3)


def F12_4_validateFunction(value):
    """
    Validate ``F12.4`` float field (underscore name avoids a dot in Python).

    Parameters
    ----------
    value : int or float
        Candidate value.

    Returns
    -------
    float
        Validated float.

    Raises
    ------
    ValueError
        From :func:`F_validateFunction`.
    """
    return F_validateFunction(value, 12, 4)


# --- Lat/lon (F7.3), zenith (I2), horizon comma lists, MM/DD/YY in A8 ---


def latitude_validateFunction(value):
    """
    Validate latitude string matching ``F7.3`` and regex pattern.

    Parameters
    ----------
    value : int or float or str
        Candidate latitude (degrees).

    Returns
    -------
    object
        ``value`` when valid.

    Raises
    ------
    ValueError
        From :func:`F_validateFunction` or if regex fails.
    """
    F_validateFunction(value, 7, 3)
    latitudeRegex = r"^(?:1[0-7][0-9]|[0-9]?[0-9])\.[0-9]{3}$"
    if not re.search(latitudeRegex, str(value)):
        raise ValueError("must have a latitude format")
    return value


def longitude_validateFunction(value):
    """
    Validate longitude string matching ``F7.3`` and regex pattern.

    Parameters
    ----------
    value : int or float or str
        Candidate longitude (degrees).

    Returns
    -------
    object
        ``value`` when valid.

    Raises
    ------
    ValueError
        From :func:`F_validateFunction` or if regex fails.
    """
    F_validateFunction(value, 7, 3)
    longitudeRegex = r"^(?:3[0-5][0-9]|2[0-9][0-9]|[01]?[0-9]?[0-9])\.[0-9]{3}$"
    if not re.search(longitudeRegex, str(value)):
        raise ValueError("must have a longitude format")
    return value


def date_validateFunction(value):
    """
    Validate ``MM/DD/YY`` date string (``A8``).

    Parameters
    ----------
    value : str
        Candidate date text.

    Returns
    -------
    str
        Validated string.

    Raises
    ------
    ValueError
        From :func:`A_validateFunction` or if ``strptime`` fails.
    """
    A_validateFunction(value, 8)
    try:
        datetime.strptime(value, "%m/%d/%y")
    except ValueError:
        raise ValueError('must have format "MM/DD/YY"')
    return value


def zenith_validateFunction(value):
    """
    Validate zenith angle ``0``–``90`` degrees (``I2``).

    Parameters
    ----------
    value : int or float
        Candidate zenith angle.

    Returns
    -------
    int
        Validated integer.

    Raises
    ------
    ValueError
        From :func:`I_validateFunction`.
    """
    return I_validateFunction(value, 2, 0, 90)


def azimuth_validateFunction(value):
    """
    Validate comma-separated azimuth list ``A1,A2,...`` (free ``A`` width).

    Parameters
    ----------
    value : str
        Candidate azimuth list string.

    Returns
    -------
    str
        Validated string.

    Raises
    ------
    ValueError
        From :func:`A_validateFunction` or if regex fails.
    """
    A_validateFunction(value)
    azimuthRegex = (
        r"^(?:(?:3[0-5][0-9]|2[0-9][0-9]|[01]?[0-9]?[0-9]),)*"
        r"(?:(?:3[0-5][0-9]|2[0-9][0-9]|[01]?[0-9]?[0-9])){1}$"
    )
    if not re.search(azimuthRegex, str(value)):
        raise ValueError("must have a azimuth format (A1,A2,...,An)")
    return value


def elevation_validateFunction(value):
    """
    Validate comma-separated horizon elevation list ``E1,E2,...``.

    Parameters
    ----------
    value : str
        Candidate elevation list string.

    Returns
    -------
    str
        Validated string.

    Raises
    ------
    ValueError
        From :func:`A_validateFunction` or if regex fails.
    """
    A_validateFunction(value)
    elevationRegex = r"^(?:(?:[0-8]?[0-9]),)*(?:(?:[0-8]?[0-9])){1}$"
    if not re.search(elevationRegex, str(value)):
        raise ValueError("must have a elevation format (E1,E2,...,En)")
    return value


# =============================================================================
# LR0100 / LR4000 minute-series fields
# =============================================================================

# ``yearMonth`` token (seven chars ``YYYY-MM``).
_YEAR_MONTH_RE = re.compile(r"^(?P<y>\d{4})-(?P<m>\d{2})$")


def genericValidateFunction(value):
    """
    Validate ``yearMonth`` token (``A7`` in LR0100 / LR4000: ``'YYYY-MM'``).

    Validates ``yearMonth`` (``'YYYY-MM'``) for minute logical records.

    Parameters
    ----------
    value : str
        Seven-character ``'YYYY-MM'`` string.

    Returns
    -------
    str
        The same token when valid.

    Raises
    ------
    ValueError
        If not a string, wrong pattern, or month outside ``1``–``12``.
    """
    if not isinstance(value, str):
        raise ValueError("must be a character string")
    m = _YEAR_MONTH_RE.match(value)
    if not m:
        raise ValueError("must match 'YYYY-MM' (7 characters)")
    month = int(m.group("m"))
    if month < 1 or month > 12:
        raise ValueError("month must be between 1 and 12")
    return value


def LR0100_validateFunction(value, yearMonth=None):
    """
    Ensure minute-series length matches the month when ``yearMonth`` is set.

    Minute vector checks for LR0100 columns (length vs. calendar month).

    Parameters
    ----------
    value : sequence
        Per-minute vector (e.g. ``list``, ``numpy.ndarray``, ``pandas.Series``).
    yearMonth : str or None, optional
        ``'YYYY-MM'`` token; if ``None``, skip length check.

    Returns
    -------
    sequence
        ``value`` unchanged when valid or when ``yearMonth`` is ``None``.

    Raises
    ------
    ValueError
        If ``len(value)`` does not equal days in month × 1440.
    """
    if yearMonth is None:
        return value
    y, mo = map(int, yearMonth.split("-"))
    n = calendar.monthrange(y, mo)[1] * 1440
    if len(value) != n:
        raise ValueError(f"The size of vector must be {n}")
    return value


def LR4000_validateFunction(value, yearMonth=None):
    """
    Ensure LR4000 minute-series length matches the month when ``yearMonth`` is set.

    Minute vector checks for LR4000 columns (length vs. calendar month).

    Parameters
    ----------
    value : sequence
        Per-minute vector (e.g. ``list``, ``numpy.ndarray``, ``pandas.Series``).
    yearMonth : str or None, optional
        ``'YYYY-MM'`` token; if ``None``, skip length check.

    Returns
    -------
    sequence
        ``value`` unchanged when valid or when ``yearMonth`` is ``None``.

    Raises
    ------
    ValueError
        If ``len(value)`` does not equal days in month × 1440.
    """
    if yearMonth is None:
        return value
    y, mo = map(int, yearMonth.split("-"))
    n = calendar.monthrange(y, mo)[1] * 1440
    if len(value) != n:
        raise ValueError(f"The size of vector must be {n}")
    return value