"""
BSRN station-to-archive logical records (R ``1_utils.R`` + ``2_R6Class_headers.R`` + ``2_R6Class_datas.R``).

Field rules come from ``specs.LR_SPECS``. BSRN on-disk column names (e.g. ``global2_avg``)
are format identifiers, distinct from QC radiometry symbols elsewhere in ``bsrn``.

BSRN 站点存档逻辑记录（对应 R 的 ``1_utils.R`` 与 ``2_R6Class_*.R``）。
字段规则见 ``specs.LR_SPECS``；磁盘列名（如 ``global2_avg``）为格式标识，与 ``bsrn`` 其他模块的辐射符号表不同。
"""

import textwrap
import numpy as np
import pandas as pd
from .specs import LR_SPECS
from .utils import number_of_days, number_of_minutes
from .validation import *

# =============================================================================
# TRANSLATION OF: 1_utils.R
# =============================================================================

def get_azimuth_elevation(azimuth=None, elevation=None):
    """Translates getAzimuthElevation"""
    if azimuth is None or elevation is None:
        return "  -1 -1"
    
    az = [float(x) for x in azimuth.split(',')] if isinstance(azimuth, str) else list(azimuth)
    el = [float(x) for x in elevation.split(',')] if isinstance(elevation, str) else list(elevation)
    
    if len(az) != len(el):
        raise ValueError("azimuth and elevation must have same size")
        
    n = len(az)
    pad = 11 - (n % 11) if n % 11 != 0 else 0
    az_padded = az + [-1] * pad
    el_padded = el + [-1] * pad
    
    rows = []
    for i in range(0, len(az_padded), 11):
        line = " ".join([f"{a:>3.0f} {e:>2.0f}" for a, e in zip(az_padded[i:i+11], el_padded[i:i+11])])
        rows.append(f" {line}")
    return "\n".join(rows)

class BSRNRecord:
    """
    Base class replicating the dynamic R6 generic functions.
    Translates: genericInitialize, rw_ActiveBinding, genericIsMandatory, 
    genericIsMissing, genericPrint, etc.
    """
    def __init__(self, lr_code, **kwargs):
        # Bypass custom __setattr__ for initialization
        super().__setattr__('_lr_code', lr_code)
        super().__setattr__('_params', LR_SPECS[lr_code])
        super().__setattr__('_private', {})

        # Set default values
        for var_name, spec in self._params.items():
            self._private[var_name] = spec.get('default')

        # Override defaults with provided kwargs
        for var_name, value in kwargs.items():
            setattr(self, var_name, value)

    def __setattr__(self, name, value):
        """Translates rw_ActiveBinding (Validates on assignment)"""
        if name in ['_lr_code', '_params', '_private']:
            super().__setattr__(name, value)
        elif name in self._params:
            spec = self._params[name]
            val_func_name = spec['validate_func']
            
            if value is not None:
                # Dynamically call the corresponding validation function
                import bsrn.archiving.validation as val_module
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
        if name in self._private:
            return self._private[name]
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")

    def is_mandatory(self, var_name):
        """Translates genericIsMandatory"""
        return self._params[var_name]['mandatory']

    def is_missing(self, var_name):
        """Translates genericIsMissing"""
        return self._private[var_name] is None

    def mandatories(self):
        """Translates genericMandatories"""
        return [name for name, spec in self._params.items() if spec['mandatory']]

    def missings(self):
        """Translates genericMissings"""
        return [name for name in self.mandatories() if self.is_missing(name)]

    def is_values_missing(self):
        """Translates genericIsValuesMissing"""
        return len(self.missings()) > 0

    def set_default(self, var_name):
        """Translates genericSetDefault"""
        self._private[var_name] = self._params[var_name]['default']

    def stop_if_values_missing(self, message=""):
        """Translates stopIfValuesMissing"""
        if self.is_values_missing():
            tmp = ", ".join(self.missings())
            raise ValueError(f"{message}\n missing value(s) : {tmp}")

    def _coerce_stored_scalar(self, var_name, value):
        """
        After validation, coerce scalars to Python types matching Fortran ``I`` / ``F`` specs
        (R stores validated integers as integers, not ``33.0``).
        校验后将标量转为与 Fortran ``I``/``F`` 一致的 Python 类型（与 R 一致，避免 ``33.0``）。
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
        """Translates genericPrint"""
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
        """Translates getFormatValue (Fortran padding logic)"""
        value = self._private.get(var_name)
        spec = self._params[var_name]
        missing_code = spec.get('missing')

        if value is None:
            value = missing_code
            if str(value) in ["-999", "-999.9", "-99.9", "-99.99"]:
                value = float(value) if '.' in str(value) else int(value)

        # Vectorized fields: return numeric arrays (formatting for output is ``_format_series_field``).
        # 向量字段：返回数值数组；写出磁盘时的格式见 ``_format_series_field``。
        if isinstance(value, pd.Series):
            return value.fillna(missing_code)
        elif isinstance(value, np.ndarray):
            return np.where(np.isnan(value), missing_code, value)

        fmt = spec['format']
        if value is None: return ""

        if fmt == "L": return "Y" if value else "N"
        if fmt.startswith("I"):
            w = int(fmt[1:])
            return f"{int(value):>{w}d}"
        if fmt.startswith("F"):
            w, d = map(int, fmt[1:].split('.'))
            return f"{float(value):>{w}.{d}f}"
        if fmt.startswith("A"):
            w = int(fmt[1:]) if len(fmt) > 1 else 80
            if fmt == "A": w = 80
            s = str(value)
            return f"{s:<{w}}"[:w]
        return str(value)

    def _format_series_field(self, var_name: str) -> pd.Series:
        """
        One Fortran-formatted string per row for vector LR fields (LR0100 / LR4000).
        Matches scalar ``get_format_value`` padding so outputs are not Python ``str(float)`` (no ``.0`` on integers).
        每分钟一行 Fortran 宽度字符串；与标量 ``get_format_value`` 一致，避免 ``33.0`` 这类输出。
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


