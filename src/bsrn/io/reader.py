"""
BSRN ``.dat.gz`` archive reader — returns validated Pydantic LR models.

The single public entry point is :func:`read_bsrn_archive`, which opens
the file once, locates ``*U`` / ``*C`` record markers, and builds
:class:`~bsrn.archive.records_models.LR0100`,
:class:`~bsrn.archive.records_models.LR0300`, and
:class:`~bsrn.archive.records_models.LR4000` instances.
"""

import gzip
from pathlib import Path

import numpy as np

from bsrn.archive.records_models import LR0100, LR0300, LR4000

_LR0100_MINUTE_COLS = (
    "ghi_avg", "ghi_std", "ghi_min", "ghi_max",
    "bni_avg", "bni_std", "bni_min", "bni_max",
    "dhi_avg", "dhi_std", "dhi_min", "dhi_max",
    "lwd_avg", "lwd_std", "lwd_min", "lwd_max",
    "temperature", "humidity", "pressure",
)

_LR0300_MINUTE_COLS = (
    "swu_avg", "swu_std", "swu_min", "swu_max",
    "lwu_avg", "lwu_std", "lwu_min", "lwu_max",
    "net_avg", "net_std", "net_min", "net_max",
)

_LR4000_MINUTE_COLS = (
    "domeT1_down", "domeT2_down", "domeT3_down",
    "bodyT_down", "longwave_down",
    "domeT1_up", "domeT2_up", "domeT3_up",
    "bodyT_up", "longwave_up",
)

_SUPPORTED_LRS = frozenset(("lr0100", "lr0300", "lr4000"))


# ------------------------------------------------------------------ #
#  Public API                                                          #
# ------------------------------------------------------------------ #

def read_bsrn_archive(path, include_lrs=None, strict=False):
    """
    Parse a BSRN ``.dat.gz`` station-to-archive file.

    Parameters
    ----------
    path : str or Path
        Path to the ``.dat.gz`` file (filename format
        ``XXXMMYY.dat.gz``).
    include_lrs : sequence of str or 'all', optional
        Logical records to parse. Currently supported:
        ``'lr0100'``, ``'lr0300'``, ``'lr4000'``. Default ``None``
        parses all three.
    strict : bool, optional
        Controls optional-LR parse failures. If ``True``, malformed
        optional LR blocks raise ``ValueError``. If ``False`` (default),
        malformed optional LRs are returned as ``None``. Missing optional
        LR blocks are returned as ``None`` in both modes.

    Returns
    -------
    dict
        Keys: ``station_code``, ``year``, ``month``, ``lr0100``,
        ``lr0300`` (or ``None``), ``lr4000`` (or ``None``),
        ``metadata_lrs`` (currently empty dict placeholder).
        Suitable for unpacking into
        :class:`~bsrn.dataset.BSRNDataset`.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    ValueError
        If the filename cannot be parsed, requested LR codes are
        unsupported, ``include_lrs`` omits ``'lr0100'``, or no lr0100
        block is found.
    """
    if include_lrs is None or include_lrs == "all":
        wanted_lrs = set(_SUPPORTED_LRS)
    else:
        if isinstance(include_lrs, str):
            include_lrs = [include_lrs]
        wanted_lrs = {str(lr).strip().lower() for lr in include_lrs}
        invalid = sorted(wanted_lrs - _SUPPORTED_LRS)
        if invalid:
            supported = ", ".join(sorted(_SUPPORTED_LRS))
            got = ", ".join(invalid)
            raise ValueError(
                f"Unsupported include_lrs: {got}. "
                f"Supported LR codes are: {supported}."
            )

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    fname = path.name
    station_code = fname[:3]
    yy = int(fname[5:7])
    year = (1900 + yy) if yy >= 91 else (2000 + yy)
    month = int(fname[3:5])
    year_month = f"{year}-{month:02d}"

    with gzip.open(path, "rt", encoding="ascii") as f:
        lines = f.readlines()

    # Collect LR blocks once, keyed by LR code.
    lr_blocks = _collect_lr_blocks(lines)

    # -- LR0100 (required by BSRNDataset) --
    if "lr0100" not in wanted_lrs:
        raise ValueError("lr0100 is required in include_lrs.")
    raw0100 = lr_blocks.get("lr0100")
    if raw0100 is None:
        raise ValueError(f"LR0100 record not found in {fname}")
    lr0100 = _parse_lr0100(raw0100, year_month)

    # -- LR0300 (optional, 1-line per minute) --
    lr0300 = None
    if "lr0300" in wanted_lrs:
        raw0300 = lr_blocks.get("lr0300")
        lr0300 = _parse_optional_lr(
            raw0300, year_month, _parse_lr0300, "lr0300", strict,
        )

    # -- LR4000 (optional, 1-line per minute) --
    lr4000 = None
    if "lr4000" in wanted_lrs:
        raw4000 = lr_blocks.get("lr4000")
        lr4000 = _parse_optional_lr(
            raw4000, year_month, _parse_lr4000, "lr4000", strict,
        )

    return dict(
        station_code=station_code,
        year=year,
        month=month,
        lr0100=lr0100,
        lr0300=lr0300,
        lr4000=lr4000,
        metadata_lrs={},
    )


# ------------------------------------------------------------------ #
#  Private line-parsers                                                #
# ------------------------------------------------------------------ #


