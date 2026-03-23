"""
bsrn.archiving.specs

Logical-record field definitions (conceptually R ``A1_formats`` / ``getParams``).
Defines fixed-width Fortran-style formats, missing tokens, mandatory flags,
defaults, and labels. Station lists and A3–A7 code tables live in
``stations`` and ``mappings``.

逻辑记录字段定义（对应 R 的 ``A1_formats`` / ``getParams``）。
包含 Fortran 固定宽度格式、缺失值、必填标志、默认值与标签。
站点列表与 A3–A7 编码表见 ``stations`` 与 ``mappings`` 模块。

Format Codes (Fortran-style):
- 'I#': Integer padded to # characters (e.g., I4)
- 'A#': String/Alphanumeric padded to # characters (e.g., A38)
- 'F#.#': Float padded to total width with specific decimals (e.g., F5.1)
- 'L': Logical boolean (usually T/F or 1/0)
- 'ND': Not defined / No specific width enforced by the original spec

定义了所有 BSRN 逻辑记录的严格 ASCII 固定宽度格式化规则、缺失值、
必填字段、默认值和说明性标签。

格式代码（Fortran 风格）：
- 'I#'：填充到 # 个字符的整数（如 I4）
- 'A#'：填充到 # 个字符的字符串/字母数字（如 A38）
- 'F#.#'：填充到指定总宽度并带特定小数位的浮点数（如 F5.1）
- 'L'：逻辑布尔值（通常为 T/F 或 1/0）
- 'ND'：未定义 / 原始规范未强制要求特定宽度
"""

