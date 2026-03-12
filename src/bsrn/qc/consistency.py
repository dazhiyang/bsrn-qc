"""
bsrn level 3 (inter-comparison) checks - closure test.
BSRN 3 级（相互比较）检查 - 闭合测试。
"""

import numpy as np
import pandas as pd


"""
Citations:
[1] Long, Chuck N., and Yan Shi. "An automated quality assessment and control algorithm for surface radiation 
measurements." Open Atmos. Sci. J 2.1 (2008): 23-37.
"""
def closure_test(ghi, bni, dhi, zenith):
    """
    Check consistency between GHI, BNI, and DHI using the closure equation.
    使用闭合方程检查 GHI、BNI 和 DHI 之间的一致性。

    Eq: $G_h = B_n \cdot \mu_0 + D_h$

    Parameters
    ----------
    ghi : numeric or Series
        global horizontal irradiance ($G_h$) in W/m^2.
        水平总辐照度 ($G_h$)，单位 W/m^2。
    bni : numeric or Series
        beam normal irradiance ($B_n$) in W/m^2.
        法向直接辐照度 ($B_n$)，单位 W/m^2。
    dhi : numeric or Series
        diffuse horizontal irradiance ($D_h$) in W/m^2.
        水平散射辐照度 ($D_h$)，单位 W/m^2。
    zenith : numeric or Series
        solar zenith angle ($Z$) in degrees.
        太阳天顶角 ($Z$)，单位为度。

    Returns
    -------
    flags : Series or ndarray
        Boolean flags where True indicates the closure is within acceptable limits.
        布尔标记，True 表示闭合在可接受范围内。
    """
    mu0 = np.cos(np.radians(zenith))
    
    # Calculated global horizontal irradiance / 计算得到的水平总辐照度
    ghi_calc = bni * mu0 + dhi
    
    # Standard check: Difference within 8% for Z < 75 or within 15% for 75 <= Z < 93
    # 标准检查：Z < 75 时差异在 8% 以内，或 75 <= Z < 93 时在 15% 以内
    
    # Avoid division by zero / 避免除以零
    ghi_calc_safe = np.where(ghi_calc > 0, ghi_calc, np.nan)
    diff_ratio = np.abs(ghi - ghi_calc) / ghi_calc_safe
    
    # Z < 75: ratio < 0.08
    # 75 <= Z < 93: ratio < 0.15
    mask_low_z = (zenith < 75) & (ghi_calc > 50)
    mask_high_z = (zenith >= 75) & (zenith < 93) & (ghi_calc > 50)
    
    if hasattr(diff_ratio, 'iloc'):
        flags = (mask_low_z & (diff_ratio < 0.08)) | (mask_high_z & (diff_ratio < 0.15))
    else:
        # Scalar case / 标量情况
        if zenith < 75 and ghi_calc > 50:
            return diff_ratio < 0.08
        elif 75 <= zenith < 93 and ghi_calc > 50:
            return diff_ratio < 0.15
        else:
            return True # Not applicable / 不适用
            
    return flags
