"""
BSRN station-to-archive base record class (R ``1_utils.R`` + R6 generics).

``BSRNRecord`` holds assignment validation and Fortran padding; concrete logical-record
classes (``LR0001``, …) and ``get_bsrn_format`` output live in ``formatter``.

BSRN 站点存档基类（``1_utils.R`` 与 R6 泛型逻辑）。
``BSRNRecord`` 负责赋值校验与 Fortran 填充；具体 ``LR0001`` 等及 ``get_bsrn_format`` 在 ``formatter``。

Field rules come from ``specs.LR_SPECS``. BSRN on-disk column names (e.g. ``ghi_avg``)
are format identifiers, distinct from QC radiometry symbols elsewhere in ``bsrn``.
字段规则见 ``specs.LR_SPECS``；磁盘列名（如 ``ghi_avg``）为格式标识。
"""

import numpy as np
import pandas as pd
from .specs import LR_SPECS

# =============================================================================
# TRANSLATION OF: 1_utils.R
# =============================================================================


def get_azimuth_elevation(azimuth=None, elevation=None):
    """
    Format horizon azimuth/elevation lists for LR0004.

    Translates from R function ``getAzimuthElevation`` (``1_utils.R``).
    对应 R 函数 ``getAzimuthElevation``（``1_utils.R``）。

    Parameters
    ----------
    azimuth : str or sequence of float, optional
        Comma-separated string ``A1,A2,...`` or sequence of degrees from north.
        逗号分隔字符串 ``A1,A2,...`` 或从正北起算的方位角序列。
    elevation : str or sequence of float, optional
        Comma-separated string ``E1,E2,...`` or sequence of elevation angles.
        逗号分隔字符串 ``E1,E2,...`` 或高度角序列。

    Returns
    -------
    str
        Fixed-width lines of ``az el`` pairs, or ``  -1 -1`` when inputs are absent.
        固定宽度 ``az el`` 行；无输入时为 ``  -1 -1``。

    Raises
    ------
    ValueError
        If ``azimuth`` and ``elevation`` lengths differ.
        ``azimuth`` 与 ``elevation`` 长度不一致时。
    """
    if azimuth is None or elevation is None:
        return "  -1 -1"

    az = [float(x) for x in azimuth.split(",")] if isinstance(azimuth, str) else list(azimuth)
    el = [float(x) for x in elevation.split(",")] if isinstance(elevation, str) else list(elevation)

    if len(az) != len(el):
        raise ValueError("azimuth and elevation must have same size")

    n = len(az)
    pad = 11 - (n % 11) if n % 11 != 0 else 0
    az_padded = az + [-1] * pad
    el_padded = el + [-1] * pad

    rows = []
    for i in range(0, len(az_padded), 11):
        line = " ".join(
            [f"{a:>3.0f} {e:>2.0f}" for a, e in zip(az_padded[i : i + 11], el_padded[i : i + 11])]
        )
        rows.append(f" {line}")
    return "\n".join(rows)