# =============================================================================
# TRANSLATION OF: 2_R6Class_headers.R
# =============================================================================

class LR0001(BSRNRecord):
    def __init__(self, **kwargs):
        super().__init__("LR0001", **kwargs)

    def get_bsrn_format(self, listSensor=["2", "3", "4", "5", "21", "22", "23"]):
        """Translates lr0001GetBsrnFormat"""
        self.stop_if_values_missing("LR0001")
        
        ls = [int(x) for x in listSensor]
        n = len(ls)
        pad = 8 - (n % 8) if (n % 8) != 0 else 0
        listIds = ls + [-1] * pad
        
        rows = [" ".join([f"{x:>9}" for x in listIds[i:i+8]]) for i in range(0, len(listIds), 8)]
        formatListSensor = " " + "\n ".join(rows)

        v = {name: self.get_format_value(name) for name in self._params.keys()}
        
        return (
            f"*C0001\n"
            f" {v['stationNumber']} {v['month']} {v['year']} {v['version']}\n"
            f"{formatListSensor}"
        )

class LR0002(BSRNRecord):
    def __init__(self, **kwargs):
        super().__init__("LR0002", **kwargs)

    def get_bsrn_format(self):
        """Translates lr0002GetBsrnFormat"""
        self.stop_if_values_missing("LR0002")
        v = {name: self.get_format_value(name) for name in self._params.keys()}
        
        sci_change = self._private['scientistChange']
        dep_change = self._private['deputyChange']
        
        c1 = "*C0002" if (sci_change or dep_change) else "*U0002"
        c2 = f" {v['scientistChangeDay']} {v['scientistChangeHour']} {v['scientistChangeMinute']}" if sci_change else " -1 -1 -1"
        c3 = f"{v['scientistName']} {v['scientistTel']} {v['scientistFax']}"
        c4 = f"{v['scientistTcpip']} {v['scientistMail']}"
        c5 = f"{v['scientistAddress']}"
        c6 = f" {v['deputyChangeDay']} {v['deputyChangeHour']} {v['deputyChangeMinute']}" if dep_change else " -1 -1 -1"
        c7 = f"{v['deputyName']} {v['deputyTel']} {v['deputyFax']}"
        c8 = f"{v['deputyTcpip']} {v['deputyMail']}"
        c9 = f"{v['deputyAddress']}"
        
        return "\n".join([c1, c2, c3, c4, c5, c6, c7, c8, c9])

