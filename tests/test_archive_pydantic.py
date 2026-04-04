"""Tests for Pydantic-based BSRN archive logical records."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from bsrn.archive import (
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
)


def test_lr0001_get_bsrn_format_prefix_and_sensor_row():
    """
    LR0001 ``get_bsrn_format`` matches expected header and default sensor list.
    LR0001 ``get_bsrn_format`` 与预期头行及默认传感器列表一致。
    """
    txt = LR0001(
        stationNumber=94, month=1, year=2024, version=1
    ).get_bsrn_format()
    lines = txt.splitlines()
    assert lines[0] == "*C0001"
    assert lines[1].split()[:4] == ["94", "1", "2024", "1"]
    assert "2" in lines[2] and "23" in lines[2]


def test_lr0001_invalid_month_validation():
    """
    Out-of-range month fails model validation.
    月份越界时模型校验失败。
    """
    with pytest.raises(ValidationError):
        LR0001(stationNumber=1, month=13, year=2020, version=1)


def test_lr0100_get_bsrn_format_january():
    """
    LR0100 emits ``*C0100`` for a full January minute grid.
    LR0100 对整月 1 月分钟网格输出 ``*C0100``。
    """
    n = 31 * 1440
    cols = [
        "ghi_avg",
        "ghi_std",
        "ghi_min",
        "ghi_max",
        "bni_avg",
        "bni_std",
        "bni_min",
        "bni_max",
        "dhi_avg",
        "dhi_std",
        "dhi_min",
        "dhi_max",
        "lwd_avg",
        "lwd_std",
        "lwd_min",
        "lwd_max",
        "temperature",
        "humidity",
        "pressure",
    ]
    kwargs = {"yearMonth": "2024-01"}
    kwargs.update({c: pd.Series(np.zeros(n, dtype=float)) for c in cols})
    rec = LR0100(**kwargs)
    out = rec.get_bsrn_format(changed=True)
    assert out.startswith("*C0100\n")
    assert out.count("\n") == 2 * n


def test_lr0100_wrong_vector_length():
    """
    Mismatched series length vs ``yearMonth`` fails validation.
    序列长度与 ``yearMonth`` 不符时校验失败。
    """
    n = 31 * 1440
    cols = [
        "ghi_avg",
        "ghi_std",
        "ghi_min",
        "ghi_max",
        "bni_avg",
        "bni_std",
        "bni_min",
        "bni_max",
        "dhi_avg",
        "dhi_std",
        "dhi_min",
        "dhi_max",
        "lwd_avg",
        "lwd_std",
        "lwd_min",
        "lwd_max",
        "temperature",
        "humidity",
        "pressure",
    ]
    kwargs = {"yearMonth": "2024-01"}
    kwargs.update({c: pd.Series(np.zeros(n, dtype=float)) for c in cols})
    kwargs["ghi_avg"] = pd.Series(np.zeros(10, dtype=float))
    with pytest.raises(ValidationError):
        LR0100(**kwargs)


def test_lr0002_get_bsrn_format_starts_with_lr0002_marker():
    """
    LR0002 block begins with ``*U0002`` or ``*C0002`` (no scientist/deputy change).
    LR0002 块以 ``*U0002`` 或 ``*C0002`` 开头（无联系人变更）。
    """
    txt = LR0002(
        scientistName="Test Scientist".ljust(38)[:38],
        scientistTel="+86123456789012",
        scientistFax="+86123456789012",
        scientistMail="sci@example.com",
        scientistAddress="Address line for station scientist contact field eighty",
        deputyName="Deputy Scientist".ljust(38)[:38],
        deputyTel="+86123456789012",
        deputyFax="+86123456789012",
        deputyMail="dep@example.com",
        deputyAddress="Address line for deputy scientist contact field eighty",
    ).get_bsrn_format()
    lines = txt.splitlines()
    assert lines[0] in ("*U0002", "*C0002")


def test_lr0004_get_bsrn_format_starts_with_lr0004_marker():
    """
    LR0004 station description block starts with ``*U0004`` or ``*C0004``.
    LR0004 台站描述块以 ``*U0004`` 或 ``*C0004`` 开头。
    """
    rec = LR0004(
        surfaceType=11,
        topographyType=2,
        address="Test station address field padded to eighty characters for A80 spec X",
        telephone="+86123456789012",
        latitude=137.796,
        longitude=304.485,
        altitude=170,
        synop="XXXXX",
        azimuth="0,90,180",
        elevation="0,0,0",
    )
    lines = rec.get_bsrn_format().splitlines()
    assert lines[0] in ("*U0004", "*C0004")


def test_lr0005_get_bsrn_format_starts_with_lr0005_marker():
    """
    LR0005 radiosonde metadata block starts with ``*U0005`` or ``*C0005``.
    LR0005 探空元数据块以 ``*U0005`` 或 ``*C0005`` 开头。
    """
    txt = LR0005(
        operating=False,
        manufacturer="N/A".ljust(30)[:30],
        location="On-site".ljust(25)[:25],
        distanceFromSite=0,
        identification="N/A".ljust(5)[:5],
    ).get_bsrn_format()
    lines = txt.splitlines()
    assert lines[0] in ("*U0005", "*C0005")


def test_lr0006_get_bsrn_format_starts_with_lr0006_marker():
    """
    LR0006 ozone metadata block starts with ``*U0006`` or ``*C0006``.
    LR0006 臭氧元数据块以 ``*U0006`` 或 ``*C0006`` 开头。
    """
    txt = LR0006(
        operating=False,
        manufacturer="N/A".ljust(30)[:30],
        location="On-site".ljust(25)[:25],
        distanceFromSite=0,
        identification="N/A".ljust(5)[:5],
    ).get_bsrn_format()
    lines = txt.splitlines()
    assert lines[0] in ("*U0006", "*C0006")


def test_lr0007_get_bsrn_format_starts_with_lr0007_marker():
    """
    LR0007 block starts with ``*U0007`` or ``*C0007``.
    LR0007 块以 ``*U0007`` 或 ``*C0007`` 开头。
    """
    txt = LR0007().get_bsrn_format()
    lines = txt.splitlines()
    assert lines[0] in ("*U0007", "*C0007")


def test_lr0003_get_bsrn_format_appends_extra_lines():
    """
    LR0003 ``get_bsrn_format`` appends optional blocks (e.g. embedded LR4000CONST text).
    LR0003 在可选附加行后拼接（如内嵌 LR4000CONST 文本）。
    """
    extra = "@LR4000CONST, stub"
    txt = LR0003(message="Station note").get_bsrn_format(extra)
    assert txt.startswith("*U0003\n")
    assert "Station note" in txt
    assert extra in txt


def test_lr4000const_get_bsrn_format_method2_prefix():
    """
    ``LR4000CONST.get_bsrn_format(method=2)`` emits wrapped ``@LR4000CONST`` with CAL id.
    ``method=2`` 时生成带 CAL 证书 id 的折行 ``@LR4000CONST``。
    """
    txt = LR4000CONST(
        serialNumber_Manufacturer="220445",
        serialNumber_WRMC="94004",
        certificateCodeID=None,
        yyyymmdd=20211026,
        manufact="KZ",
        model="CGR4",
        C=13.14,
        k0="ND",
        k1="ND",
        k2=1,
        k3="ND",
        f="ND",
    ).get_bsrn_format(method=2)
    assert "@LR4000CONST" in txt
    assert "CAL_20211026_KZ_CGR4" in txt.replace("\n", "")


def test_lr0008_get_bsrn_format_with_header():
    """
    LR0008 ``printLr=True`` prefixes ``*U0008`` / ``*C0008`` and includes instrument lines.
    ``printLr=True`` 时带 ``*U0008`` 头行及仪器信息行。
    """
    rec = LR0008(
        manufacturer="Kipp & Zonen".ljust(30)[:30],
        model="CMP 22".ljust(15)[:15],
        serialNumber="210763".ljust(18)[:18],
        identification=94001,
        radiationQuantityMeasured=2,
        pyrgeometerDome=2,
        location="Delft, The Netherlands".ljust(30)[:30],
        person="Joop Mes".ljust(40)[:40],
        startOfCalibPeriod1="02/14/22",
        endOfCalibPeriod1="02/14/22",
        numOfComp1=1,
        meanCalibCoeff1=9.41,
        stdErrorCalibCoeff1=0.08,
        remarksOnCalib1="uV/W.m2",
    )
    out = rec.get_bsrn_format(anyChange=False, printLr=True)
    lines = out.splitlines()
    assert lines[0] in ("*U0008", "*C0008")
    assert "Kipp" in out


def test_qiq0125_dat_byte_match_when_reference_present():
    """
    If both pipeline outputs exist, byte-compare to the frozen reference (regression).
    若存在参考与当前输出，则做字节级回归比较。
    """
    out_dir = Path(__file__).resolve().parent / "2025-01" / "Output"
    ref = out_dir / "qiq0125_ref.dat"
    cur = out_dir / "qiq0125.dat"
    if not (ref.is_file() and cur.is_file()):
        pytest.skip("qiq0125_ref.dat and/or qiq0125.dat not in tests/2025-01/Output")
    assert ref.read_bytes() == cur.read_bytes(), (
        "Regenerate qiq0125.dat with tests/2025-01/Code/2.station_to_archive.py "
        "or refresh qiq0125_ref.dat after intentional format changes."
    )
