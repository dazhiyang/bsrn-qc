"""
Central BSRN dataset: one monthly station file as a typed, validated object.

Encapsulates station identity, resolved geographic metadata, and minute-
resolution data in a single Pydantic model. ``lr0100`` is the source of
truth for minute data; ``data`` is a computed ``DataFrame`` view.
Pipeline methods (solar position, clear-sky, QC) are chainable and
delegate to the existing standalone functions.

BSRN 中心数据集：将一个月度站点文件封装为带类型校验的对象。``lr0100``
为分钟数据源；``data`` 是由其派生的 ``DataFrame`` 视图。管线方法
（太阳位置、晴空、QC）可链式调用，底层委托给已有独立函数。
"""

from __future__ import annotations

import calendar
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from pydantic import (BaseModel, ConfigDict,
                      field_validator, model_validator)

from .archive.records_models import LR0100, LR0300, LR4000
from .constants import BSRN_STATIONS
from .io.reader import (
    _LR0100_MINUTE_COLS,
    _LR0300_MINUTE_COLS,
    _LR4000_MINUTE_COLS,
    read_bsrn_archive,
)

# Short aliases for LR0100 / LR0300 means, matching the column names
# expected by downstream functions (QC, clear-sky, visualization).
# LR0100 / LR0300 均值的短别名，与下游函数所用列名一致。
_LR0100_SHORT_ALIASES = {
    "ghi_avg": "ghi", "bni_avg": "bni",
    "dhi_avg": "dhi", "lwd_avg": "lwd",
    "temperature": "temp", "humidity": "rh",
}
_LR0300_SHORT_ALIASES = {
    "swu_avg": "swu", "lwu_avg": "lwu", "net_avg": "net",
}


