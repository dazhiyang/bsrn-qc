"""
bsrn level 3 (inter-comparison) checks - diffuse ratio test.
BSRN 3 级（相互比较）检查 - 散射比测试。
"""

import numpy as np
import pandas as pd


"""
Citations:
[1] Long, Chuck N., and Yan Shi. "An automated quality assessment and control algorithm for surface radiation 
measurements." Open Atmos. Sci. J 2.1 (2008): 23-37.
"""
def diffuse_ratio_test(ghi, dhi, zenith):
    """
    Check the diffuse ratio (DHI/GHI) for physical consistency.
    检查散射比 (DHI/GHI) 的物理一致性。

    Parameters
    ----------
    ghi : numeric or Series
        global horizontal irradiance ($G_h$) in W/m^2.
        水平总辐照度 ($G_h$)，单位 W/m^2。
    dhi : numeric or Series
        diffuse horizontal irradiance ($D_h$) in W/m^2.
        水平散射辐照度 ($D_h$)，单位 W/m^2。
    zenith : numeric or Series
        solar zenith angle ($Z$) in degrees.
        太阳天顶角 ($Z$)，单位为度。

    Returns
    -------
    flags : Series or ndarray
        Boolean flags where True indicates the ratio is within acceptable limits.
        布尔标记，True 表示比率在可接受范围内。
    """
    # DHI should not exceed GHI by more than a margin (e.g., 5% or 15 W/m^2) / DHI 不应超过 GHI 太多（例如 5% 或 15 W/m^2）
    
    # Avoid division by zero / 避免除以零
    ghi_safe = np.where(ghi > 0, ghi, np.nan)
    ratio = dhi / ghi_safe
    
    # Typically: DHI/GHI <= 1.05 for Z < 75 or DHI/GHI <= 1.10 for 75 < Z < 93
    # 通常：Z < 75 时 DHI/GHI <= 1.05，或 75 < Z < 93 时 DHI/GHI <= 1.10
    
    mask_low_z = (zenith < 75) & (ghi > 50)
    mask_high_z = (zenith >= 75) & (zenith < 93) & (ghi > 50)
    
    if hasattr(ratio, 'iloc'):
        return (mask_low_z & (ratio <= 1.05)) | (mask_high_z & (ratio <= 1.10))
    else:
        # Scalar case / 标量情况
        if zenith < 75 and ghi > 50:
            return ratio <= 1.05
        elif 75 <= zenith < 93 and ghi > 50:
            return ratio <= 1.10
        else:
            return True # Not applicable / 不适用