class LR0003(BSRNRecord):
    def __init__(self, **kwargs):
        super().__init__("LR0003", **kwargs)

    def get_bsrn_format(self, *args):
        """Translates lr0003GetBsrnFormat"""
        self.stop_if_values_missing("LR0003")
        v = {name: self.get_format_value(name) for name in self._params.keys()}
        res = "*U0003\n" + v['message']
        if args:
            res += "\n" + "\n".join(args)
        return res

class LR0004(BSRNRecord):
    def __init__(self, **kwargs):
        super().__init__("LR0004", **kwargs)

    def get_bsrn_format(self):
        """Translates lr0004GetBsrnFormat"""
        self.stop_if_values_missing("LR0004")
        v = {name: self.get_format_value(name) for name in self._params.keys()}
        
        s_change = self._private['stationDescChange']
        h_change = self._private['horizonChange']
        
        c1 = "*C0004" if (s_change or h_change) else "*U0004"
        c2 = f" {v['stationDescChangeDay']} {v['stationDescChangeHour']} {v['stationDescChangeMinute']}" if s_change else " -1 -1 -1"
        c3 = f" {v['surfaceType']} {v['topographyType']}"
        c4 = f"{v['address']}"
        c5 = f"{v['telephone']} {v['fax']}"
        c6 = f"{v['tcpip']} {v['mail']}"
        c7 = f" {v['latitude']} {v['longitude']} {v['altitude']} {v['synop']}"
        c8 = f" {v['horizonChangeDay']} {v['horizonChangeHour']} {v['horizonChangeMinute']}" if h_change else " -1 -1 -1"
        c9 = get_azimuth_elevation(self._private['azimuth'], self._private['elevation'])
        
        return "\n".join([c1, c2, c3, c4, c5, c6, c7, c8, c9])

class LR0005(BSRNRecord):
    def __init__(self, **kwargs):
        super().__init__("LR0005", **kwargs)

    def get_bsrn_format(self):
        """Translates lr0005GetBsrnFormat"""
        self.stop_if_values_missing("LR0005")
        v = {name: self.get_format_value(name) for name in self._params.keys()}
        
        ch = self._private['change']
        c1 = "*C0005" if ch else "*U0005"
        c2_t = f" {v['changeDay']} {v['changeHour']} {v['changeMinute']}" if ch else " -1 -1 -1"
        c2_o = "Y" if self._private['operating'] else "N"
        c2 = f"{c2_t} {c2_o}"
        c3 = f"{v['manufacturer']} {v['location']} {v['distanceFromSite']} {v['time1stLaunch']} {v['time2ndLaunch']} {v['time3rdLaunch']} {v['time4thLaunch']} {v['identification']}"
        c4 = f"{v['remarks']}"
        
        return "\n".join([c1, c2, c3, c4])

class LR0006(BSRNRecord):
    def __init__(self, **kwargs):
        super().__init__("LR0006", **kwargs)

    def get_bsrn_format(self):
        """Translates lr0006GetBsrnFormat"""
        self.stop_if_values_missing("LR0006")
        v = {name: self.get_format_value(name) for name in self._params.keys()}
        
        ch = self._private['change']
        c1 = "*C0006" if ch else "*U0006"
        c2_t = f" {v['changeDay']} {v['changeHour']} {v['changeMinute']}" if ch else " -1 -1 -1"
        c2_o = "Y" if self._private['operating'] else "N"
        c2 = f"{c2_t} {c2_o}"
        c3 = f"{v['manufacturer']} {v['location']} {v['distanceFromSite']} {v['identification']}"
        c4 = f"{v['remarks']}"
        
        return "\n".join([c1, c2, c3, c4])