LR_SPECS = {
    "LR0001": {
        "stationNumber": {"label": "Station identification number", "format": "I2", "missing": None, "mandatory": True, "default": None, "validate_func": "I2_validateFunction"},
        "month":         {"label": "Month of measurement", "format": "I2", "missing": None, "mandatory": True, "default": None, "validate_func": "month_validateFunction"},
        "year":          {"label": "Year of measurement", "format": "I4", "missing": None, "mandatory": True, "default": None, "validate_func": "year_validateFunction"},
        "version":       {"label": "Version of data", "format": "I2", "missing": None, "mandatory": True, "default": None, "validate_func": "I2_validateFunction"}
    },
    "LR0002": {
        "scientistChange":       {"label": "Is scientist changed this month ?", "format": "L", "missing": None, "mandatory": True, "default": False, "validate_func": "L_validateFunction"},
        "scientistChangeDay":    {"label": "Day", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "day_validateFunction"},
        "scientistChangeHour":   {"label": "Hour", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "hour_validateFunction"},
        "scientistChangeMinute": {"label": "Minute", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "minute_validateFunction"},
        "scientistName":         {"label": "Name", "format": "A38", "missing": None, "mandatory": True, "default": None, "validate_func": "A38_validateFunction"},
        "scientistTel":          {"label": "Telephone no.", "format": "A20", "missing": None, "mandatory": True, "default": None, "validate_func": "telephone_validateFunction"},
        "scientistFax":          {"label": "Fax no.", "format": "A20", "missing": None, "mandatory": True, "default": None, "validate_func": "telephone_validateFunction"},
        "scientistTcpip":        {"label": "TCP/IP no.", "format": "A15", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "tcpip_validateFunction"},
        "scientistMail":         {"label": "E-mail address", "format": "A50", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "email_validateFunction"},
        "scientistAddress":      {"label": "Address", "format": "A80", "missing": None, "mandatory": True, "default": None, "validate_func": "A80_validateFunction"},
        "deputyChange":          {"label": "Is deputy changed this month ?", "format": "L", "missing": None, "mandatory": True, "default": False, "validate_func": "L_validateFunction"},
        "deputyChangeDay":       {"label": "Day", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "day_validateFunction"},
        "deputyChangeHour":      {"label": "Hour", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "hour_validateFunction"},
        "deputyChangeMinute":    {"label": "Minute", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "minute_validateFunction"},
        "deputyName":            {"label": "Name", "format": "A38", "missing": None, "mandatory": True, "default": None, "validate_func": "A38_validateFunction"},
        "deputyTel":             {"label": "Telephone no.", "format": "A20", "missing": None, "mandatory": True, "default": None, "validate_func": "telephone_validateFunction"},
        "deputyFax":             {"label": "Fax no.", "format": "A20", "missing": None, "mandatory": True, "default": None, "validate_func": "telephone_validateFunction"},
        "deputyTcpip":           {"label": "TCP/IP no.", "format": "A15", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "tcpip_validateFunction"},
        "deputyMail":            {"label": "E-mail address", "format": "A50", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "email_validateFunction"},
        "deputyAddress":         {"label": "Address", "format": "A80", "missing": None, "mandatory": True, "default": None, "validate_func": "A80_validateFunction"}
    },
    "LR0003": {
        "message": {"label": "Messages not to be inserted in the BSRN database", "format": "A", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "A_validateFunction"}
    },
    "LR0004": {
        "stationDescChange":       {"label": "Is station description changed this month ?", "format": "L", "missing": None, "mandatory": True, "default": False, "validate_func": "L_validateFunction"},
        "stationDescChangeDay":    {"label": "Day", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "day_validateFunction"},
        "stationDescChangeHour":   {"label": "Hour", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "hour_validateFunction"},
        "stationDescChangeMinute": {"label": "Minute", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "minute_validateFunction"},
        "surfaceType":             {"label": "Surface type", "format": "I2", "missing": None, "mandatory": True, "default": None, "validate_func": "surface_validateFunction"},
        "topographyType":          {"label": "Topography Type", "format": "I2", "missing": None, "mandatory": True, "default": None, "validate_func": "topography_validateFunction"},
        "address":                 {"label": "Address", "format": "A80", "missing": None, "mandatory": True, "default": None, "validate_func": "A80_validateFunction"},
        "telephone":               {"label": "Telephone no. of station", "format": "A20", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "telephone_validateFunction"},
        "fax":                     {"label": "Fax no. of station", "format": "A20", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "telephone_validateFunction"},
        "tcpip":                   {"label": "TCP/IP no. of station", "format": "A15", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "tcpip_validateFunction"},
        "mail":                    {"label": "E-mail address of station", "format": "A50", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "email_validateFunction"},
        "latitude":                {"label": "Latitude [degrees, 0 is Southpole, positive is northward]", "format": "F7.3", "missing": None, "mandatory": True, "default": None, "validate_func": "latitude_validateFunction"},
        "longitude":               {"label": "Longitude [degrees, 0 is 180W, positive is eastwards]", "format": "F7.3", "missing": None, "mandatory": True, "default": None, "validate_func": "longitude_validateFunction"},
        "altitude":                {"label": "Altitude [m above the sea]", "format": "I4", "missing": None, "mandatory": True, "default": None, "validate_func": "I4_validateFunction"},
        "synop":                   {"label": "Identification od 'SYNOP' station", "format": "A5", "missing": "XXXXX", "mandatory": False, "default": None, "validate_func": "A5_validateFunction"},
        "horizonChange":           {"label": "Is horizon changed this month ?", "format": "L", "missing": None, "mandatory": True, "default": False, "validate_func": "L_validateFunction"},
        "horizonChangeDay":        {"label": "Day", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "day_validateFunction"},
        "horizonChangeHour":       {"label": "Hour", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "hour_validateFunction"},
        "horizonChangeMinute":     {"label": "Minute", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "minute_validateFunction"},
        "azimuth":                 {"label": "Azimuth [degrees from north clockwise]; format : 'A1,A2,...,An'", "format": "ND", "missing": -1, "mandatory": False, "default": None, "validate_func": "azimuth_validateFunction"},
        "elevation":               {"label": "Elevation [degrees]; format : 'E1,E2,...,En'", "format": "ND", "missing": -1, "mandatory": False, "default": None, "validate_func": "elevation_validateFunction"}
    },
    "LR0005": {
        "change":           {"label": "Is radiosonde equipment changed this month ?", "format": "L", "missing": None, "mandatory": True, "default": False, "validate_func": "L_validateFunction"},
        "changeDay":        {"label": "Day", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "day_validateFunction"},
        "changeHour":       {"label": "Hour", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "hour_validateFunction"},
        "changeMinute":     {"label": "Minute", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "minute_validateFunction"},
        "operating":        {"label": "Is radiosonde operating?", "format": "A1", "missing": None, "mandatory": True, "default": False, "validate_func": "L_validateFunction"},
        "manufacturer":     {"label": "Manufacturer", "format": "A30", "missing": None, "mandatory": True, "default": None, "validate_func": "A30_validateFunction"},
        "location":         {"label": "Location", "format": "A25", "missing": None, "mandatory": True, "default": None, "validate_func": "A25_validateFunction"},
        "distanceFromSite": {"label": "Distance from radiation site [km]", "format": "I3", "missing": None, "mandatory": True, "default": None, "validate_func": "I3_validateFunction"},
        "time1stLaunch":    {"label": "Time of 1st launch [h UTC]", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "hour_validateFunction"},
        "time2ndLaunch":    {"label": "Time of 2nd launch [h UTC]", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "hour_validateFunction"},
        "time3rdLaunch":    {"label": "Time of 3rd launch [h UTC]", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "hour_validateFunction"},
        "time4thLaunch":    {"label": "Time of 4th launch [h UTC]", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "hour_validateFunction"},
        "identification":   {"label": "Identification of radiosonde", "format": "A5", "missing": None, "mandatory": True, "default": None, "validate_func": "A5_validateFunction"},
        "remarks":          {"label": "Remarks about radiosonde", "format": "A80", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "A80_validateFunction"}
    },
    "LR0006": {
        "change":           {"label": "Is ozone measurements equipment changed this month ?", "format": "L", "missing": None, "mandatory": True, "default": False, "validate_func": "L_validateFunction"},
        "changeDay":        {"label": "Day", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "day_validateFunction"},
        "changeHour":       {"label": "Hour", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "hour_validateFunction"},
        "changeMinute":     {"label": "Minute", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "minute_validateFunction"},
        "operating":        {"label": "Is ozone measurements opérating ?", "format": "A1", "missing": None, "mandatory": True, "default": False, "validate_func": "L_validateFunction"},
        "manufacturer":     {"label": "Manufacturer", "format": "A30", "missing": None, "mandatory": True, "default": None, "validate_func": "A30_validateFunction"},
        "location":         {"label": "Location", "format": "A25", "missing": None, "mandatory": True, "default": None, "validate_func": "A25_validateFunction"},
        "distanceFromSite": {"label": "Distance from radiation site [km]", "format": "I3", "missing": None, "mandatory": True, "default": None, "validate_func": "I3_validateFunction"},
        "identification":   {"label": "Identification number of ozone instrument", "format": "A5", "missing": None, "mandatory": True, "default": None, "validate_func": "A5_validateFunction"},
        "remarks":          {"label": "Remarks about ozone measurements", "format": "A80", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "A80_validateFunction"}
    },
    "LR0007": {
        "change":          {"label": "Is station history changed this month ?", "format": "L", "missing": None, "mandatory": True, "default": False, "validate_func": "L_validateFunction"},
        "changeDay":       {"label": "Day", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "day_validateFunction"},
        "changeHour":      {"label": "Hour", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "hour_validateFunction"},
        "changeMinute":    {"label": "Minute", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "minute_validateFunction"},
        "cloudAmount":     {"label": "Method est. cloud amount (digital proc.)", "format": "A80", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "A80_validateFunction"},
        "cloudBaseHeight": {"label": "Method est. cloud base height (with instrument)", "format": "A80", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "A80_validateFunction"},
        "cloudLiquid":     {"label": "Method est. cloud liquid water content", "format": "A80", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "A80_validateFunction"},
        "cloudAerosol":    {"label": "Method est. cloud aerosol vertical distribution", "format": "A80", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "A80_validateFunction"},
        "waterVapour":     {"label": "Method est. water vapour press. v.d. (A80)", "format": "A80", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "A80_validateFunction"}
    },
    "LR0008": {
        "change":                    {"label": "Is instruments changed this month ?", "format": "L", "missing": None, "mandatory": True, "default": False, "validate_func": "L_validateFunction"},
        "changeDay":                 {"label": "Day", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "day_validateFunction"},
        "changeHour":                {"label": "Hour", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "hour_validateFunction"},
        "changeMinute":              {"label": "Minute", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "minute_validateFunction"},
        "operating":                 {"label": "Is instrument measuring?", "format": "A1", "missing": None, "mandatory": True, "default": False, "validate_func": "L_validateFunction"},
        "radiationQuantityMeasured": {"label": "Radiation quantity measured", "format": "I9", "missing": None, "mandatory": True, "default": None, "validate_func": "quantities_validateFunction"},
        "manufacturer":              {"label": "Manufacturer", "format": "A30", "missing": None, "mandatory": True, "default": None, "validate_func": "A30_validateFunction"},
        "model":                     {"label": "Model", "format": "A15", "missing": None, "mandatory": True, "default": None, "validate_func": "A15_validateFunction"},
        "serialNumber":              {"label": "Serial number", "format": "A18", "missing": None, "mandatory": True, "default": None, "validate_func": "A18_validateFunction"},
        "dateOfPurchase":            {"label": "Date of Purchase", "format": "A8", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "date_validateFunction"},
        "identification":            {"label": "Identification number assigned by the WRMC", "format": "I5", "missing": None, "mandatory": True, "default": None, "validate_func": "I5_validateFunction"},
        "remarks":                   {"label": "Remarks about the radiation instrument", "format": "A80", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "A80_validateFunction"},
        "pyrgeometerBody":           {"label": "Pyrgeometer body compensation code", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "body_validateFunction"},
        "pyrgeometerDome":           {"label": "Pyrgeometer dome compensation code", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "dome_validateFunction"},
        "numOfBand":                 {"label": "Number of band (for spectral instruments)", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "I2_validateFunction"},
        "wavelenghBand1":            {"label": "Wavelength of band 1 of spectral i. [micron]", "format": "F7.3", "missing": -1.0, "mandatory": False, "default": None, "validate_func": "F7.3_validateFunction"},
        "bandwidthBand1":            {"label": "Bandwidth of band 1 of spectral i. [micron]", "format": "F7.3", "missing": -1.0, "mandatory": False, "default": None, "validate_func": "F7.3_validateFunction"},
        "wavelenghBand2":            {"label": "Wavelength of band 2", "format": "F7.3", "missing": -1.0, "mandatory": False, "default": None, "validate_func": "F7.3_validateFunction"},
        "bandwidthBand2":            {"label": "Bandwidth of band 2", "format": "F7.3", "missing": -1.0, "mandatory": False, "default": None, "validate_func": "F7.3_validateFunction"},
        "wavelenghBand3":            {"label": "Wavelength of band 3", "format": "F7.3", "missing": -1.0, "mandatory": False, "default": None, "validate_func": "F7.3_validateFunction"},
        "bandwidthBand3":            {"label": "Bandwidth of band 3", "format": "F7.3", "missing": -1.0, "mandatory": False, "default": None, "validate_func": "F7.3_validateFunction"},
        "maxZenithAngle":            {"label": "Max. zenith angle [degree] of direct", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "zenith_validateFunction"},
        "minSpectral":               {"label": "Min. (spectral) instrument", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "zenith_validateFunction"},
        "location":                  {"label": "Location of calibration", "format": "A30", "missing": None, "mandatory": True, "default": None, "validate_func": "A30_validateFunction"},
        "person":                    {"label": "Person doing calibration", "format": "A40", "missing": None, "mandatory": True, "default": None, "validate_func": "A40_validateFunction"},
        "startOfCalibPeriod1":       {"label": "Start of calibration period (band 1 of spectr. instr.)", "format": "A8", "missing": None, "mandatory": True, "default": None, "validate_func": "date_validateFunction"},
        "endOfCalibPeriod1":         {"label": "End of ... (both [MM/DD/YY])", "format": "A8", "missing": None, "mandatory": True, "default": None, "validate_func": "date_validateFunction"},
        "numOfComp1":                {"label": "Number of comparisons (band 1 of spectr. instr.)", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "I2_validateFunction"},
        "meanCalibCoeff1":           {"label": "Mean calibration coefficient (band 1 of spectr. instr.)", "format": "F12.4", "missing": None, "mandatory": True, "default": None, "validate_func": "F12.4_validateFunction"},
        "stdErrorCalibCoeff1":       {"label": "Standard error of cal. coeff. (band 1 of spectr. instr.)", "format": "F12.4", "missing": -1.0, "mandatory": False, "default": None, "validate_func": "F12.4_validateFunction"},
        "startOfCalibPeriod2":       {"label": "Start of calibration period (band 2 of spectr. instr.)", "format": "A8", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "date_validateFunction"},
        "endOfCalibPeriod2":         {"label": "End of ... (both [MM/DD/YY])", "format": "A8", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "date_validateFunction"},
        "numOfComp2":                {"label": "Number of comparisons (band 2 of spectr. instr.)", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "I2_validateFunction"},
        "meanCalibCoeff2":           {"label": "Mean calibration coefficient (band 2 of spectr. instr.)", "format": "F12.4", "missing": -1.0, "mandatory": False, "default": None, "validate_func": "F12.4_validateFunction"},
        "stdErrorCalibCoeff2":       {"label": "Standard error of cal. coeff. (band 2 of spectr. instr.)", "format": "F12.4", "missing": -1.0, "mandatory": False, "default": None, "validate_func": "F12.4_validateFunction"},
        "startOfCalibPeriod3":       {"label": "Start of calibration period (band 3 of spectr. instr.)", "format": "A8", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "date_validateFunction"},
        "endOfCalibPeriod3":         {"label": "End of ... (both [MM/DD/YY])", "format": "A8", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "date_validateFunction"},
        "numOfComp3":                {"label": "Number of comparisons (band 3 of spectr. instr.)", "format": "I2", "missing": -1, "mandatory": False, "default": None, "validate_func": "I2_validateFunction"},
        "meanCalibCoeff3":           {"label": "Mean calibration coefficient (band 3 of spectr. instr.)", "format": "F12.4", "missing": -1.0, "mandatory": False, "default": None, "validate_func": "F12.4_validateFunction"},
        "stdErrorCalibCoeff3":       {"label": "Standard error of cal. coeff. (band 3 of spectr. instr.)", "format": "F12.4", "missing": -1.0, "mandatory": False, "default": None, "validate_func": "F12.4_validateFunction"},
        "remarksOnCalib1":           {"label": "Remarks on calibration, e.g. units of cal. coeff.", "format": "A80", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "A80_validateFunction"},
        "remarksOnCalib2":           {"label": "Remarks on calibration (continued)", "format": "A80", "missing": "XXX", "mandatory": False, "default": None, "validate_func": "A80_validateFunction"}
    },
    "LR0100": {
        "yearMonth":    {"label": "Year and month of measurement ('YYYY-MM')", "format": "A7", "missing": None, "mandatory": True, "default": None, "validate_func": "genericValidateFunction"},
        "global2_avg":  {"label": "Global 2 mean", "format": "I4", "missing": -999, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "global2_std":  {"label": "Global 2 standard deviation", "format": "F5.1", "missing": -99.9, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "global2_min":  {"label": "Global 2 minimum", "format": "I4", "missing": -999, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "global2_max":  {"label": "Global 2 maximum", "format": "I4", "missing": -999, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "direct_avg":   {"label": "Direct mean", "format": "I4", "missing": -999, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "direct_std":   {"label": "Direct standard deviation", "format": "F5.1", "missing": -99.9, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "direct_min":   {"label": "Direct minimum", "format": "I4", "missing": -999, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "direct_max":   {"label": "Direct maximum", "format": "I4", "missing": -999, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "diffuse_avg":  {"label": "Diffuse mean", "format": "I4", "missing": -999, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "diffuse_std":  {"label": "Diffuse standard deviation", "format": "F5.1", "missing": -99.9, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "diffuse_min":  {"label": "Diffuse minimum", "format": "I4", "missing": -999, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "diffuse_max":  {"label": "Diffuse maximum", "format": "I4", "missing": -999, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "downward_avg": {"label": "Downward long-wave radiation mean", "format": "I4", "missing": -999, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "downward_std": {"label": "Downward long-wave radiation standard deviation", "format": "F5.1", "missing": -99.9, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "downward_min": {"label": "Downward long-wave radiation minimum", "format": "I4", "missing": -999, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "downward_max": {"label": "Downward long-wave radiation maximum", "format": "I4", "missing": -999, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "temperature":  {"label": "Air temperature at downward long-wave instrument height", "format": "F5.1", "missing": -99.9, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "humidity":     {"label": "Relative humidity at downward long-wave instrument height", "format": "F5.1", "missing": -99.9, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"},
        "pressure":     {"label": "Pressure at downward long-wave instrument height", "format": "I4", "missing": -999, "mandatory": False, "default": None, "validate_func": "LR0100_validateFunction"}
    },
    "LR4000": {
        "yearMonth":     {"label": "Year and month of measurement ('YYYY-MM')", "format": "A7", "missing": None, "mandatory": True, "default": None, "validate_func": "genericValidateFunction"},
        "domeT1_down":   {"label": "dome temperature 1downward long-wave instrument", "format": "F6.2", "missing": -99.99, "mandatory": False, "default": None, "validate_func": "LR4000_validateFunction"},
        "domeT2_down":   {"label": "dome temperature 2 downward long-wave instrument", "format": "F6.2", "missing": -99.99, "mandatory": False, "default": None, "validate_func": "LR4000_validateFunction"},
        "domeT3_down":   {"label": "dome temperature 3 downward long-wave instrument", "format": "F6.2", "missing": -99.99, "mandatory": False, "default": None, "validate_func": "LR4000_validateFunction"},
        "bodyT_down":    {"label": "body temperature downward long-wave instrument", "format": "F6.2", "missing": -99.99, "mandatory": False, "default": None, "validate_func": "LR4000_validateFunction"},
        "longwave_down": {"label": "thermopile output downward long-wave instrument", "format": "F6.1", "missing": -999.9, "mandatory": False, "default": None, "validate_func": "LR4000_validateFunction"},
        "domeT1_up":     {"label": "dome temperature 1upward long-wave instrument", "format": "F6.2", "missing": -99.99, "mandatory": False, "default": None, "validate_func": "LR4000_validateFunction"},
        "domeT2_up":     {"label": "dome temperature 2 upward long-wave instrument", "format": "F6.2", "missing": -99.99, "mandatory": False, "default": None, "validate_func": "LR4000_validateFunction"},
        "domeT3_up":     {"label": "dome temperature 3 upward long-wave instrument", "format": "F6.2", "missing": -99.99, "mandatory": False, "default": None, "validate_func": "LR4000_validateFunction"},
        "bodyT_up":      {"label": "body temperature upward long-wave instrument", "format": "F6.2", "missing": -99.99, "mandatory": False, "default": None, "validate_func": "LR4000_validateFunction"},
        "longwave_up":   {"label": "thermopile output upward long-wave instrument", "format": "F6.1", "missing": -999.9, "mandatory": False, "default": None, "validate_func": "LR4000_validateFunction"}
    },
    "LR4000CONST": {
        "serialNumber_Manufacturer": {"label": "The serial number as it appears in the calibration certificate/instrument plate", "format": "I6", "missing": None, "mandatory": True, "default": None, "validate_func": "A_validateFunction"},
        "serialNumber_WRMC":         {"label": "The serial nimber used in your station-to-archive files (LR0008/0009) to identify the instrument with this serial number (e.g. for dom: \"74xxx\", with xxx=001,002,003,...)", "format": "ND", "missing": None, "mandatory": False, "default": None, "validate_func": "A_validateFunction"},
        "certificateCodeID":         {"label": "The station scientist can define CertificateCodeId according to one of the 2 options. See LR4000_TableA1Update2", "format": "ND", "missing": None, "mandatory": False, "default": None, "validate_func": "A_validateFunction"},
        "yyyymmdd":                  {"label": "date of the calibration certificate issued : numeric format yyyymmdd", "format": "I8", "missing": None, "mandatory": False, "default": None, "validate_func": "I8_validateFunction"},
        "manufact":                  {"label": "KZ (Kipp and Zonen), EP (Eppley), HF (Hukseflux),...", "format": "ND", "missing": None, "mandatory": False, "default": None, "validate_func": "A_validateFunction"},
        "model":                     {"label": "CH1,CH1P,CM11,CM21,CM21P,CM22,CM22P,CG4,CGR4,...", "format": "ND", "missing": None, "mandatory": False, "default": None, "validate_func": "A_validateFunction"},
        "C":                         {"label": "Thermopile responsivity", "format": "ND", "missing": None, "mandatory": False, "default": None, "validate_func": "C_validateFunction"},
        "k0":                        {"label": "General equation of the pyrgeometer : ki are the instrument dependent calibration constants", "format": "ND", "missing": None, "mandatory": False, "default": None, "validate_func": "C_validateFunction"},
        "k1":                        {"label": "General equation of the pyrgeometer : ki are the instrument dependent calibration constants", "format": "ND", "missing": None, "mandatory": False, "default": None, "validate_func": "C_validateFunction"},
        "k2":                        {"label": "General equation of the pyrgeometer : ki are the instrument dependent calibration constants", "format": "ND", "missing": None, "mandatory": False, "default": None, "validate_func": "C_validateFunction"},
        "k3":                        {"label": "General equation of the pyrgeometer : ki are the instrument dependent calibration constants", "format": "ND", "missing": None, "mandatory": False, "default": None, "validate_func": "C_validateFunction"},
        "f":                         {"label": "General equation of the pyrgeometer : correction factor for infrared irradiance on unshaded domes", "format": "ND", "missing": None, "mandatory": False, "default": None, "validate_func": "C_validateFunction"}
    }
}