def _parse_optional_lr(raw_lines, year_month, parser, lr_code, strict):
    """Parse optional LR block; suppress parse errors unless strict=True."""
    if not raw_lines:
        return None
    try:
        return parser(raw_lines, year_month)
    except Exception as exc:
        if strict:
            raise ValueError(
                f"Failed to parse {lr_code} with strict=True."
            ) from exc
        return None


def _collect_lr_blocks(lines):
    """Collect first LR block lines for each marker key (e.g., lr0100)."""
    markers = [
        (i, lines[i].strip())
        for i in range(len(lines))
        if lines[i].startswith("*")
    ]

    lr_blocks = {}
    for idx, (pos, marker) in enumerate(markers):
        lr_key = f"lr{marker[-4:]}"
        if lr_key in lr_blocks:
            continue
        start = pos + 1
        end = (
            markers[idx + 1][0]
            if idx + 1 < len(markers)
            else len(lines)
        )
        lr_blocks[lr_key] = lines[start:end]
    return lr_blocks

def _parse_lr0100(raw_lines, year_month):
    """
    Build ``LR0100`` from raw archive text (2-line blocks).

    LR0100 line layout (Fortran fixed-width, whitespace-delimited):
      Line 1: day min ghi_avg ghi_std ghi_min ghi_max
               bni_avg bni_std bni_min bni_max
      Line 2: dhi_avg dhi_std dhi_min dhi_max
               lwd_avg lwd_std lwd_min lwd_max
               temperature humidity pressure
    """
    if len(raw_lines) % 2 != 0:
        raw_lines = raw_lines[:-1]
    vecs = {col: [] for col in _LR0100_MINUTE_COLS}
    for i in range(0, len(raw_lines), 2):
        t1 = raw_lines[i].split()
        t2 = raw_lines[i + 1].split()
        if len(t1) < 10 or len(t2) < 11:
            continue
        vecs["ghi_avg"].append(float(t1[2]))
        vecs["ghi_std"].append(float(t1[3]))
        vecs["ghi_min"].append(float(t1[4]))
        vecs["ghi_max"].append(float(t1[5]))
        vecs["bni_avg"].append(float(t1[6]))
        vecs["bni_std"].append(float(t1[7]))
        vecs["bni_min"].append(float(t1[8]))
        vecs["bni_max"].append(float(t1[9]))
        vecs["dhi_avg"].append(float(t2[0]))
        vecs["dhi_std"].append(float(t2[1]))
        vecs["dhi_min"].append(float(t2[2]))
        vecs["dhi_max"].append(float(t2[3]))
        vecs["lwd_avg"].append(float(t2[4]))
        vecs["lwd_std"].append(float(t2[5]))
        vecs["lwd_min"].append(float(t2[6]))
        vecs["lwd_max"].append(float(t2[7]))
        vecs["temperature"].append(float(t2[8]))
        vecs["humidity"].append(float(t2[9]))
        vecs["pressure"].append(float(t2[10]))
    return LR0100(
        yearMonth=year_month,
        **{k: np.array(v) for k, v in vecs.items()},
    )


def _parse_lr0300(raw_lines, year_month):
    """
    Build ``LR0300`` from raw archive text (1-line per minute).

    Line layout: day min swu(avg std min max) lwu(…) net(…)
    """
    vecs = {col: [] for col in _LR0300_MINUTE_COLS}
    for line in raw_lines:
        t = line.split()
        if len(t) < 14:
            continue
        vecs["swu_avg"].append(float(t[2]))
        vecs["swu_std"].append(float(t[3]))
        vecs["swu_min"].append(float(t[4]))
        vecs["swu_max"].append(float(t[5]))
        vecs["lwu_avg"].append(float(t[6]))
        vecs["lwu_std"].append(float(t[7]))
        vecs["lwu_min"].append(float(t[8]))
        vecs["lwu_max"].append(float(t[9]))
        vecs["net_avg"].append(float(t[10]))
        vecs["net_std"].append(float(t[11]))
        vecs["net_min"].append(float(t[12]))
        vecs["net_max"].append(float(t[13]))
    if not vecs["swu_avg"]:
        return None
    return LR0300(
        yearMonth=year_month,
        **{k: np.array(v) for k, v in vecs.items()},
    )


def _parse_lr4000(raw_lines, year_month):
    """
    Build ``LR4000`` from raw archive text (1-line per minute).

    Line layout: day min domeT1-3_down bodyT_down lw_down
                 domeT1-3_up bodyT_up lw_up
    """
    vecs = {col: [] for col in _LR4000_MINUTE_COLS}
    for line in raw_lines:
        t = line.split()
        if len(t) < 12:
            continue
        try:
            vecs["domeT1_down"].append(float(t[2]))
            vecs["domeT2_down"].append(float(t[3]))
            vecs["domeT3_down"].append(float(t[4]))
            vecs["bodyT_down"].append(float(t[5]))
            vecs["longwave_down"].append(float(t[6]))
            vecs["domeT1_up"].append(float(t[7]))
            vecs["domeT2_up"].append(float(t[8]))
            vecs["domeT3_up"].append(float(t[9]))
            vecs["bodyT_up"].append(float(t[10]))
            vecs["longwave_up"].append(float(t[11]))
        except ValueError:
            continue
    if not vecs["domeT1_down"]:
        return None
    return LR4000(
        yearMonth=year_month,
        **{k: np.array(v) for k, v in vecs.items()},
    )