class LR0007(BSRNRecord):
    def __init__(self, **kwargs):
        super().__init__("LR0007", **kwargs)

    def get_bsrn_format(self, synop=None):
        """Translates lr0007GetBsrnFormat"""
        self.stop_if_values_missing("LR0007")
        v = {name: self.get_format_value(name) for name in self._params.keys()}
        
        flags = [
            "N" if synop is None else "Y",
            "N" if self._private['cloudAmount'] is None else "Y",
            "N" if self._private['cloudBaseHeight'] is None else "Y",
            "N" if self._private['cloudLiquid'] is None else "Y",
            "N" if self._private['cloudAerosol'] is None else "Y",
            "N" if self._private['waterVapour'] is None else "Y"
        ]
        flags_str = "".join(flags)
        
        ch = self._private['change']
        c1 = "*C0007" if ch else "*U0007"
        c2 = f" {v['changeDay']} {v['changeHour']} {v['changeMinute']}" if ch else " -1 -1 -1"
        c3 = f"{v['cloudAmount']}"
        c4 = f"{v['cloudBaseHeight']}"
        c5 = f"{v['cloudLiquid']}"
        c6 = f"{v['cloudAerosol']}"
        c7 = f"{v['waterVapour']}"
        
        return "\n".join([c1, c2, c3, c4, c5, c6, c7, flags_str])

class LR0008(BSRNRecord):
    def __init__(self, **kwargs):
        super().__init__("LR0008", **kwargs)

    def get_bsrn_format(self, anyChange=False, printLr=False, LR0009Format=False):
        """Translates lr0008GetBsrnFormat"""
        self.stop_if_values_missing("LR0008")
        v = {name: self.get_format_value(name) for name in self._params.keys()}
        
        ch = self._private['change']
        t_str = f" {v['changeDay']} {v['changeHour']} {v['changeMinute']}" if ch else " -1 -1 -1"
        
        if LR0009Format:
            thisFormat = f"{t_str}\n{v['radiationQuantityMeasured']} {v['identification']} {v['numOfBand']}"
        else:
            c1 = f"{t_str} {'Y' if self._private['operating'] else 'N'}"
            c2 = f"{v['manufacturer']} {v['model']} {v['serialNumber']} {v['dateOfPurchase']} {v['identification']}"
            c3 = f"{v['remarks']}"
            c4 = f" {v['pyrgeometerBody']} {v['pyrgeometerDome']} {v['wavelenghBand1']} {v['bandwidthBand1']} {v['wavelenghBand2']} {v['bandwidthBand2']} {v['wavelenghBand3']} {v['bandwidthBand3']} {v['maxZenithAngle']} {v['minSpectral']}"
            c5 = f"{v['location']} {v['person']}"
            c6 = f"{v['startOfCalibPeriod1']} {v['endOfCalibPeriod1']} {v['numOfComp1']} {v['meanCalibCoeff1']} {v['stdErrorCalibCoeff1']}"
            c7 = f"{v['startOfCalibPeriod2']} {v['endOfCalibPeriod2']} {v['numOfComp2']} {v['meanCalibCoeff2']} {v['stdErrorCalibCoeff2']}"
            c8 = f"{v['startOfCalibPeriod3']} {v['endOfCalibPeriod3']} {v['numOfComp3']} {v['meanCalibCoeff3']} {v['stdErrorCalibCoeff3']}"
            c9 = f"{v['remarksOnCalib1']}"
            c10 = f"{v['remarksOnCalib2']}"
            thisFormat = "\n".join([c1, c2, c3, c4, c5, c6, c7, c8, c9, c10])
            
        if printLr:
            h = f"{'*C000' if anyChange else '*U000'}{'9' if LR0009Format else '8'}\n"
            thisFormat = h + thisFormat
            
        return thisFormat

