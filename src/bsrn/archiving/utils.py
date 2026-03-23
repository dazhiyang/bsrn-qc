"""
Calendar helpers for BSRN logical records (mirrors `numberOfDays` / `numberOfMinutes` in `1_utils.R`).
日历辅助函数，对应 R 源码 `1_utils.R` 中的 `numberOfDays` / `numberOfMinutes`。
"""

import calendar


def number_of_days(year_month):
    """
    Days in month for a ``'YYYY-MM'`` token (R ``numberOfDays``).
    返回 ``'YYYY-MM'`` 所在月份的天数（对应 R 的 ``numberOfDays``）。

    Parameters
    ----------
    year_month : str
        Month label, e.g. ``'2024-03'``.
        年月字符串，例如 ``'2024-03'``。
    """
    year, month = map(int, year_month.split("-"))
    return calendar.monthrange(year, month)[1]


def number_of_minutes(year_month):
    """
    Minutes in month (R ``numberOfMinutes``, ``1440 * numberOfDays``).
    当月总分钟数（R ``numberOfMinutes``，即 ``1440 * numberOfDays``）。
    """
    return number_of_days(year_month) * 1440
