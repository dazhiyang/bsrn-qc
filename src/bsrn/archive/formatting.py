"""
Fortran-width formatting helpers for BSRN logical-record Pydantic models.
"""

import numpy as np
import pandas as pd


class ArchiveFormatMixin:
    """
    Shared ASCII formatting and mandatory-field checks for archive LRs.
    """

    def _field_meta(self, var_name):
        """
        Return archive metadata dict for one model field (LR_SPECS-shaped).

        Parameters
        ----------
        var_name : str
            Model field name.

        Returns
        -------
        dict
            Keys ``label``, ``format``, ``missing``, ``mandatory``, ``default``,
            ``validate_func``.
        """
        extra = type(self).model_fields[var_name].json_schema_extra
        if not isinstance(extra, dict):
            raise KeyError(var_name)
        return extra["archive"]

    @property
    def _params(self):
        """
        Field-name → spec mapping compatible with legacy ``LR_SPECS[lr]`` entries.
        """
        return {n: self._field_meta(n) for n in type(self).model_fields}

    def is_mandatory(self, var_name):
        """
        Return whether ``var_name`` is mandatory.

        Parameters
        ----------
        var_name : str
            Field name.

        Returns
        -------
        bool
            True if mandatory in archive metadata.
        """
        return self._field_meta(var_name)["mandatory"]

    def is_missing(self, var_name):
        """
        Return whether ``var_name`` is currently ``None``.

        Parameters
        ----------
        var_name : str
            Field name.

        Returns
        -------
        bool
            True if value is ``None``.
        """
        return getattr(self, var_name) is None

    def mandatories(self):
        """
        List mandatory field names.

        Returns
        -------
        list of str
            Names with ``mandatory: True``.
        """
        return [n for n in type(self).model_fields if self._field_meta(n)["mandatory"]]

    def missings(self):
        """
        List mandatory fields that are ``None``.

        Returns
        -------
        list of str
            Mandatory names still missing.
        """
        return [n for n in self.mandatories() if self.is_missing(n)]

    def is_values_missing(self):
        """
        Return whether any mandatory field is ``None``.

        Returns
        -------
        bool
            True if ``missings()`` is non-empty.
        """
        return len(self.missings()) > 0

    def stop_if_values_missing(self, message=""):
        """
        Raise if any mandatory field is missing.

        Parameters
        ----------
        message : str, optional
            Prefix before the missing-field list.

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If any mandatory value is ``None``.
        """
        if self.is_values_missing():
            tmp = ", ".join(self.missings())
            raise ValueError(f"{message}\n missing value(s) : {tmp}")

    @staticmethod
    def _coerce_stored_scalar(var_name, value, meta):
        """
        Coerce validated scalars to int/float for Fortran I/F formats.

        Parameters
        ----------
        var_name : str
            Field name (unused; kept for parity with legacy API).
        value : object
            Post-validation value.
        meta : dict
            Archive metadata with ``format`` key.

        Returns
        -------
        object
            Coerced scalar or original array-like / ``None``.
        """
        if value is None or isinstance(value, (pd.Series, np.ndarray, list, tuple)):
            return value
        fmt = meta.get("format", "")
        if fmt.startswith("I"):
            return int(round(float(value)))
        if fmt.startswith("F"):
            return float(value)
        return value

    def get_format_value(self, var_name):
        """
        Format a single field for ASCII output.

        Parameters
        ----------
        var_name : str
            Field name.

        Returns
        -------
        str or pandas.Series or numpy.ndarray
            Fortran-width string or filled series/array.
        """
        value = getattr(self, var_name)
        spec = self._field_meta(var_name)
        missing_code = spec.get("missing")

        if value is None:
            value = missing_code
            if str(value) in ["-999", "-999.9", "-99.9", "-99.99"]:
                value = float(value) if "." in str(value) else int(value)

        if isinstance(value, pd.Series):
            return value.fillna(missing_code)
        if isinstance(value, np.ndarray):
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

        Parameters
        ----------
        var_name : str
            Minute-series column name.

        Returns
        -------
        pandas.Series
            Object-dtype strings per row.

        Raises
        ------
        ValueError
            If format is not a supported vector I/F pattern.
        """
        spec = self._field_meta(var_name)
        miss = spec.get("missing")
        fmt = spec["format"]
        s = pd.Series(getattr(self, var_name))
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