class LR4000CONST(BSRNRecord):
    def __init__(self, **kwargs):
        super().__init__("LR4000CONST", **kwargs)

    def get_bsrn_format(self, method=1):
        """Translates lr4000constGetBsrnFormat"""
        self.stop_if_values_missing("LR4000CONST")
        if method not in [1, 2]: raise ValueError("method must be 1 or 2")
        
        v = {name: self.get_format_value(name) for name in self._params.keys()}
        
        cert_id = self._private['certificateCodeID']
        if method == 2:
            if not self._private['yyyymmdd'] or not self._private['manufact'] or not self._private['model']:
                raise ValueError("missing value(s) : yyyymmdd, manufact or model")
            cert_id = f"CAL_{self._private['yyyymmdd']}_{self._private['manufact']}_{self._private['model']}_{self._private['serialNumber_Manufacturer']}_{self._private['serialNumber_WRMC']}"
            
        if not cert_id: raise ValueError("missing value(s) : certificateCodeID")
        
        s = f"@LR4000CONST, {v['serialNumber_Manufacturer']}, {v['serialNumber_WRMC']}, {cert_id}, {v['C']}, {v['k0']}, {v['k1']}, {v['k2']}, {v['k3']}, {v['f']}"
        res = textwrap.fill(s, width=79).replace('\n', '&\n')
        return res


# =============================================================================
# TRANSLATION OF: 2_R6Class_datas.R
# =============================================================================

class LR0100(BSRNRecord):
    def __init__(self, **kwargs):
        super().__init__("LR0100", **kwargs)

    def get_bsrn_format(self, changed=True):
        """Translates lr0100GetBsrnFormat"""
        res = "*C0100" if changed else "*U0100"
        m = self._format_series_field

        nd = number_of_days(self._private['yearMonth'])

        # Replicates: rep(1:nd, each = 1440) %>% formatC(format = 'd', width = 2)
        days = np.repeat(np.arange(1, nd + 1), 1440)
        df_days = pd.Series([f"{d:>2d}" for d in days])

        # Replicates: rep(0:1439, nd) %>%  formatC(format = 'd', width = 4)
        mins = np.tile(np.arange(0, 1440), nd)
        df_mins = pd.Series([f"{m_:>4d}" for m_ in mins])

        line1 = (
            " " + df_days + " " + df_mins + "   "
            + m("global2_avg") + " " + m("global2_std") + " " + m("global2_min") + " " + m("global2_max") + "   "
            + m("direct_avg") + " " + m("direct_std") + " " + m("direct_min") + " " + m("direct_max")
        )

        line2 = (
            "           "
            + m("diffuse_avg") + " " + m("diffuse_std") + " " + m("diffuse_min") + " " + m("diffuse_max") + "   "
            + m("downward_avg") + " " + m("downward_std") + " " + m("downward_min") + " " + m("downward_max")
            + "    "
            + m("temperature") + " " + m("humidity") + " " + m("pressure")
        )

        strData = (line1 + "\n" + line2).str.cat(sep="\n")
        return f"{res}\n{strData}"

class LR4000(BSRNRecord):
    def __init__(self, **kwargs):
        super().__init__("LR4000", **kwargs)

    def get_bsrn_format(self, changed=True):
        """Translates lr4000GetBsrnFormat"""
        res = "*C4000" if changed else "*U4000"
        m = self._format_series_field

        nd = number_of_days(self._private["yearMonth"])
        days = np.repeat(np.arange(1, nd + 1), 1440)
        df_days = pd.Series([f"{d:>2d}" for d in days])
        mins = np.tile(np.arange(0, 1440), nd)
        df_mins = pd.Series([f"{mi:>4d}" for mi in mins])

        strData = (
            " " + df_days + " " + df_mins + " "
            + m("domeT1_down") + " " + m("domeT2_down") + " " + m("domeT3_down") + " "
            + m("bodyT_down") + " " + m("longwave_down") + "  "
            + m("domeT1_up") + " " + m("domeT2_up") + " " + m("domeT3_up") + " "
            + m("bodyT_up") + " " + m("longwave_up")
        ).str.cat(sep="\n")

        return f"{res}\n{strData}"