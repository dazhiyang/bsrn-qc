"""
BSRN archiving: logical-record specs, validation, and R-style helpers.

R reference layout under ``data/R``:

- ``0_data.R`` — table placeholders (A1–A7); Python: ``specs``, ``stations``, ``mappings``
- ``1_utils.R`` — calendar helpers and bindings; Python: ``utils``, ``api`` (base + ``get_azimuth_elevation``)
- ``0_bsrnFormats_*.R`` — format strings; Python: ``formatter`` (wrappers) + ``api`` (implementations)
- ``1_validateFunc_*.R`` — Python: ``validation``
- ``2_R6Class_*.R`` — Python: ``api`` (``LR0001`` … ``LR4000``)

BSRN 存档：逻辑记录规范、校验与 R 风格辅助函数。上述 R 文件与 Python 子模块对应关系见源码注释。
"""

from . import api, formatter, mappings, specs, stations, utils, validation
from .api import (
    BSRNRecord,
    LR0001,
    LR0002,
    LR0003,
    LR0004,
    LR0005,
    LR0006,
    LR0007,
    LR0008,
    LR0100,
    LR4000,
    LR4000CONST,
    get_azimuth_elevation,
    number_of_days,
    number_of_minutes,
)
from .formatter import (
    lr0001_format,
    lr0002_format,
    lr0004_format,
    lr0100_data_format,
    lr4000_data_format,
)
from .mappings import (
    PYRGEOMETER_BODY,
    PYRGEOMETER_DOME,
    QUANTITIES,
    SURFACES,
    TOPOGRAPHIES,
)
from .specs import LR_SPECS
from .stations import STATION_METADATA

__all__ = [
    "LR_SPECS",
    "STATION_METADATA",
    "TOPOGRAPHIES",
    "SURFACES",
    "QUANTITIES",
    "PYRGEOMETER_BODY",
    "PYRGEOMETER_DOME",
    "BSRNRecord",
    "LR0001",
    "LR0002",
    "LR0003",
    "LR0004",
    "LR0005",
    "LR0006",
    "LR0007",
    "LR0008",
    "LR0100",
    "LR4000",
    "LR4000CONST",
    "get_azimuth_elevation",
    "number_of_days",
    "number_of_minutes",
    "lr0001_format",
    "lr0002_format",
    "lr0004_format",
    "lr0100_data_format",
    "lr4000_data_format",
    "api",
    "formatter",
    "mappings",
    "specs",
    "stations",
    "utils",
    "validation",
]
