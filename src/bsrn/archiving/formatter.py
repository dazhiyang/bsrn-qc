"""
BSRN ASCII line builders (R ``0_bsrnFormats_headers.R`` + ``0_bsrnFormats_datas.R``).

These call the corresponding ``LR*.get_bsrn_format`` implementations in ``api`` so
there is a single formatting implementation.

对应 R 的 ``0_bsrnFormats_headers.R`` 与 ``0_bsrnFormats_datas.R``。
通过调用 ``api`` 中各类 ``get_bsrn_format``，保持单一实现来源。
"""

import pandas as pd

from .api import LR0001, LR0002, LR0003, LR0004, LR0100, LR4000


def lr0001_format(v, listSensor=None):
    """Wrapper for ``lr0001GetBsrnFormat`` / ``LR0001.get_bsrn_format``."""
    if listSensor is None:
        listSensor = ["2", "3", "4", "5", "21", "22", "23"]
    return LR0001(**v).get_bsrn_format(listSensor=listSensor)


def lr0002_format(v, _scientistChange, _deputyChange):
    """
    Wrapper for ``lr0002GetBsrnFormat``. Flags are part of ``v``; parameters kept for
    API compatibility with older call sites.
    兼容旧签名的占位参数；实际以 ``v`` 中的布尔字段为准。
    """
    return LR0002(**v).get_bsrn_format()


def lr0004_format(v, _stationDescChange, _horizonChange, azimuth, elevation):
    """
    Wrapper for ``lr0004GetBsrnFormat`` using ``stationDescChangeMinute`` /
    ``horizonChangeMinute`` keys (R ``...Minute``).
    """
    merged = {**v, "azimuth": azimuth, "elevation": elevation}
    return LR0004(**merged).get_bsrn_format()


def lr0100_data_format(df, changed, yearMonth):
    """Wrapper for ``lr0100GetBsrnFormat`` with a columnar ``DataFrame``."""
    kwargs = {c: df[c] for c in df.columns}
    kwargs["yearMonth"] = yearMonth
    return LR0100(**kwargs).get_bsrn_format(changed=changed)


def lr4000_data_format(df, changed, yearMonth):
    """Wrapper for ``lr4000GetBsrnFormat`` with a columnar ``DataFrame``."""
    kwargs = {c: df[c] for c in df.columns}
    kwargs["yearMonth"] = yearMonth
    return LR4000(**kwargs).get_bsrn_format(changed=changed)