class BSRNDataset(BaseModel):
    """
    One monthly BSRN dataset: station identity + minute data.

    单月 BSRN 数据集：站点标识 + 分钟级数据。

    Parameters
    ----------
    station_code : str
        Three-letter BSRN station code (must exist in
        ``BSRN_STATIONS``).
        三位 BSRN 站点代码（须在 ``BSRN_STATIONS`` 中）。
    year : int
        Four-digit measurement year.
        四位测量年份。
    month : int
        Measurement month (1--12).
        测量月份（1--12）。
    lr0100 : LR0100
        Validated LR0100 logical record (minute radiation and
        met data). This is the source of truth; ``data`` is
        derived from it.
        已校验的 LR0100 逻辑记录（分钟辐射与气象数据）。
        为数据源；``data`` 由其派生。
    lr0300 : LR0300 or None
        Validated LR0300 logical record (reflected / upward
        SW, LW, net radiation). Default ``None``.
        已校验的 LR0300 逻辑记录（反射/上行辐射）。
    lr4000 : LR4000 or None
        Validated LR4000 logical record (pyrgeometer minute
        data). Default ``None``.
        已校验的 LR4000 逻辑记录（长波表分钟数据）。
    station_name : str or None
        Resolved from ``BSRN_STATIONS`` when omitted.
        省略时从 ``BSRN_STATIONS`` 解析。
    lat : float or None
        Latitude (degrees); resolved from ``BSRN_STATIONS``.
        纬度（度）；从 ``BSRN_STATIONS`` 解析。
    lon : float or None
        Longitude (degrees); resolved from ``BSRN_STATIONS``.
        经度（度）；从 ``BSRN_STATIONS`` 解析。
    elev : float or None
        Elevation (m above sea level); resolved from
        ``BSRN_STATIONS``.
        海拔（米）；从 ``BSRN_STATIONS`` 解析。
    resolution : str or None
        Temporal resolution as a pandas frequency string
        (e.g. ``'1min'``, ``'3min'``, ``'5min'``). Defaults
        to ``'1min'``.
        时间分辨率（pandas 频率字符串）；默认 ``'1min'``。

    Raises
    ------
    ValueError
        If ``station_code`` is not in ``BSRN_STATIONS``,
        ``month`` is out of 1--12.
        ``station_code`` 不在 ``BSRN_STATIONS`` 或 ``month``
        不在 1--12 时。
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        frozen=False,
    )

    # Core (required): identity + minute radiation data.
    # 核心（必填）：站点标识 + 分钟辐射数据。
    station_code: str
    year: int
    month: int
    lr0100: LR0100

    # Optional logical records. / 可选逻辑记录。
    lr0300: Optional[LR0300] = None
    lr4000: Optional[LR4000] = None

    # Resolved from BSRN_STATIONS; users may override.
    # 从 BSRN_STATIONS 解析；用户可覆盖。
    station_name: str = None
    lat: float = None
    lon: float = None
    elev: float = None
    resolution: str = None

    # Case-insensitive; reject codes absent from the registry.
    # 大小写不敏感；拒绝不在注册表中的代码。
    @field_validator("station_code")
    @classmethod
    def _validate_station_code(cls, v):
        code = v.upper()
        if code not in BSRN_STATIONS:
            raise ValueError(
                f"unknown station code {v!r}; "
                f"not in BSRN_STATIONS"
            )
        return code

    # Calendar month bounds. / 日历月份范围。
    @field_validator("month")
    @classmethod
    def _validate_month(cls, v):
        if v < 1 or v > 12:
            raise ValueError(
                f"month must be 1--12, got {v}"
            )
        return v

    # Auto-fill geo metadata + infer resolution after construction.
    # 构造后自动填充地理元数据 + 推断时间分辨率。
    @model_validator(mode="after")
    def _resolve_metadata(self):
        """
        Fill ``station_name``, ``lat``, ``lon``, ``elev`` from
        ``BSRN_STATIONS`` when not explicitly provided.

        未显式传入时从 ``BSRN_STATIONS`` 填充站点名、经纬度、
        海拔。
        """
        meta = BSRN_STATIONS[self.station_code]
        if self.station_name is None:
            self.station_name = meta["name"]
        if self.lat is None:
            self.lat = meta["lat"]
        if self.lon is None:
            self.lon = meta["lon"]
        if self.elev is None:
            self.elev = meta["elev"]
        if self.resolution is None:
            self.resolution = self._infer_resolution()
        return self

    # ------------------------------------------------------------------ #
    #  Factory: delegates to io.reader for parsing                         #
    #  工厂方法：委托 io.reader 解析文件                                    #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_file(cls, path: str | Path) -> BSRNDataset:
        """
        Parse a BSRN ``.dat.gz`` station-to-archive file and return
        a fully validated ``BSRNDataset``.

        解析 BSRN ``.dat.gz`` 台站存档文件并返回完整校验的
        ``BSRNDataset``。

        Parameters
        ----------
        path : str or Path
            Path to the ``.dat.gz`` file (filename format
            ``XXXMMYY.dat.gz``).
            ``.dat.gz`` 文件路径（文件名格式
            ``XXXMMYY.dat.gz``）。

        Returns
        -------
        BSRNDataset

        Raises
        ------
        FileNotFoundError
            If *path* does not exist.
        ValueError
            If the filename cannot be parsed or no LR0100 block
            is found.
        """
        return cls(**read_bsrn_archive(path))

    def _infer_resolution(self):
        """
        Infer temporal resolution from ``lr0100`` vector length
        vs calendar month.

        根据 ``lr0100`` 向量长度与日历月推断时间分辨率。
        """
        y, m = map(int, self.lr0100.yearMonth.split("-"))
        ndays = calendar.monthrange(y, m)[1]
        expected_1min = ndays * 1440
        for col in _LR0100_MINUTE_COLS:
            vec = getattr(self.lr0100, col, None)
            if vec is not None:
                n = len(vec)
                if n == expected_1min:
                    return "1min"
                minutes_per_sample = expected_1min / n
                if minutes_per_sample == int(minutes_per_sample):
                    return f"{int(minutes_per_sample)}min"
                return f"{minutes_per_sample:.2f}min"
        return "1min"

    @property
    def data(self):
        """
        Minute-resolution DataFrame derived from ``lr0100``
        (and ``lr0300`` / ``lr4000`` when present).

        由 ``lr0100``（及 ``lr0300`` / ``lr4000``）派生的
        分钟分辨率 DataFrame。

        Returns
        -------
        pandas.DataFrame
            UTC ``DatetimeIndex``; columns are the non-None
            LR0100 / LR0300 / LR4000 minute fields.
            UTC ``DatetimeIndex``；列为非 None 的 LR0100 /
            LR0300 / LR4000 分钟字段。
        """
        y, m = map(int, self.lr0100.yearMonth.split("-"))
        first_vec = None
        for col in _LR0100_MINUTE_COLS:
            first_vec = getattr(self.lr0100, col, None)
            if first_vec is not None:
                break
        n = len(first_vec) if first_vec is not None else (
            calendar.monthrange(y, m)[1] * 1440
        )
        idx = pd.date_range(
            f"{y}-{m:02d}-01", periods=n,
            freq=self.resolution, tz="UTC",
        )
        cols = {}
        for col in _LR0100_MINUTE_COLS:
            vec = getattr(self.lr0100, col, None)
            if vec is not None:
                arr = np.asarray(vec)
                cols[col] = arr
                if col in _LR0100_SHORT_ALIASES:
                    cols[_LR0100_SHORT_ALIASES[col]] = arr
        if self.lr0300 is not None:
            for col in _LR0300_MINUTE_COLS:
                vec = getattr(self.lr0300, col, None)
                if vec is not None:
                    arr = np.asarray(vec)
                    cols[col] = arr
                    if col in _LR0300_SHORT_ALIASES:
                        cols[_LR0300_SHORT_ALIASES[col]] = arr
        if self.lr4000 is not None:
            for col in _LR4000_MINUTE_COLS:
                vec = getattr(self.lr4000, col, None)
                if vec is not None:
                    cols[col] = np.asarray(vec)
        return pd.DataFrame(cols, index=idx)