class BSRNRecord:
    """
    Base record with R6-style validation and Fortran-width formatting.

    Translates from R generics in ``1_utils.R`` (``genericInitialize``, ``rw_ActiveBinding``,
    ``genericIsMandatory``, ``genericIsMissing``, ``genericPrint``, etc.).
    对应 ``1_utils.R`` 中 R6 泛型（``genericInitialize``、``rw_ActiveBinding`` 等）。
    """

    def __init__(self, lr_code, **kwargs):
        """
        Initialize fields from ``LR_SPECS[lr_code]`` defaults and ``kwargs``.

        Translates from R ``genericInitialize`` (``1_utils.R``).
        对应 R ``genericInitialize``（``1_utils.R``）。

        Parameters
        ----------
        lr_code : str
            Logical record key (e.g. ``"LR0001"``).
            逻辑记录键（如 ``"LR0001"``）。
        **kwargs
            Field overrides; names must exist in ``LR_SPECS[lr_code]``.
            字段覆盖；名称须属于 ``LR_SPECS[lr_code]``。

        Returns
        -------
        None

        Raises
        ------
        ValueError
            From field validators when a value fails ``validate_func``.
            字段 ``validate_func`` 校验失败时。
        """
        # Bypass custom __setattr__ for initialization
        super().__setattr__("_lr_code", lr_code)
        super().__setattr__("_params", LR_SPECS[lr_code])
        super().__setattr__("_private", {})

        for var_name, spec in self._params.items():
            self._private[var_name] = spec.get("default")

        for var_name, value in kwargs.items():
            setattr(self, var_name, value)

    def __setattr__(self, name, value):
        """
        Validate and store a logical-record field.

        Translates from R ``rw_ActiveBinding`` (validates on assignment; ``1_utils.R``).
        对应 R ``rw_ActiveBinding``（赋值时校验；``1_utils.R``）。

        Parameters
        ----------
        name : str
            Field name defined in ``LR_SPECS``.
            ``LR_SPECS`` 中定义的字段名。
        value : object
            New value; ``None`` skips validation and clears optional semantics.
            新值；``None`` 表示跳过校验并清空（按可选语义）。

        Returns
        -------
        None

        Raises
        ------
        ValueError
            When the named ``validate_func`` rejects ``value``.
            对应 ``validate_func`` 拒绝该 ``value`` 时。
        """
        if name in ["_lr_code", "_params", "_private"]:
            super().__setattr__(name, value)
        elif name in self._params:
            spec = self._params[name]
            val_func_name = spec["validate_func"]

            if value is not None:
                import bsrn.archive.validation as val_module

                val_func = getattr(val_module, val_func_name, lambda x: x)
                try:
                    if val_func_name in (
                        "LR0100_validateFunction",
                        "LR4000_validateFunction",
                    ):
                        ym = self._private.get("yearMonth")
                        clean_val = val_func(value, yearMonth=ym)
                    else:
                        clean_val = val_func(value)
                    clean_val = self._coerce_stored_scalar(name, clean_val)
                except Exception as e:
                    raise ValueError(f"{name}\n {str(e)}")
                self._private[name] = clean_val
            else:
                self._private[name] = None
        else:
            super().__setattr__(name, value)

    def __getattr__(self, name):
        """
        Return a stored field from the private mapping.

        Translates from R active-binding field access (``1_utils.R``).
        对应 R 活动绑定字段读取（``1_utils.R``）。

        Parameters
        ----------
        name : str
            Field name.
            字段名。

        Returns
        -------
        object
            Stored value for ``name``.
            ``name`` 对应存储值。

        Raises
        ------
        AttributeError
            If ``name`` is not a defined field.
            ``name`` 非已定义字段时。
        """
        if name in self._private:
            return self._private[name]
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")

    def is_mandatory(self, var_name):
        """
        Return whether ``var_name`` is mandatory for this logical record.

        Translates from R ``genericIsMandatory`` (``1_utils.R``).
        对应 R ``genericIsMandatory``（``1_utils.R``）。

        Parameters
        ----------
        var_name : str
            Field name.
            字段名。

        Returns
        -------
        bool
            ``True`` if mandatory in ``LR_SPECS``.
            在 ``LR_SPECS`` 中为必填时 ``True``。
        """
        return self._params[var_name]["mandatory"]

    def is_missing(self, var_name):
        """
        Return whether ``var_name`` is currently ``None``.

        Translates from R ``genericIsMissing`` (``1_utils.R``).
        对应 R ``genericIsMissing``（``1_utils.R``）。

        Parameters
        ----------
        var_name : str
            Field name.
            字段名。

        Returns
        -------
        bool
            ``True`` if the stored value is ``None``.
            存储值为 ``None`` 时 ``True``。
        """
        return self._private[var_name] is None

    def mandatories(self):
        """
        List mandatory field names for this logical record.

        Translates from R ``genericMandatories`` (``1_utils.R``).
        对应 R ``genericMandatories``（``1_utils.R``）。

        Returns
        -------
        list of str
            Names with ``mandatory: True`` in ``LR_SPECS``.
            ``LR_SPECS`` 中 ``mandatory: True`` 的名称列表。
        """
        return [name for name, spec in self._params.items() if spec["mandatory"]]

    def missings(self):
        """
        List mandatory fields that are currently ``None``.

        Translates from R ``genericMissings`` (``1_utils.R``).
        对应 R ``genericMissings``（``1_utils.R``）。

        Returns
        -------
        list of str
            Mandatory field names still missing.
            仍为空的必填字段名。
        """
        return [name for name in self.mandatories() if self.is_missing(name)]

    def is_values_missing(self):
        """
        Return whether any mandatory field is ``None``.

        Translates from R ``genericIsValuesMissing`` (``1_utils.R``).
        对应 R ``genericIsValuesMissing``（``1_utils.R``）。

        Returns
        -------
        bool
            ``True`` if ``missings()`` is non-empty.
            ``missings()`` 非空时 ``True``。
        """
        return len(self.missings()) > 0

    def set_default(self, var_name):
        """
        Reset ``var_name`` to its ``LR_SPECS`` default.

        Translates from R ``genericSetDefault`` (``1_utils.R``).
        对应 R ``genericSetDefault``（``1_utils.R``）。

        Parameters
        ----------
        var_name : str
            Field name.
            字段名。

        Returns
        -------
        None
        """
        self._private[var_name] = self._params[var_name]["default"]

    def stop_if_values_missing(self, message=""):
        """
        Raise if any mandatory field is missing.

        Translates from R ``stopIfValuesMissing`` (``1_utils.R``).
        对应 R ``stopIfValuesMissing``（``1_utils.R``）。

        Parameters
        ----------
        message : str, optional
            Prefix text before the missing-field list.
            缺失字段列表前的提示前缀。

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If ``is_values_missing()`` is ``True``.
            ``is_values_missing()`` 为 ``True`` 时。
        """
        if self.is_values_missing():
            tmp = ", ".join(self.missings())
            raise ValueError(f"{message}\n missing value(s) : {tmp}")

    def _coerce_stored_scalar(self, var_name, value):
        """
        Coerce validated scalars to ``int`` / ``float`` to match Fortran ``I`` / ``F``.

        Supports R-style storage after validation (same intent as R ``1_utils.R`` helpers).
        校验后按 Fortran 类型存储，与 R ``1_utils.R`` 辅助逻辑一致。

        Parameters
        ----------
        var_name : str
            Field name whose ``format`` drives coercion.
            以 ``format`` 决定强制转换的字段名。
        value : object
            Post-validation value (may be array-like).
            校验后的值（可为类数组）。

        Returns
        -------
        object
            Coerced scalar, or ``value`` unchanged if array-like or ``None``.
            标量经转换；类数组或 ``None`` 则原样返回。
        """
        if value is None or isinstance(value, (pd.Series, np.ndarray, list, tuple)):
            return value
        fmt = self._params[var_name].get("format", "")
        if fmt.startswith("I"):
            return int(round(float(value)))
        if fmt.startswith("F"):
            return float(value)
        return value

    def __str__(self):
        """
        Human-readable dump of mandatory/optional fields.

        Translates from R ``genericPrint`` (``1_utils.R``).
        对应 R ``genericPrint``（``1_utils.R``）。

        Returns
        -------
        str
            Multi-line summary; warns when mandatory values are missing.
            多行摘要；必填缺失时含警告。
        """
        msg = "WARNING : The object is missing value(s).\n" if self.is_values_missing() else ""
        m_vars = self.mandatories()
        for v, spec in self._params.items():
            value = self._private[v]
            if isinstance(value, (list, np.ndarray, pd.Series)) and len(value) > 1:
                value = f"{value[0]} ..."
            req = "[mandatory]" if v in m_vars else "[optional]"
            msg += f"{req} {v} ({spec['label']}) : {value}\n"
        return msg

    def get_format_value(self, var_name):
        """
        Format a single field for ASCII output.

        Translates from R ``getFormatValue`` (Fortran padding logic; ``1_utils.R``).
        对应 R ``getFormatValue``（Fortran 填充；``1_utils.R``）。

        Parameters
        ----------
        var_name : str
            Field name in ``LR_SPECS``.
            ``LR_SPECS`` 中的字段名。

        Returns
        -------
        str or pandas.Series or numpy.ndarray
            Fortran-width string for scalars; filled series/array for vector fields.
            标量为 Fortran 宽度字符串；向量字段为填充后的 Series/ndarray。
        """
        value = self._private.get(var_name)
        spec = self._params[var_name]
        missing_code = spec.get("missing")

        if value is None:
            value = missing_code
            if str(value) in ["-999", "-999.9", "-99.9", "-99.99"]:
                value = float(value) if "." in str(value) else int(value)

        if isinstance(value, pd.Series):
            return value.fillna(missing_code)
        elif isinstance(value, np.ndarray):
            return np.where(np.isnan(value), missing_code, value)

        fmt = spec["format"]
        if value is None:
            return ""

        if fmt == "L":
            return "Y" if value else "N"
        if fmt.startswith("I"):
            w = int(fmt[1:])
            return f"{int(value):>{w}d}"
        if fmt.startswith("F"):
            w, d = map(int, fmt[1:].split("."))
            return f"{float(value):>{w}.{d}f}"
        if fmt.startswith("A"):
            w = int(fmt[1:]) if len(fmt) > 1 else 80
            if fmt == "A":
                w = 80
            s = str(value)
            return f"{s:<{w}}"[:w]
        return str(value)

    def _format_series_field(self, var_name):
        """
        One Fortran-width string per row for vector LR0100 / LR4000 columns.

        Used by LR0100 / LR4000 ``getBsrnFormat`` data paths (R ``2_R6Class_datas.R``).
        供 LR0100 / LR4000 ``getBsrnFormat`` 数据路径使用（``2_R6Class_datas.R``）。

        Parameters
        ----------
        var_name : str
            Minute-series column name (``format`` is ``I`` or ``F``).
            分钟序列列名（``format`` 为 ``I`` 或 ``F``）。

        Returns
        -------
        pandas.Series
            Object dtype strings per timestamp, aligned to the private series.
            与私有序列对齐的每时刻 Fortran 字符串。

        Raises
        ------
        ValueError
            If ``format`` is not a supported vector ``I``/``F`` pattern.
            ``format`` 非支持的向量 ``I``/``F`` 模式时。
        """
        spec = self._params[var_name]
        miss = spec.get("missing")
        fmt = spec["format"]
        s = pd.Series(self._private[var_name])
        if miss is not None:
            s = s.fillna(miss)
        if fmt.startswith("I"):
            w = int(fmt[1:])
            arr = np.rint(s.to_numpy(dtype=np.float64))
            return pd.Series([f"{int(v):>{w}d}" for v in arr])
        if fmt.startswith("F"):
            fw, fd = fmt[1:].split(".")
            w, d = int(fw), int(fd)
            arr = s.to_numpy(dtype=np.float64)
            return pd.Series([f"{float(v):>{w}.{d}f}" for v in arr])
        raise ValueError(f"Unsupported vector format {fmt!r} for {var_name}")
